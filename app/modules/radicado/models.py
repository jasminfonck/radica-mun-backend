from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base


class Radicado(Base):
    __tablename__ = "radicados"

    id              = Column(Integer, primary_key=True, index=True)
    numero_radicado = Column(String(30), unique=True, nullable=False, index=True)

    recepcion_id    = Column(Integer, ForeignKey("recepciones.id"), unique=True, nullable=False)
    dependencia_id  = Column(Integer, ForeignKey("dependencias.id"), nullable=True)
    radicado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    # Estado: pendiente | radicado | anulado
    # 'pendiente' → número asignado al recibir, sin completar; 'radicado' → oficial con PDF
    estado        = Column(String(20), default="pendiente", nullable=False)
    observaciones = Column(Text)

    # Ruta al PDF de la constancia generada
    ruta_constancia = Column(String(500))

    fecha_radicacion = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow, nullable=False)

    recepcion   = relationship("Recepcion")
    dependencia = relationship("Dependencia")
    radicado_por = relationship("Usuario")
