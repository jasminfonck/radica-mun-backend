from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class Remitente(Base):
    __tablename__ = "remitentes"

    id = Column(Integer, primary_key=True, index=True)

    # Tipo: natural | juridico
    tipo_persona = Column(String(20), default="natural", nullable=False)

    # Persona natural
    nombres    = Column(String(100))
    apellidos  = Column(String(100))

    # Persona jurídica
    razon_social = Column(String(200))
    nit          = Column(String(20))

    # Compartidos
    tipo_identificacion = Column(String(30))   # CC | CE | NIT | PP | otro
    numero_identificacion = Column(String(30), index=True)
    email     = Column(String(100), index=True)
    telefono  = Column(String(20))
    direccion = Column(String(200))
    municipio = Column(String(100))

    activo     = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    metadatos = relationship("MetadatosRecepcion", back_populates="remitente")

    @property
    def nombre_completo(self) -> str:
        if self.tipo_persona == "juridico":
            return self.razon_social or ""
        return f"{self.nombres or ''} {self.apellidos or ''}".strip()


class MetadatosRecepcion(Base):
    __tablename__ = "metadatos_recepcion"

    id           = Column(Integer, primary_key=True, index=True)
    recepcion_id = Column(Integer, ForeignKey("recepciones.id"), unique=True, nullable=False)
    remitente_id = Column(Integer, ForeignKey("remitentes.id"), nullable=False)

    # Metadatos mínimos HU-03
    asunto              = Column(String(300), nullable=False)
    tipo_soporte        = Column(String(30), nullable=False)   # fisico | digital | mixto
    numero_anexos       = Column(Integer, default=0)
    tipo_requerimiento_id = Column(Integer, ForeignKey("tipos_requerimiento.id"))
    plazo_respuesta_id    = Column(Integer, ForeignKey("plazos_respuesta.id"))
    observaciones         = Column(Text)

    # Referencia documental opcional
    numero_referencia   = Column(String(100))
    fecha_documento     = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    remitente          = relationship("Remitente", back_populates="metadatos")
    tipo_requerimiento = relationship("TipoRequerimiento")
    plazo_respuesta    = relationship("PlazoRespuesta")
