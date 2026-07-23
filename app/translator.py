"""Otomatik çeviri motoru — deep-translator (Google Translate) tabanlı.

Kullanım:
    from translator import tr
    st.button(tr("Veri Yükle"))

Nasıl çalışır:
- Seçili dil Türkçe ise metin olduğu gibi döner (çeviri yapılmaz).
- Başka bir dil seçilmişse Google Translate API üzerinden çeviri yapılır.
- Çeviriler disk önbelleğine (app/translation_cache.json) kaydedilir;
  aynı metin + dil kombinasyonu tekrar sorulduğunda ağ isteği gitmez.
- İnternet yoksa veya API hatası alınırsa orijinal metin döner (sessiz fallback).

Performans notu: tr() her çağrıda tek tek (senkron) çeviri isteği atar; bir
panel onlarca tr() çağrısı içerdiğinde bu art arda beklemeye dönüşür. Bunu
önlemek için warm_cache(lang) fonksiyonu, app/ altındaki tüm sabit (f-string
olmayan) tr("...") çağrılarını statik olarak (ast ile) tarar ve hedef dile
ait olmayanları ThreadPoolExecutor ile PARALEL çevirip önbelleğe yazar. Dil
değiştirildiğinde bir kez çağrılır (bkz. Home.py); böylece sonraki tüm panel
gezintileri önbellekten anında döner.
"""
import ast
import concurrent.futures
import glob
import json
import os
import streamlit as st

# ── Dil kodu eşlemesi ─────────────────────────────────────────────────────────
LANG_CODES = {
    "tr": "tr",   # kaynak dil
    "en": "en",
    "de": "de",
}

# Önbellek dosyası — app/ dizininin yanında
_CACHE_FILE = os.path.join(os.path.dirname(__file__), "translation_cache.json")

# Bellek önbelleği (her yeniden yükleme için) — {lang: {text: translated}}
_mem_cache: dict[str, dict[str, str]] = {}
_disk_loaded = False


def _load_disk_cache() -> None:
    global _disk_loaded
    if _disk_loaded:
        return
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, encoding="utf-8") as f:
                data = json.load(f)
            for lang, entries in data.items():
                _mem_cache.setdefault(lang, {}).update(entries)
        except Exception:
            pass
    _disk_loaded = True


def _save_disk_cache() -> None:
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_mem_cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _translate_via_api(text: str, target_lang: str) -> str | None:
    """Google Translate API'sine istek atar; başarısızsa None döner."""
    try:
        from deep_translator import GoogleTranslator
        result = GoogleTranslator(source="tr", target=target_lang).translate(text)
        return result
    except Exception:
        return None


def tr(text: str) -> str:
    """Metni aktif dile çevirir.

    - text: Türkçe orijinal metin (kaynak dil).
    - Seçili dil "tr" ise metni değiştirmez.
    - Çeviri önce bellekte, sonra diskte aranır; bulunursa API'ye gitme.
    - API'den başarılı cevap gelince önbelleğe yazar.
    - Herhangi bir hata durumunda orijinal metin döner.
    """
    if not text or not text.strip():
        return text

    _load_disk_cache()

    lang = st.session_state.get("lang", "tr")
    if lang == "tr" or lang not in LANG_CODES:
        return text

    # Önbellekten kontrol
    cached = _mem_cache.get(lang, {}).get(text)
    if cached:
        return cached

    # API'den çevir
    translated = _translate_via_api(text, lang)
    if translated and translated != text:
        _mem_cache.setdefault(lang, {})[text] = translated
        _save_disk_cache()
        return translated

    return text


def tr_cached_count() -> dict:
    """Önbellek istatistiklerini döner (debug amaçlı)."""
    return {lang: len(entries) for lang, entries in _mem_cache.items()}


def _collect_static_strings() -> set[str]:
    """app/ altındaki tüm .py dosyalarını tarayıp sabit (f-string olmayan)
    tr("...") çağrılarının içindeki metinleri toplar.

    ast kullanılır çünkü Python, bitişik string literalleri (örn. tr("a" "b"))
    tek bir Constant düğümüne birleştirir; bu sayede çok satıra yayılmış
    tr(...) çağrıları da regex'e göre daha güvenilir yakalanır. f-string'ler
    (JoinedStr) ve değişken/ifade argümanları kasıtlı olarak dışarıda bırakılır
    — bunlar çalışma zamanı verisine bağlı olduğundan önceden çevrilemez.
    """
    app_dir = os.path.dirname(__file__)
    strings: set[str] = set()
    for path in glob.glob(os.path.join(app_dir, "**", "*.py"), recursive=True):
        if os.path.abspath(path) == os.path.abspath(__file__):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
        except Exception:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "tr"
                and len(node.args) == 1
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                text = node.args[0].value
                if text.strip():
                    strings.add(text)
    return strings


def warm_cache(lang: str, max_workers: int = 10) -> int:
    """Hedef dile ait bilinen tüm sabit metinleri paralel olarak çevirip
    önbelleğe yazar. Dil değiştirildiğinde bir kez çağrılması yeterlidir;
    sonrasında tr() çağrıları önbellekten anında döner.

    Döndürülen değer: yeni çevrilip önbelleğe eklenen metin sayısı.
    """
    if lang == "tr" or lang not in LANG_CODES:
        return 0

    _load_disk_cache()
    known = _mem_cache.get(lang, {})
    todo = [text for text in _collect_static_strings() if text not in known]
    if not todo:
        return 0

    results: dict[str, str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_text = {executor.submit(_translate_via_api, text, lang): text for text in todo}
        for future in concurrent.futures.as_completed(future_to_text):
            text = future_to_text[future]
            translated = future.result()
            if translated and translated != text:
                results[text] = translated

    if results:
        _mem_cache.setdefault(lang, {}).update(results)
        _save_disk_cache()
    return len(results)
