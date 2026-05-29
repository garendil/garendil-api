from pydantic import BaseModel
from typing import Optional

class EmpresaSchema(BaseModel):
    id: int
    ruc: str
    nombre_razon_social: str
    estado: str
    fecha_creacion: Optional[str] = None
    creada_recientemente: bool = False
    concentracion_alta: bool = False

    class Config:
        from_attributes = True
