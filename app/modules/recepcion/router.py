from fastapi import APIRouter, Depends, UploadFile, File, Request, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.dependencies import get_db, get_current_user, require_rol
from app.modules.admin.models import Usuario
from app.modules.recepcion import service
from app.modules.recepcion.schemas import (
    RecepcionCreate, RecepcionUpdate, RecepcionOut, AdjuntoOut
)

router = APIRouter(prefix="/recepcion", tags=["Recepción"])


@router.get("", response_model=List[RecepcionOut])
def listar(
    canal_id:    Optional[int] = Query(None),
    estado:      Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.listar_recepciones(db, canal_id, estado, fecha_desde, fecha_hasta)


@router.get("/{recepcion_id}", response_model=RecepcionOut)
def obtener(recepcion_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.obtener_recepcion(db, recepcion_id)


@router.post("", response_model=RecepcionOut)
def crear(
    data: RecepcionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    ip = request.client.host if request.client else None
    return service.crear_recepcion(db, data, current_user.id, ip)


# Endpoint público para formulario web (ciudadano sin autenticación)
@router.post("/publica", response_model=RecepcionOut)
def crear_publica(data: RecepcionCreate, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else None
    return service.crear_recepcion(db, data, usuario_id=None, ip=ip)


@router.put("/{recepcion_id}", response_model=RecepcionOut)
def actualizar(
    recepcion_id: int,
    data: RecepcionUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.actualizar_recepcion(db, recepcion_id, data)


@router.post("/{recepcion_id}/adjuntos", response_model=AdjuntoOut)
async def subir_adjunto(
    recepcion_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return await service.guardar_adjunto(db, recepcion_id, archivo)


@router.delete("/{recepcion_id}/adjuntos/{adjunto_id}", status_code=204)
def eliminar_adjunto(
    recepcion_id: int,
    adjunto_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_rol("administrador", "operador")),
):
    service.eliminar_adjunto(db, adjunto_id)
