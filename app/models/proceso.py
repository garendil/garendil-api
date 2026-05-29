from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.base import TimestampMixin

class Proceso(Base, TimestampMixin):
    __tablename__ = "procesos"

    id = Column(Integer, primary_key=True, index=True)

    numero_expediente = Column(String(50), unique=True, nullable=False, index=True)
    juzgado = Column(String(255), nullable=False)

    acusado_id = Column(Integer, ForeignKey("funcionarios.id"), nullable=True, index=True)
    acusado = relationship("Funcionario", back_populates="procesos")
    acusado_nombre = Column(String(255), nullable=True)

    delito_imputado = Column(String(500), nullable=False, index=True)
    estado = Column(String(50), nullable=False)

    fecha_inicio = Column(DateTime, nullable=False)
    fecha_sentencia = Column(DateTime, nullable=True)

    resultado = Column(String(255), nullable=True)
    pena_anos = Column(Integer, nullable=True)

    fuente = Column(String(50), default="poder_judicial")
    url_fuente = Column(String(512), nullable=True)

    __table_args__ = (
        Index('idx_proceso_expediente', 'numero_expediente'),
        Index('idx_proceso_acusado_estado', 'acusado_id', 'estado'),
        Index('idx_proceso_delito', 'delito_imputado'),
    )

    def __repr__(self):
        return f"<Proceso(expediente={self.numero_expediente}, acusado={self.acusado_nombre}, estado={self.estado})>"
