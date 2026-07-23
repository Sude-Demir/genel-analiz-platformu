from cv_analysis import (
    analyze_cv,
    ats_compatibility,
    check_ats_format,
    detect_inconsistency,
    extract_name,
    find_duplicate_candidate,
    find_skills,
    general_score,
    match_cv_to_job,
    match_multiple_jobs,
    skill_development_tips,
    turkish_lower,
)


def test_turkish_lower_handles_dotted_capital_i():
    # Standart str.lower() 'İ'yi 'i' + birleşik nokta işaretine çevirir (U+0307);
    # bu satır o hatanın düzeltildiğini doğrular.
    assert turkish_lower("İşe Alım") == "işe alım"
    assert turkish_lower("İNGİLİZCE") == "ingilizce"


def test_turkish_lower_leaves_plain_i_untouched():
    # Düz "I" kasıtlı olarak dokunulmaz: "Power BI" gibi İngilizce kısaltmalar
    # "ı" değil "i" anlamına gelir (bkz. turkish_lower docstring).
    assert turkish_lower("Power BI") == "power bi"


def test_analyze_cv_detects_skills_starting_with_capital_i():
    cv = "İşe alım ve İnsan Kaynakları alanında 5 yıllık deneyimim var."
    result = analyze_cv(cv)

    all_skills = {kw for kws in result["skills"].values() for kw in kws}
    assert "işe alım" in all_skills
    assert "insan kaynakları" in all_skills


def test_match_full_overlap():
    job = "Python, SQL ve Power BI bilgisi aranıyor. En az 3 yıl deneyim."
    cv = "5 yıllık deneyimim var. Python, SQL, Power BI, Excel kullanıyorum."
    result = match_cv_to_job(cv, job)

    assert result["match_pct"] == 100
    assert result["missing_skills"] == []
    assert set(result["matched_skills"]) == {"python", "sql", "power bi"}


def test_match_partial():
    job = "Python, Java ve Docker deneyimi aranıyor."
    cv = "Python ve SQL biliyorum."
    result = match_cv_to_job(cv, job)

    assert result["matched_skills"] == ["python"]
    assert set(result["missing_skills"]) == {"java", "docker"}
    assert result["match_pct"] == 33  # 1/3 -> round(33.33) = 33


def test_match_no_job_skills():
    job = "Bu ilan metninde tanınan hiçbir beceri anahtar kelimesi yok."
    cv = "Python, SQL biliyorum."
    result = match_cv_to_job(cv, job)

    assert result["match_pct"] is None
    assert result["job_skills"] == []


def test_experience_comparison():
    job = "En az 5 yıl deneyim gereklidir. Python bilgisi şart."
    cv = "7 yıllık iş deneyimim boyunca Python kullandım."
    result = match_cv_to_job(cv, job)

    assert result["required_experience"] == 5
    assert result["candidate_experience"] == 7
    assert result["experience_met"] is True


def test_general_score_rewards_more_skills_experience_and_education():
    junior_cv = "Python biliyorum. Üniversite mezunuyum."
    senior_cv = (
        "10 yıllık deneyimim var. Python, SQL, Power BI, Excel, Tableau kullanıyorum. "
        "Yüksek Lisans mezunuyum."
    )
    junior_score = general_score(analyze_cv(junior_cv))
    senior_score = general_score(analyze_cv(senior_cv))

    assert senior_score > junior_score


def test_general_score_handles_missing_experience_and_education():
    cv = "Python ve SQL biliyorum."
    result = analyze_cv(cv)
    assert result["experience_years"] is None
    assert result["education"] is None

    score = general_score(result)
    assert score == len(result["all_skills"])


def test_check_ats_format_flags_missing_standard_sections():
    text = "Ahmet Yılmaz\nBu bir CV metni ama standart bölüm başlıkları içermiyor."
    issues = check_ats_format(text)
    assert any("Deneyim" in i for i in issues)
    assert any("Eğitim" in i for i in issues)
    assert any("Beceriler" in i for i in issues)


def test_check_ats_format_no_issues_for_well_structured_text():
    text = (
        "Deneyim\nYazılım Geliştirici, 3 yıl\n\n"
        "Eğitim\nBilgisayar Mühendisliği\n\n"
        "Beceriler\nPython, SQL"
    )
    assert check_ats_format(text) == []


def test_check_ats_format_flags_table_like_whitespace_patterns():
    lines = ["Deneyim   Eğitim   Beceriler"] + [f"Satır{i}   ile   geniş   boşluklar" for i in range(10)]
    issues = check_ats_format("\n".join(lines))
    assert any("tablo" in i.lower() or "sütun" in i.lower() for i in issues)


def test_check_ats_format_flags_replacement_characters():
    text = "Deneyim Eğitim Beceriler Python�� bozuk karakter içeriyor"
    issues = check_ats_format(text)
    assert any("bozuk" in i.lower() for i in issues)


def test_ats_compatibility_scores_lower_with_missing_keywords_and_format_issues():
    cv_text = "Ahmet Yılmaz\nBu CV format sorunlu ve anahtar kelime eksik."
    result = analyze_cv(cv_text)
    job = "Python, SQL ve Docker deneyimi aranıyor."
    match = match_cv_to_job(cv_text, job)
    ats = ats_compatibility(result, cv_text, match)

    assert ats["skor"] < 100
    assert set(ats["eksik_anahtar_kelimeler"]) == {"python", "sql", "docker"}
    assert len(ats["oneriler"]) <= 3


def test_ats_compatibility_high_score_for_well_formed_matching_cv():
    cv_text = (
        "Deneyim\n5 yıllık deneyimim var. Python, SQL, Docker kullanıyorum.\n\n"
        "Eğitim\nBilgisayar Mühendisliği\n\nBeceriler\nPython, SQL, Docker\n"
        "E-posta: test@example.com"
    )
    result = analyze_cv(cv_text)
    job = "Python, SQL ve Docker deneyimi aranıyor."
    match = match_cv_to_job(cv_text, job)
    ats = ats_compatibility(result, cv_text, match)

    assert ats["skor"] == 100
    assert ats["eksik_anahtar_kelimeler"] == []
    assert ats["format_sorunlari"] == []


def test_detect_inconsistency_flags_senior_title_with_low_experience():
    cv_text = "Kıdemli Yazılım Geliştirici\n1 yıllık deneyimim var. Python biliyorum."
    result = analyze_cv(cv_text)
    inconsistency = detect_inconsistency(result, cv_text)
    assert inconsistency["var_mi"] is True


def test_detect_inconsistency_reports_consistent_for_normal_cv():
    cv_text = "Yazılım Geliştirici\n5 yıllık deneyimim var. Python, SQL, Docker, Java kullanıyorum."
    result = analyze_cv(cv_text)
    inconsistency = detect_inconsistency(result, cv_text)
    assert inconsistency["var_mi"] is False


def test_match_multiple_jobs_sorts_by_score_descending():
    cv_text = "5 yıllık deneyimim var. Python, SQL, Power BI kullanıyorum."
    postings = [
        "Java ve Docker deneyimi aranıyor.",
        "Python, SQL ve Power BI bilgisi aranıyor.",
    ]
    results = match_multiple_jobs(cv_text, postings)

    assert results[0]["ilan_basligi"] == "İlan 2"
    assert results[0]["skor"] == 100
    assert results[1]["skor"] < results[0]["skor"]


def test_match_multiple_jobs_handles_empty_list():
    assert match_multiple_jobs("herhangi bir metin", []) == []


def test_find_duplicate_candidate_detects_matching_email():
    subject_text = "Ahmet Yılmaz\nE-posta: ahmet@example.com\nPython biliyorum."
    subject_result = analyze_cv(subject_text)
    pool = [
        {"dosya": "diger_aday.txt", "text": "Mehmet Kaya\nE-posta: mehmet@example.com\nJava biliyorum."},
        {"dosya": "ayni_eposta.txt", "text": "Ahmet Y.\nE-posta: ahmet@example.com\nFarklı içerik ama aynı e-posta."},
    ]
    dup = find_duplicate_candidate(subject_text, subject_result, pool)

    assert dup["bulundu_mu"] is True
    assert dup["eslesen_kayit"] == "ayni_eposta.txt"
    assert dup["benzerlik_orani"] == 100


def test_find_duplicate_candidate_returns_false_when_no_match():
    subject_text = "Ahmet Yılmaz\nE-posta: ahmet@example.com\nPython biliyorum."
    subject_result = analyze_cv(subject_text)
    pool = [{
        "dosya": "farkli_aday.txt",
        "text": "Tamamen farklı bir kişi, alakasız içerik, başka bir e-posta hiç yok burada uzun metin doldurma amaçlı.",
    }]
    dup = find_duplicate_candidate(subject_text, subject_result, pool)

    assert dup["bulundu_mu"] is False


def test_extract_name_from_first_line():
    text = "Ahmet Yılmaz\nDeneyim\n5 yıllık deneyimim var. Python biliyorum."
    assert extract_name(text) == "Ahmet Yılmaz"


def test_extract_name_skips_section_headers_and_falls_back_to_email():
    text = "Özgeçmiş\nDeneyim\nE-posta: ahmet.yilmaz@example.com\nPython biliyorum."
    assert extract_name(text) == "Ahmet Yilmaz"


def test_extract_name_returns_none_when_no_signal_found():
    text = "python sql docker beceri deneyim eğitim"
    assert extract_name(text) is None


def test_analyze_cv_includes_name_field():
    result = analyze_cv("Ahmet Yılmaz\nPython ve SQL biliyorum.")
    assert result["name"] == "Ahmet Yılmaz"


def test_find_skills_matches_abbreviation_synonym():
    skills = find_skills(turkish_lower("JS ve ML konularında tecrübeliyim."))
    all_skills = {kw for kws in skills.values() for kw in kws}
    assert "javascript" in all_skills
    assert "machine learning" in all_skills


def test_find_skills_detects_new_cloud_devops_group_via_synonyms():
    # AWS/GCP/SRE kisaltmalari kelime siniriyla (\b) kanonik forma esleşmeli.
    skills = find_skills(turkish_lower("AWS, GCP ve SRE deneyimim var, Terraform kullanıyorum."))
    all_skills = {kw for kws in skills.values() for kw in kws}
    assert "amazon web services" in all_skills
    assert "google cloud" in all_skills
    assert "site reliability engineering" in all_skills
    assert "Bulut & DevOps" in skills


def test_find_skills_rust_synonym_does_not_match_inside_trust():
    # "rust" onceden ham alt dize olarak eklenseydi "trustworthy" icindeki
    # "rust"u yanlislikla eslestirirdi; kelime siniri bu riski onlemeli.
    skills = find_skills(turkish_lower("Takım içinde güvenilir (trustworthy) bir çalışma ortamı kurdum."))
    all_skills = {kw for kws in skills.values() for kw in kws}
    assert "rust dili" not in all_skills


def test_analyze_cv_returns_improvement_tips_for_weak_cv():
    result = analyze_cv("Mehmet Kaya\nBiraz deneyimim var.\n")
    assert result["improvement_tips"], "zayıf bir CV için iyileştirme önerisi üretilmeli"
    assert any("150 kelime" in tip for tip in result["improvement_tips"])


def test_analyze_cv_improvement_tips_empty_for_strong_cv():
    strong_cv = (
        "Zeynep Aydın\n"
        "E-posta: zeynep.aydin@example.com | Telefon: 0532 999 88 77\n\n"
        "8 yıllık deneyimim boyunca Python, SQL, Power BI, Tableau, makine öğrenmesi "
        "ve büyük veri projelerinde çalıştım. Satışları %35 artırdım, 20 kişilik bir "
        "ekip yönettim ve 100'den fazla rapor ürettim. İngilizce ve Almanca biliyorum. "
        "AWS sertifikası sahibiyim. Çalıştığım kurumlarda veri odaklı karar alma "
        "kültürünü yerleştirdim ve birden fazla departmanla yakın iş birliği içinde "
        "çalıştım. Yönettiğim projelerde maliyetleri %15 oranında azalttım ve müşteri "
        "memnuniyetini artıran raporlama süreçleri kurdum. Ekip üyelerinin gelişimine "
        "mentorluk yaparak katkı sağladım ve şirket içi eğitim programları düzenledim. "
        "Ayrıca yeni teknolojilere hızlı adapte olarak süreçlerin dijitalleşmesine "
        "öncülük ettim ve üst yönetime düzenli olarak stratejik raporlar sundum. "
        "Proje yönetimi metodolojilerini (Scrum, Kanban) kullanarak çevik ekipler "
        "kurdum ve paydaşlarla düzenli iletişim sağladım. Farklı sektörlerden "
        "gelen paydaşlarla iş birliği yaparak ortak hedeflere ulaşılmasını "
        "sağladım ve süreç iyileştirme çalışmalarına liderlik ettim. Düzenli "
        "olarak sektör konferanslarına katılıp güncel gelişmeleri takip ettim "
        "ve edindiğim bilgileri ekip içinde paylaşarak ortak öğrenme kültürü "
        "oluşturdum. Kariyerim boyunca sürekli kendimi geliştirmeye önem verdim.\n"
    )
    result = analyze_cv(strong_cv)
    assert result["improvement_tips"] == []


def test_find_skills_synonym_uses_word_boundary_not_substring():
    # "ik" İnsan Kaynakları kısaltmasıdır ama "yöneticilik" kelimesinin içinde
    # yanlışlıkla eşleşmemelidir (kelime sınırı kontrolü).
    skills = find_skills(turkish_lower("Uzun süredir yöneticilik yapıyorum."))
    all_skills = {kw for kws in skills.values() for kw in kws}
    assert "insan kaynakları" not in all_skills


def test_find_skills_synonym_matches_standalone_abbreviation():
    skills = find_skills(turkish_lower("İK departmanında çalışıyorum."))
    all_skills = {kw for kws in skills.values() for kw in kws}
    assert "insan kaynakları" in all_skills


def test_skill_development_tips_uses_specific_tip_when_available():
    tips = skill_development_tips(["python"])
    assert len(tips) == 1
    assert "Python" in tips[0]


def test_skill_development_tips_falls_back_to_group_based_tip():
    tips = skill_development_tips(["kanban"])
    assert len(tips) == 1
    assert "Kanban" in tips[0]
    assert "Proje / Ürün Yönetimi" in tips[0]


def test_skill_development_tips_respects_limit():
    tips = skill_development_tips(["python", "sql", "docker", "git", "excel", "kanban"], limit=3)
    assert len(tips) == 3
