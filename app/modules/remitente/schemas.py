from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class RemitenteCreate(BaseModel):
    tipo_persona: str = "natural"       # natural | juridico

    # Persona natural
    nombres:   Optional[str] = None
    apellidos: Optional[str] = None

    # Persona jurídica
    razon_social: Optional[str] = None
    nit:          Optional[str] = None

    # Compartidos
    tipo_identificacion:   Optional[str] = None   # CC | CE | NIT | PP | otro
    numero_identificacion: Optional[str] = None
    email:     Optional[str] = None
    telefono:  Optional[str] = None
    direccion: Optional[str] = None
    municipio: Optional[str] = None

    @field_validator("tipo_persona")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        if v not in ("natural", "juridico"):
            raise ValueError("tipo_persona debe ser 'natural' o 'juridico'")
        return v


class RemitenteUpdate(BaseModel):
    nombres:   Optional[str] = None
    apellidos: Optional[str] = None
    razon_social: Optional[str] = None
    nit:          Optional[str] = None
    tipo_identificacion:   Optional[str] = None
    numero_identificacion: Optional[str] = None
    email:     Optional[str] = None
    telefono:  Optional[str] = None
    direccion: Optional[str] = None
    municipio: Optional[str] = None
    activo:    Optional[bool] = None


class RemitenteOut(BaseModel):
    id: int
    tipo_persona: str
    nombres:   Optional[str]
    apellidos: Optional[str]
    razon_social: Optional[str]
    nit:          Optional[str]
    tipo_identificacion:   Optional[str]
    numero_identificacion: Optional[str]
    email:     Optional[str]
    telefono:  Optional[str]
    direccion: Optional[str]
    municipio: Optional[str]
    activo:    bool
    nombre_completo: str
    created_at: datetime
    model_config = {"from_attributes": True}


class RemitenteResumen(BaseModel):
    id: int
    tipo_persona: str
    nombre_completo: str
    numero_identificacion: Optional[str]
    email: Optional[str]
    telefono: Optional[str]
    model_config = {"from_attributes": True}


# ── MetadatosRecepcion ────────────────────────────────────────────────────────

class MetadatosCreate(BaseModel):
    remitente_id: int
    asunto: str
    tipo_soporte: str                       # fisico | digital | mixto
    numero_anexos: int = 0
    tipo_requerimiento_id: Optional[int] = None
    plazo_respuesta_id:    Optional[int] = None
    observaciones:         Optional[str] = None
    numero_referencia:     Optional[str] = None
    fecha_documento:       Optional[datetime] = None

    @field_validator("tipo_soporte")
    @classmethod
    def validar_soporte(cls, v: str) -> str:
        if v not in ("fisico", "digital", "mixto"):
            raise ValueError("tipo_soporte debe ser 'fisico', 'digital' o 'mixto'")
        return v


class MetadatosUpdate(BaseModel):
    asunto: Optional[str] = None
    tipo_soporte: Optional[str] = None
    numero_anexos: Optional[int] = None
    tipo_requerimiento_id: Optional[int] = None
    plazo_respuesta_id:    Optional[int] = None
    observaciones:         Optional[str] = None
    numero_referencia:     Optional[str] = None
    fecha_documento:       Optional[datetime] = None


class TipoRequerimientoResumen(BaseModel):
    id: int
    nombre: str
    model_config = {"from_attributes": True}


class PlazoRespuestaResumen(BaseModel):
    id: int
    nombre: str
    dias_habiles: int
    model_config = {"from_attributes": True}


class MetadatosOut(BaseModel):
    id: int
    recepcion_id: int
    remitente: RemitenteResumen
    asunto: str
    tipo_soporte: str
    numero_anexos: int
    tipo_requerimiento: Optional[TipoRequerimientoResumen]
    plazo_respuesta:    Optional[PlazoRespuestaResumen]
    observaciones:      Optional[str]
    numero_referencia:  Optional[str]
    fecha_documento:    Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}
