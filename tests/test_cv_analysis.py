from cv_analysis import match_cv_to_job


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
