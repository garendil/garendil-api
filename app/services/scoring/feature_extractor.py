import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Funcionario, Contrato, Proceso
from app.services.scoring.interfaces import ScoringInput

logger = logging.getLogger(__name__)


class ScoringFeatureExtractor:
    """
    Extrae features del modelo Funcionario y sus relaciones
    para construir un ScoringInput desacoplado.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def extract_features(self, funcionario_id: int) -> ScoringInput:
        result = await self.db.execute(
            select(Funcionario).where(Funcionario.id == funcionario_id)
        )
        func_obj = result.scalar_one_or_none()
        if not func_obj:
            raise ValueError(f"Funcionario {funcionario_id} no encontrado")

        features: dict[str, float] = {}

        # ── Contratos ────────────────────────────────────────────────────────
        result = await self.db.execute(
            select(Contrato).where(Contrato.responsable_id == funcionario_id)
        )
        contratos = result.scalars().all()

        features["contratos_cantidad"] = float(len(contratos))

        if contratos:
            import numpy as np

            montos = [c.monto for c in contratos]
            features["monto_total"] = float(sum(montos))
            features["monto_promedio"] = float(sum(montos) / len(montos))
            features["varianza_montos"] = float(np.var(montos)) if len(montos) > 1 else 0.0
            monto_max = max(montos)
            features["concentracion_empresas"] = (
                monto_max / features["monto_total"] if features["monto_total"] > 0 else 0.0
            )
        else:
            features["monto_total"] = 0.0
            features["monto_promedio"] = 0.0
            features["varianza_montos"] = 0.0
            features["concentracion_empresas"] = 0.0

        # ── Empresas nuevas (flag del modelo) ────────────────────────────────
        features["empresas_nuevas"] = float(
            sum(1 for c in contratos if getattr(c, "empresa_nueva", False))
        )

        # ── Exoneraciones ────────────────────────────────────────────────────
        exoneraciones = sum(
            1 for c in contratos if getattr(c, "proceso_exonerado", False)
        )
        features["exoneraciones"] = float(exoneraciones)
        features["exoneraciones_ratio"] = (
            exoneraciones / len(contratos) if contratos else 0.0
        )
        # Presupuesto base aproximado (sin campo en BD → usar monto anómalo como proxy)
        features["monto_presupuesto"] = features["monto_total"]

        # ── Patrimonio (campos opcionales) ───────────────────────────────────
        patrimonio_actual = getattr(func_obj, "patrimonio_actual", None)
        patrimonio_inicial = getattr(func_obj, "patrimonio_inicial", None)
        features["patrimonio_delta"] = float(
            (patrimonio_actual or 0) - (patrimonio_inicial or 0)
        )

        # ── Temporal ─────────────────────────────────────────────────────────
        fecha_inicio = getattr(func_obj, "fecha_inicio_cargo", None)
        if fecha_inicio:
            features["edad_en_cargo_dias"] = float((datetime.now() - fecha_inicio).days)
        else:
            features["edad_en_cargo_dias"] = 0.0

        # ── Procesos ─────────────────────────────────────────────────────────
        result = await self.db.execute(
            select(Proceso).where(Proceso.acusado_id == funcionario_id)
        )
        procesos = result.scalars().all()
        features["procesos_cantidad"] = float(len(procesos))

        logger.info(
            f"Features extraídas para funcionario {funcionario_id}: "
            f"{len(features)} features, monto_total={features['monto_total']}"
        )

        return ScoringInput(
            funcionario_id=funcionario_id,
            features=features,
            metadata={
                "nombre": func_obj.nombre_completo,
                "institucion": func_obj.institucion,
                "cargo": func_obj.cargo_actual,
            },
        )
