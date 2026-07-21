"""Bir şirket adı için web/haber taraması, sezgisel duygu analizi ve öne çıkan konu çıkarımı.

Ücretli/anahtarlı bir API kullanmadan çalışır: Google News RSS (herkese açık)
ve DuckDuckGo HTML arama sonuçları üzerinden ilgili başlık/özetleri toplar,
basit bir Türkçe/İngilizce sözlük tabanlı duygu skoru hesaplar ve kelime
frekansına dayalı öne çıkan konuları çıkarır. Sonuçlar bir ön analiz niteliğindedir.
"""
import re
import xml.etree.ElementTree as ET
from collections import Counter
from urllib.parse import quote_plus

import pandas as pd
import requests
from bs4 import BeautifulSoup

REQUEST_TIMEOUT = 8
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AnalizPlatformu/1.0"}

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


def _google_news_rss(company: str, max_items: int = 12) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={quote_plus(company)}&hl=tr&gl=TR&ceid=TR:tr"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception:
        return []

    items = []
    for item in root.findall(".//item")[:max_items]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        source_el = item.find("source")
        source = source_el.text if source_el is not None else "Google Haberler"
        if title:
            items.append({
                "başlık": title, "kaynak": source, "link": link,
                "tarih": pub_date, "tür": "Haber", "özet": title,
            })
    return items


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


def collect_mentions(company: str) -> tuple[list[dict], list[str]]:
    """Şirket için haber ve web/sosyal medya bahsedilmelerini toplar. (kayıtlar, uyarılar) döndürür."""
    warnings: list[str] = []
    records: list[dict] = []

    news = _google_news_rss(company)
    if not news:
        warnings.append("Google Haberler kaynağına ulaşılamadı veya sonuç bulunamadı.")
    records += news

    queries = [f'"{company}" yorumları', f'"{company}" şikayet', f'"{company}" sosyal medya']
    seen_links = {r["link"] for r in records}
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
    text_lower = text.lower()
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
    company_tokens = {w.lower() for w in re.findall(r"[a-zçğıöşü]+", company.lower())}
    counter: Counter = Counter()
    for text in texts:
        words = re.findall(r"[a-zçğıöşüA-ZÇĞİÖŞÜ]{3,}", text)
        for w in words:
            wl = w.lower()
            if wl in STOPWORDS or wl in company_tokens:
                continue
            counter[wl] += 1
    return counter.most_common(top_n)


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
