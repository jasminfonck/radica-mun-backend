from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DependenciaResumen(BaseModel):
    id: int
    nombre: str
    codigo: Optional[str] = None
    model_config = {"from_attributes": True}


class UsuarioResumen(BaseModel):
    id: int
    nombre: str
    model_config = {"from_attributes": True}


class RadicadoCreate(BaseModel):
    recepcion_id:   int
    dependencia_id: int
    observaciones:  Optional[str] = None


class RadicadoAnular(BaseModel):
    observaciones: str


class RadicadoOut(BaseModel):
    id: int
    numero_radicado: str
    recepcion_id: int
    dependencia: DependenciaResumen
    radicado_por: UsuarioResumen
    estado: str
    observaciones: Optional[str]
    ruta_constancia: Optional[str]
    fecha_radicacion: datetime
    created_at: datetime
    model_config = {"from_attributes": True}


class RadicadoResumen(BaseModel):
    id: int
    numero_radicado: str
    recepcion_id: int
    dependencia: DependenciaResumen
    estado: str
    fecha_radicacion: datetime
    model_config = {"from_attributes": True}
