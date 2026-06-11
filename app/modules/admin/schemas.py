from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any, List
from datetime import datetime


# ── Rol ───────────────────────────────────────────────────────────────────
class RolOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    model_config = {"from_attributes": True}


# ── Usuario ───────────────────────────────────────────────────────────────
class UsuarioCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: Optional[str] = Field(None, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    rol_id: int

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    apellido: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    rol_id: Optional[int] = None
    activo: Optional[bool] = None

class UsuarioOut(BaseModel):
    id: int
    nombre: str
    apellido: Optional[str]
    email: str
    activo: bool
    rol: RolOut
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Entidad ───────────────────────────────────────────────────────────────
class EntidadUpdate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=200)
    nit: Optional[str] = None
    municipio: Optional[str] = None
    departamento: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email_institucional: Optional[str] = None

class EntidadOut(BaseModel):
    id: int
    nombre: str
    nit: Optional[str]
    municipio: Optional[str]
    departamento: Optional[str]
    direccion: Optional[str]
    telefono: Optional[str]
    email_institucional: Optional[str]
    configurada: bool
    model_config = {"from_attributes": True}


# ── Dependencia ───────────────────────────────────────────────────────────
class DependenciaCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=200)
    codigo: Optional[str] = None
    responsable: Optional[str] = None
    email: Optional[str] = None

class DependenciaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2)
    codigo: Optional[str] = None
    responsable: Optional[str] = None
    email: Optional[str] = None
    activa: Optional[bool] = None

class DependenciaOut(BaseModel):
    id: int
    nombre: str
    codigo: Optional[str]
    responsable: Optional[str]
    email: Optional[str]
    activa: bool
    model_config = {"from_attributes": True}


# ── Canal ─────────────────────────────────────────────────────────────────
class CanalUpdate(BaseModel):
    activo: bool
    config_email: Optional[dict] = None
    acuse_configurado: Optional[bool] = None

class CanalOut(BaseModel):
    id: int
    nombre: str
    tipo: str
    activo: bool
    config_email: Optional[Any]
    acuse_configurado: bool
    model_config = {"from_attributes": True}


# ── PlazoRespuesta ────────────────────────────────────────────────────────
class PlazoRespuestaCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    dias_habiles: int = Field(..., gt=0)

class PlazoRespuestaUpdate(BaseModel):
    nombre: Optional[str] = None
    dias_habiles: Optional[int] = Field(None, gt=0)
    activo: Optional[bool] = None

class PlazoRespuestaOut(BaseModel):
    id: int
    nombre: str
    dias_habiles: int
    activo: bool
    model_config = {"from_attributes": True}


# ── TipoRequerimiento ─────────────────────────────────────────────────────
class TipoRequerimientoCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    descripcion: Optional[str] = None
    plazo_respuesta_id: Optional[int] = None

class TipoRequerimientoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2)
    descripcion: Optional[str] = None
    activo: Optional[bool] = None
    plazo_respuesta_id: Optional[int] = None

class TipoRequerimientoOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    activo: bool
    plazo_respuesta_id: Optional[int]
    plazo_respuesta: Optional[PlazoRespuestaOut]
    model_config = {"from_attributes": True}


# ── ConfiguracionSistema ──────────────────────────────────────────────────
class ConfiguracionUpdate(BaseModel):
    prefijo_radicado: Optional[str] = Field(None, max_length=10)
    ruta_almacenamiento: Optional[str] = None
    color_primario: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    politica_privacidad_activa: Optional[bool] = None
    politica_privacidad_texto: Optional[str] = None

class ConfiguracionOut(BaseModel):
    id: int
    prefijo_radicado: str
    anio_radicado: int
    secuencia_actual: int
    ruta_almacenamiento: Optional[str]
    color_primario: str
    sistema_listo: bool
    politica_privacidad_activa: bool
    politica_privacidad_texto: Optional[str]
    model_config = {"from_attributes": True}


# ── BitacoraAuditoria ─────────────────────────────────────────────────────
class BitacoraOut(BaseModel):
    id: int
    usuario_nombre: str
    accion: str
    modulo: str
    modulo_id: Optional[int]
    detalle: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Respaldo ──────────────────────────────────────────────────────────────
class RespaldoOut(BaseModel):
    generado_en: datetime
    entidad: Optional[dict]
    configuracion: Optional[dict]
    dependencias: List[dict]
    canales: List[dict]
    tipos_requerimiento: List[dict]
    plazos_respuesta: List[dict]
    total_usuarios: int


# ── BuzonCorreo ───────────────────────────────────────────────────────────
class BuzonCorreoCreate(BaseModel):
    canal_id: int
    proveedor: str = Field(..., pattern="^(gmail|outlook)$")
    correo: EmailStr
    password_app: str = Field(..., min_length=8, max_length=100)
    intervalo_minutos: int = Field(default=5, ge=1, le=60)
    max_adjuntos: int = Field(default=5, ge=1, le=20)
    max_tamano_adjunto_mb: int = Field(default=10, ge=1, le=50)

class BuzonCorreoUpdate(BaseModel):
    password_app: Optional[str] = Field(None, min_length=8, max_length=100)
    intervalo_minutos: Optional[int] = Field(None, ge=1, le=60)
    max_adjuntos: Optional[int] = Field(None, ge=1, le=20)
    max_tamano_adjunto_mb: Optional[int] = Field(None, ge=1, le=50)

class BuzonCorreoOut(BaseModel):
    id: int
    canal_id: int
    proveedor: str
    correo: str
    servidor_imap: str
    puerto: int
    intervalo_minutos: int
    max_adjuntos: int
    max_tamano_adjunto_mb: int
    activo: bool
    ultimo_polling: Optional[datetime]
    estado_conexion: str
    ultimo_error: Optional[str]
    model_config = {"from_attributes": True}

class TestConexionResult(BaseModel):
    ok: bool
    mensaje: str
