"""CV değerlendirmesi ve CV↔iş ilanı eşleştirmesi için OPSİYONEL, YEREL Ollama (localhost) entegrasyonu.

Bu modül yalnızca kullanıcının kendi makinesinde çalışan bir Ollama sunucusuna
(http://localhost:11434) bağlanır: harici API çağrısı, anahtar veya veri
aktarımı yoktur. Ollama kurulu değilse/erişilemezse tüm fonksiyonlar sessizce
None/False/[] döner; çağıran taraf (src/cv_analysis.py) mevcut kural tabanlı
sonuca döner. Varsayılan olarak kapalıdır — yalnızca kullanıcı arayüzden
açıkça etkinleştirirse çağrılır.
"""
import json

import requests

OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:3b"   # Türkçe performansı iyi, küçük (3B) bir model
AVAILABILITY_TIMEOUT = 1.5
# CPU üzerinde çalışan küçük modellerde bile üretim 1-2 dakikayı bulabilir;
# gerçek donanımda ölçülen süreye göre pay bırakılmıştır (bkz. manuel test).
GENERATE_TIMEOUT = 180
_MAX_INPUT_CHARS = 6000

_CV_REVIEW_SYSTEM_PROMPT = (
    "Sen deneyimli bir Türkçe kariyer danışmanı ve İK uzmanısın. Sana bir CV metni "
    "verilecek. Görevin bu CV'yi bütünsel olarak, satır arası okuyarak değerlendirmek "
    "(yalnızca anahtar kelime taramasıyla görülemeyecek nüansları da dikkate al). "
    "Yanıtını YALNIZCA şu alanları içeren geçerli bir JSON nesnesi olarak ver, başka "
    "hiçbir metin ekleme:\n"
    '{"summary": <CV hakkında 2-3 cümlelik genel Türkçe değerlendirme>, '
    '"strengths": [<adayın öne çıkan güçlü yönleri, string listesi, en fazla 5>], '
    '"weaknesses": [<gelişime açık yönler, string listesi, en fazla 5>], '
    '"position_suggestions": [<CV\'ye en uygun 3 pozisyon adı, string listesi>], '
    '"improvement_tips": [<CV\'yi güçlendirmek için somut, uygulanabilir öneriler, '
    'string listesi, en fazla 5>]}'
)

_MATCH_SYSTEM_PROMPT = (
    "Sen deneyimli bir Türkçe İK/işe alım uzmanısın. Sana bir CV metni ve bir iş "
    "ilanı metni verilecek. Görevin, CV'de açıkça yazmasa bile metinden çıkarılabilecek "
    "(ima edilen) becerileri bulmak ve adayın ilana bütünsel uygunluğunu değerlendirmek. "
    "Yanıtını YALNIZCA şu alanları içeren geçerli bir JSON nesnesi olarak ver, başka hiçbir "
    "metin ekleme:\n"
    '{"implicit_skills": [<CV metninde ima edilen ama açıkça yazmayan beceriler, string listesi>], '
    '"semantic_match_pct": <0-100 arası tam sayı, bütünsel uygunluk yüzdesi>, '
    '"summary": <2-3 cümlelik Türkçe değerlendirme özeti>, '
    '"missing_critical": [<ilanın kritik ama CV\'de karşılığı olmayan gereksinimleri, string listesi>]}'
)


def is_available(model: str | None = None) -> bool:
    """Yerel Ollama sunucusu erişilebilir mi; verilirse `model` yüklü mü.

    Bağlantı hatası/timeout/beklenmeyen yanıt durumunda sessizce False döner,
    exception yaymaz.
    """
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=AVAILABILITY_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError, AttributeError):
        return False

    if model is None:
        return True
    names = {m.get("name", "") for m in data.get("models", [])}
    return any(name == model or name.startswith(f"{model}:") for name in names)


def list_models() -> list[str]:
    """Yüklü Ollama model adları; sunucuya erişilemezse boş liste döner."""
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=AVAILABILITY_TIMEOUT)
        resp.raise_for_status()
        return [m.get("name", "") for m in resp.json().get("models", []) if m.get("name")]
    except (requests.RequestException, ValueError, AttributeError):
        return []


def _chat(system: str, user: str, *, model: str = DEFAULT_MODEL,
          json_mode: bool = True, timeout: int = GENERATE_TIMEOUT) -> dict | None:
    """Ollama'nın /api/chat ucuna tek seferlik (stream=False) istek atar.

    Başarılı olursa yanıtın ayrıştırılmış içeriğini döner (json_mode=True ise
    json.loads edilmiş dict, değilse {"text": <ham metin>}). Bağlantı hatası,
    timeout, HTTP hatası veya ayrıştırma hatasında sessizce None döner.
    """
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }
    if json_mode:
        payload["format"] = "json"

    try:
        resp = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=timeout)
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "")
    except (requests.RequestException, ValueError, AttributeError):
        return None

    if not json_mode:
        return {"text": content}
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None


def semantic_job_match(cv_text: str, job_text: str, *, model: str = DEFAULT_MODEL) -> dict | None:
    """CV ve ilan metnini yerel Ollama modeline vererek semantik bir değerlendirme
    ister — kural tabanlı `match_cv_to_job`'ın kaçırdığı örtük/ima edilen
    beceri eşleşmelerini yakalamayı amaçlar.

    Başarılıysa şu anahtarları içeren bir dict döner:
      - implicit_skills (list[str])
      - semantic_match_pct (int, 0-100)
      - summary (str)
      - missing_critical (list[str])
    Ollama erişilemezse, yanıt bozuksa veya beklenen alanlar eksikse/tipi
    yanlışsa None döner — çağıran taraf mevcut kural tabanlı sonuca sessizce
    döner.
    """
    user_prompt = (
        f"=== CV ===\n{cv_text[:_MAX_INPUT_CHARS]}\n\n"
        f"=== İLAN ===\n{job_text[:_MAX_INPUT_CHARS]}"
    )
    data = _chat(_MATCH_SYSTEM_PROMPT, user_prompt, model=model, json_mode=True)
    if not isinstance(data, dict):
        return None

    implicit_skills = data.get("implicit_skills")
    match_pct = data.get("semantic_match_pct")
    summary = data.get("summary")
    missing_critical = data.get("missing_critical")

    if (
        not isinstance(implicit_skills, list)
        or not isinstance(match_pct, (int, float))
        or isinstance(match_pct, bool)
        or not isinstance(summary, str)
        or not isinstance(missing_critical, list)
    ):
        return None

    return {
        "implicit_skills": [str(s) for s in implicit_skills],
        "semantic_match_pct": max(0, min(100, round(match_pct))),
        "summary": summary,
        "missing_critical": [str(s) for s in missing_critical],
    }


def semantic_cv_review(cv_text: str, *, model: str = DEFAULT_MODEL) -> dict | None:
    """CV metnini yerel Ollama modeline vererek bütünsel bir değerlendirme ister —
    kural tabanlı `analyze_cv()`'in kaçırdığı bağlamsal nüansları (ör. cümle
    içinde ima edilen deneyim/beceri) yakalamayı amaçlar.

    Başarılıysa şu anahtarları içeren bir dict döner:
      - summary (str)
      - strengths (list[str])
      - weaknesses (list[str])
      - position_suggestions (list[str])
      - improvement_tips (list[str])
    Ollama erişilemezse, yanıt bozuksa veya beklenen alanlar eksikse/tipi
    yanlışsa None döner — çağıran taraf mevcut kural tabanlı sonuca sessizce
    döner.
    """
    user_prompt = f"=== CV ===\n{cv_text[:_MAX_INPUT_CHARS]}"
    data = _chat(_CV_REVIEW_SYSTEM_PROMPT, user_prompt, model=model, json_mode=True)
    if not isinstance(data, dict):
        return None

    summary = data.get("summary")
    strengths = data.get("strengths")
    weaknesses = data.get("weaknesses")
    position_suggestions = data.get("position_suggestions")
    improvement_tips = data.get("improvement_tips")

    if (
        not isinstance(summary, str)
        or not isinstance(strengths, list)
        or not isinstance(weaknesses, list)
        or not isinstance(position_suggestions, list)
        or not isinstance(improvement_tips, list)
    ):
        return None

    return {
        "summary": summary,
        "strengths": [str(s) for s in strengths],
        "weaknesses": [str(s) for s in weaknesses],
        "position_suggestions": [str(s) for s in position_suggestions],
        "improvement_tips": [str(s) for s in improvement_tips],
    }
