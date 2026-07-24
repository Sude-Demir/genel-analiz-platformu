"""Şirket bahsedilmeleri için makine öğrenmesi tabanlı (TF-IDF + sınıflandırıcı) duygu analizi.

`company_analysis.py`'deki sözlük tabanlı `analyze_sentiment()`'tan kasıtlı olarak
AYRIDIR (bkz. `borsa_model.py`/`borsa_analysis.py` ile aynı desen): burada kelime
sayımı yerine, kullanıcının sağladığı etiketli bir Türkçe metin veri setinden
(`data/raw/test.csv` — 48.965 satır, `text`/`label`/`dataset` kolonları; kaynaklar:
ürün/mağaza yorumları, tweet'ler, HUMIR film yorumu derlemi ve Wikipedia cümleleri)
gerçek bir TF-IDF + LogisticRegression/MultinomialNB sınıflandırıcısı EĞİTİLİR.

Dürüstlük notu — veri setinin bir sınırlılığı: "Nötr" sınıfının neredeyse tamamı
(17.049/17.092) Wikipedia cümlelerinden gelir; bu cümleler yapısal olarak haber
başlığı/yorum gibi kısa, günlük dilden farklıdır. Model bu yüzden "nötr" kavramını
kısmen "ansiklopedik cümle yapısı" olarak öğrenmiş olabilir, "fikir bildirmeyen
kısa haber başlığı" kavramından ziyade. Bu, `train()`'in ürettiği metrik dosyasında
da açıkça not düşülür.

Sözlük yönteminin göremediği bir örüntüyü (olumsuzluk: "hiç iyi değil") yakalayabilmesi
için TfidfVectorizer kasıtlı olarak `ngram_range=(1, 2)` kullanır ve olumsuzluk
kelimelerini (`hiç`, `değil`, `yok` vb.) hiçbir stop-word listesiyle ELEMEZ —
company_analysis.STOPWORDS burada kullanılmaz, çünkü o liste konu çıkarımı için
tasarlanmıştır ve tam da bu olumsuzluk kelimelerini içerir.

Harici bir AI/LLM servisine bağımlı değildir; scikit-learn ile yerelde çalışır.
"""
import json
import os

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from company_analysis import turkish_lower

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "raw", "test.csv")
MODEL_PATH = os.path.join(BASE_DIR, "..", "models", "sentiment_model.joblib")
METRICS_PATH = os.path.join(BASE_DIR, "..", "models", "sentiment_model_metrics.json")

# Veri setindeki İngilizce/yazım-tutarsız etiketler, uygulamanın geri kalanında
# (company_analysis.py: analyze_sentiment, reputation_score, segment_outlook, ...)
# kullanılan Türkçe etiketlerle birebir eşleşsin diye eşlenir — böylece ML yolu,
# sözlük yolunun ürettiği "duygu" kolonunu tüketen hiçbir downstream fonksiyonu
# değiştirmeden kullanabilir.
LABEL_MAP = {"Positive": "Pozitif", "Notr": "Nötr", "Negative": "Negatif"}
LABELS_ORDERED = ["Negatif", "Nötr", "Pozitif"]

MIN_SAMPLES_FOR_TRAINING = 500


def _load_labeled_data() -> pd.DataFrame:
    """Etiketli veri setini okur, etiketleri Türkçe'ye eşler, boş/yinelenen
    metinleri düşürür. Dosya yoksa boş bir DataFrame döner; istisna fırlatmaz."""
    if not os.path.exists(DATA_PATH):
        return pd.DataFrame(columns=["text", "duygu"])

    df = pd.read_csv(DATA_PATH)
    df = df.dropna(subset=["text", "label"])
    df["duygu"] = df["label"].map(LABEL_MAP)
    df = df.dropna(subset=["duygu"])
    df["text"] = df["text"].str.strip()
    df = df[df["text"] != ""]
    df = df.drop_duplicates(subset=["text"])
    return df[["text", "duygu"]].reset_index(drop=True)


def _build_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        preprocessor=turkish_lower,  # str.lower() Türkçe "İ"yi yanlış küçültür (bkz. modül docstring'i)
        lowercase=False,  # yukarıdaki preprocessor zaten küçültüyor; varsayılan (hatalı) lower'ı devre dışı bırak
        ngram_range=(1, 2),
        min_df=3,
        max_features=30000,
        sublinear_tf=True,
    )


def build_candidate_pipelines() -> dict[str, tuple[Pipeline, dict, int]]:
    """Karşılaştırılacak aday model pipeline'larını, hiperparametre arama uzaylarını
    ve RandomizedSearchCV iterasyon sayılarını döndürür (bkz. model.py/borsa_model.py'deki
    aynı 'aday modelleri karşılaştır, en iyisini seç' deseni)."""
    return {
        "LogisticRegression": (
            Pipeline([
                ("tfidf", _build_vectorizer()),
                ("clf", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)),
            ]),
            {"clf__C": [0.1, 0.3, 1.0, 3.0, 10.0]},
            5,
        ),
        "MultinomialNB": (
            Pipeline([
                ("tfidf", _build_vectorizer()),
                ("clf", MultinomialNB()),
            ]),
            {"clf__alpha": [0.1, 0.5, 1.0, 2.0]},
            4,
        ),
    }


def evaluate_predictions(y_test, y_pred) -> dict:
    """Test tahminlerinden accuracy/f1_macro/classification_report/confusion_matrix üretir.

    3 sınıf dengesiz olduğundan (bkz. modül docstring'i: Negatif azınlıkta) seçim
    kriteri olarak accuracy değil `f1_macro` kullanılır — her sınıfın eşit ağırlıkta
    sayılmasını sağlar, aksi halde çoğunluk sınıfını ezberleyen bir model yanıltıcı
    şekilde yüksek accuracy gösterebilir.
    """
    return {
        "accuracy": float((y_pred == y_test).mean()),
        "f1_macro": float(f1_score(y_test, y_pred, average="macro", labels=LABELS_ORDERED, zero_division=0)),
        "report": classification_report(y_test, y_pred, labels=LABELS_ORDERED, output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, y_pred, labels=LABELS_ORDERED).tolist(),
        "labels": LABELS_ORDERED,
    }


def predict_batch(pipeline: Pipeline, texts: list[str]) -> list[tuple[str, float]]:
    """Metin listesi için (etiket, skor) çiftleri döndürür.

    Skor, `analyze_sentiment()`'in ürettiği tam sayı fark skoruyla aynı mertebede
    (yaklaşık -1..+1) kalması için P(Pozitif) - P(Negatif) olasılık farkı olarak
    hesaplanır — böylece `company_analysis._segment_trend()` gibi mevcut eşik tabanlı
    (`fark > 0.3`) fonksiyonlar değiştirilmeden çalışmaya devam eder.
    """
    if not texts:
        return []
    proba = pipeline.predict_proba(texts)
    classes = list(pipeline.named_steps["clf"].classes_)
    pos_idx = classes.index("Pozitif")
    neg_idx = classes.index("Negatif")
    preds = pipeline.predict(texts)
    scores = proba[:, pos_idx] - proba[:, neg_idx]
    return list(zip(preds.tolist(), scores.tolist()))


def train():
    df = _load_labeled_data()
    if len(df) < MIN_SAMPLES_FOR_TRAINING:
        print(f"Yetersiz etiketli veri ({len(df)} satır); {DATA_PATH} içinde en az "
              f"{MIN_SAMPLES_FOR_TRAINING} satır bekleniyor.")
        return

    X, y = df["text"], df["duygu"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    comparison = []
    best_name, best_pipeline, best_cv_score = None, None, -1.0
    for name, (pipeline, param_dist, n_iter) in build_candidate_pipelines().items():
        search = RandomizedSearchCV(
            pipeline, param_dist, n_iter=n_iter, scoring="f1_macro",
            cv=cv, random_state=42, n_jobs=-1,
        )
        search.fit(X_train, y_train)
        comparison.append({
            "model": name,
            "cv_f1_macro": float(search.best_score_),
            "best_params": search.best_params_,
        })
        print(f"[{name}] CV f1_macro (ortalama): {search.best_score_:.3f}  |  hiperparametreler: {search.best_params_}")
        if search.best_score_ > best_cv_score:
            best_name, best_pipeline, best_cv_score = name, search.best_estimator_, search.best_score_

    comparison.sort(key=lambda r: r["cv_f1_macro"], reverse=True)
    print(f"\nSeçilen model: {best_name} (CV f1_macro: {best_cv_score:.3f})")

    y_pred = best_pipeline.predict(X_test)
    eval_metrics = evaluate_predictions(y_test.values, y_pred)
    print(classification_report(y_test, y_pred, labels=LABELS_ORDERED, zero_division=0))
    print(f"Test f1_macro: {eval_metrics['f1_macro']:.3f}")

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"pipeline": best_pipeline, "model_name": best_name, "labels": LABELS_ORDERED}, MODEL_PATH)
    print(f"Model kaydedildi: {MODEL_PATH}")

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "selected_model": best_name,
            "model_comparison": comparison,
            "n_samples": int(len(df)),
            "label_distribution": {k: int(v) for k, v in df["duygu"].value_counts().items()},
            "test_metrics": {
                "accuracy": eval_metrics["accuracy"],
                "f1_macro": eval_metrics["f1_macro"],
                "report": eval_metrics["report"],
            },
            "confusion_matrix": eval_metrics["confusion_matrix"],
            "labels": LABELS_ORDERED,
            "veri_seti_notu": (
                "Nötr sınıfının büyük çoğunluğu Wikipedia cümlelerinden gelir (yapısal "
                "olarak haber başlığı/yorumdan farklı bir dil kullanır); model gerçek "
                "kısa haber/yorum metinlerinde nötr sınıfı için daha az güvenilir olabilir."
            ),
        }, f, ensure_ascii=False, indent=2)
    print(f"Metrikler kaydedildi: {METRICS_PATH}")


if __name__ == "__main__":
    train()
