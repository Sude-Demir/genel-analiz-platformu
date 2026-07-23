import xml.etree.ElementTree as ET

import pandas as pd

from company_analysis import (
    _detect_segments,
    _parse_atom_entries,
    _parse_standard_rss,
    _resolve_article_link,
    analyze_sentiment,
    reputation_score,
    segment_outlook,
    sentiment_timeline,
    turkish_lower,
)


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


def test_parse_standard_rss_uses_source_element_when_present():
    xml = """<?xml version="1.0"?>
    <rss><channel>
      <item>
        <title>Örnek Haber Başlığı</title>
        <link>https://example.com/haber</link>
        <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
        <source>Örnek Kaynak</source>
      </item>
    </channel></rss>"""
    root = ET.fromstring(xml)
    items = _parse_standard_rss(root, "Varsayılan Haberler", max_items=8)
    assert len(items) == 1
    assert items[0]["başlık"] == "Örnek Haber Başlığı"
    assert items[0]["kaynak"] == "Örnek Kaynak"
    assert items[0]["tür"] == "Haber"


def test_parse_standard_rss_falls_back_to_domain_when_no_source_element():
    xml = """<?xml version="1.0"?>
    <rss><channel>
      <item>
        <title>Kaynaksız Haber</title>
        <link>https://www.bing.com/haber/1</link>
        <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
      </item>
    </channel></rss>"""
    root = ET.fromstring(xml)
    items = _parse_standard_rss(root, "Bing Haberler", max_items=8)
    assert items[0]["kaynak"] == "bing.com"


def test_parse_standard_rss_reads_namespaced_source_element_from_bing():
    # Bing Haberler kaynağı standart <source> değil, sorguya özel bir XML
    # namespace URI'siyle <News:Source> olarak verir (gerçek yanıttan alınmıştır);
    # bu URI her sorguda değişebildiğinden testte de değişken bir örnek kullanılır.
    xml = """<?xml version="1.0"?>
    <rss xmlns:News="https://www.bing.com/news/search?q=Turkcell&amp;format=rss">
    <channel>
      <item>
        <title>Bing'den Örnek Haber</title>
        <link>http://www.bing.com/news/apiclick.aspx?ref=FexRss&amp;aid=&amp;tid=abc&amp;url=https%3a%2f%2fwww.aksam.com.tr%2fhaber-1&amp;c=123&amp;mkt=tr-tr</link>
        <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
        <News:Source>AKŞAM</News:Source>
      </item>
    </channel></rss>"""
    root = ET.fromstring(xml)
    items = _parse_standard_rss(root, "Bing Haberler", max_items=8)
    assert items[0]["kaynak"] == "AKŞAM"
    # Bing'in tıklama-izleme yönlendiricisi yerine gerçek makale linki dönmeli.
    assert items[0]["link"] == "https://www.aksam.com.tr/haber-1"


def test_parse_standard_rss_falls_back_to_default_source_when_no_link():
    xml = """<?xml version="1.0"?>
    <rss><channel>
      <item>
        <title>Linksiz Haber</title>
        <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
      </item>
    </channel></rss>"""
    root = ET.fromstring(xml)
    items = _parse_standard_rss(root, "Varsayılan Haberler", max_items=8)
    assert items[0]["kaynak"] == "Varsayılan Haberler"


def test_resolve_article_link_extracts_real_url_from_bing_redirect():
    redirect = (
        "http://www.bing.com/news/apiclick.aspx?ref=FexRss&aid=&tid=abc"
        "&url=https%3a%2f%2fwww.hurriyet.com.tr%2fteknoloji%2fhaber-1&c=123&mkt=tr-tr"
    )
    assert _resolve_article_link(redirect) == "https://www.hurriyet.com.tr/teknoloji/haber-1"


def test_resolve_article_link_returns_link_unchanged_when_not_bing_redirect():
    link = "https://news.google.com/rss/articles/abc"
    assert _resolve_article_link(link) == link


def test_parse_atom_entries_extracts_reddit_style_fields():
    xml = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Şirket hakkında bir Reddit gönderisi</title>
        <link href="https://www.reddit.com/r/example/comments/abc123/"/>
        <updated>2024-01-01T10:00:00+00:00</updated>
      </entry>
    </feed>"""
    root = ET.fromstring(xml)
    items = _parse_atom_entries(root, max_items=8)
    assert len(items) == 1
    assert items[0]["başlık"] == "Şirket hakkında bir Reddit gönderisi"
    assert items[0]["kaynak"] == "Reddit"
    assert items[0]["link"] == "https://www.reddit.com/r/example/comments/abc123/"
    assert items[0]["tarih"] == "2024-01-01T10:00:00+00:00"
    assert items[0]["tür"] == "Web / Sosyal Medya"


def test_parse_atom_entries_respects_max_items():
    entries = "".join(
        f"<entry><title>Gönderi {i}</title><link href='https://reddit.com/{i}'/>"
        f"<updated>2024-01-0{i}T00:00:00+00:00</updated></entry>"
        for i in range(1, 5)
    )
    xml = f'<feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>'
    root = ET.fromstring(xml)
    items = _parse_atom_entries(root, max_items=2)
    assert len(items) == 2


def test_detect_segments_matches_financial_keywords():
    segments = _detect_segments("Şirketin bu çeyrekteki kar ve bilanço rakamları açıklandı.")
    assert "Finansal Performans" in segments


def test_detect_segments_matches_multiple_segments_at_once():
    segments = _detect_segments("Genel Müdür, yapay zeka yatırımlarıyla dijital dönüşümü anlattı.")
    assert "Kurumsal Yönetim & Strateji" in segments
    assert "Dijital & Teknoloji" in segments


def test_detect_segments_returns_empty_set_when_no_keyword_matches():
    assert _detect_segments("Bugün hava çok güzel, dışarıda yürüyüş yaptım.") == set()


def test_segment_outlook_returns_empty_list_for_empty_dataframe():
    assert segment_outlook(pd.DataFrame()) == []


def test_segment_outlook_skips_segments_below_minimum_mentions():
    df = pd.DataFrame({
        "başlık": ["Şirketin kar rakamları açıklandı"],
        "özet": [""],
        "tarih": [""],
        "duygu": ["Pozitif"],
        "skor": [1],
    })
    assert segment_outlook(df) == []


def test_segment_outlook_classifies_positive_outlook_with_reasoning():
    df = pd.DataFrame({
        "başlık": ["Şirket rekor kar açıkladı", "Hisse senedinde büyüme bekleniyor"],
        "özet": ["", ""],
        "tarih": ["", ""],
        "duygu": ["Pozitif", "Pozitif"],
        "skor": [2, 1],
    })
    outlooks = segment_outlook(df)
    assert len(outlooks) == 1
    assert outlooks[0]["bölüm"] == "Finansal Performans"
    assert outlooks[0]["görünüm"] == "Olumlu"
    assert "2 pozitif" in outlooks[0]["gerekçe"]


def test_segment_outlook_classifies_risky_outlook_when_negative_dominates():
    df = pd.DataFrame({
        "başlık": ["Şirket zarar açıkladı", "Hisse senedinde kayıp yaşandı"],
        "özet": ["", ""],
        "tarih": ["", ""],
        "duygu": ["Negatif", "Negatif"],
        "skor": [-1, -2],
    })
    outlooks = segment_outlook(df)
    assert outlooks[0]["görünüm"] == "Riskli"


def test_segment_outlook_sorts_by_mention_count_descending():
    df = pd.DataFrame({
        "başlık": [
            "Şirket kar açıkladı", "Hisse senedi yükseldi",
            "Genel Müdür yeni strateji açıkladı", "Yönetim kurulu toplantısı yapıldı",
            "CEO stratejik ortaklık imzaladı",
        ],
        "özet": ["", "", "", "", ""],
        "tarih": ["", "", "", "", ""],
        "duygu": ["Pozitif", "Pozitif", "Nötr", "Nötr", "Nötr"],
        "skor": [1, 1, 0, 0, 0],
    })
    outlooks = segment_outlook(df)
    assert outlooks[0]["bölüm"] == "Kurumsal Yönetim & Strateji"
    assert outlooks[0]["kaynak_sayısı"] == 3
