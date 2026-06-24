import re
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List
from datetime import datetime

ESTADOS_VALIDOS = ["recibido", "pendiente", "incompleto", "no_competente", "competente", "radicado"]

# Desde qué estados se puede pasar a cada estado destino (solo vía PUT /recepcion/{id}).
# "radicado" es un estado terminal que solo fija el servicio de radicado internamente.
TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    "recibido":      {"pendiente", "incompleto", "no_competente", "competente"},
    "pendiente":     {"recibido", "incompleto", "no_competente", "competente"},
    "incompleto":    {"recibido", "pendiente", "no_competente", "competente"},
    "no_competente": {"recibido", "pendiente"},      # requiere re-revisión antes de declarar apto
    "competente":    {"pendiente", "no_competente"}, # corrección antes de radicar
    "radicado":      set(),                          # terminal: ninguna transición manual permitida
}


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
    email_remitente: Optional[str] = None


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
    aviso_adjuntos: Optional[str] = None
    email_remitente: Optional[str]
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
    max_adjuntos: int = 5
    max_tamano_adjunto_mb: int = 10
    tipos_archivo_permitidos: List[str] = []


class FormularioPublicoCreate(BaseModel):
    # Remitente
    tipo_persona: str = "natural"
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    razon_social: Optional[str] = None
    tipo_identificacion: Optional[str] = None
    numero_identificacion: Optional[str] = None
    digito_verificacion: Optional[str] = None
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

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        digitos = re.sub(r"\D", "", v)
        if len(digitos) < 7 or len(digitos) > 10:
            raise ValueError("El teléfono debe tener entre 7 y 10 dígitos")
        return digitos

    @field_validator("numero_identificacion")
    @classmethod
    def validar_numero_identificacion(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        v = v.strip()
        if len(v) < 3 or len(v) > 20:
            raise ValueError("El número de identificación debe tener entre 3 y 20 caracteres")
        return v

    @model_validator(mode="after")
    def validar_numero_por_tipo(self) -> "FormularioPublicoCreate":
        num = self.numero_identificacion
        tipo = self.tipo_identificacion
        if not num or not tipo:
            return self
        if tipo == "CC":
            if not re.fullmatch(r"\d{5,10}", num):
                raise ValueError("La cédula de ciudadanía debe tener entre 5 y 10 dígitos")
        elif tipo == "NIT":
            if not re.fullmatch(r"\d{7,15}", num):
                raise ValueError("El NIT debe tener entre 7 y 15 dígitos (sin dígito de verificación)")
            dv = self.digito_verificacion
            if dv is not None and dv != "" and not re.fullmatch(r"\d", dv):
                raise ValueError("El dígito de verificación debe ser un único dígito numérico")
        elif tipo == "CE":
            if not re.fullmatch(r"[A-Za-z0-9]{4,15}", num):
                raise ValueError("La cédula de extranjería debe tener entre 4 y 15 caracteres alfanuméricos")
        return self


class FormularioPublicoOut(BaseModel):
    recibido: bool = True
    acuse_enviado: bool
