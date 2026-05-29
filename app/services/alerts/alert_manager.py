from enum import Enum
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import logging

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert:
    def __init__(
        self,
        funcionario_dni: str,
        titulo: str,
        descripcion: str,
        nivel: AlertLevel,
        tipo: str,
    ):
        self.funcionario_dni = funcionario_dni
        self.titulo = titulo
        self.descripcion = descripcion
        self.nivel = nivel
        self.tipo = tipo
        self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        return {
            "funcionario_dni": self.funcionario_dni,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "nivel": self.nivel.value,
            "tipo": self.tipo,
            "timestamp": self.timestamp.isoformat(),
        }


class AlertManager:
    """Gestor centralizado de alertas basadas en scores y patrones de contratos."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.alerts: List[Alert] = []

    async def check_anomalias(self, funcionario_id: int, scores: dict) -> List[Alert]:
        """
        Verifica anomalías y genera alertas según scores y contratos.

        Args:
            funcionario_id: ID del funcionario en BD
            scores: dict con keys layer1_score, layer2_score, ier_combined
        """
        from app.models import Funcionario, Contrato

        alertas: List[Alert] = []

        result = await self.db.execute(
            select(Funcionario).where(Funcionario.id == funcionario_id)
        )
        func = result.scalar_one_or_none()
        if not func:
            logger.warning(f"Funcionario {funcionario_id} no encontrado en check_anomalias")
            return alertas

        result = await self.db.execute(
            select(Contrato).where(Contrato.responsable_id == funcionario_id)
        )
        contratos = result.scalars().all()

        if scores.get("ier_combined", 0) >= 75:
            alertas.append(
                Alert(
                    funcionario_dni=func.dni,
                    titulo="Score de riesgo CRÍTICO",
                    descripcion=f"IER: {scores['ier_combined']:.1f}/100. Revisar inmediatamente.",
                    nivel=AlertLevel.CRITICAL,
                    tipo="score_critico",
                )
            )

        empresas_nuevas = sum(1 for c in contratos if c.empresa_nueva)
        if empresas_nuevas >= 3:
            alertas.append(
                Alert(
                    funcionario_dni=func.dni,
                    titulo="Patrón: múltiples empresas nuevas",
                    descripcion=f"{empresas_nuevas} empresas creadas hace < 30 días.",
                    nivel=AlertLevel.WARNING,
                    tipo="empresas_nuevas",
                )
            )

        if contratos:
            montos = [c.monto for c in contratos]
            monto_total = sum(montos)
            if monto_total > 0:
                top_pct = max(montos) / monto_total
                if top_pct > 0.5:
                    alertas.append(
                        Alert(
                            funcionario_dni=func.dni,
                            titulo="Concentración anómala",
                            descripcion=f"Un contrato representa {top_pct*100:.0f}% del total.",
                            nivel=AlertLevel.WARNING,
                            tipo="concentracion_alta",
                        )
                    )

        if scores.get("layer2_score", 0) > 0.7:
            alertas.append(
                Alert(
                    funcionario_dni=func.dni,
                    titulo="Anomalía detectada (ML)",
                    descripcion=f"Score de anomalía: {scores['layer2_score']:.2f}. Patrón inusual en histórico.",
                    nivel=AlertLevel.WARNING,
                    tipo="anomalia_ml",
                )
            )

        self.alerts.extend(alertas)
        return alertas

    def get_alertas_activas(self) -> List[dict]:
        return [a.to_dict() for a in self.alerts]
