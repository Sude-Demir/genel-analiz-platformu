"""Bir hisse senedi/endeks sembolü için güncel ve geçmiş fiyat verisi çekme ve özetleme.

Ücretli/anahtarlı bir API kullanmadan çalışır: Yahoo Finance'in herkese açık
`v8/finance/chart` JSON ucu üzerinden OHLC (açılış/yüksek/düşük/kapanış) ve hacim
verisi çeker. Bu uç, BIST (örn. "THYAO.IS"), ABD/global hisseleri (örn. "AAPL")
ve endeksleri (örn. "^GSPC") tek biçimde destekler. Trend yorumu basit bir
hareketli ortalama (SMA20) karşılaştırmasına dayalı sözlük/kural tabanlı bir
sezgiseldir; harici bir AI/istatistiksel model kullanmaz.
"""
import time

import numpy as np
import pandas as pd
import requests

REQUEST_TIMEOUT = 8
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AnalizPlatformu/1.0"}
_RETRY_MAX_WAIT_SECONDS = 3.0

RANGE_OPTIONS = {
    "1 Ay": "1mo",
    "3 Ay": "3mo",
    "6 Ay": "6mo",
    "1 Yıl": "1y",
    "5 Yıl": "5y",
}

_INTERVAL_FOR_RANGE = {
    "1mo": "1d",
    "3mo": "1d",
    "6mo": "1d",
    "1y": "1d",
    "5y": "1wk",
}

_PRICE_COLUMNS = ["tarih", "açılış", "yüksek", "düşük", "kapanış", "hacim"]

POPULAR_SYMBOLS: dict[str, str] = {
    # BIST100 — popüler hisseler
    "Türk Hava Yolları (THYAO.IS)": "THYAO.IS",
    "Garanti BBVA (GARAN.IS)": "GARAN.IS",
    "Akbank (AKBNK.IS)": "AKBNK.IS",
    "Aselsan (ASELS.IS)": "ASELS.IS",
    "BİM (BIMAS.IS)": "BIMAS.IS",
    "Ereğli Demir Çelik (EREGL.IS)": "EREGL.IS",
    "Koç Holding (KCHOL.IS)": "KCHOL.IS",
    "Sabancı Holding (SAHOL.IS)": "SAHOL.IS",
    "Şişecam (SISE.IS)": "SISE.IS",
    "Tüpraş (TUPRS.IS)": "TUPRS.IS",
    "Turkcell (TCELL.IS)": "TCELL.IS",
    "Ford Otosan (FROTO.IS)": "FROTO.IS",
    "Pegasus (PGSUS.IS)": "PGSUS.IS",
    "Yapı Kredi (YKBNK.IS)": "YKBNK.IS",
    "İş Bankası C (ISCTR.IS)": "ISCTR.IS",
    # Global — popüler hisseler
    "Apple (AAPL)": "AAPL",
    "Microsoft (MSFT)": "MSFT",
    "Alphabet / Google (GOOGL)": "GOOGL",
    "Amazon (AMZN)": "AMZN",
    "NVIDIA (NVDA)": "NVDA",
    "Tesla (TSLA)": "TSLA",
    "Meta (META)": "META",
    "Netflix (NFLX)": "NFLX",
    # Endeksler
    "BIST 100 Endeksi (^XU100.IS)": "^XU100.IS",
    "S&P 500 Endeksi (^GSPC)": "^GSPC",
}


def _request_with_retry(url: str, *, method: str = "get", max_retries: int = 1,
                         backoff_seconds: float = 1.5, **kwargs) -> "requests.Response | None":
    """Kısa ömürlü hız sınırı (429) ve geçici sunucu hatalarında (5xx) bir kez
    kısa bekleyip yeniden dener; bağlantı hatası/timeout gibi durumlarda hemen
    None döner (bunlar tekrar denemekle genelde çözülmez). company_analysis'teki
    aynı adlı fonksiyonun birebir kopyasıdır — modüller kasıtlı olarak bağımsız
    tutulur (bkz. CLAUDE.md).
    """
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


def fetch_price_history(symbol: str, range_: str = "1y") -> tuple[pd.DataFrame, dict, list[str]]:
    """Verilen sembol için Yahoo Finance'ten OHLC + hacim geçmişini çeker.

    (fiyat_df, meta, warnings) döndürür. Ağ hatası, geçersiz sembol veya boş
    sonuç durumunda boş bir DataFrame ve açıklayıcı bir uyarı döner; istisna
    fırlatmaz (bkz. company_analysis "sessiz boş liste" sözleşmesi).
    """
    empty_df = pd.DataFrame(columns=_PRICE_COLUMNS)
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return empty_df, {}, ["Sembol girilmedi."]

    interval = _INTERVAL_FOR_RANGE.get(range_, "1d")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"range": range_, "interval": interval, "includePrePost": "false"}
    resp = _request_with_retry(url, params=params)
    if resp is None:
        return empty_df, {}, [f"'{symbol}' için fiyat verisine ulaşılamadı."]

    try:
        payload = resp.json()
    except ValueError:
        return empty_df, {}, [f"'{symbol}' için gelen veri ayrıştırılamadı."]

    chart = payload.get("chart", {}) or {}
    error = chart.get("error")
    results = chart.get("result")
    if error or not results:
        desc = (error or {}).get("description") if error else None
        return empty_df, {}, [desc or f"'{symbol}' sembolü bulunamadı veya veri yok."]

    result = results[0]
    meta = result.get("meta", {}) or {}
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators", {}) or {}).get("quote") or [{}])[0]

    if not timestamps or not quote:
        return empty_df, meta, [f"'{symbol}' için fiyat geçmişi boş döndü."]

    df = pd.DataFrame({
        "tarih": pd.to_datetime(timestamps, unit="s", utc=True),
        "açılış": quote.get("open"),
        "yüksek": quote.get("high"),
        "düşük": quote.get("low"),
        "kapanış": quote.get("close"),
        "hacim": quote.get("volume"),
    })
    df = df.dropna(subset=["kapanış"]).reset_index(drop=True)
    if df.empty:
        return df, meta, [f"'{symbol}' için geçerli fiyat verisi bulunamadı."]
    return df, meta, []


def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Fiyat geçmişine klasik, kural tabanlı teknik gösterge kolonları ekler:
    `sma20`/`sma50` (basit hareketli ortalama), `rsi14` (Wilder'ın klasik göreceli
    güç endeksi) ve `macd`/`macd_sinyal`/`macd_hist` (12/26/9 üstel hareketli
    ortalama farkı). Saf pandas hesaplaması yapar; ağ çağrısı içermez, harici
    bir AI/istatistiksel model kullanmaz.

    Boş bir df verilirse aynı boş df (yeni kolonlar eklenmeden) döner.
    """
    if df.empty:
        return df.copy()

    result = df.copy()
    close = result["kapanış"]

    result["sma20"] = close.rolling(window=20, min_periods=5).mean()
    result["sma50"] = close.rolling(window=50, min_periods=10).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14, min_periods=14).mean()
    avg_loss = loss.rolling(window=14, min_periods=14).mean()
    # Kayıp sıfırsa (avg_loss=0) rs=inf olur -> rsi=100 (doğru: kayıp yoksa RSI maksimumdur).
    # Hem kazanç hem kayıp sıfırsa (tamamen düz fiyat) rs=0/0=NaN olur; bu durumda
    # nötr RSI değeri olan 50 kullanılır. Diğer durumlarda ilgili RuntimeWarning
    # (sıfıra bölme) bilinçli olarak bastırılır.
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(~((avg_gain == 0) & (avg_loss == 0)), 50.0)
    result["rsi14"] = rsi

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    result["macd"] = macd
    result["macd_sinyal"] = macd_signal
    result["macd_hist"] = macd - macd_signal

    return result


_VOLATILITY_THRESHOLDS = (1.5, 3.0)  # günlük getiri std (%) eşikleri: düşük/orta/yüksek


def summarize(df: pd.DataFrame, meta: dict) -> dict:
    """Fiyat geçmişinden güncel fiyat, günlük değişim, dönem yüksek/düşük,
    ortalama hacim ve SMA20 tabanlı kural temelli bir trend yorumu üretir.

    Veri yoksa boş sözlük döner.
    """
    if df.empty:
        return {}

    last_close = float(df["kapanış"].iloc[-1])
    prev_close = meta.get("previousClose")
    if prev_close is None and len(df) > 1:
        prev_close = float(df["kapanış"].iloc[-2])
    prev_close = float(prev_close) if prev_close is not None else last_close

    change = last_close - prev_close
    change_pct = (change / prev_close * 100) if prev_close else 0.0

    period_high = float(df["yüksek"].max())
    period_low = float(df["düşük"].min())
    avg_volume = float(df["hacim"].mean()) if df["hacim"].notna().any() else 0.0

    first_close = float(df["kapanış"].iloc[0])
    period_return_pct = ((last_close - first_close) / first_close * 100) if first_close else 0.0

    week52_high = meta.get("fiftyTwoWeekHigh")
    week52_low = meta.get("fiftyTwoWeekLow")
    week52_high = float(week52_high) if week52_high is not None else period_high
    week52_low = float(week52_low) if week52_low is not None else period_low

    daily_returns = df["kapanış"].pct_change().dropna()
    volatility_pct = float(daily_returns.std() * 100) if len(daily_returns) > 1 else 0.0
    low_thr, high_thr = _VOLATILITY_THRESHOLDS
    if volatility_pct < low_thr:
        volatility_status = "good"
    elif volatility_pct < high_thr:
        volatility_status = "warning"
    else:
        volatility_status = "critical"

    sma20 = df["kapanış"].rolling(window=20, min_periods=5).mean()
    if sma20.notna().any() and not pd.isna(sma20.iloc[-1]):
        last_sma = sma20.iloc[-1]
        if last_close > last_sma * 1.01:
            trend_status, trend_text = "good", "Son kapanış 20 dönemlik ortalamanın belirgin şekilde üzerinde; yükseliş eğiliminde."
        elif last_close < last_sma * 0.99:
            trend_status, trend_text = "critical", "Son kapanış 20 dönemlik ortalamanın belirgin şekilde altında; düşüş eğiliminde."
        else:
            trend_status, trend_text = "warning", "Fiyat 20 dönemlik ortalamaya yakın seyrediyor; belirgin bir yön tespit edilemedi."
    else:
        trend_status, trend_text = "warning", "Yeterli veri olmadığından trend yorumu üretilemedi."

    return {
        "sembol": meta.get("symbol", ""),
        "para_birimi": meta.get("currency", ""),
        "güncel_fiyat": last_close,
        "önceki_kapanış": prev_close,
        "değişim": change,
        "değişim_yüzde": change_pct,
        "dönem_yüksek": period_high,
        "dönem_düşük": period_low,
        "ortalama_hacim": avg_volume,
        "dönem_getiri_yüzde": period_return_pct,
        "hafta52_yüksek": week52_high,
        "hafta52_düşük": week52_low,
        "volatilite_yüzde": volatility_pct,
        "volatilite_durum": volatility_status,
        "trend_durum": trend_status,
        "trend_yorum": trend_text,
    }


def predict_short_term_outlook(df: pd.DataFrame) -> dict:
    """Mevcut teknik göstergelerin (SMA20/SMA50 kesişimi, fiyat/SMA20 konumu,
    RSI14 aşırı alım/satım seviyeleri, MACD/sinyal çizgisi ilişkisi) kural
    tabanlı bir birleşiminden kısa vadeli bir "yön sezgiseli" üretir.

    ÖNEMLİ: Bu bir istatistiksel tahmin veya yatırım tavsiyesi DEĞİLDİR —
    yalnızca standart teknik analiz kurallarının basit, açıklanabilir bir
    özetidir; harici bir AI/istatistiksel model kullanmaz (bkz. modül
    docstring'i). Kendi içinde compute_technical_indicators() çağırır, bu
    yüzden bağımsız olarak ham fiyat df'siyle çağrılabilir.

    Her biri -1 (düşüş)/0 (nötr)/+1 (yükseliş) katkı veren 4 sinyalin toplamı
    (-4..+4) eşiklere göre sınıflandırılır: skor>=2 → "Yükseliş", skor<=-2 →
    "Düşüş", aksi halde "Karışık / Net Yön Yok". Veri yetersizse (ör. 2'den az
    satır) durum="warning", yön="Yeterli Veri Yok" döner; istisna fırlatmaz.
    """
    if df.empty or len(df) < 2:
        return {
            "skor": 0, "yön": "Yeterli Veri Yok", "durum": "warning",
            "sinyaller": [], "gerekçe": "Sezgisel üretmek için yeterli fiyat geçmişi yok.",
        }

    ind = compute_technical_indicators(df)
    last = ind.iloc[-1]
    signals: list[dict] = []
    score = 0

    sma20_last, sma50_last = last.get("sma20"), last.get("sma50")
    if pd.isna(sma20_last) or pd.isna(sma50_last):
        signals.append({"ad": "SMA20/SMA50", "yön": 0, "açıklama": "SMA20/SMA50: yetersiz veri."})
    elif sma20_last > sma50_last:
        score += 1
        signals.append({"ad": "SMA20/SMA50", "yön": 1, "açıklama": "Kısa vadeli ortalama (SMA20) uzun vadelinin (SMA50) üzerinde."})
    elif sma20_last < sma50_last:
        score -= 1
        signals.append({"ad": "SMA20/SMA50", "yön": -1, "açıklama": "Kısa vadeli ortalama (SMA20) uzun vadelinin (SMA50) altında."})
    else:
        signals.append({"ad": "SMA20/SMA50", "yön": 0, "açıklama": "SMA20 ve SMA50 birbirine eşit."})

    close_last = last["kapanış"]
    if pd.isna(sma20_last):
        signals.append({"ad": "Fiyat/SMA20", "yön": 0, "açıklama": "Fiyat/SMA20: yetersiz veri."})
    elif close_last > sma20_last * 1.01:
        score += 1
        signals.append({"ad": "Fiyat/SMA20", "yön": 1, "açıklama": "Son kapanış SMA20'nin belirgin şekilde üzerinde."})
    elif close_last < sma20_last * 0.99:
        score -= 1
        signals.append({"ad": "Fiyat/SMA20", "yön": -1, "açıklama": "Son kapanış SMA20'nin belirgin şekilde altında."})
    else:
        signals.append({"ad": "Fiyat/SMA20", "yön": 0, "açıklama": "Fiyat SMA20'ye yakın seyrediyor."})

    rsi_last = last.get("rsi14")
    if pd.isna(rsi_last):
        signals.append({"ad": "RSI (14)", "yön": 0, "açıklama": "RSI (14): yetersiz veri."})
    elif rsi_last < 30:
        score += 1
        signals.append({"ad": "RSI (14)", "yön": 1, "açıklama": f"RSI {rsi_last:.0f} ile aşırı satım bölgesinde; teknik olarak toparlanma potansiyeli var."})
    elif rsi_last > 70:
        score -= 1
        signals.append({"ad": "RSI (14)", "yön": -1, "açıklama": f"RSI {rsi_last:.0f} ile aşırı alım bölgesinde; teknik olarak düzeltme potansiyeli var."})
    else:
        signals.append({"ad": "RSI (14)", "yön": 0, "açıklama": f"RSI {rsi_last:.0f} ile nötr bölgede."})

    macd_last, macd_signal_last = last.get("macd"), last.get("macd_sinyal")
    if pd.isna(macd_last) or pd.isna(macd_signal_last):
        signals.append({"ad": "MACD", "yön": 0, "açıklama": "MACD: yetersiz veri."})
    elif macd_last > macd_signal_last:
        score += 1
        signals.append({"ad": "MACD", "yön": 1, "açıklama": "MACD, sinyal çizgisinin üzerinde (pozitif momentum)."})
    elif macd_last < macd_signal_last:
        score -= 1
        signals.append({"ad": "MACD", "yön": -1, "açıklama": "MACD, sinyal çizgisinin altında (negatif momentum)."})
    else:
        signals.append({"ad": "MACD", "yön": 0, "açıklama": "MACD, sinyal çizgisine eşit."})

    if score >= 2:
        direction, status = "Yükseliş", "good"
    elif score <= -2:
        direction, status = "Düşüş", "critical"
    else:
        direction, status = "Karışık / Net Yön Yok", "warning"

    bullish_count = sum(1 for s in signals if s["yön"] == 1)
    bearish_count = sum(1 for s in signals if s["yön"] == -1)
    parts = []
    if bullish_count:
        parts.append(f"{bullish_count} gösterge yükseliş yönünde sinyal veriyor")
    if bearish_count:
        parts.append(f"{bearish_count} gösterge düşüş yönünde sinyal veriyor")
    if not parts:
        parts.append("göstergeler net bir yön belirtmiyor")
    gerekce = "; ".join(parts) + f" (toplam skor: {score:+d}/4)."

    return {"skor": score, "yön": direction, "durum": status, "sinyaller": signals, "gerekçe": gerekce}
