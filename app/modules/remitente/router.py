from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.dependencies import get_db, get_current_user
from app.modules.remitente import service
from app.modules.remitente.schemas import (
    RemitenteCreate, RemitenteUpdate, RemitenteOut, RemitenteResumen,
    MetadatosCreate, MetadatosUpdate, MetadatosOut,
)

router = APIRouter(prefix="/remitente", tags=["Remitente"])


# ── Remitente ─────────────────────────────────────────────────────────────────

@router.get("", response_model=List[RemitenteResumen])
def buscar(
    q:            Optional[str] = Query(None, description="Nombre, identificación o email"),
    tipo_persona: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.buscar_remitentes(db, q=q, tipo_persona=tipo_persona)


@router.get("/duplicados", response_model=List[RemitenteResumen])
def duplicados(
    numero_identificacion: Optional[str] = Query(None),
    email:                 Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """Verifica si ya existe un remitente con la misma identificación o email."""
    from app.modules.remitente.schemas import RemitenteCreate
    data = RemitenteCreate(
        numero_identificacion=numero_identificacion,
        email=email,
    )
    return service.detectar_duplicados(db, data)


@router.get("/{remitente_id}", response_model=RemitenteOut)
def obtener(
    remitente_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.obtener_remitente(db, remitente_id)


@router.post("", response_model=RemitenteOut, status_code=201)
def crear(
    data: RemitenteCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.crear_remitente(db, data)


@router.put("/{remitente_id}", response_model=RemitenteOut)
def actualizar(
    remitente_id: int,
    data: RemitenteUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.actualizar_remitente(db, remitente_id, data)


# ── Metadatos de Recepción ────────────────────────────────────────────────────

@router.get("/metadatos/{recepcion_id}", response_model=Optional[MetadatosOut])
def obtener_metadatos(
    recepcion_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.obtener_metadatos(db, recepcion_id)


@router.post("/metadatos/{recepcion_id}", response_model=MetadatosOut, status_code=201)
def guardar_metadatos(
    recepcion_id: int,
    data: MetadatosCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.crear_o_actualizar_metadatos(db, recepcion_id, data)


@router.put("/metadatos/{metadatos_id}", response_model=MetadatosOut)
def actualizar_metadatos(
    metadatos_id: int,
    data: MetadatosUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.actualizar_metadatos(db, metadatos_id, data)
