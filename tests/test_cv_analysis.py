from cv_analysis import (
    analyze_cv,
    ats_compatibility,
    check_ats_format,
    detect_inconsistency,
    find_duplicate_candidate,
    general_score,
    match_cv_to_job,
    match_multiple_jobs,
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
