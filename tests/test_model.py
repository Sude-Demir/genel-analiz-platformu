import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier

from model import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    build_explainer,
    build_pipeline,
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
