import logging
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Funcionario, Proceso
from app.services.scoring.layer3 import Layer3Scorer
from app.services.scoring.feature_extractor import ScoringFeatureExtractor

logger = logging.getLogger(__name__)


class Layer3Trainer:
    """
    Entrena Layer3 usando datos del Poder Judicial.

    Funcionarios con procesos penales CONFIRMADOS → y=1
    Funcionarios sin procesos penales               → y=0
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.extractor = ScoringFeatureExtractor(db)

    async def prepare_training_data(self, min_samples: int = 100) -> tuple:
        """Retorna (X, y, funcionario_ids, feature_names)."""
        logger.info("Preparando datos para Layer3...")

        result = await self.db.execute(
            select(Funcionario)
            .join(Proceso, Proceso.acusado_id == Funcionario.id)
            .where(Proceso.estado == "CONFIRMADO")
            .distinct()
        )
        funcionarios_riesgo = result.scalars().all()

        result = await self.db.execute(
            select(Funcionario).limit(max(len(funcionarios_riesgo), min_samples // 2))
        )
        todos = result.scalars().all()
        ids_riesgo = {f.id for f in funcionarios_riesgo}
        funcionarios_limpios = [f for f in todos if f.id not in ids_riesgo][
            : len(funcionarios_riesgo)
        ]

        logger.info(f"Riesgo: {len(funcionarios_riesgo)}, Limpios: {len(funcionarios_limpios)}")

        if len(funcionarios_riesgo) < min_samples // 2:
            logger.warning(
                f"Pocos samples de riesgo ({len(funcionarios_riesgo)}). Min: {min_samples // 2}"
            )

        X_list, y_list, func_ids = [], [], []
        feature_names = None

        for func, label in [*[(f, 1) for f in funcionarios_riesgo], *[(f, 0) for f in funcionarios_limpios]]:
            try:
                input_data = await self.extractor.extract_features(func.id)
                if feature_names is None:
                    feature_names = list(input_data.features.keys())
                X_list.append(list(input_data.features.values()))
                y_list.append(label)
                func_ids.append(func.id)
            except Exception as e:
                logger.warning(f"Error extrayendo features para {func.id}: {e}")

        X = np.array(X_list) if X_list else np.empty((0, 0))
        y = np.array(y_list)
        logger.info(f"Datos preparados: {X.shape[0]} samples, balance: {int(np.sum(y))} positivos")
        return X, y, func_ids, feature_names

    async def train(self, model_path: str = None, min_samples: int = 100) -> Layer3Scorer:
        X, y, func_ids, feature_names = await self.prepare_training_data(min_samples=min_samples)

        if X.shape[0] < min_samples:
            raise ValueError(f"No hay suficientes samples: {X.shape[0]} < {min_samples}")

        scorer = Layer3Scorer()
        scorer.fit(X, y, feature_names=feature_names)

        if model_path and scorer.is_trained():
            scorer.save_model(model_path)
            logger.info(f"Modelo guardado en {model_path}")

        return scorer
