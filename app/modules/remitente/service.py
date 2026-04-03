from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from fastapi import HTTPException, status
from typing import Optional, List

from app.modules.remitente.models import Remitente, MetadatosRecepcion
from app.modules.remitente.schemas import (
    RemitenteCreate, RemitenteUpdate,
    MetadatosCreate, MetadatosUpdate,
)


# ── Remitente ─────────────────────────────────────────────────────────────────

def buscar_remitentes(
    db: Session,
    q: Optional[str] = None,
    tipo_persona: Optional[str] = None,
    solo_activos: bool = True,
    limit: int = 20,
) -> List[Remitente]:
    query = db.query(Remitente)
    if solo_activos:
        query = query.filter(Remitente.activo == True)  # noqa: E712
    if tipo_persona:
        query = query.filter(Remitente.tipo_persona == tipo_persona)
    if q:
        termino = f"%{q}%"
        query = query.filter(
            or_(
                Remitente.nombres.ilike(termino),
                Remitente.apellidos.ilike(termino),
                Remitente.razon_social.ilike(termino),
                Remitente.numero_identificacion.ilike(termino),
                Remitente.email.ilike(termino),
            )
        )
    return query.order_by(Remitente.id.desc()).limit(limit).all()


def detectar_duplicados(db: Session, data: RemitenteCreate) -> List[Remitente]:
    """Retorna remitentes existentes que coinciden por número de identificación o email."""
    condiciones = []

    if data.numero_identificacion:
        condiciones.append(
            Remitente.numero_identificacion == data.numero_identificacion
        )
    if data.email:
        condiciones.append(
            func.lower(Remitente.email) == data.email.lower()
        )

    if not condiciones:
        return []

    return (
        db.query(Remitente)
        .filter(Remitente.activo == True, or_(*condiciones))  # noqa: E712
        .all()
    )


def obtener_remitente(db: Session, remitente_id: int) -> Remitente:
    r = db.get(Remitente, remitente_id)
    if not r:
        raise HTTPException(status_code=404, detail="Remitente no encontrado")
    return r


def crear_remitente(db: Session, data: RemitenteCreate) -> Remitente:
    remitente = Remitente(**data.model_dump())
    db.add(remitente)
    db.commit()
    db.refresh(remitente)
    return remitente


def actualizar_remitente(
    db: Session, remitente_id: int, data: RemitenteUpdate
) -> Remitente:
    remitente = obtener_remitente(db, remitente_id)
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(remitente, campo, valor)
    db.commit()
    db.refresh(remitente)
    return remitente


# ── MetadatosRecepcion ────────────────────────────────────────────────────────

def obtener_metadatos(db: Session, recepcion_id: int) -> Optional[MetadatosRecepcion]:
    return (
        db.query(MetadatosRecepcion)
        .filter(MetadatosRecepcion.recepcion_id == recepcion_id)
        .first()
    )


def crear_o_actualizar_metadatos(
    db: Session, recepcion_id: int, data: MetadatosCreate
) -> MetadatosRecepcion:
    # Verificar que el remitente existe
    if not db.get(Remitente, data.remitente_id):
        raise HTTPException(status_code=404, detail="Remitente no encontrado")

    existente = obtener_metadatos(db, recepcion_id)

    if existente:
        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(existente, campo, valor)
        db.commit()
        db.refresh(existente)
        return existente

    metadatos = MetadatosRecepcion(recepcion_id=recepcion_id, **data.model_dump())
    db.add(metadatos)
    db.commit()
    db.refresh(metadatos)
    return metadatos


def actualizar_metadatos(
    db: Session, metadatos_id: int, data: MetadatosUpdate
) -> MetadatosRecepcion:
    m = db.get(MetadatosRecepcion, metadatos_id)
    if not m:
        raise HTTPException(status_code=404, detail="Metadatos no encontrados")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(m, campo, valor)
    db.commit()
    db.refresh(m)
    return m
