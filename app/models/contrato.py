from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.base import TimestampMixin

class Contrato(Base, TimestampMixin):
    __tablename__ = "contratos"

    id = Column(Integer, primary_key=True, index=True)
    osce_id = Column(String(50), unique=True, nullable=False, index=True)

    titulo = Column(String(500), nullable=False, index=True)
    descripcion = Column(Text, nullable=True)

    entidad_contratante = Column(String(255), nullable=False, index=True)
    entidad_ruc = Column(String(11), nullable=True)

    responsable_id = Column(Integer, ForeignKey("funcionarios.id"), nullable=True, index=True)
    responsable = relationship("Funcionario", back_populates="contratos")

    proveedor_id = Column(Integer, ForeignKey("empresas.id"), nullable=True, index=True)
    proveedor = relationship("Empresa", back_populates="contratos")

    monto = Column(Float, nullable=False, index=True)
    moneda = Column(String(3), default="PEN")
    presupuesto_base = Column(Float, nullable=True)

    tipo_proceso = Column(String(50), nullable=False)
    estado = Column(String(50), nullable=False)

    fecha_publicacion = Column(DateTime, nullable=False)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)

    empresa_nueva = Column(Boolean, default=False)
    monto_anomalo = Column(Boolean, default=False)
    proceso_exonerado = Column(Boolean, default=False)

    datos_osce_json = Column(Text, nullable=True)

    __table_args__ = (
        Index('idx_contrato_osce_id', 'osce_id'),
        Index('idx_contrato_responsable_proveedor', 'responsable_id', 'proveedor_id'),
        Index('idx_contrato_fecha_publicacion', 'fecha_publicacion'),
        Index('idx_contrato_monto', 'monto'),
    )

    def __repr__(self):
        return f"<Contrato(osce_id={self.osce_id}, monto={self.monto}, estado={self.estado})>"
