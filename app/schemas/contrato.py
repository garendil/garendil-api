from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ContratoSchema(BaseModel):
    id: int
    osce_id: str
    titulo: str
    descripcion: Optional[str] = None
    entidad_contratante: str
    monto: float
    moneda: str
    tipo_proceso: str
    estado: str
    fecha_publicacion: datetime
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    empresa_nueva: bool = False
    monto_anomalo: bool = False
    proceso_exonerado: bool = False

    class Config:
        from_attributes = True
