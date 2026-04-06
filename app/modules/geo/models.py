from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class Departamento(Base):
    __tablename__ = "geo_departamentos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)

    municipios = relationship("Municipio", back_populates="departamento",
                              order_by="Municipio.nombre")


class Municipio(Base):
    __tablename__ = "geo_municipios"

    id = Column(Integer, primary_key=True, index=True)
    departamento_id = Column(Integer, ForeignKey("geo_departamentos.id"), nullable=False, index=True)
    nombre = Column(String(100), nullable=False)

    departamento = relationship("Departamento", back_populates="municipios")
