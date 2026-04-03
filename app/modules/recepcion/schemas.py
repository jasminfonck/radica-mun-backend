from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

ESTADOS_VALIDOS = ["recibido", "en_revision", "pendiente", "incompleto", "incompetente"]


class AdjuntoOut(BaseModel):
    id: int
    nombre_original: str
    nombre_archivo: str
    tipo_mime: Optional[str]
    tamano_bytes: Optional[int]
    model_config = {"from_attributes": True}


class RecepcionCreate(BaseModel):
    canal_id: int
    asunto_provisional: Optional[str] = None
    observaciones: Optional[str] = None


class RecepcionUpdate(BaseModel):
    asunto_provisional: Optional[str] = None
    observaciones: Optional[str] = None
    estado: Optional[str] = None


class CanalResumen(BaseModel):
    id: int
    nombre: str
    tipo: str
    model_config = {"from_attributes": True}


class UsuarioResumen(BaseModel):
    id: int
    nombre: str
    model_config = {"from_attributes": True}


class RecepcionOut(BaseModel):
    id: int
    canal: CanalResumen
    asunto_provisional: Optional[str]
    observaciones: Optional[str]
    estado: str
    recibido_por: Optional[UsuarioResumen]
    created_at: datetime
    adjuntos: List[AdjuntoOut] = []
    model_config = {"from_attributes": True}


class RecepcionResumen(BaseModel):
    id: int
    canal: CanalResumen
    asunto_provisional: Optional[str]
    estado: str
    created_at: datetime
    total_adjuntos: int = 0
    model_config = {"from_attributes": True}
