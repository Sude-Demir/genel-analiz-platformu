"""Fiyat geçmişinden makine öğrenmesi tabanlı kısa vadeli (ertesi gün) yön tahmini.

`borsa_analysis.py`'deki kural tabanlı `predict_short_term_outlook()`'tan kasıtlı
olarak AYRIDIR: burada teknik göstergeler sabit eşiklerle yorumlanmaz, bunun yerine
geçmiş fiyat davranışından türetilen özelliklerle bir sınıflandırıcı EĞİTİLİR ve
modelin geleceği gerçekten öngörüp öngöremediği zaman serisine uygun (sızıntısız)
bir backtest ile ölçülür.

Zaman serisi disiplini — bu modülün varlık sebebi:
  * Model DOĞRULAMASI asla rastgele bölme (`train_test_split(shuffle=True)`) ile
    yapılmaz; `TimeSeriesSplit` ile daima "geçmişte eğit → gelecekte test et"
    (walk-forward) düzeni kullanılır. Rastgele bölme, modelin geleceği görüp
    geçmişi tahmin etmesine (veri sızıntısı) yol açar ve gerçekçi olmayan yüksek
    skorlar üretir.
  * Sonuç daima naif bir temel çizgiyle (baseline: her zaman eğitim setindeki
    çoğunluk sınıfını tahmin et) karşılaştırılır. Ertesi gün yön tahmini doğası
    gereği zordur; model baseline'ı geçemiyorsa bu dürüstçe raporlanır.

Harici bir AI/LLM servisine bağımlı değildir; scikit-learn ile yerelde çalışır.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, precision_score
from sklearn.model_selection import TimeSeriesSplit

from borsa_analysis import compute_technical_indicators

# Backtest için gereken en az kullanılabilir örnek sayısı. TimeSeriesSplit(5)
# her katta anlamlı bir eğitim/test penceresi bulabilsin diye tutucu bir alt sınır.
MIN_SAMPLES_FOR_BACKTEST = 80
N_SPLITS = 5
MODEL_NAME = "RandomForest"

FEATURE_COLUMNS = [
    "getiri_1", "getiri_2", "getiri_3", "getiri_5",
    "volatilite_5", "volatilite_10",
    "momentum_10",
    "fiyat_sma20_oran", "sma20_sma50_oran",
    "rsi14", "macd_hist",
    "hacim_orani",
]


def _build_model() -> RandomForestClassifier:
    """Yön sınıflandırıcısı. Finansal veri gürültülü ve az olduğundan kasıtlı olarak
    sığ ve güçlü düzenlileştirilmiş bir orman kullanılır (aşırı öğrenmeyi sınırlamak
    için `max_depth=4`, `min_samples_leaf=20`); `feature_importances_` sağladığı için
    hangi özelliğin ne kadar etkili olduğu raporlanabilir."""
    return RandomForestClassifier(
        n_estimators=200, max_depth=4, min_samples_leaf=20,
        class_weight="balanced", random_state=42, n_jobs=-1,
    )


def _feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Ham fiyat geçmişinden özellik kolonlarını ve `hedef` (ertesi gün yön) kolonunu
    üretir; NaN satırları DÜŞÜRMEZ (çağıran taraf eğitim ve tahmin için farklı
    filtreler uygular). `compute_technical_indicators()` tekrar kullanılır.

    Özellikler yalnızca t anına kadarki bilgiden hesaplanır; hedef ise t+1 gününün
    yönüdür — böylece "bugünün özellikleriyle yarını tahmin et" kurgusu korunur ve
    ileriye dönük veri sızıntısı olmaz.
    """
    ind = compute_technical_indicators(df)
    close = ind["kapanış"]
    returns = close.pct_change()

    feat = pd.DataFrame({"tarih": ind["tarih"]})
    feat["getiri_1"] = returns
    feat["getiri_2"] = close.pct_change(2)
    feat["getiri_3"] = close.pct_change(3)
    feat["getiri_5"] = close.pct_change(5)
    feat["volatilite_5"] = returns.rolling(5).std()
    feat["volatilite_10"] = returns.rolling(10).std()
    feat["momentum_10"] = close / close.shift(10) - 1
    feat["fiyat_sma20_oran"] = close / ind["sma20"] - 1
    feat["sma20_sma50_oran"] = ind["sma20"] / ind["sma50"] - 1
    feat["rsi14"] = ind["rsi14"]
    feat["macd_hist"] = ind["macd_hist"]

    volume = ind["hacim"]
    feat["hacim_orani"] = volume / volume.rolling(20, min_periods=5).mean() - 1

    # Hedef: ertesi günün kapanışı bugünden yüksekse 1 (yükseliş), değilse 0.
    feat["hedef"] = (close.shift(-1) > close).astype("float")
    # Son satırın hedefi bilinemez (shift(-1) -> NaN); tahmin satırı olarak ayrılır.
    feat.loc[feat.index[-1], "hedef"] = np.nan
    return feat


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Eğitim için kullanılabilir (özellikleri ve hedefi tam olan) satırların
    özellik matrisi (X) ve hedef vektörünü (y) döndürür. Boş/yetersiz df'de boş
    X/y döner; istisna fırlatmaz."""
    if df.empty or len(df) < 2:
        return pd.DataFrame(columns=FEATURE_COLUMNS), pd.Series(dtype="int")

    feat = _feature_frame(df)
    usable = feat.dropna(subset=FEATURE_COLUMNS + ["hedef"])
    X = usable[FEATURE_COLUMNS].reset_index(drop=True)
    y = usable["hedef"].astype(int).reset_index(drop=True)
    return X, y


def _walk_forward_backtest(X: pd.DataFrame, y: pd.Series) -> dict:
    """TimeSeriesSplit ile sızıntısız backtest: her katta geçmişte eğitir, hemen
    sonraki (görülmemiş) pencerede tahmin eder, tüm katların test tahminlerini
    birleştirip out-of-sample metrikleri hesaplar. Model daima aynı eğitim
    setinin çoğunluk sınıfını tahmin eden naif baseline ile karşılaştırılır."""
    n_splits = min(N_SPLITS, len(X) - 1)
    splitter = TimeSeriesSplit(n_splits=n_splits)

    all_true, all_pred, all_base, fold_acc = [], [], [], []
    for train_idx, test_idx in splitter.split(X):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]

        model = _build_model()
        model.fit(X_tr, y_tr)
        pred = model.predict(X_te)

        # Naif baseline: eğitim setinin çoğunluk sınıfını her test satırı için tekrarla.
        majority = int(y_tr.mode().iloc[0]) if not y_tr.mode().empty else 0
        base = np.full(len(y_te), majority)

        all_true.extend(y_te.tolist())
        all_pred.extend(pred.tolist())
        all_base.extend(base.tolist())
        fold_acc.append(float((pred == y_te.values).mean()))

    all_true = np.array(all_true)
    all_pred = np.array(all_pred)
    all_base = np.array(all_base)

    return {
        "accuracy": float((all_pred == all_true).mean()),
        "baseline_accuracy": float((all_base == all_true).mean()),
        "precision_up": float(precision_score(all_true, all_pred, pos_label=1, zero_division=0)),
        "up_rate": float((all_true == 1).mean()),
        "n_folds": n_splits,
        "n_oos_samples": int(len(all_true)),
        "fold_accuracies": fold_acc,
        "confusion_matrix": confusion_matrix(all_true, all_pred, labels=[0, 1]).tolist(),
    }


def train_price_direction_model(df: pd.DataFrame) -> dict:
    """Fiyat geçmişinden ertesi gün yön tahmin modeli eğitir, sızıntısız backtest
    ile değerlendirir ve son güne dayanarak ertesi gün için bir tahmin üretir.

    Dönen sözlükte `ok` anahtarı işlemin başarısını belirtir. Veri yetersizse
    `{"ok": False, "warnings": [...]}` döner; istisna fırlatmaz (borsa modülünün
    "sessiz boş sonuç" sözleşmesiyle uyumlu).
    """
    X, y = build_features(df)
    if len(X) < MIN_SAMPLES_FOR_BACKTEST:
        return {
            "ok": False,
            "warnings": [
                f"ML tahmini için yeterli fiyat geçmişi yok "
                f"(kullanılabilir örnek: {len(X)}, gereken en az: {MIN_SAMPLES_FOR_BACKTEST}). "
                f"Daha uzun bir zaman aralığı seçmeyi deneyin."
            ],
        }

    # Hedefte tek sınıf varsa (ör. dönem boyunca hep yükseliş) sınıflandırma anlamsız.
    if y.nunique() < 2:
        return {"ok": False, "warnings": ["Dönem boyunca yön değişmediğinden model eğitilemedi."]}

    backtest = _walk_forward_backtest(X, y)

    # Nihai model TÜM kullanılabilir geçmişte eğitilir ve son (hedefi bilinmeyen)
    # özellik satırından ertesi gün tahmini üretilir.
    final_model = _build_model()
    final_model.fit(X, y)

    feat = _feature_frame(df)
    last_feat = feat.dropna(subset=FEATURE_COLUMNS).iloc[-1:]
    prob_up = float(final_model.predict_proba(last_feat[FEATURE_COLUMNS])[0, 1])
    direction = "Yükseliş" if prob_up >= 0.5 else "Düşüş"

    importances = pd.Series(final_model.feature_importances_, index=FEATURE_COLUMNS)
    importances = importances.sort_values(ascending=False)

    beats_baseline = backtest["accuracy"] > backtest["baseline_accuracy"]

    return {
        "ok": True,
        "model_name": MODEL_NAME,
        "n_samples": int(len(X)),
        "feature_columns": FEATURE_COLUMNS,
        "backtest": backtest,
        "beats_baseline": beats_baseline,
        "next_day": {
            "yön": direction,
            "yükseliş_olasılığı": prob_up,
            "temel_tarih": str(last_feat["tarih"].iloc[0]),
        },
        "feature_importances": importances.to_dict(),
        "warnings": [],
    }
