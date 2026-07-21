from company_analysis import analyze_sentiment, turkish_lower


def test_turkish_lower_handles_dotted_capital_i():
    assert turkish_lower("İYİ") == "iyi"


def test_analyze_sentiment_detects_positive_word_starting_with_capital_i():
    # Cümledeki tek duygu kelimesi "İyi" (büyük İ ile); standart str.lower() ile
    # bu kelime bölünüp POSITIVE_WORDS'te eşleşmiyor, skor 0 (Nötr) çıkıyordu.
    label, score = analyze_sentiment("Şirket için İyi haberler var.")
    assert label == "Pozitif"
    assert score == 1
