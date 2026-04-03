from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Optional
from datetime import datetime

from app.modules.consulta.models import LogAuditoria
from app.modules.consulta.schemas import (
    ConsultaPublicaOut, ResultadoBusqueda,
    EstadisticasOut, ItemConteo,
)
from app.modules.radicado.models  import Radicado
from app.modules.recepcion.models import Recepcion
from app.modules.remitente.models import MetadatosRecepcion, Remitente
from app.modules.admin.models     import Dependencia, Canal, TipoRequerimiento


# ── Auditoría ─────────────────────────────────────────────────────────────────

def registrar_evento(
    db: Session,
    accion: str,
    entidad: Optional[str] = None,
    entidad_id: Optional[int] = None,
    descripcion: Optional[str] = None,
    usuario_id: Optional[int] = None,
    ip: Optional[str] = None,
) -> None:
    evento = LogAuditoria(
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        descripcion=descripcion,
        usuario_id=usuario_id,
        ip=ip,
    )
    db.add(evento)
    # No hacer commit aquí — se incluye en la transacción del llamador


def listar_log(
    db: Session,
    accion: Optional[str] = None,
    usuario_id: Optional[int] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 100,
) -> list[LogAuditoria]:
    q = db.query(LogAuditoria).order_by(LogAuditoria.created_at.desc())
    if accion:
        q = q.filter(LogAuditoria.accion == accion)
    if usuario_id:
        q = q.filter(LogAuditoria.usuario_id == usuario_id)
    if fecha_desde:
        q = q.filter(LogAuditoria.created_at >= fecha_desde)
    if fecha_hasta:
        q = q.filter(LogAuditoria.created_at <= fecha_hasta)
    return q.limit(limit).all()


# ── Consulta pública ──────────────────────────────────────────────────────────

def consulta_publica(db: Session, numero_radicado: str) -> ConsultaPublicaOut:
    radicado = (
        db.query(Radicado)
        .filter(Radicado.numero_radicado == numero_radicado.upper())
        .first()
    )
    if not radicado:
        raise HTTPException(status_code=404, detail="Número de radicado no encontrado")

    recepcion = db.get(Recepcion, radicado.recepcion_id)
    metadatos = (
        db.query(MetadatosRecepcion)
        .filter(MetadatosRecepcion.recepcion_id == radicado.recepcion_id)
        .first()
    )
    dependencia = db.get(Dependencia, radicado.dependencia_id)

    return ConsultaPublicaOut(
        numero_radicado=radicado.numero_radicado,
        fecha_radicacion=radicado.fecha_radicacion,
        asunto=metadatos.asunto if metadatos else "—",
        dependencia=dependencia.nombre if dependencia else "—",
        estado_radicado=radicado.estado,
        estado_recepcion=recepcion.estado if recepcion else "—",
        tipo_soporte=metadatos.tipo_soporte if metadatos else "—",
        remitente=metadatos.remitente.nombre_completo if metadatos and metadatos.remitente else "—",
    )


# ── Búsqueda interna ──────────────────────────────────────────────────────────

def buscar(
    db: Session,
    q: Optional[str] = None,
    numero_radicado: Optional[str] = None,
    dependencia_id: Optional[int] = None,
    estado_radicado: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 50,
) -> list[ResultadoBusqueda]:
    query = (
        db.query(
            Radicado, MetadatosRecepcion, Recepcion, Dependencia
        )
        .join(Recepcion, Radicado.recepcion_id == Recepcion.id)
        .outerjoin(
            MetadatosRecepcion,
            MetadatosRecepcion.recepcion_id == Radicado.recepcion_id,
        )
        .outerjoin(Dependencia, Radicado.dependencia_id == Dependencia.id)
    )

    if numero_radicado:
        query = query.filter(
            Radicado.numero_radicado.ilike(f"%{numero_radicado}%")
        )
    if dependencia_id:
        query = query.filter(Radicado.dependencia_id == dependencia_id)
    if estado_radicado:
        query = query.filter(Radicado.estado == estado_radicado)
    if fecha_desde:
        query = query.filter(Radicado.fecha_radicacion >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Radicado.fecha_radicacion <= fecha_hasta)

    if q:
        termino = f"%{q}%"
        query = query.outerjoin(
            Remitente,
            MetadatosRecepcion.remitente_id == Remitente.id,
        ).filter(
            or_(
                MetadatosRecepcion.asunto.ilike(termino),
                Remitente.nombres.ilike(termino),
                Remitente.apellidos.ilike(termino),
                Remitente.razon_social.ilike(termino),
                Remitente.numero_identificacion.ilike(termino),
            )
        )

    rows = query.order_by(Radicado.id.desc()).limit(limit).all()

    results = []
    for radicado, metadatos, recepcion, dep in rows:
        results.append(ResultadoBusqueda(
            radicado_id=radicado.id,
            numero_radicado=radicado.numero_radicado,
            recepcion_id=radicado.recepcion_id,
            fecha_radicacion=radicado.fecha_radicacion,
            asunto=metadatos.asunto if metadatos else "—",
            remitente=metadatos.remitente.nombre_completo if metadatos and metadatos.remitente else "—",
            dependencia=dep.nombre if dep else "—",
            estado_radicado=radicado.estado,
            estado_recepcion=recepcion.estado if recepcion else "—",
        ))
    return results


# ── Estadísticas ──────────────────────────────────────────────────────────────

def estadisticas(db: Session) -> EstadisticasOut:
    total_recepciones = db.query(func.count(Recepcion.id)).scalar() or 0
    total_radicados   = db.query(func.count(Radicado.id)).scalar() or 0
    vigentes  = db.query(func.count(Radicado.id)).filter(Radicado.estado == "vigente").scalar() or 0
    anulados  = db.query(func.count(Radicado.id)).filter(Radicado.estado == "anulado").scalar() or 0

    # Por dependencia
    por_dep = (
        db.query(Dependencia.nombre, func.count(Radicado.id))
        .join(Radicado, Radicado.dependencia_id == Dependencia.id)
        .group_by(Dependencia.nombre)
        .order_by(func.count(Radicado.id).desc())
        .all()
    )

    # Por canal
    por_canal = (
        db.query(Canal.nombre, func.count(Recepcion.id))
        .join(Recepcion, Recepcion.canal_id == Canal.id)
        .group_by(Canal.nombre)
        .order_by(func.count(Recepcion.id).desc())
        .all()
    )

    # Por mes (últimos 12 meses de radicados)
    por_mes_raw = (
        db.query(
            func.to_char(Radicado.fecha_radicacion, "YYYY-MM").label("mes"),
            func.count(Radicado.id),
        )
        .group_by("mes")
        .order_by("mes")
        .limit(12)
        .all()
    )

    # Por tipo de requerimiento
    por_tipo = (
        db.query(TipoRequerimiento.nombre, func.count(MetadatosRecepcion.id))
        .join(
            MetadatosRecepcion,
            MetadatosRecepcion.tipo_requerimiento_id == TipoRequerimiento.id,
        )
        .group_by(TipoRequerimiento.nombre)
        .order_by(func.count(MetadatosRecepcion.id).desc())
        .all()
    )

    return EstadisticasOut(
        total_recepciones=total_recepciones,
        total_radicados=total_radicados,
        radicados_vigentes=vigentes,
        radicados_anulados=anulados,
        por_dependencia=[ItemConteo(label=n, total=t) for n, t in por_dep],
        por_canal=[ItemConteo(label=n, total=t) for n, t in por_canal],
        por_mes=[ItemConteo(label=m, total=t) for m, t in por_mes_raw],
        por_tipo_requerimiento=[ItemConteo(label=n, total=t) for n, t in por_tipo],
    )
