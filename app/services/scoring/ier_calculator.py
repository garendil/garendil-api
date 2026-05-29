import logging
from datetime import datetime
from typing import List, Dict, Any

from app.services.scoring.interfaces import ScoringLayer, ScoringInput, ScoringLayerException

logger = logging.getLogger(__name__)


class IERCalculator:
    """
    Agrega múltiples ScoringLayers en un IER 0-100 completamente auditable.
    Los pesos de cada layer deben sumar 1.0 ± 0.05.
    """

    def __init__(self, layers: List[ScoringLayer]):
        self.layers = layers
        self._validate_weights()

    def _validate_weights(self) -> None:
        total = sum(layer.weight for layer in self.layers)
        if not (0.95 <= total <= 1.05):
            raise ValueError(
                f"Pesos no suman 1.0: {total:.3f}. Ajusta weight en cada ScoringLayer."
            )

    async def calculate(self, input: ScoringInput) -> Dict[str, Any]:
        """
        Calcula IER completo con desglose por capa.

        Returns dict con keys: ier, layer_scores, breakdown, timestamp, funcionario_id.
        """
        layer_scores: Dict[str, Any] = {}
        total_score = 0.0
        errors: List[str] = []

        for layer in self.layers:
            try:
                can_score = await layer.validate_input(input)
                score = await layer.score(input) if can_score else 0.0

                # Clamp defensivo
                score = max(0.0, min(1.0, score))
                weighted = score * layer.weight
                total_score += weighted

                layer_scores[layer.name] = {
                    "score": round(score, 3),
                    "weight": layer.weight,
                    "weighted": round(weighted, 3),
                    "score_0_100": round(score * 100, 1),
                }

            except ScoringLayerException as e:
                logger.error(f"{layer.name} error: {e}")
                errors.append(f"{layer.name}: {e}")
                layer_scores[layer.name] = {
                    "score": 0.0,
                    "weight": layer.weight,
                    "weighted": 0.0,
                    "error": str(e),
                }

        ier_final = round(total_score * 100, 1)

        lines = [f"IER = {ier_final}/100", ""]
        for name, s in layer_scores.items():
            lines.append(
                f"  {name}: {s['score_0_100']}/100 × {s['weight']:.0%} = {s['weighted'] * 100:.1f}"
            )
        if errors:
            lines += ["", "Warnings:"] + [f"  - {e}" for e in errors]

        logger.info(f"IER calculado para funcionario {input.funcionario_id}: {ier_final}")

        return {
            "ier": ier_final,
            "layer_scores": layer_scores,
            "breakdown": "\n".join(lines),
            "timestamp": datetime.now().isoformat(),
            "funcionario_id": input.funcionario_id,
        }


class IERCalculatorV3(IERCalculator):
    """
    IER Calculator con pesos por-layer configurables en construcción.

    Permite sobrescribir los pesos declarados en cada ScoringLayer,
    útil para activar Layer3 (weight=0.0 por defecto) sin modificar la clase.
    """

    def __init__(self, layers: List[ScoringLayer], weights: Dict[str, float] = None):
        self.layers = layers
        self.custom_weights = weights or {}
        self._validate_weights()

    def _validate_weights(self) -> None:
        if self.custom_weights:
            total = sum(self.custom_weights.values())
        else:
            total = sum(layer.weight for layer in self.layers)
        if not (0.95 <= total <= 1.05):
            raise ValueError(f"Pesos no suman 1.0: {total:.3f}")

    async def calculate(self, input: ScoringInput) -> Dict[str, Any]:
        layer_scores: Dict[str, Any] = {}
        total_score = 0.0
        errors: List[str] = []
        enabled_layers: List[str] = []

        for layer in self.layers:
            weight = self.custom_weights.get(layer.name, layer.weight)
            try:
                can_score = await layer.validate_input(input)
                score = await layer.score(input) if can_score else 0.0
                score = max(0.0, min(1.0, score))
                weighted = score * weight
                total_score += weighted
                enabled_layers.append(layer.name)
                layer_scores[layer.name] = {
                    "score": round(score, 3),
                    "weight": weight,
                    "weighted": round(weighted, 3),
                    "score_0_100": round(score * 100, 1),
                }
            except ScoringLayerException as e:
                logger.error(f"{layer.name} error: {e}")
                errors.append(f"{layer.name}: {e}")
                layer_scores[layer.name] = {
                    "score": 0.0,
                    "weight": weight,
                    "weighted": 0.0,
                    "error": str(e),
                }

        ier_final = round(total_score * 100, 1)
        lines = [f"IER = {ier_final}/100 (v3 con {len(enabled_layers)} layers)", ""]
        for name, s in layer_scores.items():
            lines.append(
                f"  {name}: {s['score_0_100']}/100 × {s['weight']:.0%} = {s['weighted'] * 100:.1f}"
            )
        if errors:
            lines += ["", "Warnings:"] + [f"  - {e}" for e in errors]

        logger.info(f"IER v3 para funcionario {input.funcionario_id}: {ier_final}")

        return {
            "ier": ier_final,
            "layer_scores": layer_scores,
            "breakdown": "\n".join(lines),
            "timestamp": datetime.now().isoformat(),
            "funcionario_id": input.funcionario_id,
            "enabled_layers": enabled_layers,
            "version": "v3-layer3-ready",
        }
