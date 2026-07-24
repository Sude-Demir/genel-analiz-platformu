"""borsa_model.py için birim testleri.

Ağ çağrısı içermez; sentetik fiyat serileriyle çalışır. Zaman serisi
disiplininin (sızıntısız backtest, naif baseline karşılaştırması) korunduğunu
ve yetersiz/dejenere veri durumlarının istisna fırlatmadan ele alındığını
doğrular.
"""
import numpy as np
import pandas as pd
import pytest

from borsa_model import (
    FEATURE_COLUMNS,
    MIN_SAMPLES_FOR_BACKTEST,
    build_features,
    train_price_direction_model,
)


def _synthetic_price_df(n=150, seed=42):
    """Rastgele yürüyüş (random walk) tabanlı, hem yükseliş hem düşüş içeren
    sentetik bir OHLCV serisi üretir — gerçek fiyat verisi gibi her iki sınıfı
    (yükseliş/düşüş) da barındırır."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(loc=0.0005, scale=0.015, size=n)
    close = 100 * np.cumprod(1 + returns)
    high = close * (1 + rng.uniform(0, 0.01, size=n))
    low = close * (1 - rng.uniform(0, 0.01, size=n))
    open_ = close * (1 + rng.normal(0, 0.003, size=n))
    volume = rng.integers(500_000, 2_000_000, size=n)
    return pd.DataFrame({
        "tarih": pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC"),
        "açılış": open_, "yüksek": high, "düşük": low, "kapanış": close, "hacim": volume,
    })


def _monotonic_rising_df(n=150):
    closes = [100 + i * 0.5 for i in range(n)]
    return pd.DataFrame({
        "tarih": pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1_000_000] * n,
    })


# --- build_features ----------------------------------------------------

def test_build_features_returns_empty_for_insufficient_data():
    df = pd.DataFrame(columns=["tarih", "açılış", "yüksek", "düşük", "kapanış", "hacim"])
    X, y = build_features(df)
    assert X.empty and y.empty


def test_build_features_aligns_X_and_y_without_nans():
    df = _synthetic_price_df(n=150)
    X, y = build_features(df)
    assert len(X) == len(y)
    assert len(X) > 0
    assert not X.isna().any().any()
    assert set(X.columns) == set(FEATURE_COLUMNS)
    assert set(y.unique()).issubset({0, 1})


def test_build_features_last_row_excluded_since_next_day_target_unknown():
    df = _synthetic_price_df(n=150)
    X, _ = build_features(df)
    # Son satırın hedefi (ertesi gün) bilinemeyeceğinden kullanılabilir sette yer almamalı.
    assert len(X) < len(df)


# --- train_price_direction_model: yetersiz/dejenere veri ----------------

def test_train_price_direction_model_reports_insufficient_data():
    df = _synthetic_price_df(n=30)
    result = train_price_direction_model(df)
    assert result["ok"] is False
    assert any("yeterli" in w.lower() for w in result["warnings"])


def test_train_price_direction_model_reports_single_class_target():
    df = _monotonic_rising_df(n=150)
    result = train_price_direction_model(df)
    # Fiyat kesintisiz yükseldiğinden hedef hep 1'dir -> sınıflandırma anlamsız.
    assert result["ok"] is False
    assert any("yön değişmediğinden" in w for w in result["warnings"])


def test_train_price_direction_model_handles_empty_df_without_exception():
    df = pd.DataFrame(columns=["tarih", "açılış", "yüksek", "düşük", "kapanış", "hacim"])
    result = train_price_direction_model(df)
    assert result["ok"] is False


# --- train_price_direction_model: gerçek eğitim + backtest ---------------

def test_train_price_direction_model_runs_backtest_with_baseline_comparison():
    df = _synthetic_price_df(n=150)
    result = train_price_direction_model(df)

    assert result["ok"] is True
    assert MIN_SAMPLES_FOR_BACKTEST <= result["n_samples"]

    bt = result["backtest"]
    assert 0.0 <= bt["accuracy"] <= 1.0
    assert 0.0 <= bt["baseline_accuracy"] <= 1.0
    assert bt["n_folds"] >= 1
    # Out-of-sample örnek sayısı, TimeSeriesSplit'in ilk katı yalnızca eğitim için
    # ayırması nedeniyle toplam kullanılabilir örnek sayısından kesinlikle azdır.
    assert bt["n_oos_samples"] < result["n_samples"]
    assert len(bt["confusion_matrix"]) == 2

    assert isinstance(result["beats_baseline"], bool)


def test_train_price_direction_model_next_day_prediction_shape():
    df = _synthetic_price_df(n=150)
    result = train_price_direction_model(df)

    next_day = result["next_day"]
    assert next_day["yön"] in {"Yükseliş", "Düşüş"}
    assert 0.0 <= next_day["yükseliş_olasılığı"] <= 1.0


def test_train_price_direction_model_feature_importances_sum_to_one():
    df = _synthetic_price_df(n=150)
    result = train_price_direction_model(df)

    importances = result["feature_importances"]
    assert set(importances) == set(FEATURE_COLUMNS)
    assert round(sum(importances.values()), 6) == 1.0


def test_train_price_direction_model_is_deterministic_for_same_input():
    """RandomForestClassifier n_jobs=-1 kullandığından paralel ağaç oylarının toplanma
    sırası çalıştırmalar arası değişebilir; bu, olasılıklarda son ondalık basamakta
    (float non-associativity) ihmal edilebilir farklara yol açabilir. Bu yüzden tam
    eşitlik yerine yakınlık (tolerans) karşılaştırılır."""
    df = _synthetic_price_df(n=150)
    result_a = train_price_direction_model(df)
    result_b = train_price_direction_model(df)
    assert result_a["next_day"]["yön"] == result_b["next_day"]["yön"]
    assert result_a["next_day"]["yükseliş_olasılığı"] == pytest.approx(
        result_b["next_day"]["yükseliş_olasılığı"], abs=1e-9
    )
    assert result_a["backtest"]["accuracy"] == pytest.approx(result_b["backtest"]["accuracy"], abs=1e-9)
