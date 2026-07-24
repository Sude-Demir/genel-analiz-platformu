"""ollama_client.py için birim testleri.

Ağa hiç çıkmadan, projedeki company_analysis/ai_comparison testlerindeki
desenle (monkeypatch + sahte requests.Response) çalışır; sys.path ayarı
tests/conftest.py'de yapılır.
"""
import requests

import ollama_client
from ollama_client import is_available, list_models, semantic_cv_review, semantic_job_match


class _FakeResponse:
    """requests.Response'un testlerde ihtiyaç duyulan minimal bir taklidi."""

    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data


_SAMPLE_TAGS = {"models": [{"name": "qwen2.5:3b"}, {"name": "llama3.1:8b"}]}


# --- is_available / list_models ----------------------------------------------

def test_is_available_sunucu_yoksa_false(monkeypatch):
    def fail(*a, **k):
        raise requests.ConnectionError("no server")

    monkeypatch.setattr(ollama_client.requests, "get", fail)
    assert is_available() is False


def test_is_available_sunucu_varsa_true(monkeypatch):
    monkeypatch.setattr(ollama_client.requests, "get", lambda *a, **k: _FakeResponse(200, _SAMPLE_TAGS))
    assert is_available() is True


def test_is_available_model_filtreli_yuklu_model(monkeypatch):
    monkeypatch.setattr(ollama_client.requests, "get", lambda *a, **k: _FakeResponse(200, _SAMPLE_TAGS))
    assert is_available("qwen2.5:3b") is True
    assert is_available("qwen2.5") is True  # tag'siz ad da eşleşmeli


def test_is_available_model_filtreli_yuklu_degil(monkeypatch):
    monkeypatch.setattr(ollama_client.requests, "get", lambda *a, **k: _FakeResponse(200, _SAMPLE_TAGS))
    assert is_available("mistral") is False


def test_is_available_http_hatasinda_false(monkeypatch):
    monkeypatch.setattr(ollama_client.requests, "get", lambda *a, **k: _FakeResponse(500))
    assert is_available() is False


def test_list_models_erisilemezse_bos_liste(monkeypatch):
    def fail(*a, **k):
        raise requests.Timeout("timeout")

    monkeypatch.setattr(ollama_client.requests, "get", fail)
    assert list_models() == []


def test_list_models_basarili(monkeypatch):
    monkeypatch.setattr(ollama_client.requests, "get", lambda *a, **k: _FakeResponse(200, _SAMPLE_TAGS))
    assert list_models() == ["qwen2.5:3b", "llama3.1:8b"]


# --- semantic_job_match --------------------------------------------------------

_VALID_LLM_RESPONSE = {
    "message": {
        "content": (
            '{"implicit_skills": ["frontend"], "semantic_match_pct": 72, '
            '"summary": "Aday ilana genel olarak uygun.", "missing_critical": ["docker"]}'
        )
    }
}


def test_semantic_match_basarili_json_ayristirilir(monkeypatch):
    monkeypatch.setattr(ollama_client.requests, "post", lambda *a, **k: _FakeResponse(200, _VALID_LLM_RESPONSE))

    result = semantic_job_match("cv metni", "ilan metni")

    assert result == {
        "implicit_skills": ["frontend"],
        "semantic_match_pct": 72,
        "summary": "Aday ilana genel olarak uygun.",
        "missing_critical": ["docker"],
    }


def test_semantic_match_baglanti_hatasi_none(monkeypatch):
    def fail(*a, **k):
        raise requests.ConnectionError("no server")

    monkeypatch.setattr(ollama_client.requests, "post", fail)
    assert semantic_job_match("cv", "ilan") is None


def test_semantic_match_timeout_none(monkeypatch):
    def fail(*a, **k):
        raise requests.Timeout("timeout")

    monkeypatch.setattr(ollama_client.requests, "post", fail)
    assert semantic_job_match("cv", "ilan") is None


def test_semantic_match_http_hatasinda_none(monkeypatch):
    monkeypatch.setattr(ollama_client.requests, "post", lambda *a, **k: _FakeResponse(500))
    assert semantic_job_match("cv", "ilan") is None


def test_semantic_match_bozuk_json_none(monkeypatch):
    bozuk = {"message": {"content": "bu JSON değil"}}
    monkeypatch.setattr(ollama_client.requests, "post", lambda *a, **k: _FakeResponse(200, bozuk))
    assert semantic_job_match("cv", "ilan") is None


def test_semantic_match_eksik_alan_none(monkeypatch):
    eksik = {"message": {"content": '{"implicit_skills": ["frontend"]}'}}
    monkeypatch.setattr(ollama_client.requests, "post", lambda *a, **k: _FakeResponse(200, eksik))
    assert semantic_job_match("cv", "ilan") is None


def test_semantic_match_yanlis_tip_none(monkeypatch):
    yanlis_tip = {
        "message": {
            "content": (
                '{"implicit_skills": "frontend", "semantic_match_pct": "yuksek", '
                '"summary": "ozet", "missing_critical": []}'
            )
        }
    }
    monkeypatch.setattr(ollama_client.requests, "post", lambda *a, **k: _FakeResponse(200, yanlis_tip))
    assert semantic_job_match("cv", "ilan") is None


def test_semantic_match_yuzde_0_100_araligina_sikistirilir(monkeypatch):
    sinir_disi = {
        "message": {
            "content": (
                '{"implicit_skills": [], "semantic_match_pct": 150, '
                '"summary": "ozet", "missing_critical": []}'
            )
        }
    }
    monkeypatch.setattr(ollama_client.requests, "post", lambda *a, **k: _FakeResponse(200, sinir_disi))
    result = semantic_job_match("cv", "ilan")
    assert result["semantic_match_pct"] == 100


# --- semantic_cv_review --------------------------------------------------------

_VALID_REVIEW_RESPONSE = {
    "message": {
        "content": (
            '{"summary": "Deneyimli bir aday.", "strengths": ["Python"], '
            '"weaknesses": ["Deneyim belirsiz"], "position_suggestions": ["Yazılım Geliştirici"], '
            '"improvement_tips": ["Deneyim ekleyin"]}'
        )
    }
}


def test_cv_review_basarili_json_ayristirilir(monkeypatch):
    monkeypatch.setattr(ollama_client.requests, "post", lambda *a, **k: _FakeResponse(200, _VALID_REVIEW_RESPONSE))

    result = semantic_cv_review("cv metni")

    assert result == {
        "summary": "Deneyimli bir aday.",
        "strengths": ["Python"],
        "weaknesses": ["Deneyim belirsiz"],
        "position_suggestions": ["Yazılım Geliştirici"],
        "improvement_tips": ["Deneyim ekleyin"],
    }


def test_cv_review_baglanti_hatasi_none(monkeypatch):
    def fail(*a, **k):
        raise requests.ConnectionError("no server")

    monkeypatch.setattr(ollama_client.requests, "post", fail)
    assert semantic_cv_review("cv") is None


def test_cv_review_bozuk_json_none(monkeypatch):
    bozuk = {"message": {"content": "bu JSON değil"}}
    monkeypatch.setattr(ollama_client.requests, "post", lambda *a, **k: _FakeResponse(200, bozuk))
    assert semantic_cv_review("cv") is None


def test_cv_review_eksik_alan_none(monkeypatch):
    eksik = {"message": {"content": '{"summary": "ozet"}'}}
    monkeypatch.setattr(ollama_client.requests, "post", lambda *a, **k: _FakeResponse(200, eksik))
    assert semantic_cv_review("cv") is None
