import os
from datetime import datetime
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

    anio_actual = datetime.utcnow().year
    # Si cambió el año, reiniciar secuencia
    if config.anio_radicado != anio_actual:
        config.anio_radicado = anio_actual
        config.secuencia_actual = 0

    config.secuencia_actual += 1
    db.flush()  # persistir sin commit para mantener la transacción

    return f"{config.prefijo_radicado}-{anio_actual}-{config.secuencia_actual:05d}"


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


def crear_radicado(
    db: Session, data: RadicadoCreate, usuario_id: int
) -> Radicado:
    # Verificar que la recepción existe y no tiene radicado
    recepcion = db.get(Recepcion, data.recepcion_id)
    if not recepcion:
        raise HTTPException(status_code=404, detail="Recepción no encontrada")

    if obtener_por_recepcion(db, data.recepcion_id):
        raise HTTPException(
            status_code=400,
            detail="Esta recepción ya fue radicada"
        )

    # Verificar que tiene metadatos (remitente)
    metadatos = (
        db.query(MetadatosRecepcion)
        .filter(MetadatosRecepcion.recepcion_id == data.recepcion_id)
        .first()
    )
    if not metadatos:
        raise HTTPException(
            status_code=400,
            detail="Debe registrar el remitente y los metadatos antes de radicar"
        )

    # Generar número
    numero = _siguiente_numero(db)

    radicado = Radicado(
        numero_radicado=numero,
        recepcion_id=data.recepcion_id,
        dependencia_id=data.dependencia_id,
        radicado_por_id=usuario_id,
        observaciones=data.observaciones,
    )
    db.add(radicado)
    db.flush()

    # Generar PDF
    try:
        ruta_pdf = _generar_pdf(db, radicado, metadatos)
        radicado.ruta_constancia = ruta_pdf
    except Exception:
        # PDF falla silencioso — el radicado se crea igual
        pass

    registrar_evento(
        db,
        accion="crear_radicado",
        entidad="radicado",
        entidad_id=radicado.id,
        descripcion=f"Radicado {numero} generado para recepción #{data.recepcion_id}",
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
    radicado.estado = "anulado"
    radicado.observaciones = data.observaciones
    registrar_evento(
        db,
        accion="anular_radicado",
        entidad="radicado",
        entidad_id=radicado_id,
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
