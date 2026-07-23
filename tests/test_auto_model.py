"""auto_model.py için birim testleri.

Bu modülün önceden hiç testi yoktu; burada hem temel yardımcı fonksiyonlar
(infer_column_types, detect_task_type) hem de yeni eklenen karışıklık
matrisi/ROC eğrisi çıktısı (train_auto_model) için kapsam eklenmiştir.
"""
import numpy as np
import pandas as pd
import pytest

from auto_model import detect_task_type, infer_column_types, train_auto_model


def test_infer_column_types_separates_numeric_and_categorical():
    df = pd.DataFrame({
        "yas": [25, 30, 35],
        "departman": ["Satış", "Üretim", "Satış"],
        "maas": [5000.0, 6000.0, 5500.0],
    })
    numeric, categorical = infer_column_types(df)
    assert set(numeric) == {"yas", "maas"}
    assert categorical == ["departman"]


def test_infer_column_types_respects_exclude():
    df = pd.DataFrame({"yas": [25, 30], "hedef": [0, 1]})
    numeric, categorical = infer_column_types(df, exclude=["hedef"])
    assert numeric == ["yas"]
    assert categorical == []


def test_detect_task_type_classification_for_low_cardinality_numeric():
    assert detect_task_type(pd.Series([0, 1, 0, 1, 1])) == "classification"


def test_detect_task_type_regression_for_high_cardinality_numeric():
    assert detect_task_type(pd.Series(range(20))) == "regression"


def _binary_classification_df(n=80, seed=42):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    y = (x1 + x2 > 0).astype(int)
    kategori = rng.choice(["A", "B"], size=n)
    return pd.DataFrame({"x1": x1, "x2": x2, "kategori": kategori, "hedef": y})


def test_train_auto_model_binary_classification_returns_confusion_matrix_and_roc_curve():
    df = _binary_classification_df()
    result = train_auto_model(df, "hedef", categorical_features=["kategori"], numeric_features=["x1", "x2"])

    assert result["task_type"] == "classification"
    assert result["n_classes"] == 2

    cm = result["confusion_matrix"]
    assert cm is not None
    assert len(cm) == 2 and all(len(row) == 2 for row in cm)
    # test seti boyutu train_test_split(test_size=0.2) ile belirleniyor
    assert sum(sum(row) for row in cm) == pytest.approx(len(df) * 0.2, abs=1)

    roc = result["roc_curve"]
    assert roc is not None
    assert len(roc["fpr"]) == len(roc["tpr"])
    assert roc["fpr"][0] == 0.0 and roc["fpr"][-1] == 1.0


def _multiclass_df(n=90, seed=1):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    y = np.select([x1 < -0.5, x1 < 0.5], [0, 1], default=2)
    kategori = rng.choice(["A", "B", "C"], size=n)
    return pd.DataFrame({"x1": x1, "kategori": kategori, "hedef": y})


def test_train_auto_model_multiclass_classification_has_confusion_matrix_but_no_roc_curve():
    df = _multiclass_df()
    result = train_auto_model(df, "hedef", categorical_features=["kategori"], numeric_features=["x1"])

    assert result["n_classes"] == 3
    cm = result["confusion_matrix"]
    assert cm is not None
    assert len(cm) == 3 and all(len(row) == 3 for row in cm)
    # ROC eğrisi yalnızca ikili (binary) sınıflandırmada üretilir.
    assert result["roc_curve"] is None


def _regression_df(n=60, seed=7):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    y = x1 * 3 + rng.normal(scale=0.1, size=n)
    return pd.DataFrame({"x1": x1, "hedef": y})


def test_train_auto_model_regression_has_no_confusion_matrix_or_roc_curve():
    df = _regression_df()
    result = train_auto_model(df, "hedef", categorical_features=[], numeric_features=["x1"])

    assert result["task_type"] == "regression"
    assert result["confusion_matrix"] is None
    assert result["roc_curve"] is None
