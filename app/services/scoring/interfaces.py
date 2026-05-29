from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class ScoringInput:
    """Entrada abstracta para scoring — sin conocer el modelo Funcionario."""

    funcionario_id: int
    features: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_feature(self, name: str, default: float = 0.0) -> float:
        return self.features.get(name, default)

    def validate(self) -> bool:
        required = {"contratos_cantidad", "monto_total", "empresas_nuevas"}
        return required.issubset(set(self.features.keys()))


class ScoringLayer(ABC):
    """Interfaz base para capas de scoring."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def weight(self) -> float:
        pass

    @property
    @abstractmethod
    def min_required_features(self) -> set:
        pass

    @abstractmethod
    async def validate_input(self, input: ScoringInput) -> bool:
        pass

    @abstractmethod
    async def score(self, input: ScoringInput) -> float:
        """Retorna float en [0.0, 1.0]. El agregador escala a 0-100."""
        pass


class ScoringLayerException(Exception):
    pass
