import numpy as np
from app.services.scoring.layer2 import Layer2Scorer, _IsolationForest


def test_isolation_forest_outlier_scores_higher():
    """Outlier debe tener score mayor que puntos normales."""
    X = np.array([
        [1.0, 1.0],
        [1.0, 2.0],
        [2.0, 1.0],
        [2.0, 2.0],
        [100.0, 100.0],  # outlier
    ])

    model = _IsolationForest(n_trees=10)
    model.fit(X)
    scores = model.predict(X)

    assert scores[-1] > scores[0], (
        f"Outlier score {scores[-1]:.3f} should exceed normal score {scores[0]:.3f}"
    )


def test_isolation_forest_normal_data_low_scores():
    """Datos normales (gaussianos) deben producir scores bajos en promedio."""
    np.random.seed(42)
    X = np.random.normal(0, 1, (100, 5))

    model = _IsolationForest(n_trees=20)
    model.fit(X)
    scores = model.predict(X)

    assert np.mean(scores) < 0.7, (
        f"Mean score {np.mean(scores):.3f} too high for normal data"
    )


def test_isolation_forest_untrained_returns_zeros():
    """Modelo sin entrenar retorna ceros."""
    model = _IsolationForest()
    X = np.array([[1.0, 2.0], [3.0, 4.0]])
    scores = model.predict(X)
    assert np.all(scores == 0.0)


def test_layer2_scorer_fit_and_predict():
    """Layer2Scorer entrena y predice correctamente."""
    np.random.seed(42)
    scorer = Layer2Scorer()
    X = np.random.rand(30, 6)
    scorer.fit(X)
    assert scorer.is_trained()
