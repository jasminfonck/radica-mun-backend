import json as _json
import os
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.shared.exceptions import not_found, bad_request
from app.shared.utils import validar_adjunto, tipos_permitidos_set
from app.modules.recepcion.models import Recepcion, AdjuntoRecepcion
from app.modules.recepcion.schemas import (
    RecepcionCreate, RecepcionUpdate, ESTADOS_VALIDOS, TRANSICIONES_VALIDAS,
    FormularioPublicoCreate, FormularioPublicoOut, InfoPublicaOut, TipoReqResumen,
)
from app.modules.admin.models import Canal, Entidad, ConfiguracionSistema, TipoRequerimiento
from app.modules.remitente.models import Remitente, MetadatosRecepcion
from app.shared.email_service import enviar_acuse_recepcion
from app.modules.consulta.service import registrar_evento

# Rate limiting en memoria para el formulario público (5 envíos/hora por IP)
_RATE_STORE: dict[str, list[datetime]] = defaultdict(list)
_RATE_MAX    = 5
_RATE_WINDOW = timedelta(hours=1)

ESTADOS_REQUIEREN_OBS = {"incompleto", "no_competente"}


def check_rate_limit(ip: str) -> None:
    ahora   = datetime.now(timezone.utc)
    ventana = ahora - _RATE_WINDOW
    recientes = [t for t in _RATE_STORE[ip] if t > ventana]
    _RATE_STORE[ip] = recientes
    if len(recientes) >= _RATE_MAX:
        bad_request(
            f"Ha superado el límite de {_RATE_MAX} envíos por hora desde esta dirección. "
            "Intente más tarde."
        )
    _RATE_STORE[ip].append(ahora)


def listar_recepciones(
    db: Session,
    canal_id: Optional[int] = None,
    estado: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> List[Recepcion]:
    q = db.query(Recepcion).filter(Recepcion.estado != "radicado")
    if canal_id:
        q = q.filter(Recepcion.canal_id == canal_id)
    if estado:
        q = q.filter(Recepcion.estado == estado)
    if fecha_desde:
        q = q.filter(Recepcion.created_at >= datetime.fromisoformat(fecha_desde))
    if fecha_hasta:
        q = q.filter(Recepcion.created_at <= datetime.fromisoformat(fecha_hasta))
    return q.order_by(Recepcion.created_at.desc()).all()


def obtener_recepcion(db: Session, recepcion_id: int) -> Recepcion:
    r = db.query(Recepcion).filter(Recepcion.id == recepcion_id).first()
    if not r:
        not_found("Recepción")
    return r


def crear_recepcion(db: Session, data: RecepcionCreate, usuario_id: Optional[int], ip: Optional[str]) -> Recepcion:
    canal = db.query(Canal).filter(Canal.id == data.canal_id, Canal.activo == True).first()
    if not canal:
        bad_request("El canal seleccionado no está activo o no existe")

    recepcion = Recepcion(
        canal_id=data.canal_id,
        asunto_provisional=data.asunto_provisional,
        observaciones=data.observaciones,
        email_remitente=data.email_remitente,
        recibido_por_id=usuario_id,
        ip_origen=ip,
    )
    db.add(recepcion)
    db.flush()

    # Asignar número de radicado como referencia de seguimiento desde el inicio
    from app.modules.radicado.service import _asignar_radicado_inicial
    _asignar_radicado_inicial(db, recepcion.id)

    registrar_evento(
        db,
        accion="crear_recepcion",
        modulo="recepciones",
        modulo_id=recepcion.id,
        descripcion=f"Recepción creada por canal '{canal.nombre}'",
        usuario_id=usuario_id,
        ip=ip,
    )
    db.commit()
    db.refresh(recepcion)
    return recepcion


def actualizar_recepcion(
    db: Session,
    recepcion_id: int,
    data: RecepcionUpdate,
    usuario_id: Optional[int] = None,
    ip: Optional[str] = None,
) -> Recepcion:
    from fastapi import HTTPException
    from app.modules.radicado.models import Radicado

    recepcion = obtener_recepcion(db, recepcion_id)

    if data.estado and data.estado not in ESTADOS_VALIDOS:
        bad_request(f"Estado no válido. Use uno de: {', '.join(ESTADOS_VALIDOS)}")

    if data.estado:
        radicado_existente = db.query(Radicado).filter(Radicado.recepcion_id == recepcion_id).first()
        if radicado_existente and radicado_existente.estado == "radicado":
            raise HTTPException(
                status_code=400,
                detail="No se puede cambiar el estado de una recepción que ya fue radicada",
            )

    estado_anterior = recepcion.estado

    if data.estado and data.estado != estado_anterior:
        permitidos = TRANSICIONES_VALIDAS.get(estado_anterior, set())
        if data.estado not in permitidos:
            bad_request(
                f"Transición no permitida: '{estado_anterior}' → '{data.estado}'. "
                f"Desde '{estado_anterior}' solo se puede pasar a: "
                f"{', '.join(sorted(permitidos)) if permitidos else 'ningún estado (terminal)'}."
            )

    if data.estado in ESTADOS_REQUIEREN_OBS and not data.observaciones:
        bad_request(
            "Las observaciones son obligatorias al marcar como "
            f"'{data.estado}'. Indique el motivo."
        )

    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(recepcion, campo, valor)

    if data.estado and data.estado != estado_anterior:
        registrar_evento(
            db,
            accion="cambio_estado_recepcion",
            entidad="recepciones",
            entidad_id=recepcion_id,
            descripcion=f"Estado: '{estado_anterior}' → '{data.estado}'",
            usuario_id=usuario_id,
            ip=ip,
        )

    db.commit()
    db.refresh(recepcion)
    return recepcion


async def guardar_adjunto(
    db: Session,
    recepcion_id: int,
    archivo: UploadFile,
    fase_creacion: bool = False,
) -> AdjuntoRecepcion:
    from fastapi import HTTPException

    obtener_recepcion(db, recepcion_id)  # valida existencia

    if not fase_creacion:
        raise HTTPException(
            status_code=403,
            detail="No se pueden agregar adjuntos después de creada la recepción. "
                   "Los documentos solo se adjuntan durante el registro inicial.",
        )

    config = db.query(ConfiguracionSistema).first()
    contenido = await archivo.read()

    validar_adjunto(
        mime_type=archivo.content_type or "application/octet-stream",
        tamano_bytes=len(contenido),
        max_tamano_mb=config.max_tamano_adjunto_mb if config else 10,
        tipos_permitidos=config.tipos_archivo_permitidos if config else "",
    )

    adjuntos_actuales = db.query(AdjuntoRecepcion).filter(
        AdjuntoRecepcion.recepcion_id == recepcion_id
    ).count()
    max_adj = config.max_adjuntos if config else 5
    if adjuntos_actuales >= max_adj:
        bad_request(f"Se ha alcanzado el límite máximo de {max_adj} adjuntos por recepción.")

    # Crear carpeta si no existe
    carpeta = os.path.join(settings.STORAGE_PATH, "adjuntos", str(recepcion_id))
    os.makedirs(carpeta, exist_ok=True)

    # Nombre único en disco
    ext = os.path.splitext(archivo.filename or "")[1]
    nombre_disco = f"{uuid.uuid4().hex}{ext}"
    ruta_completa = os.path.join(carpeta, nombre_disco)

    with open(ruta_completa, "wb") as f:
        f.write(contenido)

    adjunto = AdjuntoRecepcion(
        recepcion_id=recepcion_id,
        nombre_original=archivo.filename or nombre_disco,
        nombre_archivo=nombre_disco,
        ruta=ruta_completa,
        tipo_mime=archivo.content_type,
        tamano_bytes=len(contenido),
    )
    db.add(adjunto)
    registrar_evento(
        db,
        accion="subir_adjunto",
        modulo="recepciones",
        modulo_id=recepcion_id,
        descripcion=f"Adjunto '{archivo.filename}' subido a recepción #{recepcion_id}",
        usuario_id=None,
        ip=None,
    )
    db.commit()
    db.refresh(adjunto)
    return adjunto


def descargar_adjunto(db: Session, adjunto_id: int) -> FileResponse:
    adjunto = db.query(AdjuntoRecepcion).filter(AdjuntoRecepcion.id == adjunto_id).first()
    if not adjunto:
        not_found("Adjunto")
    if not os.path.exists(adjunto.ruta):
        bad_request("El archivo no está disponible en el servidor")
    return FileResponse(
        path=adjunto.ruta,
        filename=adjunto.nombre_original,
        media_type=adjunto.tipo_mime or "application/octet-stream",
    )


def eliminar_adjunto(db: Session, adjunto_id: int) -> None:
    adjunto = db.query(AdjuntoRecepcion).filter(AdjuntoRecepcion.id == adjunto_id).first()
    if not adjunto:
        not_found("Adjunto")
    if os.path.exists(adjunto.ruta):
        os.remove(adjunto.ruta)
    recepcion_id = adjunto.recepcion_id
    nombre_original = adjunto.nombre_original
    db.delete(adjunto)
    registrar_evento(
        db,
        accion="eliminar_adjunto",
        modulo="recepciones",
        modulo_id=recepcion_id,
        descripcion=f"Adjunto '{nombre_original}' eliminado de recepción #{recepcion_id}",
        usuario_id=None,
        ip=None,
    )
    db.commit()


# ── Formulario web público ────────────────────────────────────────────────────

def get_info_publica(db: Session) -> InfoPublicaOut:
    entidad = db.query(Entidad).first()
    config = db.query(ConfiguracionSistema).first()
    canal = db.query(Canal).filter(Canal.tipo == "digital", Canal.activo == True).first()
    tipos = db.query(TipoRequerimiento).filter(TipoRequerimiento.activo == True).order_by(TipoRequerimiento.nombre).all()

    return InfoPublicaOut(
        entidad_nombre=entidad.nombre if entidad else "Entidad Municipal",
        entidad_municipio=entidad.municipio if entidad else None,
        entidad_departamento=entidad.departamento if entidad else None,
        entidad_telefono=entidad.telefono if entidad else None,
        entidad_email=entidad.email_institucional if entidad else None,
        color_primario=config.color_primario if config else "#1a237e",
        canal_id=canal.id if canal else None,
        canal_activo=canal is not None,
        tipos_requerimiento=[TipoReqResumen.model_validate(t) for t in tipos],
        politica_privacidad_activa=config.politica_privacidad_activa if config else False,
        politica_privacidad_texto=config.politica_privacidad_texto if config else None,
        max_adjuntos=config.max_adjuntos if config else 5,
        max_tamano_adjunto_mb=config.max_tamano_adjunto_mb if config else 10,
        tipos_archivo_permitidos=list(tipos_permitidos_set(config.tipos_archivo_permitidos)) if config else [],
    )


async def crear_desde_formulario(
    db: Session,
    data: FormularioPublicoCreate,
    ip: Optional[str],
    adjuntos: List[UploadFile] = [],
) -> FormularioPublicoOut:
    config = db.query(ConfiguracionSistema).first()
    if config and config.politica_privacidad_activa and not data.acepta_politica:
        bad_request("Debe aceptar la política de privacidad para continuar")

    canal = db.query(Canal).filter(Canal.tipo == "digital", Canal.activo == True).first()
    if not canal:
        bad_request("El canal de formulario web no está activo. Contacte a la entidad.")

    # Crear recepción
    recepcion = Recepcion(
        canal_id=canal.id,
        asunto_provisional=data.asunto[:300],
        observaciones=data.observaciones,
        ip_origen=ip,
    )
    db.add(recepcion)
    db.flush()

    # Buscar o crear remitente
    remitente = None
    if data.numero_identificacion:
        remitente = (
            db.query(Remitente)
            .filter(Remitente.numero_identificacion == data.numero_identificacion)
            .first()
        )

    if not remitente:
        remitente = Remitente(
            tipo_persona=data.tipo_persona,
            nombres=data.nombres,
            apellidos=data.apellidos,
            razon_social=data.razon_social,
            tipo_identificacion=data.tipo_identificacion,
            numero_identificacion=data.numero_identificacion,
            nit=data.numero_identificacion if data.tipo_identificacion == "NIT" else None,
            digito_verificacion=data.digito_verificacion,
            email=data.email,
            telefono=data.telefono,
        )
        db.add(remitente)
        db.flush()

    # Determinar campos que provienen del formulario y no deben editarse manualmente
    bloqueados = ["asunto", "remitente_id", "tipo_soporte"]
    if data.tipo_requerimiento_id:
        bloqueados.append("tipo_requerimiento_id")

    # Crear metadatos
    metadatos = MetadatosRecepcion(
        recepcion_id=recepcion.id,
        remitente_id=remitente.id,
        asunto=data.asunto,
        tipo_soporte="digital",
        tipo_requerimiento_id=data.tipo_requerimiento_id,
        observaciones=data.observaciones,
        campos_bloqueados=_json.dumps(bloqueados),
    )
    db.add(metadatos)
    db.flush()

    # Asignar número de radicado como referencia de seguimiento desde el inicio
    from app.modules.radicado.service import _asignar_radicado_inicial
    _asignar_radicado_inicial(db, recepcion.id)

    db.commit()
    db.refresh(recepcion)

    # Guardar adjuntos si los hay
    archivos_validos = [a for a in adjuntos if a.filename]
    if archivos_validos:
        max_adj = config.max_adjuntos if config else 5
        if len(archivos_validos) > max_adj:
            bad_request(f"Se permiten máximo {max_adj} adjuntos por envío.")

        carpeta = os.path.join(settings.STORAGE_PATH, "adjuntos", str(recepcion.id))
        os.makedirs(carpeta, exist_ok=True)
        for archivo in archivos_validos:
            contenido = await archivo.read()
            validar_adjunto(
                mime_type=archivo.content_type or "application/octet-stream",
                tamano_bytes=len(contenido),
                max_tamano_mb=config.max_tamano_adjunto_mb if config else 10,
                tipos_permitidos=config.tipos_archivo_permitidos if config else "",
            )
            ext = os.path.splitext(archivo.filename or "")[1]
            nombre_disco = f"{uuid.uuid4().hex}{ext}"
            ruta_completa = os.path.join(carpeta, nombre_disco)
            with open(ruta_completa, "wb") as f:
                f.write(contenido)
            db.add(AdjuntoRecepcion(
                recepcion_id=recepcion.id,
                nombre_original=archivo.filename or nombre_disco,
                nombre_archivo=nombre_disco,
                ruta=ruta_completa,
                tipo_mime=archivo.content_type,
                tamano_bytes=len(contenido),
            ))
        db.commit()

    acuse_enviado = False
    if data.email:
        entidad = db.query(Entidad).first()
        acuse_enviado = enviar_acuse_recepcion(
            destinatario=data.email,
            asunto=data.asunto,
            entidad_nombre=entidad.nombre if entidad else "la entidad",
        )

    return FormularioPublicoOut(acuse_enviado=acuse_enviado)


# ── Notificación de adjuntos rechazados ────────────────────────────────────────

_MIME_LABEL: dict[str, str] = {
    "application/pdf": "PDF",
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/gif": "GIF",
    "application/msword": "Word",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word",
    "application/vnd.ms-excel": "Excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel",
    "text/plain": "TXT",
    "application/rtf": "RTF",
    "application/zip": "ZIP",
}


def notificar_adjuntos(
    db: Session,
    recepcion_id: int,
    usuario_id: Optional[int] = None,
    ip: Optional[str] = None,
) -> bool:
    from app.shared.email_service import enviar_aviso_adjuntos

    recepcion = obtener_recepcion(db, recepcion_id)

    if not recepcion.aviso_adjuntos:
        bad_request("Esta recepción no tiene avisos de adjuntos pendientes.")

    if not recepcion.email_remitente:
        bad_request("Esta recepción no tiene correo electrónico del remitente. No se puede enviar el aviso.")

    config = db.query(ConfiguracionSistema).first()
    entidad = db.query(Entidad).first()

    max_adj = config.max_adjuntos if config else 5
    max_mb  = config.max_tamano_adjunto_mb if config else 10
    tipos_raw = config.tipos_archivo_permitidos if config else ""
    tipos_set = tipos_permitidos_set(tipos_raw)

    seen: set[str] = set()
    tipos_legibles: list[str] = []
    for mime in tipos_set:
        label = _MIME_LABEL.get(mime, mime)
        if label not in seen:
            seen.add(label)
            tipos_legibles.append(label)

    avisos = [a.strip() for a in recepcion.aviso_adjuntos.split("\n") if a.strip()]

    enviado = enviar_aviso_adjuntos(
        destinatario=recepcion.email_remitente,
        asunto_recepcion=recepcion.asunto_provisional or "(sin asunto)",
        entidad_nombre=entidad.nombre if entidad else "la entidad",
        avisos=avisos,
        max_adjuntos=max_adj,
        max_mb=max_mb,
        tipos_legibles=tipos_legibles,
    )

    if enviado:
        recepcion.aviso_adjuntos = None
        registrar_evento(
            db,
            accion="notificar_adjuntos",
            modulo="recepciones",
            modulo_id=recepcion_id,
            descripcion=f"Aviso de adjuntos rechazados enviado a {recepcion.email_remitente}",
            usuario_id=usuario_id,
            ip=ip,
        )
        db.commit()

    return enviado
