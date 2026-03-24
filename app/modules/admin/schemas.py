from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any
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
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=6)
    rol_id: int

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[str] = None
    rol_id: Optional[int] = None
    activo: Optional[bool] = None

class UsuarioOut(BaseModel):
    id: int
    nombre: str
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

class CanalOut(BaseModel):
    id: int
    nombre: str
    tipo: str
    activo: bool
    config_email: Optional[Any]
    model_config = {"from_attributes": True}


# ── TipoRequerimiento ─────────────────────────────────────────────────────
class TipoRequerimientoCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    descripcion: Optional[str] = None

class TipoRequerimientoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2)
    descripcion: Optional[str] = None
    activo: Optional[bool] = None

class TipoRequerimientoOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    activo: bool
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


# ── ConfiguracionSistema ──────────────────────────────────────────────────
class ConfiguracionUpdate(BaseModel):
    prefijo_radicado: Optional[str] = Field(None, max_length=10)
    ruta_almacenamiento: Optional[str] = None
    color_primario: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')

class ConfiguracionOut(BaseModel):
    id: int
    prefijo_radicado: str
    anio_radicado: int
    secuencia_actual: int
    ruta_almacenamiento: Optional[str]
    color_primario: str
    sistema_listo: bool
    model_config = {"from_attributes": True}
