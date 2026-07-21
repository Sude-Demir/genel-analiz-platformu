"""CV Analizi panelini Streamlit'in AppTest çerçevesiyle uçtan uca (gerçek widget
etkileşimleriyle, başsız modda) çalıştıran entegrasyon testi.
"""
import os

from streamlit.testing.v1 import AppTest

APP_HOME = os.path.join(os.path.dirname(__file__), "..", "app", "Home.py")

JOB_TEXT = "Python, SQL ve Power BI bilgisi aranıyor. En az 3 yıl deneyim."
CV_TEXT = (
    "Ayşe Şölöz\n"
    "E-posta: ayse.soloz@example.com\n"
    "Telefon: 0532 123 45 67\n\n"
    "5 yıllık deneyime sahibim.\n"
    "İşe alım, İnsan Kaynakları, performans yönetimi konularında çalıştım.\n"
    "Ayrıca Python, SQL, Power BI, Excel kullanıyorum.\n"
    "Üniversite: Boğaziçi Üniversitesi, İşletme\n"
    "İngilizce biliyorum. Sertifika almış bulunuyorum.\n"
    "Projede yüzde 30 verimlilik artışı sağladım."
)


def _open_cv_panel():
    at = AppTest.from_file(APP_HOME, default_timeout=60)
    at.run()
    assert not at.exception

    cv_button = next(b for b in at.sidebar.button if "CV Analizi" in b.label)
    cv_button.click().run()
    assert not at.exception
    return at


def test_cv_panel_loads_without_exceptions():
    at = _open_cv_panel()
    assert not at.exception


def test_cv_upload_detects_turkish_and_english_skills():
    at = _open_cv_panel()
    uploader = at.file_uploader[0]
    uploader.upload("test_cv.txt", CV_TEXT.encode("utf-8"), "text/plain").run()
    assert not at.exception

    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Tahmini Deneyim"] == "5 yıl"
    assert metrics["Eğitim Düzeyi"] == "Lisans"
    assert metrics["Tespit Edilen Beceri Sayısı"] == "7"


def test_job_matching_section_renders_correct_score():
    at = _open_cv_panel()
    uploader = at.file_uploader[0]
    uploader.upload("test_cv.txt", CV_TEXT.encode("utf-8"), "text/plain").run()

    job_area = next(ta for ta in at.text_area if ta.label == "İş ilanı metni")
    job_area.set_value(JOB_TEXT).run()
    assert not at.exception

    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Uygunluk Skoru"] == "%100"
    assert metrics["Eşleşen Beceri"] == "3"
    assert metrics["Eksik Beceri"] == "0"


JUNIOR_CV_TEXT = (
    "Mehmet Yılmaz\n"
    "E-posta: mehmet.yilmaz@example.com\n\n"
    "1 yıllık deneyimim var.\n"
    "Python biliyorum.\n"
    "Üniversite: Ankara Üniversitesi\n"
)


def _open_compare_mode():
    at = AppTest.from_file(APP_HOME, default_timeout=60)
    at.run()
    assert not at.exception

    cv_button = next(b for b in at.sidebar.button if "CV Analizi" in b.label)
    cv_button.click().run()
    assert not at.exception

    mode_radio = next(r for r in at.radio if r.label == "Mod")
    mode_radio.set_value("📊 Çoklu CV Karşılaştırma").run()
    assert not at.exception
    return at


def test_compare_mode_ranks_candidates_by_general_score_without_job():
    at = _open_compare_mode()
    uploader = next(fu for fu in at.file_uploader if fu.label == "CV dosyaları")
    uploader.upload("aday_deneyimli.txt", CV_TEXT.encode("utf-8"), "text/plain")
    uploader.upload("aday_junior.txt", JUNIOR_CV_TEXT.encode("utf-8"), "text/plain")
    uploader.run()
    assert not at.exception

    # Daha çok beceri/deneyim/eğitime sahip aday en üstte olmalı.
    success_msgs = [m.value for m in at.success]
    assert any("aday_deneyimli.txt" in msg for msg in success_msgs)


def test_compare_mode_ranks_candidates_by_job_match_when_job_given():
    at = _open_compare_mode()
    uploader = next(fu for fu in at.file_uploader if fu.label == "CV dosyaları")
    uploader.upload("aday_deneyimli.txt", CV_TEXT.encode("utf-8"), "text/plain")
    uploader.upload("aday_junior.txt", JUNIOR_CV_TEXT.encode("utf-8"), "text/plain")
    uploader.run()
    assert not at.exception

    job_area = next(ta for ta in at.text_area if ta.label == "İş ilanı metni (opsiyonel)")
    job_area.set_value(JOB_TEXT).run()
    assert not at.exception

    # JOB_TEXT (Python, SQL, Power BI) tümüyle CV_TEXT'te var (%100 uygunluk),
    # JUNIOR_CV_TEXT'te yalnızca Python var -> deneyimli aday üstte olmalı.
    success_msgs = [m.value for m in at.success]
    assert any("aday_deneyimli.txt" in msg and "Uygunluk %" in msg for msg in success_msgs)


def _open_deep_mode_with_uploaded_compare_cvs():
    at = AppTest.from_file(APP_HOME, default_timeout=60)
    at.run()
    assert not at.exception

    cv_button = next(b for b in at.sidebar.button if "CV Analizi" in b.label)
    cv_button.click().run()
    mode_radio = next(r for r in at.radio if r.label == "Mod")
    mode_radio.set_value("📊 Çoklu CV Karşılaştırma").run()
    uploader = next(fu for fu in at.file_uploader if fu.label == "CV dosyaları")
    uploader.upload("aday_deneyimli.txt", CV_TEXT.encode("utf-8"), "text/plain")
    uploader.upload("aday_junior.txt", JUNIOR_CV_TEXT.encode("utf-8"), "text/plain")
    uploader.run()
    assert not at.exception

    mode_radio = next(r for r in at.radio if r.label == "Mod")
    mode_radio.set_value("🆓 ATS & Derin Analiz").run()
    assert not at.exception
    return at


def test_deep_mode_without_compare_cvs_shows_guidance_and_does_not_crash():
    at = AppTest.from_file(APP_HOME, default_timeout=60)
    at.run()
    cv_button = next(b for b in at.sidebar.button if "CV Analizi" in b.label)
    cv_button.click().run()
    mode_radio = next(r for r in at.radio if r.label == "Mod")
    mode_radio.set_value("🆓 ATS & Derin Analiz").run()
    assert not at.exception

    info_msgs = [m.value for m in at.info]
    assert any("Çoklu CV Karşılaştırma" in msg for msg in info_msgs)


def test_deep_mode_renders_four_sections_without_job_postings():
    at = _open_deep_mode_with_uploaded_compare_cvs()

    analyze_btn = next(b for b in at.button if b.label == "Analiz Et")
    analyze_btn.click().run()
    assert not at.exception

    markdowns = [m.value for m in at.markdown]
    assert any("ATS Uyum Skoru" in m for m in markdowns)
    assert any("Tutarsızlık Analizi" in m for m in markdowns)
    assert any("İlan Eşleştirme" in m for m in markdowns)
    assert any("Yinelenen Aday Kontrolü" in m for m in markdowns)

    # aday_deneyimli.txt ve aday_junior.txt farklı kişiler -> yinelenen aday bulunmamalı.
    success_msgs = [m.value for m in at.success]
    assert any("yinelenen bir kayıt bulunamadı" in msg.lower() for msg in success_msgs)


def test_deep_mode_matches_multiple_job_postings():
    at = _open_deep_mode_with_uploaded_compare_cvs()

    job_area = next(ta for ta in at.text_area if "İş ilanları" in ta.label)
    job_area.set_value(
        "Python, SQL ve Power BI bilgisi aranıyor. En az 3 yıl deneyim.\n"
        "---\n"
        "Java ve Docker deneyimi aranıyor."
    ).run()

    analyze_btn = next(b for b in at.button if b.label == "Analiz Et")
    analyze_btn.click().run()
    assert not at.exception

    # Varsayılan aday (aday_deneyimli.txt) Python/SQL/Power BI ilanına %100 uyar,
    # Java/Docker ilanına uymaz -> ilk ilan skor olarak üstte (azalan sıralı) olmalı.
    ilan_dfs = [d.value for d in at.dataframe]
    ilan_df = next(df for df in ilan_dfs if "İlan" in df.columns and "Skor" in df.columns)
    assert list(ilan_df["Skor"])[0] >= list(ilan_df["Skor"])[1]
    assert ilan_df["Skor"].iloc[0] == 100


def test_deep_mode_detects_duplicate_candidate_by_matching_contact_info():
    at = AppTest.from_file(APP_HOME, default_timeout=60)
    at.run()
    assert not at.exception

    cv_button = next(b for b in at.sidebar.button if "CV Analizi" in b.label)
    cv_button.click().run()
    mode_radio = next(r for r in at.radio if r.label == "Mod")
    mode_radio.set_value("📊 Çoklu CV Karşılaştırma").run()
    uploader = next(fu for fu in at.file_uploader if fu.label == "CV dosyaları")
    # aday_deneyimli.txt ve aday_deneyimli_kopya.txt aynı e-postaya sahip -> yinelenen olmalı.
    uploader.upload("aday_deneyimli.txt", CV_TEXT.encode("utf-8"), "text/plain")
    uploader.upload("aday_deneyimli_kopya.txt", CV_TEXT.encode("utf-8"), "text/plain")
    uploader.upload("aday_junior.txt", JUNIOR_CV_TEXT.encode("utf-8"), "text/plain")
    uploader.run()
    assert not at.exception

    mode_radio = next(r for r in at.radio if r.label == "Mod")
    mode_radio.set_value("🆓 ATS & Derin Analiz").run()
    assert not at.exception

    analyze_btn = next(b for b in at.button if b.label == "Analiz Et")
    analyze_btn.click().run()
    assert not at.exception

    warning_msgs = [m.value for m in at.warning]
    assert any("aday_deneyimli_kopya.txt" in msg and "%100" in msg for msg in warning_msgs)
