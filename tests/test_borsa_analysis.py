"""borsa_analysis.py için birim testleri.

Dış ağ isteği atmadan, company_analysis testlerindeki desenle (monkeypatch +
sahte requests.Response) çalışır; sys.path ayarı tests/conftest.py'de yapılır.
"""
import math

import pandas as pd
import requests

import borsa_analysis
from borsa_analysis import (
    _request_with_retry,
    compute_technical_indicators,
    fetch_price_history,
    predict_short_term_outlook,
    summarize,
)


class _FakeResponse:
    """requests.Response'un testlerde ihtiyaç duyulan minimal bir taklidi."""

    def __init__(self, status_code=200, headers=None, json_data=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._json_data = json_data if json_data is not None else {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data


def _valid_chart_payload():
    return {
        "chart": {
            "result": [{
                "meta": {"currency": "TRY", "symbol": "THYAO.IS", "previousClose": 95.0},
                "timestamp": [1700000000, 1700086400, 1700172800],
                "indicators": {"quote": [{
                    "open": [94.5, 95.2, 96.0],
                    "high": [96.0, 96.5, 97.2],
                    "low": [94.0, 95.0, 95.8],
                    "close": [95.8, 96.2, 97.0],
                    "volume": [1_000_000, 1_200_000, 900_000],
                }]},
            }],
            "error": None,
        }
    }


# --- fetch_price_history ---------------------------------------------------

def test_fetch_price_history_parses_valid_response(monkeypatch):
    monkeypatch.setattr(borsa_analysis.requests, "get",
                         lambda *a, **k: _FakeResponse(200, json_data=_valid_chart_payload()))

    df, meta, warnings = fetch_price_history("thyao.is", "1mo")

    assert warnings == []
    assert list(df.columns) == ["tarih", "açılış", "yüksek", "düşük", "kapanış", "hacim"]
    assert len(df) == 3
    assert df["kapanış"].tolist() == [95.8, 96.2, 97.0]
    assert pd.api.types.is_datetime64_any_dtype(df["tarih"])
    assert meta["symbol"] == "THYAO.IS"


def test_fetch_price_history_uppercases_symbol_in_request_url(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        return _FakeResponse(200, json_data=_valid_chart_payload())

    monkeypatch.setattr(borsa_analysis.requests, "get", fake_get)
    fetch_price_history("thyao.is")
    assert captured["url"].endswith("/THYAO.IS")


def test_fetch_price_history_empty_symbol_returns_warning_without_network_call(monkeypatch):
    def fail_if_called(*a, **k):
        raise AssertionError("boş sembol için ağ isteği atılmamalı")

    monkeypatch.setattr(borsa_analysis.requests, "get", fail_if_called)
    df, meta, warnings = fetch_price_history("   ")
    assert df.empty
    assert meta == {}
    assert warnings == ["Sembol girilmedi."]


def test_fetch_price_history_returns_warning_on_connection_error(monkeypatch):
    def fake_get(*a, **k):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr(borsa_analysis.requests, "get", fake_get)
    monkeypatch.setattr(borsa_analysis.time, "sleep", lambda s: None)

    df, meta, warnings = fetch_price_history("AAPL")
    assert df.empty
    assert meta == {}
    assert len(warnings) == 1 and "AAPL" in warnings[0]


def test_fetch_price_history_returns_warning_on_invalid_symbol(monkeypatch):
    payload = {"chart": {"result": None, "error": {
        "code": "Not Found", "description": "No data found, symbol may be delisted",
    }}}
    monkeypatch.setattr(borsa_analysis.requests, "get", lambda *a, **k: _FakeResponse(200, json_data=payload))

    df, meta, warnings = fetch_price_history("ZZZZ")
    assert df.empty
    assert meta == {}
    assert warnings == ["No data found, symbol may be delisted"]


def test_fetch_price_history_returns_warning_on_unparseable_json(monkeypatch):
    class _BadJsonResponse(_FakeResponse):
        def json(self):
            raise ValueError("invalid json")

    monkeypatch.setattr(borsa_analysis.requests, "get", lambda *a, **k: _BadJsonResponse(200))
    df, meta, warnings = fetch_price_history("AAPL")
    assert df.empty
    assert "AAPL" in warnings[0]


# --- summarize ---------------------------------------------------------------

def test_summarize_returns_empty_dict_for_empty_df():
    assert summarize(pd.DataFrame(columns=["tarih", "açılış", "yüksek", "düşük", "kapanış", "hacim"]), {}) == {}


def test_summarize_computes_change_and_percentage_from_meta_previous_close():
    df = pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=3, tz="UTC"),
        "açılış": [98.0, 99.0, 100.0],
        "yüksek": [99.5, 100.5, 101.0],
        "düşük": [97.5, 98.5, 99.0],
        "kapanış": [99.0, 100.0, 101.0],
        "hacim": [1000, 1200, 900],
    })
    meta = {"symbol": "AAPL", "currency": "USD", "previousClose": 100.0}

    result = summarize(df, meta)

    assert result["sembol"] == "AAPL"
    assert result["para_birimi"] == "USD"
    assert result["güncel_fiyat"] == 101.0
    assert result["değişim"] == 1.0
    assert round(result["değişim_yüzde"], 2) == 1.0
    assert result["dönem_yüksek"] == 101.0
    assert result["dönem_düşük"] == 97.5


def test_summarize_reports_uptrend_when_close_well_above_sma20():
    closes = [100.0] * 25 + [110.0, 112.0, 115.0, 118.0, 120.0]
    df = pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=len(closes), tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1000] * len(closes),
    })
    result = summarize(df, {"previousClose": closes[-2]})
    assert result["trend_durum"] == "good"
    assert "yükseliş" in result["trend_yorum"]


def test_summarize_reports_downtrend_when_close_well_below_sma20():
    closes = [100.0] * 25 + [90.0, 88.0, 85.0, 82.0, 80.0]
    df = pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=len(closes), tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1000] * len(closes),
    })
    result = summarize(df, {"previousClose": closes[-2]})
    assert result["trend_durum"] == "critical"
    assert "düşüş" in result["trend_yorum"]


def test_summarize_reports_insufficient_data_with_few_rows():
    closes = [100.0, 101.0, 99.0]
    df = pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=3, tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1000, 1000, 1000],
    })
    result = summarize(df, {"previousClose": 100.0})
    assert result["trend_durum"] == "warning"
    assert "Yeterli veri" in result["trend_yorum"]


def test_summarize_computes_period_return_percentage():
    closes = [100.0, 105.0, 110.0, 129.5]
    df = pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=4, tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1000] * 4,
    })
    result = summarize(df, {"previousClose": closes[-2]})
    assert round(result["dönem_getiri_yüzde"], 2) == 29.5


def test_summarize_uses_meta_52_week_high_low_when_present():
    closes = [100.0, 101.0, 99.0, 102.0]
    df = pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=4, tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1000] * 4,
    })
    result = summarize(df, {"previousClose": 99.0, "fiftyTwoWeekHigh": 150.0, "fiftyTwoWeekLow": 80.0})
    assert result["hafta52_yüksek"] == 150.0
    assert result["hafta52_düşük"] == 80.0


def test_summarize_falls_back_to_period_high_low_when_meta_missing_52_week():
    closes = [100.0, 101.0, 99.0, 102.0]
    df = pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=4, tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1000] * 4,
    })
    result = summarize(df, {"previousClose": 99.0})
    assert result["hafta52_yüksek"] == 102.0
    assert result["hafta52_düşük"] == 99.0


def test_summarize_classifies_low_volatility_for_smooth_series():
    closes = [100 + i * 0.5 for i in range(30)]
    df = pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=30, tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1000] * 30,
    })
    result = summarize(df, {"previousClose": closes[-2]})
    assert result["volatilite_durum"] == "good"


def test_summarize_classifies_high_volatility_for_zigzag_series():
    closes = []
    val = 100.0
    for i in range(30):
        val *= 1.05 if i % 2 == 0 else 0.94
        closes.append(val)
    df = pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=30, tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1000] * 30,
    })
    result = summarize(df, {"previousClose": closes[-2]})
    assert result["volatilite_durum"] == "critical"


# --- compute_technical_indicators --------------------------------------------

def test_compute_technical_indicators_returns_copy_for_empty_df():
    empty = pd.DataFrame(columns=["tarih", "açılış", "yüksek", "düşük", "kapanış", "hacim"])
    result = compute_technical_indicators(empty)
    assert result.empty


def test_compute_technical_indicators_sma_matches_manual_rolling_mean():
    closes = [100 + i for i in range(30)]
    df = pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=30, tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1000] * 30,
    })
    result = compute_technical_indicators(df)
    expected_sma20 = sum(closes[-20:]) / 20
    assert round(result["sma20"].iloc[-1], 6) == round(expected_sma20, 6)


def test_compute_technical_indicators_rsi_is_100_for_continuously_rising_series():
    closes = [100 + i * 0.5 for i in range(40)]
    df = pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=40, tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1000] * 40,
    })
    result = compute_technical_indicators(df)
    assert result["rsi14"].iloc[-1] == 100.0


def test_compute_technical_indicators_rsi_is_0_for_continuously_falling_series():
    closes = [150 - i * 0.5 for i in range(40)]
    df = pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=40, tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1000] * 40,
    })
    result = compute_technical_indicators(df)
    assert result["rsi14"].iloc[-1] == 0.0


def test_compute_technical_indicators_rsi_is_neutral_50_for_flat_series():
    closes = [100.0] * 30
    df = pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=30, tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1000] * 30,
    })
    result = compute_technical_indicators(df)
    assert result["rsi14"].iloc[-1] == 50.0


def test_compute_technical_indicators_rsi_stays_within_0_100_bounds():
    closes = []
    val = 100.0
    for i in range(60):
        val *= 1.05 if i % 3 != 0 else 0.94
        closes.append(val)
    df = pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=60, tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1000] * 60,
    })
    result = compute_technical_indicators(df)
    assert result["rsi14"].dropna().between(0, 100).all()


def test_compute_technical_indicators_macd_matches_ema12_minus_ema26():
    closes = [100 + i * 0.3 for i in range(40)]
    df = pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=40, tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1000] * 40,
    })
    result = compute_technical_indicators(df)
    close_series = pd.Series(closes)
    expected_macd = close_series.ewm(span=12, adjust=False).mean() - close_series.ewm(span=26, adjust=False).mean()
    assert round(result["macd"].iloc[-1], 6) == round(expected_macd.iloc[-1], 6)
    assert round(result["macd_hist"].iloc[-1], 6) == round(result["macd"].iloc[-1] - result["macd_sinyal"].iloc[-1], 6)


# --- predict_short_term_outlook ----------------------------------------------

def _make_price_df(closes):
    n = len(closes)
    return pd.DataFrame({
        "tarih": pd.date_range("2026-01-01", periods=n, tz="UTC"),
        "açılış": closes, "yüksek": closes, "düşük": closes, "kapanış": closes,
        "hacim": [1000] * n,
    })


def test_predict_short_term_outlook_returns_insufficient_data_for_empty_df():
    result = predict_short_term_outlook(pd.DataFrame(columns=["tarih", "açılış", "yüksek", "düşük", "kapanış", "hacim"]))
    assert result["yön"] == "Yeterli Veri Yok"
    assert result["durum"] == "warning"
    assert result["sinyaller"] == []


def test_predict_short_term_outlook_returns_insufficient_data_for_single_row():
    result = predict_short_term_outlook(_make_price_df([100.0]))
    assert result["yön"] == "Yeterli Veri Yok"


def test_predict_short_term_outlook_reports_uptrend_for_rising_series():
    closes = [100 + i * 0.8 for i in range(60)]
    result = predict_short_term_outlook(_make_price_df(closes))
    assert result["skor"] >= 2
    assert result["yön"] == "Yükseliş"
    assert result["durum"] == "good"
    assert len(result["sinyaller"]) == 4


def test_predict_short_term_outlook_reports_downtrend_for_falling_series():
    closes = [200 - i * 0.8 for i in range(60)]
    result = predict_short_term_outlook(_make_price_df(closes))
    assert result["skor"] <= -2
    assert result["yön"] == "Düşüş"
    assert result["durum"] == "critical"


def test_predict_short_term_outlook_reports_mixed_for_oscillating_series():
    closes = [100 + 3 * math.sin(i / 4) for i in range(60)]
    result = predict_short_term_outlook(_make_price_df(closes))
    assert -1 <= result["skor"] <= 1
    assert result["yön"] == "Karışık / Net Yön Yok"
    assert result["durum"] == "warning"


def test_predict_short_term_outlook_gerekce_mentions_signal_counts():
    closes = [100 + i * 0.8 for i in range(60)]
    result = predict_short_term_outlook(_make_price_df(closes))
    assert "sinyal veriyor" in result["gerekçe"]
    assert f"{result['skor']:+d}/4" in result["gerekçe"]


# --- _request_with_retry (company_analysis'teki desenden uyarlanmıştır) ------

def test_request_with_retry_succeeds_immediately_without_sleeping(monkeypatch):
    sleeps = []
    monkeypatch.setattr(borsa_analysis.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(borsa_analysis.requests, "get", lambda *a, **k: _FakeResponse(200))

    resp = _request_with_retry("https://example.com")
    assert resp is not None and resp.status_code == 200
    assert sleeps == []


def test_request_with_retry_retries_after_429_respecting_retry_after_header(monkeypatch):
    sleeps = []
    monkeypatch.setattr(borsa_analysis.time, "sleep", lambda s: sleeps.append(s))
    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeResponse(429, headers={"Retry-After": "2"})
        return _FakeResponse(200)

    monkeypatch.setattr(borsa_analysis.requests, "get", fake_get)

    resp = _request_with_retry("https://example.com")
    assert resp is not None and resp.status_code == 200
    assert calls["n"] == 2
    assert sleeps == [2.0]


def test_request_with_retry_returns_none_immediately_on_connection_error(monkeypatch):
    sleeps = []
    monkeypatch.setattr(borsa_analysis.time, "sleep", lambda s: sleeps.append(s))

    def fake_get(*a, **k):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr(borsa_analysis.requests, "get", fake_get)

    resp = _request_with_retry("https://example.com")
    assert resp is None
    assert sleeps == []
