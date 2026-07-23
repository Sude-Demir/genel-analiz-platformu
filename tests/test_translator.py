"""app/translator.py için birim testleri.

Gerçek Google Translate API'sine bağımlı olmamak için `_translate_via_api`
(alt seviye ağ çağrısı) monkeypatch ile sahte bir çeviri fonksiyonuyla
değiştirilir; böylece testler hızlı, deterministik ve internet bağlantısından
bağımsızdır. Yalnızca `_translate_via_api`'nin kendi try/except zarfını
doğrulayan test gerçek `deep_translator.GoogleTranslator` sınıfını
(ağa hiç çıkmadan, hata fırlatan sahte bir sınıfla) devre dışı bırakır.
"""
import ast
import glob
import os

import pytest

import translator


@pytest.fixture(autouse=True)
def _isolated_cache(monkeypatch, tmp_path):
    """Her testten önce bellek/disk önbelleğini izole eder; gerçek
    translation_cache.json dosyasına dokunmaz veya ondan etkilenmez."""
    monkeypatch.setattr(translator, "_mem_cache", {})
    monkeypatch.setattr(translator, "_disk_loaded", True)
    monkeypatch.setattr(translator, "_CACHE_FILE", str(tmp_path / "translation_cache.json"))


@pytest.fixture
def lang(monkeypatch):
    """Aktif dili kontrol etmek için st.session_state'i, gerçek bir Streamlit
    çalışma zamanı olmadan basit bir sözlükle değiştirir."""
    state = {"lang": "tr"}
    monkeypatch.setattr(translator.st, "session_state", state)
    return state


def _fake_api(prefix="ÇEVİRİ: "):
    def _translate(text, target_lang):
        return f"{prefix}{text}"
    return _translate


# ── tr() ─────────────────────────────────────────────────────────────────

def test_tr_returns_original_text_when_lang_is_turkish(lang, monkeypatch):
    monkeypatch.setattr(translator, "_translate_via_api", _fake_api())
    lang["lang"] = "tr"
    assert translator.tr("Merhaba") == "Merhaba"


def test_tr_returns_empty_or_whitespace_text_unchanged(lang, monkeypatch):
    monkeypatch.setattr(translator, "_translate_via_api", _fake_api())
    lang["lang"] = "en"
    assert translator.tr("") == ""
    assert translator.tr("   ") == "   "


def test_tr_translates_via_api_when_lang_is_not_turkish(lang, monkeypatch):
    monkeypatch.setattr(translator, "_translate_via_api", _fake_api())
    lang["lang"] = "en"
    assert translator.tr("Merhaba") == "ÇEVİRİ: Merhaba"


def test_tr_caches_translation_and_does_not_call_api_twice(lang, monkeypatch):
    calls = []

    def counting_api(text, target_lang):
        calls.append(text)
        return f"EN:{text}"

    monkeypatch.setattr(translator, "_translate_via_api", counting_api)
    lang["lang"] = "en"

    assert translator.tr("Merhaba") == "EN:Merhaba"
    assert translator.tr("Merhaba") == "EN:Merhaba"
    assert calls == ["Merhaba"]  # ikinci çağrı önbellekten döndü, API'ye gitmedi


def test_tr_falls_back_to_original_text_on_api_failure(lang, monkeypatch):
    monkeypatch.setattr(translator, "_translate_via_api", lambda text, target_lang: None)
    lang["lang"] = "en"
    assert translator.tr("Merhaba") == "Merhaba"


def test_tr_falls_back_to_original_text_for_unsupported_language_code(lang, monkeypatch):
    monkeypatch.setattr(translator, "_translate_via_api", _fake_api())
    lang["lang"] = "fr"  # LANG_CODES içinde yok
    assert translator.tr("Merhaba") == "Merhaba"


def test_translate_via_api_returns_none_when_deep_translator_raises(monkeypatch):
    import deep_translator

    class FailingTranslator:
        def __init__(self, *a, **k):
            pass

        def translate(self, text):
            raise ConnectionError("ağ hatası")

    monkeypatch.setattr(deep_translator, "GoogleTranslator", FailingTranslator)
    assert translator._translate_via_api("Merhaba", "en") is None


# ── trf() ────────────────────────────────────────────────────────────────

def test_trf_returns_original_when_lang_is_turkish(lang, monkeypatch):
    monkeypatch.setattr(translator, "_translate_via_api", _fake_api())
    lang["lang"] = "tr"
    assert translator.trf("Satır: {n}", n=7) == "Satır: 7"


def test_trf_translates_template_then_substitutes_dynamic_values(lang, monkeypatch):
    monkeypatch.setattr(
        translator, "_translate_via_api",
        lambda text, target_lang: text.replace("Toplam", "Total").replace("satır", "rows").replace("bulundu", "found"),
    )
    lang["lang"] = "en"
    assert translator.trf("Toplam {n} satır bulundu.", n=42) == "Total 42 rows found."


def test_trf_supports_format_specifiers_in_placeholders(lang, monkeypatch):
    monkeypatch.setattr(translator, "_translate_via_api", lambda text, target_lang: text.replace("Ortalama", "Average"))
    lang["lang"] = "en"
    assert translator.trf("Ortalama gelir: {val:,.0f} $", val=1234.5) == "Average gelir: 1,234 $"


def test_trf_same_template_with_different_values_only_calls_api_once(lang, monkeypatch):
    calls = []

    def counting_api(text, target_lang):
        calls.append(text)
        return text.replace("Satır", "Row")

    monkeypatch.setattr(translator, "_translate_via_api", counting_api)
    lang["lang"] = "en"

    assert translator.trf("Satır: {n}", n=1) == "Row: 1"
    assert translator.trf("Satır: {n}", n=2) == "Row: 2"
    assert calls == ["Satır: {n}"]  # şablon yalnızca bir kez çevrildi (asıl kazanım)


def test_trf_falls_back_to_original_template_if_translation_breaks_placeholders(lang, monkeypatch):
    # Çeviri servisi yer tutucuyu bozarsa (örn. adı değiştirirse) .format()
    # KeyError fırlatır; trf orijinal Türkçe şablona düşerek çökmemeli.
    monkeypatch.setattr(translator, "_translate_via_api", lambda text, target_lang: "Bozuk şablon: {yanlis_ad}")
    lang["lang"] = "en"
    assert translator.trf("Satır: {n}", n=5) == "Satır: 5"


# ── warm_cache() ─────────────────────────────────────────────────────────

def test_warm_cache_returns_zero_for_turkish():
    assert translator.warm_cache("tr") == 0


def test_warm_cache_returns_zero_for_unsupported_language():
    assert translator.warm_cache("fr") == 0


def test_warm_cache_translates_only_uncached_static_strings(monkeypatch):
    calls = []

    def counting_api(text, target_lang):
        calls.append(text)
        return f"EN:{text}"

    monkeypatch.setattr(translator, "_translate_via_api", counting_api)
    monkeypatch.setattr(translator, "_collect_static_strings", lambda: {"Merhaba", "Görüşürüz"})

    n = translator.warm_cache("en")
    assert n == 2
    assert set(calls) == {"Merhaba", "Görüşürüz"}
    assert translator._mem_cache["en"]["Merhaba"] == "EN:Merhaba"

    calls.clear()
    monkeypatch.setattr(translator, "_collect_static_strings", lambda: {"Merhaba", "Yeni Metin"})
    n2 = translator.warm_cache("en")
    assert n2 == 1
    assert calls == ["Yeni Metin"]  # "Merhaba" zaten önbellekte, tekrar çevrilmedi


def test_warm_cache_integration_picks_up_real_tr_and_trf_calls_in_app(monkeypatch):
    """AST taramasının app/ altındaki gerçek tr()/trf() çağrılarını bulduğunu
    ve warm_cache()'in bunları (API mocklanmış olarak) önbelleğe yazdığını
    doğrular — yalnızca ağ çağrısı taklit edilir, tarama gerçek koddur."""
    monkeypatch.setattr(translator, "_translate_via_api", lambda text, target_lang: f"[{target_lang}] {text}")
    n = translator.warm_cache("en")
    assert n > 0
    assert len(translator._mem_cache["en"]) == n


# ── tr_cached_count() ────────────────────────────────────────────────────

def test_tr_cached_count_reports_entry_counts_per_language(lang, monkeypatch):
    monkeypatch.setattr(translator, "_translate_via_api", _fake_api())
    lang["lang"] = "en"
    translator.tr("Bir")
    translator.tr("İki")
    lang["lang"] = "de"
    translator.tr("Bir")
    assert translator.tr_cached_count() == {"en": 2, "de": 1}


# ── Disk önbelleği kalıcılığı ────────────────────────────────────────────

def test_disk_cache_persists_and_reloads_after_memory_reset(lang, monkeypatch):
    monkeypatch.setattr(translator, "_translate_via_api", _fake_api())
    lang["lang"] = "en"
    translator.tr("Merhaba")
    assert os.path.exists(translator._CACHE_FILE)

    monkeypatch.setattr(translator, "_mem_cache", {})
    monkeypatch.setattr(translator, "_disk_loaded", False)
    assert translator.tr("Merhaba") == "ÇEVİRİ: Merhaba"


# ── Regresyon koruması: tr(f"...") kullanımı yasak ──────────────────────
# app/ altında bir yerde tr() çağrısına dinamik (f-string veya string
# birleştirme) metin geçirilirse, warm_cache() bunu önceden çeviremez ve
# her render'da canlı API isteğine yol açar (bkz. trf() ve ilgili panel
# düzeltmeleri). Bu test böyle bir kullanımın yeniden eklenmesini engeller.

def test_no_panel_code_passes_dynamic_text_to_tr():
    app_dir = os.path.dirname(translator.__file__)
    offenders = []
    for path in glob.glob(os.path.join(app_dir, "**", "*.py"), recursive=True):
        if os.path.abspath(path) == os.path.abspath(translator.__file__):
            continue
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "tr"
                and len(node.args) == 1
                and isinstance(node.args[0], (ast.JoinedStr, ast.BinOp))
            ):
                offenders.append(f"{path}:{node.lineno}")
    assert not offenders, (
        "tr() çağrılarına dinamik (f-string/birleştirme) metin geçirilmiş; "
        "bunun yerine trf(sabit_sablon, **degerler) kullanın: " + ", ".join(offenders)
    )
