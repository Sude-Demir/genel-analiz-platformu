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
