from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class LogAuditoria(Base):
    __tablename__ = "log_auditoria"

    id         = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    # Qué ocurrió
    accion     = Column(String(60), nullable=False, index=True)
    # Sobre qué entidad
    entidad    = Column(String(50))
    entidad_id = Column(Integer)
    descripcion = Column(Text)

    ip         = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    usuario = relationship("Usuario")
