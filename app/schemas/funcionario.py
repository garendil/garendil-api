from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class FuncionarioBaseSchema(BaseModel):
    dni: str
    nombre_completo: str
    cargo_actual: Optional[str] = None
    institucion: Optional[str] = None

class FuncionarioSchema(FuncionarioBaseSchema):
    id: int
    score_ier: float
    score_competencia: float
    score_adecuacion: float
    foto_url: Optional[str] = None
    activo: bool
    created_at: datetime

    class Config:
        from_attributes = True

class FuncionarioDetailSchema(FuncionarioSchema):
    contratos: List["ContratoSchema"] = []
    procesos: List[dict] = []
    conexiones: List[dict] = []

    class Config:
        from_attributes = True
