from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── Consulta pública ──────────────────────────────────────────────────────────

class ConsultaPublicaOut(BaseModel):
    numero_radicado:  str
    fecha_radicacion: datetime
    asunto:           str
    dependencia:      str
    estado_radicado:  str
    estado_recepcion: str
    tipo_soporte:     str
    remitente:        str


# ── Búsqueda interna ──────────────────────────────────────────────────────────

class ResultadoBusqueda(BaseModel):
    radicado_id:     int
    numero_radicado: str
    recepcion_id:    int
    fecha_radicacion: datetime
    asunto:          str
    remitente:       str
    dependencia:     str
    estado_radicado: str
    estado_recepcion: str


# ── Estadísticas ──────────────────────────────────────────────────────────────

class ItemConteo(BaseModel):
    label: str
    total: int


class EstadisticasOut(BaseModel):
    total_recepciones:   int
    total_radicados:     int
    radicados_vigentes:  int
    radicados_anulados:  int
    por_dependencia:     List[ItemConteo]
    por_canal:           List[ItemConteo]
    por_mes:             List[ItemConteo]
    por_tipo_requerimiento: List[ItemConteo]


# ── Auditoría ─────────────────────────────────────────────────────────────────

class UsuarioResumen(BaseModel):
    id:     int
    nombre: str
    model_config = {"from_attributes": True}


class LogAuditoriaOut(BaseModel):
    id:          int
    usuario:     Optional[UsuarioResumen]
    accion:      str
    entidad:     Optional[str]
    entidad_id:  Optional[int]
    descripcion: Optional[str]
    ip:          Optional[str]
    created_at:  datetime
    model_config = {"from_attributes": True}
