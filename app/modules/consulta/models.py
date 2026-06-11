from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base


class BitacoraOperativa(Base):
    __tablename__ = "bitacora_operativa"

    id         = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    accion     = Column(String(60), nullable=False, index=True)
    modulo     = Column(String(50), index=True)   # ej. "recepciones", "radicados", "remitentes"
    modulo_id  = Column(Integer)
    descripcion = Column(Text)

    ip         = Column(String(45))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    usuario = relationship("Usuario")


# Alias de compatibilidad — eliminar cuando todos los imports estén migrados
LogAuditoria = BitacoraOperativa
