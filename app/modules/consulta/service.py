import csv
import io
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Optional
from datetime import datetime, timezone

from app.modules.consulta.models import BitacoraOperativa
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
    modulo: Optional[str] = None,
    modulo_id: Optional[int] = None,
    descripcion: Optional[str] = None,
    usuario_id: Optional[int] = None,
    ip: Optional[str] = None,
) -> None:
    evento = BitacoraOperativa(
        accion=accion,
        modulo=modulo,
        modulo_id=modulo_id,
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
    modulo: Optional[str] = None,
    limit: int = 100,
) -> list[BitacoraOperativa]:
    q = db.query(BitacoraOperativa).order_by(BitacoraOperativa.created_at.desc())
    if accion:
        q = q.filter(BitacoraOperativa.accion == accion)
    if usuario_id:
        q = q.filter(BitacoraOperativa.usuario_id == usuario_id)
    if fecha_desde:
        q = q.filter(BitacoraOperativa.created_at >= fecha_desde)
    if fecha_hasta:
        q = q.filter(BitacoraOperativa.created_at <= fecha_hasta)
    if modulo:
        q = q.filter(BitacoraOperativa.modulo == modulo)
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
    canal = db.get(Canal, recepcion.canal_id) if recepcion else None

    url_constancia = None
    if radicado.ruta_constancia:
        import os
        if os.path.exists(radicado.ruta_constancia):
            url_constancia = f"/api/consulta/publica/{radicado.numero_radicado}/constancia"

    return ConsultaPublicaOut(
        numero_radicado=radicado.numero_radicado,
        fecha_radicacion=radicado.fecha_radicacion,
        asunto=metadatos.asunto if metadatos else "—",
        dependencia=dependencia.nombre if dependencia else "—",
        canal=canal.nombre if canal else "—",
        estado_radicado=radicado.estado,
        estado_recepcion=recepcion.estado if recepcion else "—",
        tipo_soporte=metadatos.tipo_soporte if metadatos else "—",
        remitente=metadatos.remitente.nombre_completo if metadatos and metadatos.remitente else "—",
        url_constancia=url_constancia,
    )


def get_constancia_path(db: Session, numero_radicado: str) -> str:
    """Retorna la ruta del PDF de constancia para descarga pública."""
    radicado = (
        db.query(Radicado)
        .filter(Radicado.numero_radicado == numero_radicado.upper())
        .first()
    )
    if not radicado:
        raise HTTPException(status_code=404, detail="Número de radicado no encontrado")
    import os
    if not radicado.ruta_constancia or not os.path.exists(radicado.ruta_constancia):
        raise HTTPException(status_code=404, detail="Constancia no disponible aún")
    return radicado.ruta_constancia


# ── Búsqueda interna ──────────────────────────────────────────────────────────

def _build_buscar_query(
    db: Session,
    q: Optional[str] = None,
    numero_radicado: Optional[str] = None,
    canal_id: Optional[int] = None,
    dependencia_id: Optional[int] = None,
    estado_radicado: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    query = (
        db.query(Radicado, MetadatosRecepcion, Recepcion, Dependencia, Canal)
        .join(Recepcion, Radicado.recepcion_id == Recepcion.id)
        .outerjoin(MetadatosRecepcion, MetadatosRecepcion.recepcion_id == Radicado.recepcion_id)
        .outerjoin(Dependencia, Radicado.dependencia_id == Dependencia.id)
        .outerjoin(Canal, Recepcion.canal_id == Canal.id)
    )

    if numero_radicado:
        query = query.filter(Radicado.numero_radicado.ilike(f"%{numero_radicado}%"))
    if canal_id:
        query = query.filter(Recepcion.canal_id == canal_id)
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

    return query.order_by(Radicado.id.desc())


def buscar(
    db: Session,
    q: Optional[str] = None,
    numero_radicado: Optional[str] = None,
    canal_id: Optional[int] = None,
    dependencia_id: Optional[int] = None,
    estado_radicado: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 200,
) -> list[ResultadoBusqueda]:
    rows = _build_buscar_query(
        db, q, numero_radicado, canal_id, dependencia_id, estado_radicado, fecha_desde, fecha_hasta
    ).limit(limit).all()

    results = []
    for radicado, metadatos, recepcion, dep, canal in rows:
        results.append(ResultadoBusqueda(
            radicado_id=radicado.id,
            numero_radicado=radicado.numero_radicado,
            recepcion_id=radicado.recepcion_id,
            fecha_radicacion=radicado.fecha_radicacion,
            asunto=metadatos.asunto if metadatos else "—",
            remitente=metadatos.remitente.nombre_completo if metadatos and metadatos.remitente else "—",
            canal=canal.nombre if canal else "—",
            dependencia=dep.nombre if dep else "—",
            estado_radicado=radicado.estado,
            estado_recepcion=recepcion.estado if recepcion else "—",
        ))
    return results


def exportar_csv(
    db: Session,
    q: Optional[str] = None,
    numero_radicado: Optional[str] = None,
    canal_id: Optional[int] = None,
    dependencia_id: Optional[int] = None,
    estado_radicado: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> str:
    """Genera el contenido CSV de los radicados que cumplen los filtros."""
    rows = _build_buscar_query(
        db, q, numero_radicado, canal_id, dependencia_id, estado_radicado, fecha_desde, fecha_hasta
    ).all()

    output = io.StringIO()
    writer = csv.writer(output, dialect="excel")
    writer.writerow([
        "Número de radicado", "Fecha radicación", "Remitente",
        "Asunto", "Canal", "Dependencia destino", "Estado radicado", "Estado recepción",
    ])
    for radicado, metadatos, recepcion, dep, canal in rows:
        writer.writerow([
            radicado.numero_radicado,
            radicado.fecha_radicacion.strftime("%d/%m/%Y %H:%M") if radicado.fecha_radicacion else "",
            metadatos.remitente.nombre_completo if metadatos and metadatos.remitente else "—",
            metadatos.asunto if metadatos else "—",
            canal.nombre if canal else "—",
            dep.nombre if dep else "—",
            radicado.estado,
            recepcion.estado if recepcion else "—",
        ])
    return output.getvalue()


# ── Estadísticas ──────────────────────────────────────────────────────────────

def estadisticas(db: Session) -> EstadisticasOut:
    total_recepciones = db.query(func.count(Recepcion.id)).scalar() or 0
    total_radicados   = db.query(func.count(Radicado.id)).scalar() or 0
    vigentes  = db.query(func.count(Radicado.id)).filter(Radicado.estado == "radicado").scalar() or 0
    anulados  = db.query(func.count(Radicado.id)).filter(Radicado.estado == "anulado").scalar() or 0

    por_dep = (
        db.query(Dependencia.nombre, func.count(Radicado.id))
        .join(Radicado, Radicado.dependencia_id == Dependencia.id)
        .group_by(Dependencia.nombre)
        .order_by(func.count(Radicado.id).desc())
        .all()
    )

    por_canal = (
        db.query(Canal.nombre, func.count(Recepcion.id))
        .join(Recepcion, Recepcion.canal_id == Canal.id)
        .group_by(Canal.nombre)
        .order_by(func.count(Recepcion.id).desc())
        .all()
    )

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

    por_tipo = (
        db.query(TipoRequerimiento.nombre, func.count(MetadatosRecepcion.id))
        .join(MetadatosRecepcion, MetadatosRecepcion.tipo_requerimiento_id == TipoRequerimiento.id)
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
