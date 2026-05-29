from sqlalchemy import Column, String, Integer, Float, Text, Boolean, Index
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.base import TimestampMixin

class Funcionario(Base, TimestampMixin):
    __tablename__ = "funcionarios"

    id = Column(Integer, primary_key=True, index=True)
    dni = Column(String(8), unique=True, nullable=False, index=True)
    nombre_completo = Column(String(255), nullable=False, index=True)
    cargo_actual = Column(String(255), nullable=True)
    institucion = Column(String(255), nullable=True, index=True)

    score_ier = Column(Float, default=0.0)
    score_competencia = Column(Float, default=0.0)
    score_adecuacion = Column(Float, default=0.0)

    foto_url = Column(String(512), nullable=True)
    descripcion = Column(Text, nullable=True)

    verificado = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)

    contratos = relationship("Contrato", back_populates="responsable")
    procesos = relationship("Proceso", back_populates="acusado")
    conexiones = relationship(
        "Conexion",
        back_populates="origen",
        foreign_keys="[Conexion.origen_id]",
    )

    __table_args__ = (
        Index('idx_funcionario_dni_institucion', 'dni', 'institucion'),
        Index('idx_funcionario_score_ier', 'score_ier'),
    )

    def __repr__(self):
        return f"<Funcionario(dni={self.dni}, nombre={self.nombre_completo}, score_ier={self.score_ier})>"
