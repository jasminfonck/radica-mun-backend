import os
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.shared.exceptions import not_found, bad_request
from app.modules.recepcion.models import Recepcion, AdjuntoRecepcion
from app.modules.recepcion.schemas import (
    RecepcionCreate, RecepcionUpdate, ESTADOS_VALIDOS,
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

ESTADOS_REQUIEREN_OBS = {"incompleto", "incompetente"}


def check_rate_limit(ip: str) -> None:
    ahora   = datetime.utcnow()
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
    q = db.query(Recepcion)
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
        recibido_por_id=usuario_id,
        ip_origen=ip,
    )
    db.add(recepcion)
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
    recepcion = obtener_recepcion(db, recepcion_id)

    if data.estado and data.estado not in ESTADOS_VALIDOS:
        bad_request(f"Estado no válido. Use uno de: {', '.join(ESTADOS_VALIDOS)}")

    if data.estado in ESTADOS_REQUIEREN_OBS and not data.observaciones:
        bad_request(
            "Las observaciones son obligatorias al marcar como "
            f"'{data.estado}'. Indique el motivo."
        )

    estado_anterior = recepcion.estado

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


async def guardar_adjunto(db: Session, recepcion_id: int, archivo: UploadFile) -> AdjuntoRecepcion:
    recepcion = obtener_recepcion(db, recepcion_id)

    # Crear carpeta si no existe
    carpeta = os.path.join(settings.STORAGE_PATH, "adjuntos", str(recepcion_id))
    os.makedirs(carpeta, exist_ok=True)

    # Nombre único en disco
    ext = os.path.splitext(archivo.filename or "")[1]
    nombre_disco = f"{uuid.uuid4().hex}{ext}"
    ruta_completa = os.path.join(carpeta, nombre_disco)

    # Guardar archivo
    contenido = await archivo.read()
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
    db.commit()
    db.refresh(adjunto)
    return adjunto


def eliminar_adjunto(db: Session, adjunto_id: int) -> None:
    adjunto = db.query(AdjuntoRecepcion).filter(AdjuntoRecepcion.id == adjunto_id).first()
    if not adjunto:
        not_found("Adjunto")
    if os.path.exists(adjunto.ruta):
        os.remove(adjunto.ruta)
    db.delete(adjunto)
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
            email=data.email,
            telefono=data.telefono,
        )
        db.add(remitente)
        db.flush()

    # Crear metadatos
    metadatos = MetadatosRecepcion(
        recepcion_id=recepcion.id,
        remitente_id=remitente.id,
        asunto=data.asunto,
        tipo_soporte="digital",
        tipo_requerimiento_id=data.tipo_requerimiento_id,
        observaciones=data.observaciones,
    )
    db.add(metadatos)
    db.commit()
    db.refresh(recepcion)

    # Guardar adjuntos si los hay
    archivos_validos = [a for a in adjuntos if a.filename]
    if archivos_validos:
        carpeta = os.path.join(settings.STORAGE_PATH, "adjuntos", str(recepcion.id))
        os.makedirs(carpeta, exist_ok=True)
        for archivo in archivos_validos:
            ext = os.path.splitext(archivo.filename or "")[1]
            nombre_disco = f"{uuid.uuid4().hex}{ext}"
            ruta_completa = os.path.join(carpeta, nombre_disco)
            contenido = await archivo.read()
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
