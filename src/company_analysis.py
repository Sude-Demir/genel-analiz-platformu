"""Bir şirket adı için web/haber taraması, sezgisel duygu analizi ve öne çıkan konu çıkarımı.

Ücretli/anahtarlı bir API kullanmadan çalışır: Google/Bing Haberler RSS, Reddit RSS
(herkese açık) ve DuckDuckGo HTML arama sonuçları üzerinden ilgili başlık/özetleri
toplar, basit bir Türkçe/İngilizce sözlük tabanlı duygu skoru hesaplar ve kelime
frekansına dayalı öne çıkan konuları çıkarır. Sonuçlar bir ön analiz niteliğindedir.

Not: Instagram, X (Twitter) gibi sosyal medya platformları kasıtlı olarak
desteklenmez — içerikleri anahtarsız/girişsiz güvenilir şekilde çekilemez ve
kullanım şartları scraping'i yasaklar. Reddit RSS, anahtarsız erişilebilen ve
gerçek "sosyal medya bahsi" boyutuna en yakın kaynaktır. Yahoo News RSS ucu da
denendi ancak artık RSS değil HTML sayfası döndürdüğü (kapatılmış/değişmiş
uç) için eklenmedi.
"""
import re
import xml.etree.ElementTree as ET
from collections import Counter
from urllib.parse import parse_qs, quote_plus, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

REQUEST_TIMEOUT = 8
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AnalizPlatformu/1.0"}

_TURKISH_UPPER_MAP = str.maketrans("İ", "i")


def turkish_lower(text: str) -> str:
    """Türkçe İ/I harflerini doğru küçültür (bkz. cv_analysis.turkish_lower)."""
    return text.translate(_TURKISH_UPPER_MAP).lower()

POSITIVE_WORDS = {
    "harika", "mükemmel", "memnun", "memnuniyet", "kaliteli", "hızlı", "güvenilir",
    "teşekkür", "başarılı", "iyi", "tavsiye", "beğendim", "profesyonel", "keyifli",
    "avantajlı", "uygun", "yardımsever", "ilgili", "kazandı", "büyüme", "rekor",
    "ödül", "yenilikçi", "lider", "artış", "olumlu", "great", "excellent", "love",
    "recommend", "best", "good", "growth", "award", "success", "positive",
}
NEGATIVE_WORDS = {
    "kötü", "berbat", "yavaş", "sorun", "sorunlu", "şikayet", "dolandırıcı",
    "rezalet", "iptal", "başarısız", "memnuniyetsiz", "kayıp", "zarar", "dava",
    "ceza", "skandal", "kriz", "iflas", "işten çıkarma", "grev", "olumsuz",
    "kötüleşti", "hayal kırıklığı", "bad", "worst", "scam", "complaint",
    "lawsuit", "fraud", "layoff", "negative", "decline", "loss",
}
STOPWORDS = {
    "ve", "ile", "bir", "bu", "şu", "da", "de", "için", "gibi", "çok", "daha",
    "ama", "veya", "olan", "olarak", "kadar", "göre", "sonra", "önce", "ise",
    "ki", "mi", "mı", "mu", "mü", "en", "ne", "nasıl", "neden", "şey", "tüm",
    "her", "hiç", "ben", "sen", "o", "biz", "siz", "onlar", "var", "yok",
    "the", "and", "for", "with", "that", "this", "are", "was", "were", "from",
    "will", "have", "has", "had", "not", "you", "your", "our", "their", "its",
    "yeni", "yıl", "ilk", "son", "büyük", "genel", "milyon", "bin", "günü",
}


def _find_source_text(item: ET.Element) -> str | None:
    """<source> elemanını isim alanından (namespace) bağımsız bulur.

    Google Haberler standart RSS 2.0 `<source>` (namespace'siz) kullanır.
    Bing Haberler ise kaynağı `<News:Source>` şeklinde, sorguya özel bir XML
    namespace URI'siyle verir (örn. ".../news/search?q=Turkcell&format=rss");
    bu URI her sorguda değiştiğinden sabit kodlanamaz. item.find("source")
    bu yüzden Bing'de hiç eşleşmez ve kaynak adı kaybolup linkin domaini
    ("bing.com") kullanılırdı — bunun yerine her alt elemanın namespace'siz
    (yerel) adını karşılaştırıyoruz.
    """
    for child in item:
        local_tag = child.tag.rsplit("}", 1)[-1]
        if local_tag.lower() == "source" and child.text:
            return child.text
    return None


def _resolve_article_link(link: str) -> str:
    """Bing'in tıklama-izleme yönlendirici linkinden (apiclick.aspx?...&url=...)
    gerçek makale URL'sini çıkarır; başka bir formatsa linki olduğu gibi döner.
    """
    if "bing.com/news/apiclick.aspx" not in link:
        return link
    query = urlparse(link).query
    params = parse_qs(query)
    real_url = params.get("url", [None])[0]
    return real_url if real_url else link


def _parse_standard_rss(root: ET.Element, default_source: str, max_items: int) -> list[dict]:
    """RSS 2.0 `<item>` tabanlı beslemeleri (Google/Bing Haberler) ortak biçimde ayrıştırır."""
    items = []
    for item in root.findall(".//item")[:max_items]:
        title = (item.findtext("title") or "").strip()
        link = _resolve_article_link((item.findtext("link") or "").strip())
        pub_date = (item.findtext("pubDate") or "").strip()
        source_text = _find_source_text(item)
        source = source_text if source_text else (_domain(link) if link else default_source)
        if title:
            items.append({
                "başlık": title, "kaynak": source, "link": link,
                "tarih": pub_date, "tür": "Haber", "özet": title,
            })
    return items


def _fetch_news_rss(url: str, default_source: str, max_items: int) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception:
        return []
    return _parse_standard_rss(root, default_source, max_items)


def _google_news_rss(company: str, max_items: int = 12) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={quote_plus(company)}&hl=tr&gl=TR&ceid=TR:tr"
    return _fetch_news_rss(url, "Google Haberler", max_items)


def _bing_news_rss(company: str, max_items: int = 8) -> list[dict]:
    url = f"https://www.bing.com/news/search?q={quote_plus(company)}&format=rss"
    return _fetch_news_rss(url, "Bing Haberler", max_items)


_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _parse_atom_entries(root: ET.Element, max_items: int) -> list[dict]:
    """Reddit arama beslemesi gibi Atom `<entry>` tabanlı beslemeleri ayrıştırır."""
    items = []
    for entry in root.findall("atom:entry", _ATOM_NS)[:max_items]:
        title = (entry.findtext("atom:title", default="", namespaces=_ATOM_NS) or "").strip()
        link_el = entry.find("atom:link", _ATOM_NS)
        link = link_el.get("href", "") if link_el is not None else ""
        updated = (entry.findtext("atom:updated", default="", namespaces=_ATOM_NS) or "").strip()
        if title:
            items.append({
                "başlık": title, "kaynak": "Reddit", "link": link,
                "tarih": updated, "tür": "Web / Sosyal Medya", "özet": title,
            })
    return items


def _reddit_rss(company: str, max_items: int = 8) -> list[dict]:
    """Reddit arama beslemesi RSS 2.0 değil Atom biçimindedir; ayrı ayrıştırma gerekir."""
    url = f"https://www.reddit.com/search.rss?q={quote_plus(company)}&sort=new"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception:
        return []
    return _parse_atom_entries(root, max_items)


def _duckduckgo_search(query: str, max_items: int = 8) -> list[dict]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        resp = requests.post(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return []

    items = []
    for result in soup.select(".result")[:max_items]:
        title_el = result.select_one(".result__title a")
        snippet_el = result.select_one(".result__snippet")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        link = title_el.get("href", "")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        if title:
            items.append({
                "başlık": title, "kaynak": _domain(link), "link": link,
                "tarih": "", "tür": "Web / Sosyal Medya", "özet": snippet,
            })
    return items


def _domain(url: str) -> str:
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return match.group(1) if match else "web"


_NEWS_SOURCES = [
    (_google_news_rss, "Google Haberler"),
    (_bing_news_rss, "Bing Haberler"),
    (_reddit_rss, "Reddit"),
]


def collect_mentions(company: str) -> tuple[list[dict], list[str]]:
    """Şirket için haber ve web/sosyal medya bahsedilmelerini toplar. (kayıtlar, uyarılar) döndürür.

    Kaynaklar: Google/Bing Haberler RSS, Reddit RSS ve DuckDuckGo web araması.
    Aynı bağlantının birden fazla kaynaktan gelmesi olasılığına karşı tüm kaynaklar
    tek bir `seen_links` kümesiyle tekilleştirilir.
    """
    warnings: list[str] = []
    records: list[dict] = []
    seen_links: set[str] = set()

    for fetch_fn, label in _NEWS_SOURCES:
        results = fetch_fn(company)
        if not results:
            warnings.append(f"{label} kaynağına ulaşılamadı veya sonuç bulunamadı.")
            continue
        for r in results:
            if r["link"] and r["link"] in seen_links:
                continue
            seen_links.add(r["link"])
            records.append(r)

    queries = [f'"{company}" yorumları', f'"{company}" şikayet', f'"{company}" sosyal medya']
    for q in queries:
        results = _duckduckgo_search(q)
        if not results:
            warnings.append(f"Web araması sonuç vermedi: {q}")
            continue
        for r in results:
            if r["link"] not in seen_links:
                seen_links.add(r["link"])
                records.append(r)

    return records, warnings


def analyze_sentiment(text: str) -> tuple[str, int]:
    text_lower = turkish_lower(text)
    words = re.findall(r"[a-zçğıöşü]+", text_lower)
    pos = sum(1 for w in words if w in POSITIVE_WORDS)
    neg = sum(1 for w in words if w in NEGATIVE_WORDS)
    score = pos - neg
    if score > 0:
        return "Pozitif", score
    if score < 0:
        return "Negatif", score
    return "Nötr", score


def extract_topics(texts: list[str], company: str, top_n: int = 15) -> list[tuple[str, int]]:
    company_tokens = {turkish_lower(w) for w in re.findall(r"[a-zçğıöşü]+", turkish_lower(company))}
    counter: Counter = Counter()
    for text in texts:
        words = re.findall(r"[a-zçğıöşüA-ZÇĞİÖŞÜ]{3,}", text)
        for w in words:
            wl = turkish_lower(w)
            if wl in STOPWORDS or wl in company_tokens:
                continue
            counter[wl] += 1
    return counter.most_common(top_n)


SEGMENT_KEYWORDS = {
    "Finansal Performans": {
        "kar", "zarar", "gelir", "ciro", "bilanço", "hisse", "borsa", "temettü",
        "büyüme", "kayıp", "profit", "loss", "revenue", "earnings", "stock", "dividend",
    },
    "Mobil İletişim & Altyapı": {
        "mobil", "telekom", "şebeke", "altyapı", "5g", "4.5g", "baz istasyonu",
        "fiber", "internet", "network", "telecom", "infrastructure", "operatör",
    },
    "Dijital & Teknoloji": {
        "dijital", "yapay zeka", "teknoloji", "uygulama", "yazılım", "bulut", "inovasyon",
        "yapay zekâ", "app", "digital", "cloud", "software", "innovation", "startup",
    },
    "Müşteri Hizmetleri & Marka İtibarı": {
        "müşteri", "hizmet", "şikayet", "memnuniyet", "destek", "kalite", "customer",
        "service", "complaint", "satisfaction", "support",
    },
    "İnsan Kaynakları & Çalışan İlişkileri": {
        "çalışan", "işten çıkarma", "grev", "personel", "istihdam", "sendika",
        "employee", "layoff", "strike", "staff", "union",
    },
    "Kurumsal Yönetim & Strateji": {
        "genel müdür", "ceo", "yönetim kurulu", "strateji", "atama", "ortaklık",
        "birleşme", "satın alma", "management", "strategy", "merger", "acquisition",
    },
}

MIN_SEGMENT_MENTIONS = 2


def _detect_segments(text: str) -> set[str]:
    """Bir haber/gönderi metnini SEGMENT_KEYWORDS sözlüğüne göre bölüm(ler)e etiketler.

    Tek kelimelik anahtarlar tam kelime eşleşmesiyle aranır (örn. "kar", "kariyer"
    kelimesinin içinde yanlışlıkla eşleşmesin diye); boşluk/nokta içeren öbek
    anahtarlar ("genel müdür", "4.5g" gibi) alt dize (substring) olarak aranır.
    Bir metin birden fazla bölümle eşleşebilir (örn. hem finans hem strateji haberi olabilir).
    """
    text_lower = turkish_lower(text)
    word_tokens = set(re.findall(r"[a-z0-9çğıöşü]+", text_lower))
    matched = set()
    for segment, keywords in SEGMENT_KEYWORDS.items():
        for kw in keywords:
            is_phrase = " " in kw or "." in kw
            if (kw in text_lower) if is_phrase else (kw in word_tokens):
                matched.add(segment)
                break
    return matched


def _segment_trend(seg_df: pd.DataFrame) -> str:
    """Bölüme ait tarihli kayıtları kronolojik olarak ikiye bölüp duygu skoru ortalamasını
    kıyaslayarak basit bir yön ifadesi üretir. Yeterli tarihli veri yoksa boş döner.
    """
    dated = seg_df.copy()
    dated["tarih_ayristirilmis"] = pd.to_datetime(dated["tarih"], errors="coerce", utc=True)
    dated = dated.dropna(subset=["tarih_ayristirilmis"]).sort_values("tarih_ayristirilmis")
    if len(dated) < 4:
        return ""

    mid = len(dated) // 2
    older_score = dated.iloc[:mid]["skor"].mean()
    newer_score = dated.iloc[mid:]["skor"].mean()
    fark = newer_score - older_score
    if fark > 0.3:
        return "son dönemdeki haberlerde duygu tonu iyileşme eğiliminde"
    if fark < -0.3:
        return "son dönemdeki haberlerde duygu tonu kötüleşme eğiliminde"
    return "duygu tonu zaman içinde durağan seyrediyor"


def segment_outlook(df: pd.DataFrame, company: str = "") -> list[dict]:
    """Toplanan kayıtları iş kolu/bölüm bazında sözlük tabanlı sınıflandırıp her bölüm için
    sektördeki geleceğine ilişkin sezgisel bir görünüm (Olumlu/Riskli/Belirsiz) ve bunun
    hangi veriye (duygu dağılımı, trend, öne çıkan konular) dayandığını açıklayan bir
    gerekçe metni üretir.

    `company` verilirse öne çıkan konu listesinden şirket adının kendisi filtrelenir
    (aksi halde her bölümde tekrar eden, bilgi değeri düşük bir konu olarak çıkar).

    Not: Bu bir tahmin değil, toplanan haber/yorum örnekleminin duygu ve konu analizine
    dayalı sözlük tabanlı bir sezgisel çıkarımdır; harici bir AI/istatistiksel model
    kullanmaz. En az MIN_SEGMENT_MENTIONS kaynağı olan bölümler raporlanır.
    """
    if df.empty:
        return []

    segment_rows: dict[str, list] = {}
    for _, row in df.iterrows():
        text = f"{row['başlık']} {row['özet']}"
        for segment in _detect_segments(text):
            segment_rows.setdefault(segment, []).append(row)

    results = []
    for segment, rows in segment_rows.items():
        if len(rows) < MIN_SEGMENT_MENTIONS:
            continue

        seg_df = pd.DataFrame(rows)
        pos = int((seg_df["duygu"] == "Pozitif").sum())
        neg = int((seg_df["duygu"] == "Negatif").sum())
        total = len(seg_df)
        notr = total - pos - neg
        net = pos - neg

        if net > 0:
            gorunum = "Olumlu"
        elif net < 0:
            gorunum = "Riskli"
        else:
            gorunum = "Belirsiz / Dengeli"

        trend = _segment_trend(seg_df)
        topics = extract_topics((seg_df["başlık"] + " " + seg_df["özet"]).tolist(), company, top_n=5)

        gerekce_parcalari = [f"{total} kaynaktan {pos} pozitif, {neg} negatif, {notr} nötr bahsedilme tespit edildi"]
        if trend:
            gerekce_parcalari.append(trend)
        if topics:
            gerekce_parcalari.append("öne çıkan konular: " + ", ".join(f"{w} ({c})" for w, c in topics))

        results.append({
            "bölüm": segment,
            "görünüm": gorunum,
            "kaynak_sayısı": total,
            "gerekçe": "; ".join(gerekce_parcalari) + ".",
            "konular": topics,
        })

    results.sort(key=lambda r: r["kaynak_sayısı"], reverse=True)
    return results


def reputation_score(df: pd.DataFrame) -> tuple[int, str]:
    """Duygu dağılımından 0-100 arası bir itibar puanı ve durum anahtarı üretir.

    Durum anahtarı theme.STATUS sözlüğüyle eşleşir: good/warning/serious/critical.
    Tüm bahsedilmeler pozitifse 100'e, tümü negatifse 0'a yaklaşır; veri yoksa
    veya duygular dengeliyse nötr varsayılan olan 50 döner.
    """
    total = len(df)
    if total == 0:
        return 50, "warning"

    pos = int((df["duygu"] == "Pozitif").sum())
    neg = int((df["duygu"] == "Negatif").sum())
    score = round(50 + 50 * (pos - neg) / total)
    score = max(0, min(100, score))

    if score >= 75:
        status = "good"
    elif score >= 50:
        status = "warning"
    elif score >= 25:
        status = "serious"
    else:
        status = "critical"
    return score, status


def sentiment_timeline(df: pd.DataFrame) -> pd.DataFrame:
    """Toplanan kayıtlardaki `tarih` alanını (RSS pubDate ya da Atom updated) ayrıştırıp
    güne göre pozitif/nötr/negatif sayımını döndürür.

    Haber kaynaklarında (Google/Bing Haberler) ve Reddit'te `tarih` doldurulur;
    DuckDuckGo sonuçlarında boştur. Tarih ayrıştırılamayan kayıtlar sessizce göz ardı
    edilir. Ayrıştırılabilir tarih bulunamazsa boş bir DataFrame döner.
    """
    if df.empty or "tarih" not in df.columns:
        return pd.DataFrame(columns=["tarih", "duygu", "adet"])

    calisma = df.copy()
    calisma["tarih_ayristirilmis"] = pd.to_datetime(calisma["tarih"], errors="coerce", utc=True)
    calisma = calisma.dropna(subset=["tarih_ayristirilmis"])
    if calisma.empty:
        return pd.DataFrame(columns=["tarih", "duygu", "adet"])

    calisma["gun"] = calisma["tarih_ayristirilmis"].dt.date
    grouped = calisma.groupby(["gun", "duygu"]).size().reset_index(name="adet")
    grouped = grouped.rename(columns={"gun": "tarih"}).sort_values("tarih")
    return grouped


def build_dataframe(company: str) -> tuple[pd.DataFrame, list[str]]:
    records, warnings = collect_mentions(company)
    if not records:
        return pd.DataFrame(columns=["başlık", "kaynak", "link", "tarih", "tür", "özet", "duygu", "skor"]), warnings

    for r in records:
        label, score = analyze_sentiment(f"{r['başlık']} {r['özet']}")
        r["duygu"] = label
        r["skor"] = score
    return pd.DataFrame(records), warnings


def build_report(company: str, df: pd.DataFrame, topics: list[tuple[str, int]], warnings: list[str]) -> str:
    lines = [f"# Sosyal Medya / Web Analiz Raporu — {company}", ""]
    lines.append(f"Toplam taranan kaynak: **{len(df)}**")
    if not df.empty:
        counts = df["duygu"].value_counts()
        for label in ["Pozitif", "Nötr", "Negatif"]:
            lines.append(f"- {label}: {int(counts.get(label, 0))}")
    lines.append("")
    lines.append("## Öne Çıkan Konular")
    if topics:
        lines += [f"- {word} ({count})" for word, count in topics]
    else:
        lines.append("- Yeterli veri toplanamadığı için konu çıkarılamadı.")
    lines.append("")
    lines.append("## Bölüm Bazlı Sektör Görünümü")
    outlooks = segment_outlook(df, company) if not df.empty else []
    if outlooks:
        for o in outlooks:
            lines.append(f"- **{o['bölüm']}** — {o['görünüm']}: {o['gerekçe']}")
    else:
        lines.append("- Yeterli veri toplanamadığı için bölüm bazlı görünüm üretilemedi.")
    lines.append("")
    lines.append("## Kaynaklar")
    for _, row in df.iterrows():
        lines.append(f"- [{row['duygu']}] **{row['başlık']}** — {row['kaynak']} ({row['tür']})  \n  {row['link']}")
    if warnings:
        lines.append("")
        lines.append("## Uyarılar")
        lines += [f"- {w}" for w in warnings]
    lines.append("")
    lines.append("_Not: Duygu analizi sözlük tabanlı sezgisel bir yöntemle hesaplanmıştır; nihai yorum için kaynakların incelenmesi önerilir._")
    return "\n".join(lines)
