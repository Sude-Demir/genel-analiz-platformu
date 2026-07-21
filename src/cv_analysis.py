"""CV dosyalarından metin/bilgi çıkarımı ve kural tabanlı (sezgisel) CV değerlendirmesi.

Harici bir LLM/API'ye bağımlı olmadan çalışır: beceri anahtar kelimeleri, basit
regex desenleri ve alan->pozisyon eşlemesi üzerinden güçlü/zayıf yön özeti ve
uygun pozisyon önerisi üretir. Bu nedenle sonuçlar bir ön değerlendirme niteliğindedir.
"""
import io
import re
from collections import Counter

from docx import Document
from pypdf import PdfReader

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


def extract_text(uploaded_file) -> str:
    """Yüklenen PDF/DOCX/TXT dosyasından düz metin çıkarır."""
    name = uploaded_file.name.lower()
    raw = uploaded_file.read()

    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
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
    text_lower = text.lower()
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


def match_cv_to_job(cv_text: str, job_text: str) -> dict:
    """Bir CV'yi belirli bir iş ilanı metnine göre eşleştirir.

    İlan ve CV aynı SKILL_GROUPS sözlüğüyle taranır; ortak/eksik beceriler ve
    ilanın istediği deneyim ile adayın tahmini deneyimi karşılaştırılır.
    """
    job_lower = job_text.lower()
    cv_lower = cv_text.lower()

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
