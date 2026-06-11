from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import io

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


@router.get("/consulta/publica/{numero_radicado}/constancia")
def descargar_constancia_publica(numero_radicado: str, db: Session = Depends(get_db)):
    """Descarga la constancia PDF de un radicado sin autenticación (acceso por número)."""
    ruta = service.get_constancia_path(db, numero_radicado)
    return FileResponse(
        path=ruta,
        media_type="application/pdf",
        filename=f"constancia_{numero_radicado.upper()}.pdf",
    )


# ── Búsqueda interna ──────────────────────────────────────────────────────────

@router.get("/consulta/buscar", response_model=List[ResultadoBusqueda])
def buscar(
    q:               Optional[str] = Query(None, description="Asunto, remitente o identificación"),
    numero_radicado: Optional[str] = Query(None),
    canal_id:        Optional[int] = Query(None),
    dependencia_id:  Optional[int] = Query(None),
    estado_radicado: Optional[str] = Query(None),
    fecha_desde:     Optional[str] = Query(None),
    fecha_hasta:     Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.buscar(
        db, q, numero_radicado, canal_id, dependencia_id,
        estado_radicado, fecha_desde, fecha_hasta,
    )


@router.get("/consulta/exportar")
def exportar_csv(
    q:               Optional[str] = Query(None),
    numero_radicado: Optional[str] = Query(None),
    canal_id:        Optional[int] = Query(None),
    dependencia_id:  Optional[int] = Query(None),
    estado_radicado: Optional[str] = Query(None),
    fecha_desde:     Optional[str] = Query(None),
    fecha_hasta:     Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """Exporta los radicados filtrados como archivo CSV descargable."""
    contenido = service.exportar_csv(
        db, q, numero_radicado, canal_id, dependencia_id,
        estado_radicado, fecha_desde, fecha_hasta,
    )
    from datetime import datetime
    nombre = f"radicados_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return StreamingResponse(
        io.StringIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={nombre}"},
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
    modulo:      Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_rol("administrador")),
):
    return service.listar_log(db, accion, usuario_id, fecha_desde, fecha_hasta, modulo)
