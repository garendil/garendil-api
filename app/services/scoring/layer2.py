import logging
import numpy as np
from typing import Optional, List

from app.services.scoring.interfaces import ScoringLayer, ScoringInput, ScoringLayerException

logger = logging.getLogger(__name__)

# Feature order is fixed — training and inference must use the same sequence.
_FEATURE_NAMES: List[str] = [
    "contratos_cantidad",
    "monto_promedio",
    "varianza_montos",
    "concentracion_empresas",
    "exoneraciones_ratio",
    "edad_en_cargo_dias",
]


class _IsolationForest:
    """
    Implementación propia de Isolation Forest (sin dependencias externas).
    Outliers requieren menos splits → score > 0.5 indica anomalía.
    """

    def __init__(self, n_trees: int = 50, max_depth: int = 10, contamination: float = 0.1):
        self.n_trees = n_trees
        self.max_depth = max_depth
        self.contamination = contamination
        self.trees: list = []

    def _build_tree(self, X: np.ndarray, depth: int = 0) -> dict:
        if depth >= self.max_depth or X.shape[0] <= 1:
            return {"leaf": True, "size": X.shape[0]}
        feat = np.random.randint(0, X.shape[1])
        lo, hi = X[:, feat].min(), X[:, feat].max()
        if lo == hi:
            return {"leaf": True, "size": X.shape[0]}
        split = np.random.uniform(lo, hi)
        left = X[X[:, feat] < split]
        right = X[X[:, feat] >= split]
        if left.shape[0] == 0 or right.shape[0] == 0:
            return {"leaf": True, "size": X.shape[0]}
        return {
            "leaf": False,
            "feat": feat,
            "val": split,
            "left": self._build_tree(left, depth + 1),
            "right": self._build_tree(right, depth + 1),
        }

    def fit(self, X: np.ndarray) -> None:
        self.trees = []
        size = min(256, X.shape[0])
        for _ in range(self.n_trees):
            idx = np.random.choice(X.shape[0], size=size, replace=False)
            self.trees.append(self._build_tree(X[idx]))

    def _path_len(self, x: np.ndarray, node: dict, depth: int = 0) -> float:
        if node["leaf"]:
            n = node.get("size", 1)
            return depth + (2 * (np.log(n - 1) + 0.5772156649) - 2 * (n - 1) / n if n > 1 else 0)
        if x[node["feat"]] < node["val"]:
            return self._path_len(x, node["left"], depth + 1)
        return self._path_len(x, node["right"], depth + 1)

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.trees:
            return np.zeros(X.shape[0])
        c = 2 * (np.log(255) + 0.5772156649) - 2 * 255 / 256
        scores = np.zeros(X.shape[0])
        for i, x in enumerate(X):
            avg = np.mean([self._path_len(x, t) for t in self.trees])
            scores[i] = 2 ** (-avg / c) if c > 0 else 0.5
        return scores


class Layer2Scorer(ScoringLayer):
    """
    Capa 2: Detección de anomalías sin etiquetas (Isolation Forest).
    Si el modelo no está entrenado retorna 0.0 (score neutro).
    """

    def __init__(self):
        self._model: Optional[_IsolationForest] = None
        self._is_trained = False

    @property
    def name(self) -> str:
        return "Layer2"

    @property
    def weight(self) -> float:
        return 0.3

    @property
    def min_required_features(self) -> set:
        return set(_FEATURE_NAMES)

    async def validate_input(self, input: ScoringInput) -> bool:
        if not self._is_trained:
            logger.warning("Layer2: modelo no entrenado — retornará 0.0")
            return False
        missing = self.min_required_features - set(input.features.keys())
        if missing:
            logger.warning(f"Layer2: features faltantes: {missing}")
            return False
        return True

    async def score(self, input: ScoringInput) -> float:
        if not self._is_trained:
            return 0.0
        if not await self.validate_input(input):
            raise ScoringLayerException(
                f"Layer2: features insuficientes para funcionario {input.funcionario_id}"
            )
        X = np.array([[input.get_feature(f) for f in _FEATURE_NAMES]])
        X_norm = np.log1p(X)
        result = float(self._model.predict(X_norm)[0])
        logger.info(f"Layer2 funcionario {input.funcionario_id}: {result:.3f}")
        return result

    def fit(self, X: np.ndarray) -> None:
        if X.shape[0] < 2:
            logger.warning(f"Layer2: insuficientes muestras ({X.shape[0]}), omitiendo fit")
            return
        self._model = _IsolationForest(n_trees=50, contamination=0.1)
        X_norm = np.log1p(X)
        self._model.fit(X_norm)
        self._is_trained = True
        logger.info(f"Layer2 entrenado con {X.shape[0]} muestras")

    def is_trained(self) -> bool:
        return self._is_trained

    async def score_funcionario(self, funcionario_id: int) -> float:
        """Compatibilidad con código legado (v0.3 API)."""
        return 0.0

    async def train(self) -> None:
        """Compatibilidad con código legado — reentrenamiento vía DB."""
        logger.info("Layer2.train() llamado sin DB — usar Layer2Scorer.fit(X) directamente")
