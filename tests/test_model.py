import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.model_selection import StratifiedKFold, train_test_split

from model import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    build_candidate_pipelines,
    build_explainer,
    build_pipeline,
    compute_calibration_curve,
    compute_learning_curve,
    evaluate_predictions,
    explain_batch,
)


def _synthetic_frame(n=20, seed=42):
    rng = np.random.default_rng(seed)
    data = {kolon: rng.integers(1, 10, n) for kolon in NUMERIC_FEATURES}
    for kolon in CATEGORICAL_FEATURES:
        data[kolon] = rng.choice(["A", "B"], n)
    return pd.DataFrame(data)


def test_pipeline_fits_and_predicts():
    X = _synthetic_frame()
    y = pd.Series([0, 1] * (len(X) // 2))

    pipeline = build_pipeline()
    pipeline.fit(X, y)

    preds = pipeline.predict(X)
    assert len(preds) == len(X)

    proba = pipeline.predict_proba(X)
    assert proba.shape == (len(X), 2)


def test_pipeline_handles_unknown_category():
    X = _synthetic_frame()
    y = pd.Series([0, 1] * (len(X) // 2))
    pipeline = build_pipeline()
    pipeline.fit(X, y)

    X_yeni = X.copy()
    X_yeni.loc[0, CATEGORICAL_FEATURES[0]] = "EGITIMDE_OLMAYAN_DEGER"
    # OneHotEncoder(handle_unknown="ignore") sayesinde hata fırlatmamalı
    pipeline.predict(X_yeni)


def test_pipeline_uses_lightgbm():
    pipeline = build_pipeline()
    assert isinstance(pipeline.named_steps["model"], LGBMClassifier)


def test_shap_explainer_works_with_lightgbm():
    X = _synthetic_frame(n=40)
    y = pd.Series([0, 1] * (len(X) // 2))
    pipeline = build_pipeline()
    pipeline.fit(X, y)

    explainer = build_explainer(pipeline)
    shap_df = explain_batch(pipeline, explainer, X)

    assert shap_df.shape[0] == len(X)
    assert not shap_df.isna().any().any()


def test_build_candidate_pipelines_are_tree_based_and_fit():
    """Adaylar (LightGBM, RandomForest) `.feature_importances_` sağlamalı ki mevcut
    SHAP/Aksiyon Merkezi zinciri hangisi seçilirse seçilsin değişmeden çalışsın."""
    X = _synthetic_frame(n=40)
    y = pd.Series([0, 1] * (len(X) // 2))

    candidates = build_candidate_pipelines()
    assert set(candidates) == {"LightGBM", "RandomForest"}

    for name, (pipeline, param_dist, n_iter) in candidates.items():
        assert isinstance(param_dist, dict) and param_dist
        assert n_iter > 0
        pipeline.fit(X, y)
        assert hasattr(pipeline.named_steps["model"], "feature_importances_"), name
        preds = pipeline.predict(X)
        assert len(preds) == len(X)


def test_evaluate_predictions_returns_expected_metrics():
    y_test = pd.Series([0, 0, 1, 1])
    y_pred = np.array([0, 1, 1, 1])
    y_proba = np.array([0.1, 0.6, 0.7, 0.9])

    metrics = evaluate_predictions(y_test, y_pred, y_proba)

    assert metrics["accuracy"] == 0.75
    assert 0 <= metrics["roc_auc"] <= 1
    assert len(metrics["confusion_matrix"]) == 2
    assert set(metrics["roc_curve"]) == {"fpr", "tpr"}
    assert "Ayrılıyor" in metrics["report"]


def test_compute_learning_curve_shape():
    X = _synthetic_frame(n=100)
    y = pd.Series([0, 1] * (len(X) // 2))
    pipeline = build_pipeline()
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)

    result = compute_learning_curve(pipeline, X, y, cv)

    assert len(result["train_sizes"]) == len(result["train_scores_mean"]) == len(result["test_scores_mean"])
    assert len(result["train_sizes"]) == 5


def test_compute_calibration_curve_shape():
    X = _synthetic_frame(n=100)
    y = pd.Series([0, 1] * (len(X) // 2))
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, stratify=y, random_state=42)

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    result = compute_calibration_curve(y_test, y_proba, n_bins=5)

    assert set(result) == {"prob_true", "prob_pred"}
    assert len(result["prob_true"]) == len(result["prob_pred"])
    assert len(result["prob_true"]) <= 5
