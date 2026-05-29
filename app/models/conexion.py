from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.base import TimestampMixin

class Conexion(Base, TimestampMixin):
    __tablename__ = "conexiones"

    id = Column(Integer, primary_key=True, index=True)

    origen_id = Column(Integer, ForeignKey("funcionarios.id"), nullable=False, index=True)
    origen = relationship("Funcionario", back_populates="conexiones", foreign_keys=[origen_id])

    destino_id = Column(Integer, ForeignKey("funcionarios.id"), nullable=False, index=True)

    tipo = Column(String(50), nullable=False)
    fortaleza = Column(Float, default=0.5)
    evidencia = Column(Text, nullable=True)
    fuente = Column(String(255), nullable=True)

    __table_args__ = (
        Index('idx_conexion_origen_destino', 'origen_id', 'destino_id'),
        Index('idx_conexion_tipo', 'tipo'),
        Index('idx_conexion_fortaleza', 'fortaleza'),
    )

    def __repr__(self):
        return f"<Conexion(origen_id={self.origen_id}, destino_id={self.destino_id}, tipo={self.tipo})>"
