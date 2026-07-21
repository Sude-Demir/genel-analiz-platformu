"""CV dosyalarından metin/bilgi çıkarımı ve kural tabanlı (sezgisel) CV değerlendirmesi.

Harici bir LLM/API'ye bağımlı olmadan çalışır: beceri anahtar kelimeleri, basit
regex desenleri ve alan->pozisyon eşlemesi üzerinden güçlü/zayıf yön özeti ve
uygun pozisyon önerisi üretir. Bu nedenle sonuçlar bir ön değerlendirme niteliğindedir.
"""
import difflib
import io
import math
import re
from collections import Counter

import pdfplumber
from docx import Document

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+90|0)?[\s.-]?5\d{2}[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}")
EXPERIENCE_YEAR_RE = re.compile(r"(\d{1,2})\+?\s*(?:yıl|yıllık|years?)\b", re.IGNORECASE)
DATE_RANGE_RE = re.compile(r"\b(19|20)\d{2}\s*[-–—]\s*((?:19|20)\d{2}|[Gg]ünümüz|[Hh]alen|[Pp]resent)\b")
QUANTIFIED_RESULT_RE = re.compile(r"(%\s?\d+|\d+\s?%|\d+\s*(kişi|proje|milyon|bin|kat|adet|ekip))", re.IGNORECASE)
LANGUAGE_KEYWORDS = ["ingilizce", "i̇ngilizce", "english", "almanca", "german", "fransızca", "french", "ispanyolca", "arapça", "rusça"]
CERT_KEYWORDS = ["sertifika", "certificate", "certified", "sertifikası"]

SKILL_GROUPS: dict[str, list[str]] = {
    "Veri Analizi / Bilim": [
        "python", "sql", "excel", "power bi", "tableau", "pandas", "numpy",
        "makine öğrenmesi", "machine learning", "r dili", "istatistik",
        "veri analizi", "veri bilimi", "veri görselleştirme", "büyük veri",
    ],
    "Yazılım Geliştirme": [
        "java", "c++", "c#", "javascript", "typescript", "react", "node.js",
        "spring", ".net", "git", "docker", "kubernetes", "api geliştirme",
        "yazılım geliştirme", "algoritma", "mikroservis",
    ],
    "Proje / Ürün Yönetimi": [
        "proje yönetimi", "scrum", "agile", "kanban", "jira", "ürün yönetimi",
        "product owner", "paydaş yönetimi", "risk yönetimi",
    ],
    "Pazarlama": [
        "dijital pazarlama", "seo", "sem", "sosyal medya yönetimi",
        "içerik pazarlama", "marka yönetimi", "google ads", "pazarlama stratejisi",
        "kampanya yönetimi",
    ],
    "Satış / Müşteri İlişkileri": [
        "satış", "müşteri ilişkileri", "crm", "iş geliştirme", "müzakere",
        "hesap yönetimi", "müşteri memnuniyeti",
    ],
    "Finans / Muhasebe": [
        "muhasebe", "finansal analiz", "bütçeleme", "sap", "finansal raporlama",
        "denetim", "vergi", "maliyet analizi", "bilanço",
    ],
    "İnsan Kaynakları": [
        "işe alım", "insan kaynakları", "performans yönetimi", "bordro",
        "yetenek yönetimi", "eğitim ve gelişim", "özlük işleri",
    ],
    "Tasarım": [
        "ui/ux", "figma", "adobe photoshop", "adobe illustrator",
        "grafik tasarım", "kullanıcı deneyimi", "kullanıcı arayüzü",
    ],
    "Liderlik / Yönetim": [
        "liderlik", "ekip yönetimi", "takım yönetimi", "stratejik planlama",
        "karar verme", "mentorluk", "operasyon yönetimi",
    ],
    "İletişim / Analitik Düşünme": [
        "iletişim becerileri", "sunum", "raporlama", "problem çözme",
        "takım çalışması", "analitik düşünme", "zaman yönetimi",
    ],
}

POSITION_MAP: dict[str, list[str]] = {
    "Veri Analisti / Veri Bilimci": ["Veri Analizi / Bilim"],
    "Yazılım Geliştirici": ["Yazılım Geliştirme"],
    "Proje / Ürün Yöneticisi": ["Proje / Ürün Yönetimi", "Liderlik / Yönetim"],
    "Dijital Pazarlama Uzmanı": ["Pazarlama"],
    "Satış / İş Geliştirme Uzmanı": ["Satış / Müşteri İlişkileri"],
    "Finans / Muhasebe Uzmanı": ["Finans / Muhasebe"],
    "İnsan Kaynakları Uzmanı": ["İnsan Kaynakları"],
    "UI/UX Tasarımcı": ["Tasarım"],
    "Takım Lideri / Operasyon Yöneticisi": ["Liderlik / Yönetim", "Proje / Ürün Yönetimi"],
}

EDUCATION_LEVELS: dict[str, list[str]] = {
    "Doktora": ["doktora", "phd", "ph.d"],
    "Yüksek Lisans": ["yüksek lisans", "master", "msc", "mba", "yl."],
    "Lisans": ["lisans", "üniversite", "bachelor", "fakülte"],
    "Ön Lisans": ["ön lisans", "meslek yüksekokulu"],
}

STRONG_GROUP_THRESHOLD = 3

_TURKISH_UPPER_MAP = str.maketrans("İ", "i")


def turkish_lower(text: str) -> str:
    """Türkçe büyük "İ" harfini doğru küçültür.

    Standart str.lower(), "İ"yi tek bir "i" yerine "i" + görünmez birleşik
    nokta işaretine (U+0307) çevirir; bu da "İşe", "İnsan Kaynakları" gibi
    İ ile başlayan kelimelerin anahtar kelime eşleşmesinde kaçırılmasına yol
    açar. Düz "I" harfine kasıtlı olarak dokunulmaz: Türkçe kelimelerde "ı"
    anlamına gelse de, CV/ilan metinlerinde sık geçen "Power BI", "UI/UX",
    "AI" gibi İngilizce kısaltmalarda "i" anlamına gelir — iki anlamlı
    olduğundan standart (İngilizce) davranışta bırakılır.
    """
    return text.translate(_TURKISH_UPPER_MAP).lower()


def extract_text(uploaded_file) -> str:
    """Yüklenen PDF/DOCX/TXT dosyasından düz metin çıkarır.

    PDF çıkarımı için pypdf yerine pdfplumber kullanılır: pypdf, glifleri tek tek
    konumlandıran bazı PDF üretim araçlarıyla (örn. Canva) oluşturulmuş dosyalarda
    her harf arasına boşluk sokarak metni ("S u d e  D e m i r" gibi) bozuyor; bu da
    anahtar kelime eşleştirmesinin (beceri/deneyim/eğitim tespiti) tamamen başarısız
    olmasına yol açıyordu. pdfplumber karakter konumlarını dikkate alarak kelimeleri
    doğru birleştirir.

    Çağrıdan önce (varsa) `seek(0)` yapılır: aynı `UploadedFile` nesnesi birden
    fazla panel/mod tarafından (örn. Streamlit session_state üzerinden) tekrar
    okunduğunda, önceki okumadan kalan imleç konumu yüzünden boş metin dönmesini
    önler.
    """
    seek = getattr(uploaded_file, "seek", None)
    if callable(seek):
        seek(0)
    name = uploaded_file.name.lower()
    raw = uploaded_file.read()

    if name.endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    if name.endswith(".docx"):
        doc = Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs)
    return raw.decode("utf-8", errors="ignore")


def extract_contact(text: str) -> dict:
    email = EMAIL_RE.search(text)
    phone = PHONE_RE.search(text)
    return {
        "email": email.group(0) if email else None,
        "phone": phone.group(0) if phone else None,
    }


def find_skills(text_lower: str) -> dict[str, list[str]]:
    matched: dict[str, list[str]] = {}
    for group, keywords in SKILL_GROUPS.items():
        found = [kw for kw in keywords if kw in text_lower]
        if found:
            matched[group] = found
    return matched


def estimate_experience_years(text: str, text_lower: str) -> int | None:
    explicit = [int(m.group(1)) for m in EXPERIENCE_YEAR_RE.finditer(text_lower)]
    if explicit:
        return max(explicit)

    ranges = DATE_RANGE_RE.findall(text)
    if ranges:
        return len(ranges) * 2  # her rol dönemi için kaba bir kıdem tahmini
    return None


def detect_education(text_lower: str) -> str | None:
    for level, keywords in EDUCATION_LEVELS.items():
        if any(kw in text_lower for kw in keywords):
            return level
    return None


def analyze_cv(text: str) -> dict:
    text_lower = turkish_lower(text)
    contact = extract_contact(text)
    skills = find_skills(text_lower)
    all_skills = sorted({kw for kws in skills.values() for kw in kws})
    experience_years = estimate_experience_years(text, text_lower)
    education = detect_education(text_lower)
    word_count = len(text.split())
    has_quantified_results = bool(QUANTIFIED_RESULT_RE.search(text))
    has_language = any(kw in text_lower for kw in LANGUAGE_KEYWORDS)
    has_cert = any(kw in text_lower for kw in CERT_KEYWORDS)

    strengths: list[str] = []
    weaknesses: list[str] = []

    for group, found in skills.items():
        if len(found) >= STRONG_GROUP_THRESHOLD:
            strengths.append(f"{group} alanında güçlü bir beceri seti ({len(found)} anahtar beceri tespit edildi).")
    if len(skills) >= 3:
        strengths.append("Çok yönlü, disiplinlerarası bir beceri seti öne çıkıyor.")
    if experience_years and experience_years >= 5:
        strengths.append(f"Kayda değer düzeyde iş deneyimi (yaklaşık {experience_years}+ yıl).")
    if has_quantified_results:
        strengths.append("Ölçülebilir başarılar / sayısal sonuçlar CV'de vurgulanmış.")
    if education in ("Yüksek Lisans", "Doktora"):
        strengths.append(f"İleri düzey eğitim geçmişi ({education}).")
    if has_cert:
        strengths.append("Ek sertifikasyon / sürekli öğrenme göstergesi mevcut.")
    if has_language:
        strengths.append("Yabancı dil bilgisi belirtilmiş.")
    if not strengths:
        strengths.append("Belirgin bir güçlü yön tespit edilemedi; CV'nin daha fazla ayrıntı içermesi önerilir.")

    if word_count < 150:
        weaknesses.append("CV oldukça kısa; deneyim ve başarılar daha detaylı anlatılabilir.")
    if not has_quantified_results:
        weaknesses.append("Somut, ölçülebilir başarılar (sayı, yüzde, oran) eksik görünüyor.")
    if not all_skills:
        weaknesses.append("Belirgin bir teknik/işlevsel beceri anahtar kelimesi tespit edilemedi.")
    elif len(skills) == 1:
        weaknesses.append("Beceri seti tek bir alanla sınırlı görünüyor; çapraz yetkinlik eklemek faydalı olabilir.")
    if experience_years is None:
        weaknesses.append("Deneyim süresi CV'de net biçimde belirtilmemiş.")
    if not contact["email"] and not contact["phone"]:
        weaknesses.append("İletişim bilgileri (e-posta/telefon) eksik veya net değil.")
    if not has_language:
        weaknesses.append("Yabancı dil bilgisi belirtilmemiş.")
    if not weaknesses:
        weaknesses.append("Belirgin bir zayıf yön tespit edilemedi.")

    position_scores = []
    for position, groups in POSITION_MAP.items():
        matched_skills = [kw for g in groups for kw in skills.get(g, [])]
        if not matched_skills:
            continue
        score = len(matched_skills)
        if experience_years:
            score += min(experience_years, 10) * 0.2
        position_scores.append({
            "Pozisyon": position,
            "Uygunluk Skoru": round(score, 1),
            "Eşleşen Beceriler": ", ".join(sorted(set(matched_skills))[:8]),
        })
    position_scores.sort(key=lambda r: r["Uygunluk Skoru"], reverse=True)

    return {
        "contact": contact,
        "skills": skills,
        "all_skills": all_skills,
        "experience_years": experience_years,
        "education": education,
        "word_count": word_count,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "position_suggestions": position_scores[:5],
    }


EDUCATION_SCORE_WEIGHTS: dict[str, float] = {"Ön Lisans": 0.5, "Lisans": 1, "Yüksek Lisans": 2, "Doktora": 3}


def general_score(result: dict) -> float:
    """Bir iş ilanı olmadan CV'leri kıyaslamak için genel bir güç skoru üretir.

    Beceri sayısı + (üst sınırlı) deneyim yılı + eğitim düzeyi ağırlığından oluşan
    basit, açıklanabilir bir toplam. `analyze_cv()` çıktısı üzerinde çalışır; çoklu
    CV karşılaştırmasında ilan metni girilmediğinde sıralama ölçütü olarak kullanılır.
    """
    score = len(result["all_skills"])
    if result["experience_years"]:
        score += min(result["experience_years"], 15) * 0.5
    score += EDUCATION_SCORE_WEIGHTS.get(result["education"], 0)
    return round(score, 1)


def match_cv_to_job(cv_text: str, job_text: str) -> dict:
    """Bir CV'yi belirli bir iş ilanı metnine göre eşleştirir.

    İlan ve CV aynı SKILL_GROUPS sözlüğüyle taranır; ortak/eksik beceriler ve
    ilanın istediği deneyim ile adayın tahmini deneyimi karşılaştırılır.
    """
    job_lower = turkish_lower(job_text)
    cv_lower = turkish_lower(cv_text)

    job_skills_by_group = find_skills(job_lower)
    cv_skills_by_group = find_skills(cv_lower)

    job_skills = sorted({kw for kws in job_skills_by_group.values() for kw in kws})
    cv_skills = sorted({kw for kws in cv_skills_by_group.values() for kw in kws})

    matched_skills = sorted(set(job_skills) & set(cv_skills))
    missing_skills = sorted(set(job_skills) - set(cv_skills))
    match_pct = round(len(matched_skills) / len(job_skills) * 100) if job_skills else None

    group_breakdown = []
    for group, job_kws in job_skills_by_group.items():
        cv_kws = set(cv_skills_by_group.get(group, []))
        job_kw_set = set(job_kws)
        group_breakdown.append({
            "Alan": group,
            "İlan Beceri Sayısı": len(job_kw_set),
            "Eşleşen": len(job_kw_set & cv_kws),
        })
    group_breakdown.sort(key=lambda r: r["İlan Beceri Sayısı"], reverse=True)

    required_experience = estimate_experience_years(job_text, job_lower)
    candidate_experience = estimate_experience_years(cv_text, cv_lower)
    experience_met = (
        candidate_experience >= required_experience
        if required_experience is not None and candidate_experience is not None
        else None
    )

    return {
        "job_skills": job_skills,
        "cv_skills": cv_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "match_pct": match_pct,
        "required_experience": required_experience,
        "candidate_experience": candidate_experience,
        "experience_met": experience_met,
        "group_breakdown": group_breakdown,
    }


def hire_likelihood(result: dict, match: dict | None = None) -> int:
    """CV (ve varsa ilan eşleşmesi) sinyallerinden 0-100 arası sezgisel bir 'işe uygunluk
    olasılığı' tahmini üretir.

    Gerçek bir ML modeli değildir (bkz. modül docstring'i); mevcut `analyze_cv`/
    `match_cv_to_job` çıktılarının kural tabanlı ağırlıklı bir birleşimidir, bir ön
    değerlendirme niteliğindedir.

    - İlan verilmişse: beceri örtüşme yüzdesi (`match_pct`) ana etken (%70 ağırlık),
      deneyim şartının karşılanması (+%15 / nötr +%7 / karşılanmıyorsa +0) ve adayın
      genel profil gücü (`general_score`, %15 ağırlıkla, en fazla 20 puanlık dilimde
      doygunlaşır) eklenir.
    - İlan verilmemişse: `general_score` bir doygunluk eğrisiyle (skor arttıkça 100'e
      yaklaşır ama asla ulaşmaz) 0-100 aralığına ölçeklenir.
    """
    if match is not None and match.get("match_pct") is not None:
        score = match["match_pct"] * 0.7
        if match.get("experience_met") is True:
            score += 15
        elif match.get("experience_met") is None:
            score += 7
        score += min(general_score(result), 20) / 20 * 15
        return round(min(score, 100))

    score = general_score(result)
    likelihood = 100 * (1 - math.exp(-score / 12))
    return round(min(likelihood, 99))


STANDARD_SECTION_HEADERS: dict[str, list[str]] = {
    "Deneyim": ["deneyim", "iş deneyimi", "çalışma deneyimi", "work experience", "experience"],
    "Eğitim": ["eğitim", "öğrenim", "education"],
    "Beceriler": ["beceri", "yetkinlik", "skill"],
}
MULTI_SPACE_RUN_RE = re.compile(r"\S {3,}\S")
REPLACEMENT_CHAR_RE = re.compile(r"�")
SENIOR_TITLE_KEYWORDS = ["kıdemli", "senior", "yönetici", "müdür", "direktör", "lead", "şef", "başkan"]


def check_ats_format(text: str) -> list[str]:
    """OpenResume'un ATS ayrıştırma yaklaşımından (github.com/xitanggg/open-resume)
    esinlenerek, bir CV'nin format açısından ATS (Başvuru Takip Sistemi) tarafından
    ne kadar kolay ayrıştırılabileceğini kural tabanlı kontrol eder: standart bölüm
    başlıklarının varlığı, tablo/çoklu sütun kullanımına işaret eden geniş boşluk
    desenleri, ve bozuk/okunamayan karakterler. Harici bir servise bağımlı değildir.
    """
    text_lower = turkish_lower(text)
    issues = []

    for section, keywords in STANDARD_SECTION_HEADERS.items():
        if not any(kw in text_lower for kw in keywords):
            issues.append(f"Standart '{section}' bölüm başlığı bulunamadı; ATS sistemleri bu bölümü tanımayabilir.")

    lines = [line for line in text.split("\n") if line.strip()]
    if lines:
        multi_space_lines = sum(1 for line in lines if MULTI_SPACE_RUN_RE.search(line))
        if multi_space_lines / len(lines) > 0.15:
            issues.append(
                "Metinde çok sayıda geniş boşluk deseni tespit edildi; bu genellikle tablo veya "
                "çoklu sütun düzeninden kaynaklanır ve ATS'in metni yanlış sırada okumasına yol açabilir."
            )

    if REPLACEMENT_CHAR_RE.search(text):
        issues.append(
            "Metinde bozuk/okunamayan karakterler tespit edildi; bu genellikle özel yazı tipi, "
            "görsel öğe veya taranmış içerikten kaynaklanır."
        )

    return issues


def ats_compatibility(result: dict, text: str, match: dict | None = None) -> dict:
    """ATS uyum skoru (0-100), eksik anahtar kelimeler, format sorunları ve en fazla
    3 iyileştirme önerisi üretir.

    `result` = `analyze_cv()` çıktısı, `match` = (varsa) `match_cv_to_job()` çıktısı.
    Tamamen kural tabanlıdır; harici bir LLM/API kullanmaz.
    """
    format_sorunlari = check_ats_format(text)

    if match is not None and match.get("job_skills"):
        eksik_anahtar_kelimeler = match["missing_skills"]
        keyword_coverage = match["match_pct"] if match["match_pct"] is not None else 100
    else:
        eksik_anahtar_kelimeler = []
        keyword_coverage = 100 if result["all_skills"] else 40

    skor = keyword_coverage - len(format_sorunlari) * 15
    if not result["contact"]["email"] and not result["contact"]["phone"]:
        skor -= 10
    skor = max(0, min(100, round(skor)))

    oneriler = []
    if eksik_anahtar_kelimeler:
        oneriler.append(f"İlanda geçen ama CV'de olmayan şu anahtar kelimeleri ekleyin: {', '.join(eksik_anahtar_kelimeler[:5])}.")
    oneriler.extend(format_sorunlari)
    if not result["contact"]["email"] and not result["contact"]["phone"]:
        oneriler.append("İletişim bilgilerinizi (e-posta, telefon) CV'nin üst kısmına düz metin olarak ekleyin.")

    return {
        "skor": skor,
        "eksik_anahtar_kelimeler": eksik_anahtar_kelimeler,
        "format_sorunlari": format_sorunlari,
        "oneriler": oneriler[:3],
    }


def detect_inconsistency(result: dict, text: str) -> dict:
    """Beyan edilen deneyim yılı/unvan ile CV içeriğinin genel zenginliği arasındaki
    kaba bir tutarsızlık sinyalini kural tabanlı olarak tespit eder.

    Gerçek bir dil modeli muhakemesi değildir (bu nedenle yalnızca belirgin
    uyumsuzlukları yakalar); sonuç bir ön değerlendirme niteliğindedir.
    """
    text_lower = turkish_lower(text)
    has_senior_title = any(kw in text_lower for kw in SENIOR_TITLE_KEYWORDS)
    experience_years = result["experience_years"]

    if has_senior_title and (experience_years is None or experience_years < 3):
        deneyim_str = f"{experience_years} yıl" if experience_years is not None else "belirtilmemiş"
        return {
            "var_mi": True,
            "aciklama": (
                f"CV'de kıdemli/yönetici düzeyinde bir unvan geçiyor ama beyan edilen deneyim "
                f"({deneyim_str}) bu düzeyle örtüşmüyor gibi görünüyor. İnsan incelemesi önerilir."
            ),
        }
    if has_senior_title and result["word_count"] < 120:
        return {
            "var_mi": True,
            "aciklama": (
                "CV'de kıdemli/yönetici düzeyinde bir unvan geçiyor ama CV metni bu düzeyi "
                "destekleyecek ayrıntıda (proje/sorumluluk anlatımı) değil."
            ),
        }
    return {
        "var_mi": False,
        "aciklama": "Tutarlı: beyan edilen deneyim/unvan ile CV içeriği arasında belirgin bir uyumsuzluk tespit edilmedi.",
    }


def match_multiple_jobs(cv_text: str, job_postings: list[str]) -> list[dict]:
    """Birden fazla ilan için `match_cv_to_job()`'u çalıştırıp skor azalan sırada
    sıralanmış, kısa gerekçeli bir liste döndürür."""
    results = []
    for i, posting in enumerate(job_postings, start=1):
        m = match_cv_to_job(cv_text, posting)
        if m["match_pct"] is None:
            skor = 0
            gerekce = "İlan metninde tanınan beceri anahtar kelimesi bulunamadı."
        else:
            skor = m["match_pct"]
            gerekce = (
                f"{len(m['matched_skills'])} eşleşen / {len(m['missing_skills'])} eksik beceri "
                f"(%{m['match_pct']} örtüşme)."
            )
            if m.get("experience_met") is True:
                gerekce += " Deneyim şartı karşılanıyor."
            elif m.get("experience_met") is False:
                gerekce += " Deneyim şartı karşılanmıyor."
        results.append({"ilan_basligi": f"İlan {i}", "skor": skor, "gerekce": gerekce})
    results.sort(key=lambda r: r["skor"], reverse=True)
    return results


def find_duplicate_candidate(subject_text: str, subject_result: dict, pool: list[dict]) -> dict:
    """Aday havuzunda (`[{"dosya": str, "text": str}, ...]`) isim/e-posta/telefon veya
    içerik benzerliği (>%80) olan bir kayıt olup olmadığını kural tabanlı kontrol eder.

    İçerik benzerliği `difflib.SequenceMatcher` ile hesaplanır; e-posta/telefon tam
    eşleşmesi doğrudan %100 benzerlik olarak kabul edilir.
    """
    subject_lower = turkish_lower(subject_text)
    best = None
    for candidate in pool:
        c_result = analyze_cv(candidate["text"])
        contact_match = bool(
            (subject_result["contact"]["email"] and subject_result["contact"]["email"] == c_result["contact"]["email"])
            or (subject_result["contact"]["phone"] and subject_result["contact"]["phone"] == c_result["contact"]["phone"])
        )
        content_ratio = difflib.SequenceMatcher(None, subject_lower, turkish_lower(candidate["text"])).ratio() * 100
        benzerlik = 100 if contact_match else round(content_ratio)
        if best is None or benzerlik > best["benzerlik_orani"]:
            best = {"dosya": candidate["dosya"], "benzerlik_orani": benzerlik, "contact_match": contact_match}

    if best is None or best["benzerlik_orani"] < 80:
        return {
            "bulundu_mu": False, "eslesen_kayit": None, "benzerlik_orani": None,
            "aciklama": "Aday havuzunda yinelenen bir kayıt bulunamadı.",
        }

    aciklama = (
        "İletişim bilgileri (e-posta/telefon) örtüşüyor." if best["contact_match"]
        else "İçerik benzerliği yüksek; aynı adayın farklı bir sürümü olabilir."
    )
    return {
        "bulundu_mu": True, "eslesen_kayit": best["dosya"], "benzerlik_orani": best["benzerlik_orani"],
        "aciklama": aciklama,
    }


def build_report(file_name: str, result: dict) -> str:
    lines = [f"# CV Analiz Raporu — {file_name}", ""]
    lines.append("## İletişim Bilgileri")
    lines.append(f"- E-posta: {result['contact']['email'] or 'Tespit edilemedi'}")
    lines.append(f"- Telefon: {result['contact']['phone'] or 'Tespit edilemedi'}")
    lines.append("")
    lines.append("## Genel Bilgiler")
    lines.append(f"- Tahmini deneyim: {result['experience_years'] if result['experience_years'] else 'Belirlenemedi'} yıl")
    lines.append(f"- Eğitim düzeyi: {result['education'] or 'Belirlenemedi'}")
    lines.append(f"- Kelime sayısı: {result['word_count']}")
    lines.append("")
    lines.append("## Tespit Edilen Beceriler")
    if result["skills"]:
        for group, kws in result["skills"].items():
            lines.append(f"- **{group}**: {', '.join(kws)}")
    else:
        lines.append("- Belirgin beceri anahtar kelimesi tespit edilemedi.")
    lines.append("")
    lines.append("## Güçlü Yönler")
    lines += [f"- {s}" for s in result["strengths"]]
    lines.append("")
    lines.append("## Gelişime Açık Yönler")
    lines += [f"- {w}" for w in result["weaknesses"]]
    lines.append("")
    lines.append("## Uygun Pozisyon Önerileri")
    if result["position_suggestions"]:
        for row in result["position_suggestions"]:
            lines.append(f"- **{row['Pozisyon']}** (skor: {row['Uygunluk Skoru']}) — {row['Eşleşen Beceriler']}")
    else:
        lines.append("- Yeterli beceri anahtar kelimesi bulunamadığı için pozisyon önerisi üretilemedi.")
    lines.append("")
    lines.append("_Not: Bu rapor anahtar kelime tabanlı sezgisel bir analizle üretilmiştir; nihai değerlendirme için insan incelemesi önerilir._")
    return "\n".join(lines)
