import logging
from app.services.scoring.interfaces import ScoringLayer, ScoringInput, ScoringLayerException

logger = logging.getLogger(__name__)


class Layer1Scorer(ScoringLayer):
    """
    Capa 1: Reglas explícitas y auditables.

    Reglas (score 0-100, normalizado a 0.0-1.0):
    - Empresas nuevas (<30d): hasta +15 pts
    - Monto supera presupuesto >20%: hasta +10 pts
    - Exoneraciones >50% del total: +20 pts
    - Patrimonio delta elevado: hasta +15 pts
    """

    @property
    def name(self) -> str:
        return "Layer1"

    @property
    def weight(self) -> float:
        return 0.7

    @property
    def min_required_features(self) -> set:
        return {
            "contratos_cantidad",
            "empresas_nuevas",
            "monto_total",
            "monto_presupuesto",
            "exoneraciones",
            "patrimonio_delta",
        }

    async def validate_input(self, input: ScoringInput) -> bool:
        missing = self.min_required_features - set(input.features.keys())
        if missing:
            logger.warning(f"Layer1: features faltantes: {missing}")
            return False
        return True

    async def score(self, input: ScoringInput) -> float:
        if not await self.validate_input(input):
            raise ScoringLayerException(
                f"Layer1: features insuficientes para funcionario {input.funcionario_id}"
            )

        pts = 0.0

        # Regla 1: empresas nuevas
        empresas_nuevas = input.get_feature("empresas_nuevas")
        if empresas_nuevas >= 1:
            pts += min(empresas_nuevas * 5, 15)

        # Regla 2: monto supera presupuesto
        monto = input.get_feature("monto_total")
        presupuesto = input.get_feature("monto_presupuesto", monto)
        if presupuesto > 0:
            exceso = (monto / presupuesto) - 1.0
            if exceso > 0.2:
                pts += min(exceso * 100, 10)

        # Regla 3: alta tasa de exoneraciones
        exoneraciones = input.get_feature("exoneraciones")
        total = input.get_feature("contratos_cantidad", 1)
        if total > 0 and (exoneraciones / total) > 0.5:
            pts += 20

        # Regla 4: patrimonio delta
        delta = input.get_feature("patrimonio_delta")
        if delta > 50_000:
            pts += min((delta / 100_000) * 15, 15)

        normalized = min(pts / 100.0, 1.0)
        logger.info(
            f"Layer1 funcionario {input.funcionario_id}: {pts:.1f}/100 → {normalized:.3f}"
        )
        return normalized


def apply_layer1_flags(contrato, empresa):
    """Aplica flags Layer1 en-línea a un contrato (usado por osce_ingester)."""
    from datetime import datetime

    if empresa and empresa.fecha_creacion:
        try:
            fecha_creacion = datetime.strptime(str(empresa.fecha_creacion), "%Y-%m-%d")
            if (datetime.now() - fecha_creacion).days < 30:
                contrato.empresa_nueva = True
        except (ValueError, TypeError):
            pass

    if (
        getattr(contrato, "presupuesto_base", None)
        and contrato.presupuesto_base > 0
        and contrato.monto > 0
    ):
        if (contrato.monto - contrato.presupuesto_base) / contrato.presupuesto_base > 0.2:
            contrato.monto_anomalo = True

    if getattr(contrato, "tipo_proceso", None) == "exoneración":
        contrato.proceso_exonerado = True
