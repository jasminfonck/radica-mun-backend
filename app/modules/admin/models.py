from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base


class BuzonCorreo(Base):
    """
    Configuración del buzón oficial de radicación por correo electrónico.
    Soporta autenticación por contraseña de aplicación (IMAP LOGIN/PLAIN)
    u OAuth2 (IMAP XOAUTH2) para Gmail y Outlook personal/empresarial.
    """
    __tablename__ = "buzon_correo"

    id = Column(Integer, primary_key=True, index=True)
    canal_id = Column(Integer, ForeignKey("canales.id"), nullable=False, unique=True)
    proveedor = Column(String(20), nullable=False)              # "gmail" | "outlook"
    tipo_cuenta = Column(String(20), nullable=False, default="personal")   # "personal" | "empresarial"
    auth_type = Column(String(20), nullable=False, default="oauth2")
    correo = Column(String(150), nullable=False)

    # Credenciales básicas (auth_type == "password_app")
    password_app_enc = Column(Text, nullable=True)             # Fernet-encrypted

    # Credenciales OAuth2 (auth_type == "oauth2")
    oauth_client_id = Column(String(200), nullable=True)
    oauth_client_secret_enc = Column(Text, nullable=True)      # Fernet-encrypted
    oauth_tenant_id = Column(String(200), nullable=True)       # Sólo Microsoft 365 (empresarial)
    oauth_access_token_enc = Column(Text, nullable=True)       # Fernet-encrypted, expira ~1h
    oauth_refresh_token_enc = Column(Text, nullable=True)      # Fernet-encrypted, larga duración
    oauth_token_expiry = Column(DateTime, nullable=True)
    oauth_state = Column(String(100), nullable=True)           # CSRF state del flujo en curso

    # Método de conexión: "imap" (IMAP+XOAUTH2) o "graph" (Microsoft Graph API vía HTTPS)
    metodo_conexion = Column(String(10), nullable=False, default="imap")

    # IMAP
    servidor_imap = Column(String(100), nullable=False)
    puerto = Column(Integer, default=993, nullable=False)
    intervalo_minutos = Column(Integer, default=5, nullable=False)
    activo = Column(Boolean, default=False, nullable=False)
    ultimo_polling = Column(DateTime, nullable=True)
    estado_conexion = Column(String(20), default="sin_probar", nullable=False)
    ultimo_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    canal = relationship("Canal")

    @property
    def oauth_autorizado(self) -> bool:
        return bool(self.oauth_refresh_token_enc)


class BitacoraAuditoria(Base):
    __tablename__ = "bitacora_auditoria"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    usuario_nombre = Column(String(100), nullable=False)
    accion = Column(String(100), nullable=False)       # ej. "crear_usuario", "actualizar_canal"
    modulo = Column(String(100), nullable=False)       # ej. "Usuario", "Canal"
    modulo_id = Column(Integer, nullable=True)
    detalle = Column(Text, nullable=True)              # JSON serializado con valor anterior/nuevo
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    usuario = relationship("Usuario", foreign_keys=[usuario_id])


class Rol(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(String(200))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    usuarios = relationship("Usuario", back_populates="rol")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    activo        = Column(Boolean,  default=True, nullable=False)
    token_version = Column(Integer,  default=1,    nullable=False)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow, nullable=False)

    rol = relationship("Rol", back_populates="usuarios")


class Entidad(Base):
    __tablename__ = "entidad"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    nit = Column(String(20))
    municipio = Column(String(100))
    departamento = Column(String(100))
    direccion = Column(String(200))
    telefono = Column(String(20))
    email_institucional = Column(String(100))
    configurada = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow, nullable=False)


class Dependencia(Base):
    __tablename__ = "dependencias"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    codigo = Column(String(20))
    responsable = Column(String(100))
    email = Column(String(100))
    activa = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow, nullable=False)


class Canal(Base):
    __tablename__ = "canales"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    tipo = Column(String(20), nullable=False)   # presencial | digital | email
    activo = Column(Boolean, default=False, nullable=False)
    config_email = Column(JSON, nullable=True)  # {host, port, user, password, from}
    acuse_configurado = Column(Boolean, default=False, nullable=False)  # RN-20: requerido para canal digital
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow, nullable=False)


class TipoRequerimiento(Base):
    __tablename__ = "tipos_requerimiento"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(300))
    activo = Column(Boolean, default=True, nullable=False)
    plazo_respuesta_id = Column(Integer, ForeignKey("plazos_respuesta.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow, nullable=False)

    plazo_respuesta = relationship("PlazoRespuesta")


class PlazoRespuesta(Base):
    __tablename__ = "plazos_respuesta"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    dias_habiles = Column(Integer, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow, nullable=False)


class ConfiguracionSistema(Base):
    __tablename__ = "configuracion_sistema"

    id = Column(Integer, primary_key=True, index=True)
    prefijo_radicado = Column(String(10), default="RAD", nullable=False)
    anio_radicado = Column(Integer, default=lambda: datetime.now(timezone.utc).year, nullable=False)
    secuencia_actual = Column(Integer, default=0, nullable=False)
    ruta_almacenamiento = Column(String(500), default="../storage")
    color_primario = Column(String(7), default="#1a237e")
    sistema_listo = Column(Boolean, default=False, nullable=False)
    # RN-19: política de privacidad obligatoria (Ley 1581/2012)
    politica_privacidad_activa = Column(Boolean, default=False, nullable=False)
    politica_privacidad_texto  = Column(Text, nullable=True)
    # Parametrización global de adjuntos (formulario público, buzón y recepciones)
    max_adjuntos             = Column(Integer, default=5,  nullable=False)
    max_tamano_adjunto_mb    = Column(Integer, default=10, nullable=False)
    tipos_archivo_permitidos = Column(
        Text,
        default=(
            "application/pdf,"
            "image/jpeg,"
            "image/png,"
            "application/msword,"
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
            "application/vnd.ms-excel,"
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
            "text/plain"
        ),
        nullable=False,
    )
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow, nullable=False)
