import os
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.modules.radicado.models import Radicado
from app.modules.radicado.schemas import RadicadoCreate, RadicadoAnular
from app.modules.radicado.pdf_generator import generar_constancia
from app.modules.admin.models import ConfiguracionSistema, Entidad, Dependencia, Usuario
from app.modules.recepcion.models import Recepcion
from app.modules.remitente.models import MetadatosRecepcion
from app.modules.consulta.service import registrar_evento


# ── Número de radicado ────────────────────────────────────────────────────────

def _siguiente_numero(db: Session) -> str:
    """Genera el número de radicado y actualiza la secuencia de forma atómica."""
    config = db.query(ConfiguracionSistema).first()
    if not config:
        raise HTTPException(status_code=500, detail="Sistema no configurado")

    anio_actual = datetime.now(timezone.utc).year
    # Si cambió el año, reiniciar secuencia
    if config.anio_radicado != anio_actual:
        config.anio_radicado = anio_actual
        config.secuencia_actual = 0

    config.secuencia_actual += 1
    db.flush()  # persistir sin commit para mantener la transacción

    return f"{config.prefijo_radicado}-{anio_actual}-{config.secuencia_actual:05d}"


def _asignar_radicado_inicial(db: Session, recepcion_id: int) -> Radicado:
    """Crea el stub de radicado en el momento de la recepción (estado='pendiente').

    El número queda asignado desde el inicio como referencia de seguimiento.
    La dependencia y el operador se completan cuando el operador finaliza el trámite.
    """
    numero = _siguiente_numero(db)
    radicado = Radicado(
        numero_radicado=numero,
        recepcion_id=recepcion_id,
        dependencia_id=None,
        radicado_por_id=None,
        estado="pendiente",
    )
    db.add(radicado)
    registrar_evento(
        db,
        accion="asignar_numero_radicado",
        modulo="recepciones",
        modulo_id=recepcion_id,
        descripcion=f"Número de seguimiento asignado: {numero}",
    )
    return radicado


# ── CRUD ──────────────────────────────────────────────────────────────────────

def listar_radicados(
    db: Session,
    dependencia_id: int | None = None,
    estado: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    limit: int = 50,
) -> list[Radicado]:
    q = db.query(Radicado)
    if dependencia_id:
        q = q.filter(Radicado.dependencia_id == dependencia_id)
    if estado:
        q = q.filter(Radicado.estado == estado)
    if fecha_desde:
        q = q.filter(Radicado.fecha_radicacion >= fecha_desde)
    if fecha_hasta:
        q = q.filter(Radicado.fecha_radicacion <= fecha_hasta)
    return q.order_by(Radicado.id.desc()).limit(limit).all()


def obtener_radicado(db: Session, radicado_id: int) -> Radicado:
    r = db.get(Radicado, radicado_id)
    if not r:
        raise HTTPException(status_code=404, detail="Radicado no encontrado")
    return r


def obtener_por_numero(db: Session, numero: str) -> Radicado:
    r = db.query(Radicado).filter(Radicado.numero_radicado == numero).first()
    if not r:
        raise HTTPException(status_code=404, detail="Radicado no encontrado")
    return r


def obtener_por_recepcion(db: Session, recepcion_id: int) -> Radicado | None:
    return db.query(Radicado).filter(Radicado.recepcion_id == recepcion_id).first()


def consulta_publica(db: Session, numero: str) -> dict:
    from app.modules.admin.models import Dependencia
    from app.modules.remitente.models import MetadatosRecepcion
    from app.modules.recepcion.models import Recepcion

    r = db.query(Radicado).filter(Radicado.numero_radicado == numero).first()
    if not r:
        raise HTTPException(status_code=404, detail="Número de radicado no encontrado")

    dep = db.get(Dependencia, r.dependencia_id) if r.dependencia_id else None
    metadatos = (
        db.query(MetadatosRecepcion)
        .filter(MetadatosRecepcion.recepcion_id == r.recepcion_id)
        .first()
    )

    asunto = None
    tipo_req = None
    remitente_nombre = None
    if metadatos:
        asunto = metadatos.asunto
        if metadatos.tipo_requerimiento:
            tipo_req = metadatos.tipo_requerimiento.nombre
        if metadatos.remitente:
            remitente_nombre = metadatos.remitente.nombre_completo
    else:
        # Para radicados pendientes sin metadatos aún, usar asunto provisional
        recepcion = db.get(Recepcion, r.recepcion_id)
        if recepcion:
            asunto = recepcion.asunto_provisional

    return {
        "numero_radicado": r.numero_radicado,
        "fecha_radicacion": r.fecha_radicacion,
        "estado": r.estado,
        "dependencia_nombre": dep.nombre if dep else "En proceso",
        "asunto": asunto,
        "tipo_requerimiento": tipo_req,
        "remitente_nombre": remitente_nombre,
        "tiene_constancia": bool(r.ruta_constancia and os.path.exists(r.ruta_constancia)),
    }


def crear_radicado(
    db: Session, data: RadicadoCreate, usuario_id: int
) -> Radicado:
    """Completa el stub de radicado: asigna dependencia, operador, genera PDF.

    El número ya fue asignado al crear la recepción (_asignar_radicado_inicial).
    Si por alguna razón no existe el stub (datos previos a la migración), lo crea.
    """
    recepcion = db.get(Recepcion, data.recepcion_id)
    if not recepcion:
        raise HTTPException(status_code=404, detail="Recepción no encontrada")

    radicado = obtener_por_recepcion(db, data.recepcion_id)
    if radicado and radicado.estado == "radicado":
        raise HTTPException(status_code=400, detail="Esta recepción ya fue radicada")

    metadatos = (
        db.query(MetadatosRecepcion)
        .filter(MetadatosRecepcion.recepcion_id == data.recepcion_id)
        .first()
    )
    if not metadatos:
        raise HTTPException(
            status_code=400,
            detail="Debe registrar el remitente y los metadatos antes de completar el radicado"
        )

    if recepcion.estado != "competente":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Solo se puede completar el radicado de una recepción en estado 'competente'. "
                f"Estado actual: '{recepcion.estado}'. "
                "Cambie el estado a 'Competente' en la pestaña de Información antes de continuar."
            ),
        )

    if radicado:
        # Completar el stub existente
        radicado.dependencia_id  = data.dependencia_id
        radicado.radicado_por_id = usuario_id
        radicado.observaciones   = data.observaciones
        radicado.estado          = "radicado"
        db.flush()
        numero = radicado.numero_radicado
    else:
        # Compatibilidad con recepciones creadas antes de la migración
        numero = _siguiente_numero(db)
        radicado = Radicado(
            numero_radicado=numero,
            recepcion_id=data.recepcion_id,
            dependencia_id=data.dependencia_id,
            radicado_por_id=usuario_id,
            observaciones=data.observaciones,
            estado="radicado",
        )
        db.add(radicado)
        db.flush()

    recepcion.estado = "radicado"

    # Generar PDF
    try:
        ruta_pdf = _generar_pdf(db, radicado, metadatos)
        radicado.ruta_constancia = ruta_pdf
    except Exception:
        pass

    registrar_evento(
        db,
        accion="completar_radicado",
        modulo="radicado",
        modulo_id=radicado.id,
        descripcion=f"Radicado {numero} completado para recepción #{data.recepcion_id}",
        usuario_id=usuario_id,
    )
    registrar_evento(
        db,
        accion="generar_radicado",
        modulo="recepciones",
        modulo_id=data.recepcion_id,
        descripcion=f"Radicado completado: {numero}",
        usuario_id=usuario_id,
    )
    db.commit()
    db.refresh(radicado)
    return radicado


def anular_radicado(
    db: Session, radicado_id: int, data: RadicadoAnular
) -> Radicado:
    radicado = obtener_radicado(db, radicado_id)
    if radicado.estado == "anulado":
        raise HTTPException(status_code=400, detail="El radicado ya está anulado")
    if radicado.estado != "radicado":
        raise HTTPException(status_code=400, detail=f"Estado inesperado: '{radicado.estado}'")
    radicado.estado = "anulado"
    radicado.observaciones = data.observaciones
    registrar_evento(
        db,
        accion="anular_radicado",
        modulo="radicado",
        modulo_id=radicado_id,
        descripcion=f"Radicado {radicado.numero_radicado} anulado. Motivo: {data.observaciones}",
    )
    db.commit()
    db.refresh(radicado)
    return radicado


# ── PDF ───────────────────────────────────────────────────────────────────────

def _generar_pdf(
    db: Session, radicado: Radicado, metadatos: MetadatosRecepcion
) -> str:
    config    = db.query(ConfiguracionSistema).first()
    entidad   = db.query(Entidad).first()
    dep       = db.get(Dependencia, radicado.dependencia_id)
    operador  = db.get(Usuario, radicado.radicado_por_id)
    remitente = metadatos.remitente

    ruta_base = (config.ruta_almacenamiento if config else "../storage") or "../storage"
    ruta_dir  = os.path.join(ruta_base, "constancias")
    ruta_pdf  = os.path.join(ruta_dir, f"{radicado.numero_radicado}.pdf")

    generar_constancia(
        ruta_destino=ruta_pdf,
        numero_radicado=radicado.numero_radicado,
        fecha_radicacion=radicado.fecha_radicacion,
        entidad_nombre=entidad.nombre if entidad else "Entidad Municipal",
        entidad_municipio=entidad.municipio or "" if entidad else "",
        entidad_nit=entidad.nit or "" if entidad else "",
        entidad_email=entidad.email_institucional or "" if entidad else "",
        entidad_telefono=entidad.telefono or "" if entidad else "",
        remitente_nombre=remitente.nombre_completo,
        remitente_id=remitente.numero_identificacion or "",
        remitente_email=remitente.email or "",
        remitente_telefono=remitente.telefono or "",
        asunto=metadatos.asunto,
        tipo_soporte=metadatos.tipo_soporte,
        numero_anexos=metadatos.numero_anexos or 0,
        numero_referencia=metadatos.numero_referencia or "",
        dependencia_nombre=dep.nombre if dep else "",
        operador_nombre=operador.nombre if operador else "",
        observaciones=radicado.observaciones or "",
    )
    return ruta_pdf


def regenerar_pdf(db: Session, radicado_id: int) -> Radicado:
    radicado  = obtener_radicado(db, radicado_id)
    metadatos = (
        db.query(MetadatosRecepcion)
        .filter(MetadatosRecepcion.recepcion_id == radicado.recepcion_id)
        .first()
    )
    if not metadatos:
        raise HTTPException(status_code=400, detail="No hay metadatos para generar la constancia")

    ruta = _generar_pdf(db, radicado, metadatos)
    radicado.ruta_constancia = ruta
    db.commit()
    db.refresh(radicado)
    return radicado
