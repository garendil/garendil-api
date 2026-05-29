import pytest
import numpy as np

from app.services.scoring.interfaces import ScoringLayer, ScoringInput
from app.services.scoring.layer1 import Layer1Scorer
from app.services.scoring.layer2 import Layer2Scorer


def _full_input(funcionario_id: int = 1) -> ScoringInput:
    return ScoringInput(
        funcionario_id=funcionario_id,
        features={
            "contratos_cantidad": 5.0,
            "empresas_nuevas": 0.0,
            "monto_total": 100_000.0,
            "monto_presupuesto": 100_000.0,
            "exoneraciones": 0.0,
            "patrimonio_delta": 10_000.0,
            "monto_promedio": 20_000.0,
            "varianza_montos": 5_000.0,
            "concentracion_empresas": 0.3,
            "exoneraciones_ratio": 0.0,
            "edad_en_cargo_dias": 365.0,
        },
    )


@pytest.mark.asyncio
async def test_layer1_implements_interface():
    scorer = Layer1Scorer()
    assert isinstance(scorer, ScoringLayer)
    assert scorer.name == "Layer1"
    assert 0.0 < scorer.weight <= 1.0
    assert isinstance(scorer.min_required_features, set)


@pytest.mark.asyncio
async def test_layer2_implements_interface():
    scorer = Layer2Scorer()
    assert isinstance(scorer, ScoringLayer)
    assert scorer.name == "Layer2"
    assert 0.0 < scorer.weight <= 1.0
    assert isinstance(scorer.min_required_features, set)


@pytest.mark.asyncio
async def test_layer1_score_returns_0_to_1():
    scorer = Layer1Scorer()
    score = await scorer.score(_full_input())
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_layer2_score_returns_0_to_1():
    scorer = Layer2Scorer()
    np.random.seed(42)
    X = np.random.rand(30, 6)
    scorer.fit(X)

    score = await scorer.score(_full_input())
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_layer1_rejects_incomplete_input():
    scorer = Layer1Scorer()
    incomplete = ScoringInput(
        funcionario_id=1,
        features={"contratos_cantidad": 5.0},
    )
    assert await scorer.validate_input(incomplete) is False


@pytest.mark.asyncio
async def test_ier_weights_sum_to_1():
    total = Layer1Scorer().weight + Layer2Scorer().weight
    assert 0.95 <= total <= 1.05, f"Pesos no suman 1.0: {total}"


@pytest.mark.asyncio
async def test_layer1_is_idempotent():
    scorer = Layer1Scorer()
    inp = _full_input()
    score1 = await scorer.score(inp)
    score2 = await scorer.score(inp)
    assert score1 == score2
