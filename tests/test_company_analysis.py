import pandas as pd

from company_analysis import analyze_sentiment, reputation_score, sentiment_timeline, turkish_lower


def test_turkish_lower_handles_dotted_capital_i():
    assert turkish_lower("İYİ") == "iyi"


def test_analyze_sentiment_detects_positive_word_starting_with_capital_i():
    # Cümledeki tek duygu kelimesi "İyi" (büyük İ ile); standart str.lower() ile
    # bu kelime bölünüp POSITIVE_WORDS'te eşleşmiyor, skor 0 (Nötr) çıkıyordu.
    label, score = analyze_sentiment("Şirket için İyi haberler var.")
    assert label == "Pozitif"
    assert score == 1


def test_reputation_score_all_positive_is_100_good():
    df = pd.DataFrame({"duygu": ["Pozitif", "Pozitif", "Pozitif"]})
    score, status = reputation_score(df)
    assert score == 100
    assert status == "good"


def test_reputation_score_all_negative_is_0_critical():
    df = pd.DataFrame({"duygu": ["Negatif", "Negatif"]})
    score, status = reputation_score(df)
    assert score == 0
    assert status == "critical"


def test_reputation_score_balanced_is_50_warning():
    df = pd.DataFrame({"duygu": ["Pozitif", "Negatif"]})
    score, status = reputation_score(df)
    assert score == 50
    assert status == "warning"


def test_reputation_score_empty_df_defaults_to_50_warning():
    df = pd.DataFrame(columns=["duygu"])
    score, status = reputation_score(df)
    assert score == 50
    assert status == "warning"


def test_sentiment_timeline_groups_by_day_and_sentiment():
    df = pd.DataFrame({
        "tarih": [
            "Mon, 01 Jan 2024 10:00:00 GMT",
            "Mon, 01 Jan 2024 14:00:00 GMT",
            "Tue, 02 Jan 2024 09:00:00 GMT",
        ],
        "duygu": ["Pozitif", "Pozitif", "Negatif"],
    })
    timeline = sentiment_timeline(df)
    assert len(timeline) == 2
    assert set(timeline["duygu"]) == {"Pozitif", "Negatif"}
    pos_row = timeline[timeline["duygu"] == "Pozitif"].iloc[0]
    assert pos_row["adet"] == 2


def test_sentiment_timeline_ignores_unparseable_dates():
    df = pd.DataFrame({"tarih": ["", "", ""], "duygu": ["Pozitif", "Nötr", "Negatif"]})
    timeline = sentiment_timeline(df)
    assert timeline.empty


def test_sentiment_timeline_handles_empty_dataframe():
    df = pd.DataFrame(columns=["başlık", "kaynak", "link", "tarih", "tür", "özet", "duygu", "skor"])
    timeline = sentiment_timeline(df)
    assert timeline.empty
