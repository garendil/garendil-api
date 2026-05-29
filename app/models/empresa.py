from sqlalchemy import Column, String, Integer, Text, Boolean, Index
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.base import TimestampMixin

class Empresa(Base, TimestampMixin):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    ruc = Column(String(11), unique=True, nullable=False, index=True)
    nombre_razon_social = Column(String(255), nullable=False, index=True)

    estado = Column(String(50))
    fecha_creacion = Column(String(10), nullable=True)
    domicilio = Column(String(512), nullable=True)

    creada_recientemente = Column(Boolean, default=False)
    concentracion_alta = Column(Boolean, default=False)

    contratos = relationship("Contrato", back_populates="proveedor")

    __table_args__ = (
        Index('idx_empresa_ruc', 'ruc'),
        Index('idx_empresa_creada_recientemente', 'creada_recientemente'),
    )

    def __repr__(self):
        return f"<Empresa(ruc={self.ruc}, nombre={self.nombre_razon_social})>"
