"""sentiment_model.py için birim testleri.

Gerçek 48.965 satırlık `data/raw/test.csv` kullanılmaz (test paketini yavaşlatır);
bunun yerine küçük sentetik etiketli metinlerle çalışılır. `_load_labeled_data()`
için `DATA_PATH` monkeypatch ile geçici bir mini CSV'ye yönlendirilir.
"""
import pandas as pd

import sentiment_model
from sentiment_model import (
    LABEL_MAP,
    LABELS_ORDERED,
    build_candidate_pipelines,
    evaluate_predictions,
    predict_batch,
)


def _tiny_labeled_csv(tmp_path):
    rows = [
        ("Ürün harikaydı, çok memnun kaldım", "Positive"),
        ("Kesinlikle tavsiye ederim, mükemmel hizmet", "Positive"),
        ("Harika bir deneyimdi teşekkürler", "Positive"),
        ("Çok iyi ve hızlı kargo", "Positive"),
        ("Berbat bir deneyimdi, hiç memnun kalmadım", "Negative"),
        ("Rezalet, bir daha asla almam", "Negative"),
        ("Ürün bozuk geldi, iade ettim", "Negative"),
        ("Hiç iyi değil, kötü bir tecrübeydi", "Negative"),
        ("Kral akbaba dikkat çekici renklere sahiptir", "Notr"),
        ("Şirket merkezi İstanbul'dadır", "Notr"),
        ("Toplantı saat üçte başlayacak", "Notr"),
        ("Rapor önümüzdeki hafta teslim edilecek", "Notr"),
    ]
    df = pd.DataFrame(rows * 5, columns=["text", "label"])  # CV/split için yeterli tekrar
    df["dataset"] = "test"
    path = tmp_path / "mini_sentiment.csv"
    df.to_csv(path, index=False)
    return str(path)


def test_load_labeled_data_maps_labels_to_turkish_and_dedupes(tmp_path, monkeypatch):
    path = _tiny_labeled_csv(tmp_path)
    monkeypatch.setattr(sentiment_model, "DATA_PATH", path)

    df = sentiment_model._load_labeled_data()

    assert set(df["duygu"].unique()) == {"Pozitif", "Negatif", "Nötr"}
    # Kaynak CSV'de 5 kat tekrar var ama metinler aynı -> dedup sonrası 12 benzersiz satır kalmalı.
    assert len(df) == 12


def test_load_labeled_data_returns_empty_frame_when_file_missing(monkeypatch):
    monkeypatch.setattr(sentiment_model, "DATA_PATH", "olmayan_dosya.csv")
    df = sentiment_model._load_labeled_data()
    assert df.empty


def test_build_candidate_pipelines_returns_expected_models():
    candidates = build_candidate_pipelines()
    assert set(candidates) == {"LogisticRegression", "MultinomialNB"}
    for name, (pipeline, param_dist, n_iter) in candidates.items():
        assert isinstance(param_dist, dict) and param_dist
        assert n_iter > 0
        assert "tfidf" in pipeline.named_steps
        assert "clf" in pipeline.named_steps


def test_candidate_pipelines_fit_and_predict_on_tiny_corpus(tmp_path, monkeypatch):
    path = _tiny_labeled_csv(tmp_path)
    monkeypatch.setattr(sentiment_model, "DATA_PATH", path)
    df = sentiment_model._load_labeled_data()

    for name, (pipeline, _, _) in build_candidate_pipelines().items():
        pipeline.fit(df["text"], df["duygu"])
        preds = pipeline.predict(df["text"])
        assert len(preds) == len(df)
        assert set(preds).issubset({"Pozitif", "Negatif", "Nötr"}), name


def test_evaluate_predictions_uses_f1_macro_for_imbalanced_classes():
    y_test = pd.Series(["Pozitif"] * 8 + ["Negatif"] * 2)
    # Modelin çoğunluk sınıfını ezberlediği (her şeyi "Pozitif" tahmin ettiği) durum:
    y_pred = ["Pozitif"] * 10

    metrics = evaluate_predictions(y_test.values, y_pred)

    assert metrics["accuracy"] == 0.8
    # Negatif sınıfı hiç yakalanamadığından f1_macro, yanıltıcı yüksek accuracy'den belirgin düşük olmalı.
    assert metrics["f1_macro"] < metrics["accuracy"]
    assert metrics["labels"] == LABELS_ORDERED
    assert len(metrics["confusion_matrix"]) == 3


def test_predict_batch_returns_label_and_score_in_expected_range(tmp_path, monkeypatch):
    path = _tiny_labeled_csv(tmp_path)
    monkeypatch.setattr(sentiment_model, "DATA_PATH", path)
    df = sentiment_model._load_labeled_data()

    pipeline, _, _ = build_candidate_pipelines()["LogisticRegression"]
    pipeline.fit(df["text"], df["duygu"])

    results = predict_batch(pipeline, ["Harika bir ürün, çok memnunum", "Berbat, hiç beğenmedim"])

    assert len(results) == 2
    for label, score in results:
        assert label in {"Pozitif", "Negatif", "Nötr"}
        assert -1.0 <= score <= 1.0


def test_predict_batch_returns_empty_list_for_no_texts(tmp_path, monkeypatch):
    path = _tiny_labeled_csv(tmp_path)
    monkeypatch.setattr(sentiment_model, "DATA_PATH", path)
    df = sentiment_model._load_labeled_data()
    pipeline, _, _ = build_candidate_pipelines()["LogisticRegression"]
    pipeline.fit(df["text"], df["duygu"])

    assert predict_batch(pipeline, []) == []


def test_label_map_covers_all_dataset_labels():
    assert LABEL_MAP == {"Positive": "Pozitif", "Notr": "Nötr", "Negative": "Negatif"}
