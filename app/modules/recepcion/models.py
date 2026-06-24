from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base


class Recepcion(Base):
    __tablename__ = "recepciones"

    id = Column(Integer, primary_key=True, index=True)

    # Origen
    canal_id = Column(Integer, ForeignKey("canales.id"), nullable=False)
    canal = relationship("Canal")

    # Datos iniciales del documento
    asunto_provisional = Column(String(300))
    observaciones      = Column(Text)
    email_remitente    = Column(String(200), nullable=True)

    # Aviso de adjuntos rechazados por el poller (campo separado, no toca observaciones)
    aviso_adjuntos = Column(Text, nullable=True)

    # Estado
    # recibido | pendiente | incompleto | no_competente | competente | radicado
    estado = Column(String(30), default="recibido", nullable=False)

    # Trazabilidad
    recibido_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    recibido_por    = relationship("Usuario")
    ip_origen       = Column(String(45))  # para formulario web

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow, nullable=False)

    adjuntos = relationship("AdjuntoRecepcion", back_populates="recepcion", cascade="all, delete-orphan")


class AdjuntoRecepcion(Base):
    __tablename__ = "adjuntos_recepcion"

    id            = Column(Integer, primary_key=True, index=True)
    recepcion_id  = Column(Integer, ForeignKey("recepciones.id"), nullable=False)
    nombre_original = Column(String(300), nullable=False)
    nombre_archivo  = Column(String(300), nullable=False)  # nombre en disco
    ruta            = Column(String(500), nullable=False)
    tipo_mime       = Column(String(100))
    tamano_bytes    = Column(Integer)
    created_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    recepcion = relationship("Recepcion", back_populates="adjuntos")
