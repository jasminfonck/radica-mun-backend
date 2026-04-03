import os
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.shared.exceptions import not_found, bad_request
from app.modules.recepcion.models import Recepcion, AdjuntoRecepcion
from app.modules.recepcion.schemas import RecepcionCreate, RecepcionUpdate, ESTADOS_VALIDOS
from app.modules.admin.models import Canal


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


def actualizar_recepcion(db: Session, recepcion_id: int, data: RecepcionUpdate) -> Recepcion:
    recepcion = obtener_recepcion(db, recepcion_id)
    if data.estado and data.estado not in ESTADOS_VALIDOS:
        bad_request(f"Estado no válido. Use uno de: {', '.join(ESTADOS_VALIDOS)}")
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(recepcion, campo, valor)
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
