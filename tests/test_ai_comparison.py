"""ai_comparison.py için birim testleri.

Dış ağ isteği atmadan, company_analysis/borsa_analysis testlerindeki desenle
(monkeypatch + sahte requests.Response) çalışır; sys.path ayarı tests/conftest.py'de yapılır.
"""
import requests

import ai_comparison
from ai_comparison import (
    AI_MODELS,
    BENCHMARK_COLUMNS,
    FEATURE_COLUMNS,
    _request_with_retry,
    build_comparison_table,
    collect_model_news,
    get_model_names,
    get_providers,
)


class _FakeResponse:
    """requests.Response'un testlerde ihtiyaç duyulan minimal bir taklidi."""

    def __init__(self, status_code=200, headers=None, content=b""):
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


_SAMPLE_RSS = b"""<?xml version="1.0"?>
<rss><channel>
  <item>
    <title>Ornek Model Duyurusu</title>
    <link>https://example.com/haber</link>
    <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
    <source>Ornek Kaynak</source>
  </item>
</channel></rss>"""


# --- AI_MODELS statik veri bütünlüğü -----------------------------------------

def test_ai_models_have_all_expected_fields():
    expected_fields = set(FEATURE_COLUMNS + BENCHMARK_COLUMNS + ["arama_terimi"])
    for name, info in AI_MODELS.items():
        assert expected_fields.issubset(info.keys()), f"{name} eksik alan içeriyor"


def test_ai_models_benchmark_scores_within_0_100():
    for name, info in AI_MODELS.items():
        for col in BENCHMARK_COLUMNS:
            assert 0 <= info[col] <= 100, f"{name}.{col} sınır dışı"


def test_get_model_names_matches_ai_models_keys():
    assert get_model_names() == list(AI_MODELS.keys())


def test_get_providers_is_sorted_and_deduplicated():
    providers = get_providers()
    assert providers == sorted(set(providers))
    assert "OpenAI" in providers
    assert "Anthropic" in providers


# --- build_comparison_table ---------------------------------------------------

def test_build_comparison_table_includes_selected_models_in_order():
    names = get_model_names()[:2]
    table = build_comparison_table(names)
    assert list(table["Model"]) == names
    assert set(FEATURE_COLUMNS + BENCHMARK_COLUMNS).issubset(table.columns)


def test_build_comparison_table_skips_unknown_model_names():
    names = [get_model_names()[0], "Bilinmeyen Model XYZ"]
    table = build_comparison_table(names)
    assert len(table) == 1
    assert table.iloc[0]["Model"] == names[0]


def test_build_comparison_table_empty_selection_returns_empty_dataframe():
    table = build_comparison_table([])
    assert table.empty


# --- collect_model_news -------------------------------------------------------

def test_collect_model_news_unknown_model_returns_warning_without_network_call(monkeypatch):
    def fail_if_called(*a, **k):
        raise AssertionError("bilinmeyen model için ağ isteği atılmamalı")

    monkeypatch.setattr(ai_comparison.requests, "get", fail_if_called)
    records, warnings = collect_model_news("Bilinmeyen Model XYZ")
    assert records == []
    assert "Bilinmeyen Model XYZ" in warnings[0]


def test_collect_model_news_parses_and_dedupes_across_sources(monkeypatch):
    monkeypatch.setattr(ai_comparison.requests, "get", lambda *a, **k: _FakeResponse(200, content=_SAMPLE_RSS))
    model_name = get_model_names()[0]

    records, warnings = collect_model_news(model_name)

    assert len(records) == 1  # google + bing aynı linki döndürüyor -> tekilleşir
    assert records[0]["başlık"] == "Ornek Model Duyurusu"
    assert records[0]["kaynak"] == "Ornek Kaynak"
    assert warnings == []


def test_collect_model_news_returns_warnings_when_sources_unreachable(monkeypatch):
    monkeypatch.setattr(ai_comparison.requests, "get", lambda *a, **k: _FakeResponse(500))
    monkeypatch.setattr(ai_comparison.time, "sleep", lambda s: None)
    model_name = get_model_names()[0]

    records, warnings = collect_model_news(model_name)

    assert records == []
    assert len(warnings) == 2  # Google + Bing ikisi de ulaşılamadı


# --- _request_with_retry (company_analysis/borsa_analysis'teki desenden uyarlanmıştır) ---

def test_request_with_retry_succeeds_immediately_without_sleeping(monkeypatch):
    sleeps = []
    monkeypatch.setattr(ai_comparison.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(ai_comparison.requests, "get", lambda *a, **k: _FakeResponse(200))

    resp = _request_with_retry("https://example.com")
    assert resp is not None and resp.status_code == 200
    assert sleeps == []


def test_request_with_retry_returns_none_immediately_on_connection_error(monkeypatch):
    sleeps = []
    monkeypatch.setattr(ai_comparison.time, "sleep", lambda s: sleeps.append(s))

    def fake_get(*a, **k):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr(ai_comparison.requests, "get", fake_get)

    resp = _request_with_retry("https://example.com")
    assert resp is None
    assert sleeps == []
