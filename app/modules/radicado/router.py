from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from app.core.dependencies import get_db, get_current_user, require_rol
from app.modules.admin.models import Usuario
from app.modules.radicado import service
from app.modules.radicado.schemas import (
    RadicadoCreate, RadicadoAnular, RadicadoOut, RadicadoResumen,
)

router = APIRouter(prefix="/radicado", tags=["Radicado"])

solo_admin_operador = Depends(require_rol("administrador", "operador"))


@router.get("", response_model=List[RadicadoResumen])
def listar(
    dependencia_id: Optional[int] = Query(None),
    estado:         Optional[str] = Query(None),
    fecha_desde:    Optional[str] = Query(None),
    fecha_hasta:    Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.listar_radicados(db, dependencia_id, estado, fecha_desde, fecha_hasta)


@router.get("/numero/{numero}", response_model=RadicadoOut)
def obtener_por_numero(
    numero: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.obtener_por_numero(db, numero)


@router.get("/recepcion/{recepcion_id}", response_model=Optional[RadicadoOut])
def obtener_por_recepcion(
    recepcion_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.obtener_por_recepcion(db, recepcion_id)


@router.get("/{radicado_id}", response_model=RadicadoOut)
def obtener(
    radicado_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.obtener_radicado(db, radicado_id)


@router.post("", response_model=RadicadoOut, status_code=201)
def crear(
    data: RadicadoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_rol("administrador", "operador")),
):
    return service.crear_radicado(db, data, current_user.id)


@router.put("/{radicado_id}/anular", response_model=RadicadoOut)
def anular(
    radicado_id: int,
    data: RadicadoAnular,
    db: Session = Depends(get_db),
    _=Depends(require_rol("administrador")),
):
    return service.anular_radicado(db, radicado_id, data)


@router.post("/{radicado_id}/constancia/regenerar", response_model=RadicadoOut)
def regenerar_pdf(
    radicado_id: int,
    db: Session = Depends(get_db),
    _=solo_admin_operador,
):
    return service.regenerar_pdf(db, radicado_id)


@router.get("/{radicado_id}/constancia/descargar")
def descargar_constancia(
    radicado_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    radicado = service.obtener_radicado(db, radicado_id)
    if not radicado.ruta_constancia or not os.path.exists(radicado.ruta_constancia):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Constancia no disponible")

    return FileResponse(
        path=radicado.ruta_constancia,
        media_type="application/pdf",
        filename=f"constancia_{radicado.numero_radicado}.pdf",
    )
