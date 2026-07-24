"""Güncel yapay zeka (LLM) modellerini özellik/fiyat/benchmark açısından karşılaştırma
ve her model için güncel haber/duyuru taraması.

Model özellikleri (fiyatlandırma, bağlam penceresi, benchmark skorları) elle
küratörlüğü yapılmış, sabit kodlanmış referans verisidir (AI_MODELS) — sağlayıcıların
resmi duyurularına dayanır ancak zamanla eskiyebilir; kesin/güncel rakamlar için
resmi kaynaklar kontrol edilmelidir. Bu tabloyu güncel tutmak için AI_MODELS
sözlüğünü elle güncelle.

Haber taraması ücretli/anahtarlı bir API kullanmadan çalışır: Google/Bing Haberler
RSS üzerinden model adıyla ilgili başlıkları toplar (bkz. company_analysis.py'deki
aynı desen). _request_with_retry ve RSS ayrıştırma yardımcıları company_analysis'ten
kasıtlı olarak bağımsız tutulur — modüller birbirine bağımlı değildir (bkz. CLAUDE.md,
borsa_analysis.py'deki aynı kopyalama deseni).
"""
import time
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, quote_plus, urlparse

import pandas as pd
import requests

REQUEST_TIMEOUT = 8
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AnalizPlatformu/1.0"}
_RETRY_MAX_WAIT_SECONDS = 3.0

# AI_MODELS içindeki fiyat/bağlam/benchmark verilerinin sağlayıcıların resmi
# fiyatlandırma sayfalarından (anthropic/claude.com, ai.google.dev, docs.x.ai,
# api-docs.deepseek.com, mistral.ai) canlı olarak doğrulandığı tarih/saat —
# sözlük güncellendiğinde bu değer de güncellenmeli.
PRICING_REFERENCE_TIMESTAMP = "23.07.2026 16:52"

# Claude Sonnet 5 girdi/çıktı fiyatı 1 Eylül 2026'dan itibaren $2/$10'dan
# $3/$15'e çıkacak (Anthropic'in resmi fiyatlandırma sayfasındaki tanıtım
# fiyatı notu) — AI_MODELS'teki değer o tarihe kadar geçerli tanıtım fiyatıdır.
SONNET5_PRICE_CHANGE_NOTE = "Claude Sonnet 5 tanıtım fiyatı ($2/$10), 1 Eylül 2026'dan itibaren standart fiyata ($3/$15) çıkacaktır."

# Sağlayıcıya göre modeller; her modelin özellik/fiyat/benchmark verisi elle
# küratörlüğü yapılmıştır (referans niteliğindedir, resmi kaynaklarla teyit edilmeli).
# Fiyatlar USD/1M token (giriş/çıkış); bağlam penceresi bin token cinsindendir.
# Benchmark skorları (mmlu/humaneval/gpqa) yaklaşık, sağlayıcı tarafından yayınlanan
# yüzde değerleridir; metodoloji farklılıkları nedeniyle sağlayıcılar arası birebir
# kıyaslanabilirlikleri sınırlıdır.
AI_MODELS: dict[str, dict] = {
    "GPT-5.6 Sol (OpenAI)": {
        "sağlayıcı": "OpenAI", "açık_kaynak": False, "çoklu_modal": True,
        "bağlam_penceresi_bin_token": 1050, "giriş_fiyat_1m_usd": 5.0, "çıkış_fiyat_1m_usd": 30.0,
        "mmlu": 92.0, "humaneval": 92.0, "gpqa": 85.0, "arama_terimi": "GPT-5.6 Sol OpenAI model",
    },
    "GPT-5.6 Luna (OpenAI)": {
        "sağlayıcı": "OpenAI", "açık_kaynak": False, "çoklu_modal": True,
        "bağlam_penceresi_bin_token": 1050, "giriş_fiyat_1m_usd": 1.0, "çıkış_fiyat_1m_usd": 6.0,
        "mmlu": 86.0, "humaneval": 86.0, "gpqa": 60.0, "arama_terimi": "GPT-5.6 Luna OpenAI model",
    },
    "Claude Opus 4.8 (Anthropic)": {
        "sağlayıcı": "Anthropic", "açık_kaynak": False, "çoklu_modal": True,
        "bağlam_penceresi_bin_token": 1000, "giriş_fiyat_1m_usd": 5.0, "çıkış_fiyat_1m_usd": 25.0,
        "mmlu": 92.0, "humaneval": 94.0, "gpqa": 87.0, "arama_terimi": "Claude Opus Anthropic model",
    },
    "Claude Sonnet 5 (Anthropic)": {
        "sağlayıcı": "Anthropic", "açık_kaynak": False, "çoklu_modal": True,
        "bağlam_penceresi_bin_token": 1000, "giriş_fiyat_1m_usd": 2.0, "çıkış_fiyat_1m_usd": 10.0,
        "mmlu": 90.0, "humaneval": 93.0, "gpqa": 80.0, "arama_terimi": "Claude Sonnet Anthropic model",
    },
    "Claude Haiku 4.5 (Anthropic)": {
        "sağlayıcı": "Anthropic", "açık_kaynak": False, "çoklu_modal": True,
        "bağlam_penceresi_bin_token": 200, "giriş_fiyat_1m_usd": 1.0, "çıkış_fiyat_1m_usd": 5.0,
        "mmlu": 85.0, "humaneval": 88.0, "gpqa": 70.0, "arama_terimi": "Claude Haiku Anthropic model",
    },
    "Gemini 3.1 Pro (Google)": {
        "sağlayıcı": "Google", "açık_kaynak": False, "çoklu_modal": True,
        "bağlam_penceresi_bin_token": 1000, "giriş_fiyat_1m_usd": 2.0, "çıkış_fiyat_1m_usd": 12.0,
        "mmlu": 91.0, "humaneval": 90.0, "gpqa": 94.0, "arama_terimi": "Gemini 3.1 Pro Google model",
    },
    "Gemini 2.5 Flash (Google)": {
        "sağlayıcı": "Google", "açık_kaynak": False, "çoklu_modal": True,
        "bağlam_penceresi_bin_token": 1000, "giriş_fiyat_1m_usd": 0.3, "çıkış_fiyat_1m_usd": 2.5,
        "mmlu": 84.0, "humaneval": 85.0, "gpqa": 68.0, "arama_terimi": "Gemini Flash Google model",
    },
    "Llama 4 Maverick (Meta)": {
        "sağlayıcı": "Meta", "açık_kaynak": True, "çoklu_modal": True,
        "bağlam_penceresi_bin_token": 1000, "giriş_fiyat_1m_usd": 0.2, "çıkış_fiyat_1m_usd": 0.6,
        "mmlu": 87.0, "humaneval": 85.0, "gpqa": 70.0, "arama_terimi": "Llama 4 Maverick Meta model",
    },
    "Mistral Large (Mistral AI)": {
        "sağlayıcı": "Mistral AI", "açık_kaynak": True, "çoklu_modal": False,
        "bağlam_penceresi_bin_token": 128, "giriş_fiyat_1m_usd": 2.0, "çıkış_fiyat_1m_usd": 6.0,
        "mmlu": 84.0, "humaneval": 84.0, "gpqa": 60.0, "arama_terimi": "Mistral Large model",
    },
    "DeepSeek V4 Flash (DeepSeek)": {
        "sağlayıcı": "DeepSeek", "açık_kaynak": True, "çoklu_modal": False,
        "bağlam_penceresi_bin_token": 1000, "giriş_fiyat_1m_usd": 0.14, "çıkış_fiyat_1m_usd": 0.28,
        "mmlu": 86.2, "humaneval": 89.0, "gpqa": 88.1, "arama_terimi": "DeepSeek V4 Flash model",
    },
    "Grok 4.5 (xAI)": {
        "sağlayıcı": "xAI", "açık_kaynak": False, "çoklu_modal": True,
        "bağlam_penceresi_bin_token": 500, "giriş_fiyat_1m_usd": 2.0, "çıkış_fiyat_1m_usd": 6.0,
        "mmlu": 90.0, "humaneval": 89.0, "gpqa": 82.0, "arama_terimi": "Grok 4.5 xAI model",
    },
    "Qwen3-Max (Alibaba)": {
        "sağlayıcı": "Alibaba", "açık_kaynak": True, "çoklu_modal": True,
        "bağlam_penceresi_bin_token": 256, "giriş_fiyat_1m_usd": 2.5, "çıkış_fiyat_1m_usd": 7.5,
        "mmlu": 86.0, "humaneval": 87.0, "gpqa": 76.4, "arama_terimi": "Qwen3-Max Alibaba model",
    },
}

FEATURE_COLUMNS = [
    "sağlayıcı", "açık_kaynak", "çoklu_modal", "bağlam_penceresi_bin_token",
    "giriş_fiyat_1m_usd", "çıkış_fiyat_1m_usd",
]
BENCHMARK_COLUMNS = ["mmlu", "humaneval", "gpqa"]


def get_model_names() -> list[str]:
    return list(AI_MODELS.keys())


def get_providers() -> list[str]:
    return sorted({info["sağlayıcı"] for info in AI_MODELS.values()})


def build_comparison_table(selected: list[str]) -> pd.DataFrame:
    """Seçilen modeller için özellik + benchmark kolonlarını içeren bir tablo döndürür.

    Bilinmeyen model adları sessizce atlanır (AI_MODELS'te bulunmayan bir isim
    sözlük tabanlı bir eşleştirme hatasına işaret eder; yine de hata fırlatmak
    yerine mevcut olanlarla devam edilir).
    """
    rows = []
    for name in selected:
        info = AI_MODELS.get(name)
        if info is None:
            continue
        rows.append({"Model": name, **{k: info[k] for k in FEATURE_COLUMNS + BENCHMARK_COLUMNS}})
    return pd.DataFrame(rows)


def _request_with_retry(url: str, *, method: str = "get", max_retries: int = 1,
                         backoff_seconds: float = 1.5, **kwargs) -> "requests.Response | None":
    """company_analysis._request_with_retry'nin birebir kopyasıdır — modüller
    kasıtlı olarak bağımsız tutulur (bkz. CLAUDE.md, borsa_analysis'teki aynı desen)."""
    request_fn = requests.post if method == "post" else requests.get
    for attempt in range(max_retries + 1):
        try:
            resp = request_fn(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, **kwargs)
        except requests.RequestException:
            return None

        if resp.status_code == 429 or 500 <= resp.status_code < 600:
            if attempt < max_retries:
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else backoff_seconds
                time.sleep(min(wait, _RETRY_MAX_WAIT_SECONDS))
                continue
            return None

        try:
            resp.raise_for_status()
        except requests.HTTPError:
            return None
        return resp
    return None


def _find_source_text(item: ET.Element) -> str | None:
    """company_analysis._find_source_text'in birebir kopyasıdır (bkz. oradaki docstring)."""
    for child in item:
        local_tag = child.tag.rsplit("}", 1)[-1]
        if local_tag.lower() == "source" and child.text:
            return child.text
    return None


def _resolve_article_link(link: str) -> str:
    if "bing.com/news/apiclick.aspx" not in link:
        return link
    query = urlparse(link).query
    params = parse_qs(query)
    real_url = params.get("url", [None])[0]
    return real_url if real_url else link


def _parse_standard_rss(root: ET.Element, default_source: str, max_items: int) -> list[dict]:
    items = []
    for item in root.findall(".//item")[:max_items]:
        title = (item.findtext("title") or "").strip()
        link = _resolve_article_link((item.findtext("link") or "").strip())
        pub_date = (item.findtext("pubDate") or "").strip()
        source_text = _find_source_text(item)
        source = source_text if source_text else default_source
        if title:
            items.append({"başlık": title, "kaynak": source, "link": link, "tarih": pub_date})
    return items


def _fetch_news_rss(url: str, default_source: str, max_items: int) -> list[dict]:
    resp = _request_with_retry(url)
    if resp is None:
        return []
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        return []
    return _parse_standard_rss(root, default_source, max_items)


def _google_news_rss(query: str, max_items: int = 10) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=tr&gl=TR&ceid=TR:tr"
    return _fetch_news_rss(url, "Google Haberler", max_items)


def _bing_news_rss(query: str, max_items: int = 8) -> list[dict]:
    url = f"https://www.bing.com/news/search?q={quote_plus(query)}&format=rss"
    return _fetch_news_rss(url, "Bing Haberler", max_items)


def collect_model_news(model_name: str) -> tuple[list[dict], list[str]]:
    """Bir yapay zeka modeli için Google/Bing Haberler RSS üzerinden güncel
    haber/duyuru başlıklarını toplar. (kayıtlar, uyarılar) döndürür.

    AI_MODELS'teki `arama_terimi` alanı kullanılır (yalnızca model adını
    aramak, aynı isimli alakasız sonuçları — örn. "Grok" kelime oyunu —
    artırabileceğinden sağlayıcı adı da sorguya eklenmiştir). Bilinmeyen bir
    model adı verilirse boş liste ve bir uyarı döner.
    """
    info = AI_MODELS.get(model_name)
    if info is None:
        return [], [f"Bilinmeyen model: {model_name}"]

    query = info["arama_terimi"]
    warnings: list[str] = []
    records: list[dict] = []
    seen_links: set[str] = set()

    for fetch_fn, label in [(_google_news_rss, "Google Haberler"), (_bing_news_rss, "Bing Haberler")]:
        results = fetch_fn(query)
        if not results:
            warnings.append(f"{label} kaynağına ulaşılamadı veya sonuç bulunamadı.")
            continue
        for r in results:
            if r["link"] and r["link"] in seen_links:
                continue
            seen_links.add(r["link"])
            records.append(r)

    return records, warnings
