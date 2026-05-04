from pydantic import BaseModel, field_validator
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


# ── Formulario web público ────────────────────────────────────────────────────

class TipoReqResumen(BaseModel):
    id: int
    nombre: str
    model_config = {"from_attributes": True}


class InfoPublicaOut(BaseModel):
    entidad_nombre: str
    entidad_municipio: Optional[str] = None
    entidad_departamento: Optional[str] = None
    entidad_telefono: Optional[str] = None
    entidad_email: Optional[str] = None
    color_primario: str = "#1a237e"
    canal_id: Optional[int] = None
    canal_activo: bool = False
    tipos_requerimiento: List[TipoReqResumen] = []
    politica_privacidad_activa: bool = False
    politica_privacidad_texto: Optional[str] = None


class FormularioPublicoCreate(BaseModel):
    # Remitente
    tipo_persona: str = "natural"
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    razon_social: Optional[str] = None
    tipo_identificacion: Optional[str] = None
    numero_identificacion: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    # Documento
    asunto: str
    tipo_requerimiento_id: Optional[int] = None
    observaciones: Optional[str] = None
    # Consentimiento
    acepta_politica: bool = False

    @field_validator("tipo_persona")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        if v not in ("natural", "juridico"):
            raise ValueError("tipo_persona debe ser 'natural' o 'juridico'")
        return v


class FormularioPublicoOut(BaseModel):
    recibido: bool = True
    acuse_enviado: bool
