from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.dependencies import get_db
from app.modules.geo import models
from app.modules.geo.schemas import DepartamentoOut, MunicipioOut

router = APIRouter(prefix="/geo", tags=["Geografía"])


@router.get("/departamentos", response_model=List[DepartamentoOut])
def listar_departamentos(db: Session = Depends(get_db)):
    """Lista todos los departamentos de Colombia ordenados alfabéticamente."""
    return db.query(models.Departamento).order_by(models.Departamento.nombre).all()


@router.get("/municipios", response_model=List[MunicipioOut])
def listar_municipios(
    departamento_id: Optional[int] = Query(None, description="ID del departamento"),
    db: Session = Depends(get_db),
):
    """Lista municipios. Si se provee departamento_id, filtra por ese departamento."""
    q = db.query(models.Municipio).order_by(models.Municipio.nombre)
    if departamento_id is not None:
        q = q.filter(models.Municipio.departamento_id == departamento_id)
    return q.all()
