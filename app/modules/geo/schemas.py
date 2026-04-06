from pydantic import BaseModel
from typing import List


class MunicipioOut(BaseModel):
    id: int
    nombre: str

    model_config = {"from_attributes": True}


class DepartamentoOut(BaseModel):
    id: int
    nombre: str

    model_config = {"from_attributes": True}


class DepartamentoConMunicipiosOut(DepartamentoOut):
    municipios: List[MunicipioOut] = []
