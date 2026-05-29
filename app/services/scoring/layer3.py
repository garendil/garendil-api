import logging
import numpy as np
from typing import Optional, Dict

from joblib import dump, load
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from app.services.scoring.interfaces import ScoringLayer, ScoringInput, ScoringLayerException

logger = logging.getLogger(__name__)


class Layer3Scorer(ScoringLayer):
    """
    Capa 3: ML Supervisado (Random Forest)

    Requiere datos etiquetados del Poder Judicial para entrenar.
    Output: Probabilidad [0-1] de caso confirmado.
    Retorna 0.0 hasta estar entrenado (safe default).
    """

    _FEATURE_NAMES = [
        "contratos_cantidad",
        "monto_promedio",
        "varianza_montos",
        "concentracion_empresas",
        "exoneraciones_ratio",
        "edad_en_cargo_dias",
        "procesos_penales",
        "procesos_disciplinarios",
        "patrimonio_delta",
    ]

    def __init__(
        self,
        model: Optional[RandomForestClassifier] = None,
        scaler: Optional[StandardScaler] = None,
        model_path: Optional[str] = None,
    ):
        self._model = model
        self._scaler = scaler
        self._is_trained = model is not None and scaler is not None
        self._model_path = model_path

    @property
    def name(self) -> str:
        return "Layer3"

    @property
    def weight(self) -> float:
        return 0.0  # disabled until trained; IERCalculator must handle 0-weight layers

    @property
    def min_required_features(self) -> set:
        return set(self._FEATURE_NAMES)

    async def validate_input(self, input: ScoringInput) -> bool:
        if not self._is_trained:
            logger.warning("Layer3: modelo no entrenado — retornará 0.0")
            return False
        missing = self.min_required_features - set(input.features.keys())
        if missing:
            logger.warning(f"Layer3: features faltantes: {missing}")
            return False
        return True

    async def score(self, input: ScoringInput) -> float:
        if not self._is_trained:
            return 0.0
        if not await self.validate_input(input):
            raise ScoringLayerException(
                f"Layer3: features insuficientes para funcionario {input.funcionario_id}"
            )
        X = np.array([[input.get_feature(f) for f in self._FEATURE_NAMES]])
        X_scaled = self._scaler.transform(X)
        try:
            proba = float(self._model.predict_proba(X_scaled)[0][1])
            logger.info(f"Layer3 funcionario {input.funcionario_id}: {proba:.3f}")
            return proba
        except Exception as e:
            logger.error(f"Layer3 prediction error: {e}")
            return 0.0

    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: list = None) -> None:
        if X.shape[0] < 50:
            logger.warning(f"Layer3: pocos samples ({X.shape[0]}), omitiendo fit")
            return
        if len(np.unique(y)) != 2:
            logger.warning("Layer3: labels no binarios, omitiendo fit")
            return
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X)
        self._model = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced",
        )
        self._model.fit(X_scaled, y)
        self._is_trained = True
        if feature_names:
            for name, imp in sorted(
                zip(feature_names, self._model.feature_importances_),
                key=lambda x: x[1],
                reverse=True,
            ):
                logger.info(f"  {name}: {imp:.3f}")
        logger.info(f"Layer3 entrenado con {X.shape[0]} samples")

    def save_model(self, path: str) -> None:
        if not self._is_trained:
            raise ValueError("No hay modelo entrenado para guardar")
        dump({"model": self._model, "scaler": self._scaler}, path)
        logger.info(f"Layer3 model guardado en {path}")

    @classmethod
    def load_model(cls, path: str) -> "Layer3Scorer":
        data = load(path)
        return cls(model=data["model"], scaler=data["scaler"], model_path=path)

    def is_trained(self) -> bool:
        return self._is_trained

    def get_feature_importance(self) -> Dict[str, float]:
        if not self._is_trained:
            return {}
        return dict(zip(self._FEATURE_NAMES, self._model.feature_importances_.tolist()))
