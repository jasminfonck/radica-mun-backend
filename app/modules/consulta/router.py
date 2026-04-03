from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.dependencies import get_db, get_current_user, require_rol
from app.modules.consulta import service
from app.modules.consulta.schemas import (
    ConsultaPublicaOut, ResultadoBusqueda,
    EstadisticasOut, LogAuditoriaOut,
)

router = APIRouter(tags=["Consulta"])


# ── Pública (sin auth) ────────────────────────────────────────────────────────

@router.get("/consulta/publica/{numero_radicado}", response_model=ConsultaPublicaOut)
def consulta_publica(numero_radicado: str, db: Session = Depends(get_db)):
    """Consulta ciudadana: estado de un radicado por su número (sin autenticación)."""
    return service.consulta_publica(db, numero_radicado)


# ── Búsqueda interna ──────────────────────────────────────────────────────────

@router.get("/consulta/buscar", response_model=List[ResultadoBusqueda])
def buscar(
    q:               Optional[str] = Query(None, description="Asunto, remitente o identificación"),
    numero_radicado: Optional[str] = Query(None),
    dependencia_id:  Optional[int] = Query(None),
    estado_radicado: Optional[str] = Query(None),
    fecha_desde:     Optional[str] = Query(None),
    fecha_hasta:     Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.buscar(
        db, q, numero_radicado, dependencia_id,
        estado_radicado, fecha_desde, fecha_hasta,
    )


# ── Estadísticas ──────────────────────────────────────────────────────────────

@router.get("/consulta/estadisticas", response_model=EstadisticasOut)
def estadisticas(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.estadisticas(db)


# ── Auditoría ─────────────────────────────────────────────────────────────────

@router.get("/auditoria", response_model=List[LogAuditoriaOut])
def log_auditoria(
    accion:      Optional[str] = Query(None),
    usuario_id:  Optional[int] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_rol("administrador")),
):
    return service.listar_log(db, accion, usuario_id, fecha_desde, fecha_hasta)
