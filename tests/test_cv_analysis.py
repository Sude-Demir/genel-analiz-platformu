from cv_analysis import analyze_cv, general_score, match_cv_to_job, turkish_lower


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
