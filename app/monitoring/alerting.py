import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class SystemAlertManager:
    """Gestor centralizado de alertas de sistema."""

    def __init__(self):
        self._alerts: List[Dict[str, Any]] = []

    async def alert(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        context: Dict[str, Any] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity.value,
            "title": title,
            "message": message,
            "context": context or {},
        }
        self._alerts.append(entry)

        level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.CRITICAL: logging.CRITICAL,
        }.get(severity, logging.INFO)
        logger.log(level, f"[{severity.value.upper()}] {title}: {message}")

        if severity == AlertSeverity.CRITICAL:
            await self._send_slack_alert(entry)

    async def _send_slack_alert(self, alert: Dict) -> None:
        pass  # TODO: Slack webhook integration

    async def alert_scoring_error(self, dni: str, error: str) -> None:
        await self.alert(
            AlertSeverity.WARNING,
            "Scoring error",
            f"No se pudo calcular IER para {dni}",
            context={"dni": dni, "error": error},
        )

    async def alert_high_risk_official(self, dni: str, ier_score: float) -> None:
        if ier_score >= 75:
            await self.alert(
                AlertSeverity.CRITICAL,
                "High risk official detected",
                f"Funcionario {dni} con IER {ier_score:.1f}/100",
                context={"dni": dni, "ier_score": ier_score},
            )

    async def alert_layer3_training_failed(self, error: str) -> None:
        await self.alert(
            AlertSeverity.WARNING,
            "Layer3 training failed",
            error,
            context={"component": "Layer3"},
        )

    @property
    def alerts(self) -> List[Dict[str, Any]]:
        return list(self._alerts)
