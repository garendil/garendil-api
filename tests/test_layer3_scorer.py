import os
import tempfile

import numpy as np
import pytest

from app.services.scoring.interfaces import ScoringInput
from app.services.scoring.layer3 import Layer3Scorer


def _make_input(**overrides) -> ScoringInput:
    defaults = {
        "contratos_cantidad": 5.0,
        "monto_promedio": 20000.0,
        "varianza_montos": 5000.0,
        "concentracion_empresas": 0.3,
        "exoneraciones_ratio": 0.1,
        "edad_en_cargo_dias": 365.0,
        "procesos_penales": 1.0,
        "procesos_disciplinarios": 0.0,
        "patrimonio_delta": 50000.0,
    }
    defaults.update(overrides)
    return ScoringInput(funcionario_id=1, features=defaults)


@pytest.mark.asyncio
async def test_layer3_implements_interface():
    scorer = Layer3Scorer()
    assert scorer.name == "Layer3"
    assert isinstance(scorer.min_required_features, set)
    assert scorer.weight == 0.0


@pytest.mark.asyncio
async def test_layer3_untrained_returns_zero():
    scorer = Layer3Scorer()
    score = await scorer.score(_make_input())
    assert score == 0.0


@pytest.mark.asyncio
async def test_layer3_training():
    np.random.seed(42)
    X = np.random.rand(100, 9)
    y = np.random.randint(0, 2, 100)

    scorer = Layer3Scorer()
    scorer.fit(X, y)

    assert scorer.is_trained()
    assert scorer._model is not None
    assert scorer._scaler is not None


@pytest.mark.asyncio
async def test_layer3_score_bounds():
    np.random.seed(0)
    X = np.random.rand(60, 9)
    y = np.array([0] * 30 + [1] * 30)

    scorer = Layer3Scorer()
    scorer.fit(X, y)

    score = await scorer.score(_make_input())
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_layer3_model_persistence():
    np.random.seed(7)
    X = np.random.rand(60, 9)
    y = np.array([0] * 30 + [1] * 30)

    scorer1 = Layer3Scorer()
    scorer1.fit(X, y)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
        temp_path = f.name

    try:
        scorer1.save_model(temp_path)
        scorer2 = Layer3Scorer.load_model(temp_path)
        assert scorer2.is_trained()

        inp = _make_input()
        score1 = await scorer1.score(inp)
        score2 = await scorer2.score(inp)
        assert score1 == score2
    finally:
        os.unlink(temp_path)
