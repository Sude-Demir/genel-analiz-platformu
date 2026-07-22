"""Çok dil desteği — Türkçe (tr) / İngilizce (en) / Almanca (de).

Kullanım:
    from i18n import t
    st.button(t("kaydet"))

Dil, st.session_state["lang"] üzerinden kontrol edilir.
Varsayılan dil: "tr" (Türkçe).
"""
import streamlit as st

TRANSLATIONS: dict[str, dict[str, str]] = {
    # ── Genel / Ortak ────────────────────────────────────────────────────────
    "json_indir": {
        "tr": "JSON indir",
        "en": "Download JSON",
        "de": "JSON herunterladen",
    },
    "pdf_indir": {
        "tr": "PDF indir",
        "en": "Download PDF",
        "de": "PDF herunterladen",
    },
    "csv_indir": {
        "tr": "CSV indir",
        "en": "Download CSV",
        "de": "CSV herunterladen",
    },
    "dis_aktar": {
        "tr": "### Dışa Aktar",
        "en": "### Export",
        "de": "### Exportieren",
    },
    "ornek_dene": {
        "tr": "🔎 Örnek Dene",
        "en": "🔎 Try Example",
        "de": "🔎 Beispiel ausprobieren",
    },
    "analiz_et": {
        "tr": "Analiz Et",
        "en": "Analyze",
        "de": "Analysieren",
    },

    # ── Sidebar / Home ────────────────────────────────────────────────────────
    "uygulama_adi": {
        "tr": "## 🧪 Genel Analiz Platformu",
        "en": "## 🧪 General Analysis Platform",
        "de": "## 🧪 Allgemeine Analyseplattform",
    },
    "uygulama_alt_baslik": {
        "tr": "Genel amaçlı çok modüllü analiz aracı",
        "en": "General-purpose multi-module analysis tool",
        "de": "Allgemeines Multi-Modul-Analysewerkzeug",
    },
    "sidebar_caption": {
        "tr": "Her panelin sonucu kendi sekmesinde JSON / PDF / CSV olarak dışa aktarılabilir.",
        "en": "Each panel's results can be exported as JSON / PDF / CSV in its own tab.",
        "de": "Die Ergebnisse jedes Panels können als JSON / PDF / CSV exportiert werden.",
    },
    "dil_sec": {
        "tr": "Dil / Language / Sprache",
        "en": "Dil / Language / Sprache",
        "de": "Dil / Language / Sprache",
    },

    # ── Panel menü isimleri ───────────────────────────────────────────────────
    "panel_home": {
        "tr": "🏠 Anasayfa",
        "en": "🏠 Home",
        "de": "🏠 Startseite",
    },
    "panel_dataset": {
        "tr": "📁 Dataset Analizi",
        "en": "📁 Dataset Analysis",
        "de": "📁 Datensatz-Analyse",
    },
    "panel_cv": {
        "tr": "📄 CV Analizi",
        "en": "📄 CV Analysis",
        "de": "📄 Lebenslauf-Analyse",
    },
    "panel_company": {
        "tr": "🌐 Şirket Analizi",
        "en": "🌐 Company Analysis",
        "de": "🌐 Unternehmensanalyse",
    },

    # ── Home panel ────────────────────────────────────────────────────────────
    "hero_subtitle": {
        "tr": (
            "İK verisi, CV ve şirket itibarı üzerine çalışan çok modüllü bir analiz aracı."
            " Harici bir yapay zekâ servisine bağımlı değildir — analizler kural/sözlük tabanlı"
            " sezgisel yöntemlerle veya (yalnızca çalışan kaybı tahmininde) eğitilmiş bir makine"
            " öğrenmesi modeliyle yapılır."
        ),
        "en": (
            "A multi-module analysis tool working on HR data, CVs and company reputation."
            " No external AI API dependency — analyses are performed using rule/dictionary-based"
            " heuristics or (only for attrition prediction) a trained machine learning model."
        ),
        "de": (
            "Ein Multi-Modul-Analysetool für HR-Daten, Lebensläufe und Unternehmensreputation."
            " Keine externe KI-API-Abhängigkeit — Analysen werden mit regelbasierten"
            " Heuristiken oder (nur für Fluktuationsvorhersage) einem trainierten ML-Modell durchgeführt."
        ),
    },
    "modul_analiz_sayisi": {
        "tr": "Analiz Modülü",
        "en": "Analysis Modules",
        "de": "Analysemodule",
    },
    "modul_ai_bagimlilik": {
        "tr": "Harici AI API Bağımlılığı",
        "en": "External AI API Dependencies",
        "de": "Externe KI-API-Abhängigkeiten",
    },
    "modul_ml_model": {
        "tr": "Gerçek ML Modeli",
        "en": "Real ML Model",
        "de": "Echtes ML-Modell",
    },
    "moduller_baslik": {
        "tr": "#### Modüller",
        "en": "#### Modules",
        "de": "#### Module",
    },
    "moduller_caption": {
        "tr": "Başlamak için bir kart seçin veya sol menüyü kullanın.",
        "en": "Select a card or use the left menu to get started.",
        "de": "Wählen Sie eine Karte oder verwenden Sie das linke Menü.",
    },
    "ac_btn": {
        "tr": "Aç →",
        "en": "Open →",
        "de": "Öffnen →",
    },
    "home_card_dataset_title": {
        "tr": "Dataset Analizi",
        "en": "Dataset Analysis",
        "de": "Datensatz-Analyse",
    },
    "home_card_dataset_desc": {
        "tr": "Herhangi bir veri setini yükleyip genel istatistik, görselleştirme ve İK'ya özgü alt analizler yapar.",
        "en": "Upload any dataset and perform general statistics, visualizations and HR-specific sub-analyses.",
        "de": "Laden Sie einen beliebigen Datensatz hoch und führen Sie allgemeine Statistiken, Visualisierungen und HR-spezifische Unteranalysen durch.",
    },
    "home_card_cv_title": {
        "tr": "CV Analizi",
        "en": "CV Analysis",
        "de": "Lebenslauf-Analyse",
    },
    "home_card_cv_desc": {
        "tr": "CV metnini beceri/pozisyon/eğitim sözlükleriyle değerlendirir, ilanla eşleştirme yüzdesi üretir.",
        "en": "Evaluates CV text using skill/position/education dictionaries and produces a job posting match percentage.",
        "de": "Bewertet den Lebenslauftext anhand von Wörterbüchern und ermittelt einen Stellenanzeigen-Übereinstimmungsprozentsatz.",
    },
    "home_card_company_title": {
        "tr": "Şirket Analizi",
        "en": "Company Analysis",
        "de": "Unternehmensanalyse",
    },
    "home_card_company_desc": {
        "tr": "Google News RSS ve DuckDuckGo taramasıyla şirket haberlerinde duygu analizi yapar.",
        "en": "Performs sentiment analysis on company news via Google News RSS and DuckDuckGo search.",
        "de": "Führt eine Stimmungsanalyse von Unternehmensnachrichten via Google News RSS und DuckDuckGo durch.",
    },
    "home_caption": {
        "tr": "Her panelin sonucu kendi sekmesinde JSON / PDF / CSV olarak dışa aktarılabilir.",
        "en": "Each panel's results can be exported as JSON / PDF / CSV in its own tab.",
        "de": "Die Ergebnisse jedes Panels können als JSON / PDF / CSV exportiert werden.",
    },

    # ── Dataset panel ─────────────────────────────────────────────────────────
    "ds_veri_yukle": {
        "tr": "Veri Seti Yükle",
        "en": "Upload Dataset",
        "de": "Datensatz hochladen",
    },
    "ds_kaynak": {
        "tr": "Kaynak",
        "en": "Source",
        "de": "Quelle",
    },
    "ds_dosya_yukle": {
        "tr": "Dosya Yükle",
        "en": "Upload File",
        "de": "Datei hochladen",
    },
    "ds_dahili": {
        "tr": "Dahili İK Örnek Verisi",
        "en": "Built-in HR Sample Data",
        "de": "Integrierte HR-Beispieldaten",
    },
    "ds_uploader_label": {
        "tr": "CSV, Excel veya JSON dosyası",
        "en": "CSV, Excel or JSON file",
        "de": "CSV-, Excel- oder JSON-Datei",
    },
    "ds_spinner_okuma": {
        "tr": "Dosya okunuyor...",
        "en": "Reading file...",
        "de": "Datei wird gelesen...",
    },
    "ds_hata_okuma": {
        "tr": "Dosya okunamadı. Dosyanın seçilen formatta (CSV/Excel/JSON) ve bozuk olmadığından emin olun.",
        "en": "Could not read file. Make sure the file is in the selected format (CSV/Excel/JSON) and is not corrupted.",
        "de": "Datei konnte nicht gelesen werden. Stellen Sie sicher, dass die Datei im richtigen Format (CSV/Excel/JSON) und nicht beschädigt ist.",
    },
    "ds_dahili_bulunamadi": {
        "tr": "Dahili İK veri seti bulunamadı. Önce `python src/data_prep.py` çalıştırın.",
        "en": "Built-in HR dataset not found. Run `python src/data_prep.py` first.",
        "de": "Integrierter HR-Datensatz nicht gefunden. Führen Sie zuerst `python src/data_prep.py` aus.",
    },
    "ds_dahili_yukle_btn": {
        "tr": "Dahili İK Veri Setini Yükle",
        "en": "Load Built-in HR Dataset",
        "de": "Integrierten HR-Datensatz laden",
    },
    "ds_aktif": {
        "tr": "Aktif veri seti: **{name}** — {rows} satır, {cols} kolon",
        "en": "Active dataset: **{name}** — {rows} rows, {cols} columns",
        "de": "Aktiver Datensatz: **{name}** — {rows} Zeilen, {cols} Spalten",
    },
    "ds_genel_istatistikler": {
        "tr": "### Genel İstatistikler",
        "en": "### General Statistics",
        "de": "### Allgemeine Statistiken",
    },
    "ds_eksik_degerler": {
        "tr": "**Eksik Değerler**",
        "en": "**Missing Values**",
        "de": "**Fehlende Werte**",
    },
    "ds_eksik_sayisi": {
        "tr": "Eksik Sayısı",
        "en": "Missing Count",
        "de": "Fehlende Anzahl",
    },
    "ds_kalite_icgoruler": {
        "tr": "### 🔎 Veri Kalitesi & Otomatik İçgörüler",
        "en": "### 🔎 Data Quality & Auto Insights",
        "de": "### 🔎 Datenqualität & Automatische Einblicke",
    },
    "ds_otomatik_icgoruler": {
        "tr": "**Otomatik İçgörüler**",
        "en": "**Automatic Insights**",
        "de": "**Automatische Einblicke**",
    },
    "ds_icgoru_yok": {
        "tr": "Bu veri setinde öne çıkan otomatik bir içgörü bulunamadı.",
        "en": "No notable automatic insights found in this dataset.",
        "de": "Keine nennenswerten automatischen Einblicke in diesem Datensatz gefunden.",
    },
    "ds_kalite_notlari": {
        "tr": "**Veri Kalitesi Notları**",
        "en": "**Data Quality Notes**",
        "de": "**Datenqualitätshinweise**",
    },
    "ds_aykiri": {
        "tr": "**Aykırı Değerler (IQR yöntemi)**",
        "en": "**Outliers (IQR method)**",
        "de": "**Ausreißer (IQR-Methode)**",
    },
    "ds_gorsellestirmeler": {
        "tr": "### Görselleştirmeler",
        "en": "### Visualizations",
        "de": "### Visualisierungen",
    },
    "ds_sayisal_dagilim": {
        "tr": "**Sayısal Kolon Dağılımları**",
        "en": "**Numeric Column Distributions**",
        "de": "**Numerische Spaltenverteilungen**",
    },
    "ds_kategorik_dagilim": {
        "tr": "**Kategorik Kolon Dağılımları**",
        "en": "**Categorical Column Distributions**",
        "de": "**Kategorische Spaltenverteilungen**",
    },
    "ds_korelasyon": {
        "tr": "**Korelasyon Matrisi**",
        "en": "**Correlation Matrix**",
        "de": "**Korrelationsmatrix**",
    },
    "ds_kolon_sec": {
        "tr": "Kolon seç",
        "en": "Select column",
        "de": "Spalte auswählen",
    },
    "ds_istatistik_csv": {
        "tr": "İstatistik Özetini CSV indir",
        "en": "Download Statistics Summary as CSV",
        "de": "Statistikzusammenfassung als CSV herunterladen",
    },
    "ds_info_yukle": {
        "tr": "Devam etmek için bir dosya yükleyin veya dahili İK veri setini seçin.",
        "en": "Upload a file or select the built-in HR dataset to continue.",
        "de": "Laden Sie eine Datei hoch oder wählen Sie den integrierten HR-Datensatz aus.",
    },
    "ds_ozel_moduller": {
        "tr": "## 🧩 Özel Analiz Modülleri",
        "en": "## 🧩 Special Analysis Modules",
        "de": "## 🧩 Spezielle Analysemodule",
    },
    "ds_modul_sec": {
        "tr": "Modül Seç",
        "en": "Select Module",
        "de": "Modul auswählen",
    },
    "ds_modul_yok": {
        "tr": "Yok (sadece genel istatistik)",
        "en": "None (general statistics only)",
        "de": "Keine (nur allgemeine Statistiken)",
    },
    "ds_modul_auto": {
        "tr": "🤖 Otomatik Model Eğitimi & Açıklama (Genel)",
        "en": "🤖 Auto Model Training & Explanation (General)",
        "de": "🤖 Automatisches Modelltraining & Erklärung (Allgemein)",
    },
    "ds_modul_attrition": {
        "tr": "📉 Çalışan Kaybı Tahmini",
        "en": "📉 Employee Attrition Prediction",
        "de": "📉 Mitarbeiterfluktuation Vorhersage",
    },
    "ds_modul_performance": {
        "tr": "🏆 Performans Analizi",
        "en": "🏆 Performance Analysis",
        "de": "🏆 Leistungsanalyse",
    },
    "ds_modul_salary": {
        "tr": "💰 Maaş & Kariyer Analizi",
        "en": "💰 Salary & Career Analysis",
        "de": "💰 Gehalts- & Karriereanalyse",
    },
    "ds_modul_action": {
        "tr": "🎯 Aksiyon Merkezi",
        "en": "🎯 Action Center",
        "de": "🎯 Aktionszentrum",
    },
    "ds_caption_hr_schema": {
        "tr": (
            "İK'ya özgü modüller (Çalışan Kaybı Tahmini, Performans Analizi, Maaş & Kariyer Analizi, "
            "Aksiyon Merkezi) yalnızca beklenen İK şemasına sahip bir veri setinde (örn. dahili İK "
            "örnek verisi) kullanılabilir."
        ),
        "en": (
            "HR-specific modules (Attrition Prediction, Performance Analysis, Salary & Career Analysis, "
            "Action Center) are only available for datasets with the expected HR schema (e.g. built-in HR sample)."
        ),
        "de": (
            "HR-spezifische Module (Fluktuationsvorhersage, Leistungsanalyse, Gehalts- & Karriereanalyse, "
            "Aktionszentrum) sind nur für Datensätze mit dem erwarteten HR-Schema verfügbar."
        ),
    },
    "ds_caption_model_yok": {
        "tr": "Eğitilmiş çalışan kaybı modeli bulunamadı; önce `python src/model.py` çalıştırın.",
        "en": "Trained attrition model not found; run `python src/model.py` first.",
        "de": "Trainiertes Fluktuationsmodell nicht gefunden; führen Sie zuerst `python src/model.py` aus.",
    },

    # ── Company panel ─────────────────────────────────────────────────────────
    "company_baslik": {
        "tr": "Şirket Adı ile Web / Sosyal Medya Analizi",
        "en": "Web / Social Media Analysis by Company Name",
        "de": "Web- / Social-Media-Analyse nach Unternehmensname",
    },
    "company_caption": {
        "tr": (
            "Google Haberler ve genel web araması üzerinden şirketle ilgili haber/yorum/gönderi başlıklarını tarar, "
            "sözlük tabanlı duygu analizi yapar ve öne çıkan konuları çıkarır. İnternet bağlantısı gerektirir."
        ),
        "en": (
            "Scans news/comment/post headlines about the company via Google News and general web search, "
            "performs dictionary-based sentiment analysis and extracts prominent topics. Requires internet connection."
        ),
        "de": (
            "Durchsucht Nachrichten-Schlagzeilen über das Unternehmen via Google News und allgemeiner Web-Suche, "
            "führt wörterbuchbasierte Sentiment-Analyse durch und extrahiert prominente Themen. Erfordert Internetverbindung."
        ),
    },
    "company_sirket_adi": {
        "tr": "Şirket Adı",
        "en": "Company Name",
        "de": "Unternehmensname",
    },
    "company_placeholder": {
        "tr": "Örn: Turkcell",
        "en": "e.g.: Apple",
        "de": "z.B.: BMW",
    },
    "company_spinner": {
        "tr": "'{target}' için web ve haber kaynakları taranıyor...",
        "en": "Scanning web and news sources for '{target}'...",
        "de": "Web- und Nachrichtenquellen werden für '{target}' durchsucht...",
    },
    "company_info": {
        "tr": "Analiz başlatmak için bir şirket adı girip 'Analiz Et' butonuna tıklayın veya 'Örnek Dene' ile hemen deneyin.",
        "en": "Enter a company name and click 'Analyze' to start, or click 'Try Example' to try immediately.",
        "de": "Geben Sie einen Unternehmensnamen ein und klicken Sie auf 'Analysieren', oder klicken Sie auf 'Beispiel ausprobieren'.",
    },
    "company_bos_uyari": {
        "tr": "'{name}' için hiçbir kaynak bulunamadı. Şirket adını farklı yazarak tekrar deneyin.",
        "en": "No sources found for '{name}'. Try a different spelling.",
        "de": "Keine Quellen für '{name}' gefunden. Versuchen Sie eine andere Schreibweise.",
    },
    "company_bulundu": {
        "tr": "'{name}' için {n} kaynak bulundu.",
        "en": "{n} sources found for '{name}'.",
        "de": "{n} Quellen für '{name}' gefunden.",
    },
    "company_toplam_kaynak": {
        "tr": "Toplam Kaynak",
        "en": "Total Sources",
        "de": "Gesamtquellen",
    },
    "company_pozitif": {
        "tr": "Pozitif",
        "en": "Positive",
        "de": "Positiv",
    },
    "company_notr": {
        "tr": "Nötr",
        "en": "Neutral",
        "de": "Neutral",
    },
    "company_negatif": {
        "tr": "Negatif",
        "en": "Negative",
        "de": "Negativ",
    },
    "company_itibar_puani": {
        "tr": "**İtibar Puanı**",
        "en": "**Reputation Score**",
        "de": "**Reputationspunktzahl**",
    },
    "company_duygu_dagilim": {
        "tr": "**Duygu Dağılımı**",
        "en": "**Sentiment Distribution**",
        "de": "**Sentiment-Verteilung**",
    },
    "company_one_cikan_konular": {
        "tr": "**Öne Çıkan Konular**",
        "en": "**Prominent Topics**",
        "de": "**Prominente Themen**",
    },
    "company_konu_yok": {
        "tr": "Öne çıkan konu tespit edilemedi.",
        "en": "No prominent topics detected.",
        "de": "Keine prominenten Themen erkannt.",
    },
    "company_trend_baslik": {
        "tr": "### 📈 Zaman İçinde İtibar Trendi",
        "en": "### 📈 Reputation Trend Over Time",
        "de": "### 📈 Reputationstrend im Zeitverlauf",
    },
    "company_trend_caption": {
        "tr": "Yalnızca tarih bilgisi taşıyan (esas olarak Google Haberler) kaynaklar bu grafiğe dahildir.",
        "en": "Only sources with date information (mainly Google News) are included in this chart.",
        "de": "Nur Quellen mit Datumsinformationen (hauptsächlich Google News) sind in diesem Diagramm enthalten.",
    },
    "company_kaynaklar": {
        "tr": "### Kaynaklar",
        "en": "### Sources",
        "de": "### Quellen",
    },
    "company_tarama_uyarilari": {
        "tr": "Tarama Uyarıları",
        "en": "Scan Warnings",
        "de": "Scan-Warnungen",
    },
    "company_kaynak_csv": {
        "tr": "Kaynak Listesini CSV indir",
        "en": "Download Source List as CSV",
        "de": "Quellliste als CSV herunterladen",
    },
    "company_not": {
        "tr": "Not: Duygu analizi sözlük tabanlı sezgisel bir yöntemle hesaplanmıştır; nihai yorum için kaynakların incelenmesi önerilir.",
        "en": "Note: Sentiment analysis is computed using a dictionary-based heuristic; reviewing the sources is recommended for final interpretation.",
        "de": "Hinweis: Die Sentiment-Analyse wird mit einer wörterbuchbasierten Heuristik berechnet; für die endgültige Interpretation wird eine Überprüfung der Quellen empfohlen.",
    },

    # ── CV panel ──────────────────────────────────────────────────────────────
    "cv_mod": {
        "tr": "Mod",
        "en": "Mode",
        "de": "Modus",
    },
    "cv_mod_tek": {
        "tr": "📄 Tek CV Analizi",
        "en": "📄 Single CV Analysis",
        "de": "📄 Einzelner Lebenslauf",
    },
    "cv_mod_coklu": {
        "tr": "📊 Çoklu CV Karşılaştırma",
        "en": "📊 Multiple CV Comparison",
        "de": "📊 Mehrere Lebensläufe vergleichen",
    },
    "cv_mod_derin": {
        "tr": "🆓 ATS & Derin Analiz",
        "en": "🆓 ATS & Deep Analysis",
        "de": "🆓 ATS & Tiefenanalyse",
    },
    "cv_yukle_baslik": {
        "tr": "CV Yükle",
        "en": "Upload CV",
        "de": "Lebenslauf hochladen",
    },
    "cv_yukle_caption": {
        "tr": "PDF, DOCX veya TXT formatında bir CV yükleyin. Analiz anahtar kelime tabanlı sezgisel bir yöntemle yapılır; harici bir dil modeli API'sine bağımlı değildir.",
        "en": "Upload a CV in PDF, DOCX or TXT format. Analysis is performed using keyword-based heuristics; no external language model API dependency.",
        "de": "Laden Sie einen Lebenslauf im PDF-, DOCX- oder TXT-Format hoch. Die Analyse erfolgt mit schlüsselwortbasierten Heuristiken; keine externe Sprachmodell-API-Abhängigkeit.",
    },
    "cv_dosya_label": {
        "tr": "CV dosyası",
        "en": "CV file",
        "de": "Lebenslauf-Datei",
    },
    "cv_cikarma_spinner": {
        "tr": "CV metni çıkarılıyor...",
        "en": "Extracting CV text...",
        "de": "Lebenslauftext wird extrahiert...",
    },
    "cv_gorsel_pdf_uyari": {
        "tr": "Dosyadan metin çıkarılamadı (taranmış görsel PDF olabilir).",
        "en": "Could not extract text from file (may be a scanned image PDF).",
        "de": "Text konnte nicht aus der Datei extrahiert werden (möglicherweise ein gescanntes Bild-PDF).",
    },
    "cv_info_yukle": {
        "tr": "Devam etmek için bir CV dosyası yükleyin veya 'Örnek Dene' ile hemen deneyin.",
        "en": "Upload a CV file or click 'Try Example' to get started.",
        "de": "Laden Sie eine Lebenslauf-Datei hoch oder klicken Sie auf 'Beispiel ausprobieren'.",
    },
    "cv_aday": {
        "tr": "Analiz edilen aday: **{name}** ({file})",
        "en": "Analyzed candidate: **{name}** ({file})",
        "de": "Analysierter Kandidat: **{name}** ({file})",
    },
    "cv_dosya_msg": {
        "tr": "Analiz edilen dosya: **{file}**",
        "en": "Analyzed file: **{file}**",
        "de": "Analysierte Datei: **{file}**",
    },
    "cv_tahmini_deneyim": {
        "tr": "Tahmini Deneyim",
        "en": "Estimated Experience",
        "de": "Geschätzte Erfahrung",
    },
    "cv_yil": {
        "tr": "{n} yıl",
        "en": "{n} years",
        "de": "{n} Jahre",
    },
    "cv_egitim_duzeyi": {
        "tr": "Eğitim Düzeyi",
        "en": "Education Level",
        "de": "Bildungsniveau",
    },
    "cv_beceri_sayisi": {
        "tr": "Tespit Edilen Beceri Sayısı",
        "en": "Detected Skills Count",
        "de": "Erkannte Fähigkeiten Anzahl",
    },
    "cv_iletisim": {
        "tr": "**İletişim Bilgileri**",
        "en": "**Contact Information**",
        "de": "**Kontaktinformationen**",
    },
    "cv_tespit_edilemedi": {
        "tr": "Tespit edilemedi",
        "en": "Not detected",
        "de": "Nicht erkannt",
    },
    "cv_beceriler_baslik": {
        "tr": "### Tespit Edilen Beceriler",
        "en": "### Detected Skills",
        "de": "### Erkannte Fähigkeiten",
    },
    "cv_beceri_yok": {
        "tr": "Beceri anahtar kelimesi tespit edilemedi.",
        "en": "No skill keywords detected.",
        "de": "Keine Kompetenzstichwörter erkannt.",
    },
    "cv_guclu": {
        "tr": "### 💪 Güçlü Yönler",
        "en": "### 💪 Strengths",
        "de": "### 💪 Stärken",
    },
    "cv_zayif": {
        "tr": "### 🔧 Gelişime Açık Yönler",
        "en": "### 🔧 Areas for Improvement",
        "de": "### 🔧 Verbesserungsbereiche",
    },
    "cv_pozisyon_onerileri": {
        "tr": "### 🎯 Uygun Pozisyon Önerileri",
        "en": "### 🎯 Suitable Position Suggestions",
        "de": "### 🎯 Geeignete Positionsvorschläge",
    },
    "cv_pozisyon_yok": {
        "tr": "Yeterli beceri anahtar kelimesi bulunamadığı için pozisyon önerisi üretilemedi.",
        "en": "Not enough skill keywords found to generate position suggestions.",
        "de": "Nicht genügend Kompetenzstichwörter gefunden, um Positionsvorschläge zu generieren.",
    },
    "cv_ilan_eslesme_baslik": {
        "tr": "### 🎯 İlana Göre Eşleştirme",
        "en": "### 🎯 Job Posting Match",
        "de": "### 🎯 Stellenanzeigen-Übereinstimmung",
    },
    "cv_ilan_caption": {
        "tr": "Bir iş ilanı metni yapıştırın; CV'deki beceriler ilanla karşılaştırılıp uygunluk yüzdesi hesaplanır.",
        "en": "Paste a job posting; skills in the CV will be compared and a match percentage calculated.",
        "de": "Fügen Sie eine Stellenanzeige ein; Fähigkeiten im Lebenslauf werden verglichen und ein Übereinstimmungsprozentsatz berechnet.",
    },
    "cv_ilan_label": {
        "tr": "İş ilanı metni",
        "en": "Job posting text",
        "de": "Stellenanzeigentext",
    },
    "cv_ilan_beceri_yok": {
        "tr": "İlan metninde tanınan beceri anahtar kelimesi bulunamadı.",
        "en": "No recognized skill keywords found in the job posting.",
        "de": "Keine erkannten Kompetenzstichwörter in der Stellenanzeige gefunden.",
    },
    "cv_uygunluk_skoru": {
        "tr": "Uygunluk Skoru",
        "en": "Match Score",
        "de": "Übereinstimmungspunktzahl",
    },
    "cv_eslesen_beceri": {
        "tr": "Eşleşen Beceri",
        "en": "Matched Skills",
        "de": "Übereinstimmende Fähigkeiten",
    },
    "cv_eksik_beceri": {
        "tr": "Eksik Beceri",
        "en": "Missing Skills",
        "de": "Fehlende Fähigkeiten",
    },
    "cv_eslesen_beceriler_label": {
        "tr": "**✅ Eşleşen Beceriler**",
        "en": "**✅ Matched Skills**",
        "de": "**✅ Übereinstimmende Fähigkeiten**",
    },
    "cv_eksik_beceriler_label": {
        "tr": "**❌ Eksik Beceriler**",
        "en": "**❌ Missing Skills**",
        "de": "**❌ Fehlende Fähigkeiten**",
    },
    "cv_gelisim_onerileri": {
        "tr": "**📚 Gelişim Önerileri**",
        "en": "**📚 Development Tips**",
        "de": "**📚 Entwicklungstipps**",
    },
    "cv_eslesme_info": {
        "tr": "Eşleştirme sonucu görmek için yukarıya bir ilan metni yapıştırın.",
        "en": "Paste a job posting above to see the match result.",
        "de": "Fügen Sie oben eine Stellenanzeige ein, um das Übereinstimmungsergebnis zu sehen.",
    },
    "cv_not": {
        "tr": "Not: Bu analiz anahtar kelime tabanlı sezgisel bir yöntemle üretilmiştir; bir ön değerlendirme olarak kullanılmalı, nihai karar için insan incelemesi yapılmalıdır.",
        "en": "Note: This analysis is generated using keyword-based heuristics; it should be used as a preliminary evaluation and human review is recommended for the final decision.",
        "de": "Hinweis: Diese Analyse wird mit schlüsselwortbasierten Heuristiken erstellt; sie sollte als Vorabauswertung verwendet werden.",
    },
    "cv_karsilastirma_baslik": {
        "tr": "Birden Fazla CV Yükle ve Karşılaştır",
        "en": "Upload and Compare Multiple CVs",
        "de": "Mehrere Lebensläufe hochladen und vergleichen",
    },
    "cv_karsilastirma_caption": {
        "tr": "PDF, DOCX veya TXT formatında birden fazla CV yükleyin. Aşağıya bir iş ilanı metni yapıştırırsanız adaylar o ilana uygunluk yüzdesine göre; yapıştırmazsanız beceri sayısı, deneyim ve eğitim düzeyinden oluşan genel bir güç skoruna göre sıralanır.",
        "en": "Upload multiple CVs in PDF, DOCX or TXT format. If you paste a job posting below, candidates are ranked by match percentage; otherwise by a general strength score.",
        "de": "Laden Sie mehrere Lebensläufe hoch. Wenn Sie eine Stellenanzeige einfügen, werden Kandidaten nach Übereinstimmungsprozentsatz gerankt; andernfalls nach einem allgemeinen Stärke-Score.",
    },
    "cv_karsilastirma_info": {
        "tr": "Devam etmek için en az iki CV dosyası yükleyin.",
        "en": "Upload at least two CV files to continue.",
        "de": "Laden Sie mindestens zwei Lebenslauf-Dateien hoch, um fortzufahren.",
    },
    "cv_ilan_opsiyonel": {
        "tr": "İş ilanı metni (opsiyonel)",
        "en": "Job posting text (optional)",
        "de": "Stellenanzeigentext (optional)",
    },
    "cv_derin_baslik": {
        "tr": "🆓 ATS Uyumu & Derin Analiz",
        "en": "🆓 ATS Compatibility & Deep Analysis",
        "de": "🆓 ATS-Kompatibilität & Tiefenanalyse",
    },
    "cv_derin_caption": {
        "tr": "ATS uyum skoru, deneyim/unvan tutarsızlığı tespiti, ilan listesine göre gerekçeli eşleştirme ve yinelenen aday kontrolü — tamamen kural tabanlı, **ücretsiz** ve harici hiçbir API'ye bağımlı değil.",
        "en": "ATS compatibility score, experience/title inconsistency detection, justified matching against job listing and duplicate candidate check — fully rule-based, **free** and no external API dependency.",
        "de": "ATS-Kompatibilitätspunktzahl, Inkonsistenz-Erkennung, begründete Übereinstimmung und Duplikat-Kandidatenprüfung — vollständig regelbasiert, **kostenlos**.",
    },
    "cv_deep_pool_info": {
        "tr": "Bu özellik, **📊 Çoklu CV Karşılaştırma** sekmesinde yüklediğiniz CV'leri kullanır. Lütfen önce o sekmede en az bir CV yükleyin.",
        "en": "This feature uses CVs uploaded in the **📊 Multiple CV Comparison** tab. Please upload at least one CV there first.",
        "de": "Diese Funktion verwendet in der Registerkarte **📊 Mehrere Lebensläufe vergleichen** hochgeladene Lebensläufe. Bitte laden Sie dort zuerst mindestens einen Lebenslauf hoch.",
    },
    "cv_deep_sec": {
        "tr": "Derin analiz edilecek CV",
        "en": "CV to deep analyze",
        "de": "Zu analysierender Lebenslauf",
    },
    "cv_deep_ilan_label": {
        "tr": "İş ilanları (birden fazla ilanı '---' ile ayırın, opsiyonel)",
        "en": "Job postings (separate multiple postings with '---', optional)",
        "de": "Stellenanzeigen (mehrere Anzeigen mit '---' trennen, optional)",
    },

    # ── Attrition ─────────────────────────────────────────────────────────────
    "attr_risk_hesapla": {
        "tr": "Varsayımsal Çalışan İçin Risk Skoru Hesapla",
        "en": "Calculate Risk Score for Hypothetical Employee",
        "de": "Risikopunktzahl für hypothetischen Mitarbeiter berechnen",
    },
    "attr_departman": {
        "tr": "Departman",
        "en": "Department",
        "de": "Abteilung",
    },
    "attr_pozisyon": {
        "tr": "Pozisyon",
        "en": "Position",
        "de": "Position",
    },
    "attr_fazla_mesai": {
        "tr": "Fazla Mesai",
        "en": "Overtime",
        "de": "Überstunden",
    },
    "attr_medeni": {
        "tr": "Medeni Durum",
        "en": "Marital Status",
        "de": "Familienstand",
    },
    "attr_yas": {
        "tr": "Yaş",
        "en": "Age",
        "de": "Alter",
    },
    "attr_aylik_gelir": {
        "tr": "Aylık Gelir ($)",
        "en": "Monthly Income ($)",
        "de": "Monatliches Einkommen ($)",
    },
    "attr_kidem": {
        "tr": "Şirkette Kıdem (Yıl)",
        "en": "Tenure at Company (Years)",
        "de": "Betriebszugehörigkeit (Jahre)",
    },
    "attr_rol_kidem": {
        "tr": "Mevcut Roldeki Kıdem (Yıl)",
        "en": "Tenure in Current Role (Years)",
        "de": "Dauer in aktueller Rolle (Jahre)",
    },
    "attr_is_tatmini": {
        "tr": "İş Tatmini (1-4)",
        "en": "Job Satisfaction (1-4)",
        "de": "Arbeitszufriedenheit (1-4)",
    },
    "attr_wlb": {
        "tr": "İş-Yaşam Dengesi (1-4)",
        "en": "Work-Life Balance (1-4)",
        "de": "Work-Life-Balance (1-4)",
    },
    "attr_mesafe": {
        "tr": "Ev Uzaklığı (km)",
        "en": "Distance from Home (km)",
        "de": "Entfernung zum Wohnort (km)",
    },
    "attr_seyahat": {
        "tr": "Seyahat Sıklığı",
        "en": "Travel Frequency",
        "de": "Reisehäufigkeit",
    },
    "attr_ayrilma_olasiligi": {
        "tr": "Ayrılma Olasılığı",
        "en": "Attrition Probability",
        "de": "Fluktuationswahrscheinlichkeit",
    },
    "attr_dusuk_risk": {
        "tr": "Düşük Risk",
        "en": "Low Risk",
        "de": "Geringes Risiko",
    },
    "attr_orta_risk": {
        "tr": "Orta Risk",
        "en": "Medium Risk",
        "de": "Mittleres Risiko",
    },
    "attr_yuksek_risk": {
        "tr": "Yüksek Risk",
        "en": "High Risk",
        "de": "Hohes Risiko",
    },
    "attr_kritik_risk": {
        "tr": "Kritik Risk",
        "en": "Critical Risk",
        "de": "Kritisches Risiko",
    },
    "attr_faktorler": {
        "tr": "Bu Tahmini Etkileyen Faktörler",
        "en": "Factors Affecting This Prediction",
        "de": "Faktoren, die diese Vorhersage beeinflussen",
    },
    "attr_model_ozeti": {
        "tr": "Model Özeti",
        "en": "Model Summary",
        "de": "Modellzusammenfassung",
    },
    "attr_risk_hesapla_sekme": {
        "tr": "Risk Skoru Hesaplayıcı",
        "en": "Risk Score Calculator",
        "de": "Risikopunktzahl-Rechner",
    },
    "attr_en_riskli": {
        "tr": "En Riskli Çalışanlar",
        "en": "Highest Risk Employees",
        "de": "Mitarbeiter mit höchstem Risiko",
    },
    "attr_onemli_faktorler": {
        "tr": "Modeli Etkileyen En Önemli Faktörler",
        "en": "Most Important Factors Affecting the Model",
        "de": "Wichtigste Faktoren, die das Modell beeinflussen",
    },
    "attr_spinner": {
        "tr": "Tüm çalışanlar için risk skorları hesaplanıyor...",
        "en": "Calculating risk scores for all employees...",
        "de": "Risikopunktzahlen für alle Mitarbeiter werden berechnet...",
    },
    "attr_en_riskli_20": {
        "tr": "Mevcut Çalışanlar Arasında En Yüksek Riskli 20 Kişi",
        "en": "Top 20 Highest Risk Among Current Employees",
        "de": "Top 20 der höchsten Risikomitarbeiter",
    },
    "attr_model_caption": {
        "tr": "Model: LightGBM (Gradient Boosting) sınıflandırıcı, IBM HR Analytics Employee Attrition veri seti üzerinde eğitildi.",
        "en": "Model: LightGBM (Gradient Boosting) classifier trained on IBM HR Analytics Employee Attrition dataset.",
        "de": "Modell: LightGBM (Gradient Boosting) Klassifikator, trainiert auf IBM HR Analytics Employee Attrition Datensatz.",
    },

    # ── Performance ───────────────────────────────────────────────────────────
    "perf_dept_filtre": {
        "tr": "Departman Filtrele",
        "en": "Filter by Department",
        "de": "Nach Abteilung filtern",
    },
    "perf_tumü": {
        "tr": "Tümü",
        "en": "All",
        "de": "Alle",
    },
    "perf_ort_puan": {
        "tr": "Ortalama Performans Puanı",
        "en": "Average Performance Score",
        "de": "Durchschnittliche Leistungspunktzahl",
    },
    "perf_yuksek_oran": {
        "tr": "Yüksek Performanslı Oranı (Puan≥4)",
        "en": "High Performer Ratio (Score≥4)",
        "de": "Hochleistungsquote (Punktzahl≥4)",
    },
    "perf_ort_egitim": {
        "tr": "Ortalama Eğitim Sayısı (Yıllık)",
        "en": "Average Training Count (Annual)",
        "de": "Durchschnittliche Schulungsanzahl (jährlich)",
    },
    "perf_dagilim": {
        "tr": "Performans Puanı Dağılımı",
        "en": "Performance Score Distribution",
        "de": "Leistungspunktzahl-Verteilung",
    },
    "perf_dept_ort": {
        "tr": "Departmana Göre Ortalama Performans",
        "en": "Average Performance by Department",
        "de": "Durchschnittliche Leistung nach Abteilung",
    },
    "perf_tatmin_iliski": {
        "tr": "İş Tatmini ile Performans İlişkisi",
        "en": "Job Satisfaction vs Performance",
        "de": "Arbeitszufriedenheit vs. Leistung",
    },
    "perf_pozisyon_en_iyi": {
        "tr": "Pozisyona Göre Ortalama Performans (En İyi 10)",
        "en": "Average Performance by Position (Top 10)",
        "de": "Durchschnittliche Leistung nach Position (Top 10)",
    },
    "perf_csv": {
        "tr": "Pozisyon Tablosunu CSV indir",
        "en": "Download Position Table as CSV",
        "de": "Positionstabelle als CSV herunterladen",
    },

    # ── Salary & Career ───────────────────────────────────────────────────────
    "salary_ort_gelir": {
        "tr": "Ortalama Aylık Gelir",
        "en": "Average Monthly Income",
        "de": "Durchschnittliches monatliches Einkommen",
    },
    "salary_ort_artis": {
        "tr": "Ortalama Maaş Artış Oranı",
        "en": "Average Salary Increase Rate",
        "de": "Durchschnittliche Gehaltserhöhungsrate",
    },
    "salary_son_terfi": {
        "tr": "Son Terfiden Beri Ortalama Yıl",
        "en": "Average Years Since Last Promotion",
        "de": "Durchschnittliche Jahre seit letzter Beförderung",
    },
    "salary_dept_dagilim": {
        "tr": "Departmana Göre Aylık Gelir Dağılımı",
        "en": "Monthly Income Distribution by Department",
        "de": "Monatliche Einkommensverteilung nach Abteilung",
    },
    "salary_kademe_dagilim": {
        "tr": "Kademeye Göre Aylık Gelir Dağılımı",
        "en": "Monthly Income Distribution by Job Level",
        "de": "Monatliche Einkommensverteilung nach Stufe",
    },
    "salary_kidem_iliski": {
        "tr": "Kıdem ile Aylık Gelir İlişkisi",
        "en": "Tenure vs Monthly Income",
        "de": "Betriebszugehörigkeit vs. monatliches Einkommen",
    },
    "salary_terfi_dagilim": {
        "tr": "Son Terfiden Beri Geçen Yıl Dağılımı",
        "en": "Distribution of Years Since Last Promotion",
        "de": "Verteilung der Jahre seit letzter Beförderung",
    },
    "salary_hisse_opsiyonu": {
        "tr": "Kademeye Göre Ortalama Hisse Opsiyonu Seviyesi",
        "en": "Average Stock Option Level by Job Level",
        "de": "Durchschnittliche Aktienoptionsstufe nach Jobstufe",
    },
    "salary_csv": {
        "tr": "Hisse Opsiyonu Tablosunu CSV indir",
        "en": "Download Stock Options Table as CSV",
        "de": "Aktienoptionstabelle als CSV herunterladen",
    },

    # ── Action Center ─────────────────────────────────────────────────────────
    "ac_risk_esigi": {
        "tr": "Risk Eşiğini Aşan Çalışanlar",
        "en": "Employees Exceeding Risk Threshold",
        "de": "Mitarbeiter, die den Risikoschwellenwert überschreiten",
    },
    "ac_esik_slider": {
        "tr": "Risk Eşiği (%)",
        "en": "Risk Threshold (%)",
        "de": "Risikoschwellenwert (%)",
    },
    "ac_esik_caption": {
        "tr": "{n} çalışan bu eşiğin üzerinde risk skoruna sahip.",
        "en": "{n} employees have a risk score above this threshold.",
        "de": "{n} Mitarbeiter haben eine Risikopunktzahl über diesem Schwellenwert.",
    },
    "ac_esik_bos": {
        "tr": "Bu eşiği aşan çalışan yok.",
        "en": "No employees exceed this threshold.",
        "de": "Keine Mitarbeiter überschreiten diesen Schwellenwert.",
    },
    "ac_ilgi_sekme": {
        "tr": "İlgi Gerektiren Çalışanlar",
        "en": "Employees Needing Attention",
        "de": "Mitarbeiter, die Aufmerksamkeit benötigen",
    },
    "ac_senaryo_sekme": {
        "tr": "Toplu Senaryo Simülasyonu",
        "en": "Bulk Scenario Simulation",
        "de": "Bulk-Szenario-Simulation",
    },
    "ac_tekil_sekme": {
        "tr": "Tekil Çalışan Senaryosu",
        "en": "Individual Employee Scenario",
        "de": "Einzelner Mitarbeiter-Szenario",
    },
    "ac_toplu_baslik": {
        "tr": "Toplu Müdahale Senaryosu",
        "en": "Bulk Intervention Scenario",
        "de": "Bulk-Interventionsszenario",
    },
    "ac_toplu_caption": {
        "tr": "Seçilen çalışan grubuna aşağıdaki müdahaleleri uygulayıp risk skorunun ortalama nasıl değişeceğini gösterir.",
        "en": "Shows how the average risk score changes when the selected interventions are applied to the chosen employee group.",
        "de": "Zeigt, wie sich die durchschnittliche Risikopunktzahl ändert, wenn die ausgewählten Interventionen auf die gewählte Gruppe angewendet werden.",
    },
    "ac_hedef_grup": {
        "tr": "Hedef Grup",
        "en": "Target Group",
        "de": "Zielgruppe",
    },
    "ac_en_riskli_n": {
        "tr": "En riskli N çalışan",
        "en": "Top N riskiest employees",
        "de": "Top N risikoreichste Mitarbeiter",
    },
    "ac_dept_gore": {
        "tr": "Departmana göre",
        "en": "By department",
        "de": "Nach Abteilung",
    },
    "ac_calisan_sayisi": {
        "tr": "Çalışan Sayısı",
        "en": "Employee Count",
        "de": "Mitarbeiteranzahl",
    },
    "ac_departman": {
        "tr": "Departman",
        "en": "Department",
        "de": "Abteilung",
    },
    "ac_maas_zammi": {
        "tr": "Maaş Zammı (%)",
        "en": "Salary Increase (%)",
        "de": "Gehaltserhöhung (%)",
    },
    "ac_mesai_kaldir": {
        "tr": "Fazla mesaiyi kaldır",
        "en": "Remove overtime",
        "de": "Überstunden entfernen",
    },
    "ac_wlb_artir": {
        "tr": "İş-yaşam dengesini 1 puan artır",
        "en": "Increase work-life balance by 1 point",
        "de": "Work-Life-Balance um 1 Punkt verbessern",
    },
    "ac_risk_once": {
        "tr": "Ortalama Risk (Önce)",
        "en": "Average Risk (Before)",
        "de": "Durchschnittliches Risiko (Vorher)",
    },
    "ac_risk_sonra": {
        "tr": "Ortalama Risk (Sonra)",
        "en": "Average Risk (After)",
        "de": "Durchschnittliches Risiko (Nachher)",
    },
    "ac_yuksek_riskten_cikan": {
        "tr": "Yüksek Riskten Çıkan Kişi Sayısı",
        "en": "Employees Leaving High Risk",
        "de": "Mitarbeiter, die aus dem hohen Risiko herausgehen",
    },
    "ac_tekil_baslik": {
        "tr": "Tek Bir Çalışan İçin Müdahale Senaryosu",
        "en": "Intervention Scenario for a Single Employee",
        "de": "Interventionsszenario für einen einzelnen Mitarbeiter",
    },
    "ac_calisan_sec": {
        "tr": "Çalışan Seç (en riskli 50)",
        "en": "Select Employee (top 50 riskiest)",
        "de": "Mitarbeiter auswählen (Top 50 risikoreichste)",
    },
    "ac_mevcut_risk": {
        "tr": "Mevcut Risk Skoru",
        "en": "Current Risk Score",
        "de": "Aktuelle Risikopunktzahl",
    },
    "ac_onerilen_aksiyonlar": {
        "tr": "**Önerilen Aksiyonlar:**",
        "en": "**Recommended Actions:**",
        "de": "**Empfohlene Maßnahmen:**",
    },
    "ac_aksiyon_yok": {
        "tr": "Belirgin bir aksiyon önerisi yok.",
        "en": "No significant action suggestions.",
        "de": "Keine wesentlichen Aktionsvorschläge.",
    },
    "ac_simulasyon_et": {
        "tr": "**Müdahaleyi Simüle Et**",
        "en": "**Simulate Intervention**",
        "de": "**Intervention simulieren**",
    },
    "ac_simulasyon_risk": {
        "tr": "Simülasyon Sonrası Risk Skoru",
        "en": "Post-Simulation Risk Score",
        "de": "Risikopunktzahl nach Simulation",
    },
    "ac_aksiyon_spinner": {
        "tr": "{n} çalışan için aksiyon önerileri hesaplanıyor...",
        "en": "Calculating action suggestions for {n} employees...",
        "de": "Aktionsvorschläge für {n} Mitarbeiter werden berechnet...",
    },
    "ac_performans_kap": {
        "tr": "Performans nedeniyle en riskli {display_n} çalışan gösteriliyor (toplam {total}).",
        "en": "Showing top {display_n} riskiest employees for performance reasons (total {total}).",
        "de": "Aus Leistungsgründen werden die {display_n} risikoreichsten Mitarbeiter angezeigt (gesamt {total}).",
    },
    "ac_aksiyon_yok_str": {
        "tr": "Belirgin bir aksiyon önerisi yok",
        "en": "No significant action suggestions",
        "de": "Keine wesentlichen Aktionsvorschläge",
    },

    # ── Auto Model ────────────────────────────────────────────────────────────
    "auto_baslik": {
        "tr": "Otomatik Model Eğitimi ve Açıklama",
        "en": "Automatic Model Training & Explanation",
        "de": "Automatisches Modelltraining & Erklärung",
    },
    "auto_caption": {
        "tr": "Seçtiğiniz hedef kolona göre otomatik bir sınıflandırma/regresyon modeli eğitir.",
        "en": "Trains an automatic classification/regression model based on your selected target column.",
        "de": "Trainiert ein automatisches Klassifizierungs-/Regressionsmodell basierend auf Ihrer ausgewählten Zielspalte.",
    },
    "auto_hedef_kolon": {
        "tr": "Hedef Kolon (tahmin edilecek)",
        "en": "Target Column (to predict)",
        "de": "Zielspalte (vorherzusagen)",
    },
    "auto_gorev_turu": {
        "tr": "Otomatik algılanan görev türü: **{task}**",
        "en": "Auto-detected task type: **{task}**",
        "de": "Automatisch erkannter Aufgabentyp: **{task}**",
    },
    "auto_siniflandirma": {
        "tr": "Sınıflandırma",
        "en": "Classification",
        "de": "Klassifizierung",
    },
    "auto_regresyon": {
        "tr": "Regresyon",
        "en": "Regression",
        "de": "Regression",
    },
    "auto_egit_btn": {
        "tr": "Modeli Eğit",
        "en": "Train Model",
        "de": "Modell trainieren",
    },
    "auto_ozellik_yok": {
        "tr": "Hedef kolon dışında kullanılabilir özellik kolonu bulunamadı.",
        "en": "No usable feature columns found apart from the target column.",
        "de": "Keine verwendbaren Merkmalsspalten außer der Zielspalte gefunden.",
    },
    "auto_spinner": {
        "tr": "Model eğitiliyor...",
        "en": "Training model...",
        "de": "Modell wird trainiert...",
    },
    "auto_onem_sirasi": {
        "tr": "**Özellik Önem Sırası**",
        "en": "**Feature Importance Ranking**",
        "de": "**Merkmalswichtigkeitsranking**",
    },
    "auto_elle_tahmin": {
        "tr": "Elle Veri Girerek Tahmin Al",
        "en": "Make Prediction by Manual Input",
        "de": "Vorhersage durch manuelle Eingabe treffen",
    },
    "auto_tahmin_et_btn": {
        "tr": "Tahmin Et",
        "en": "Predict",
        "de": "Vorhersagen",
    },
    "auto_shap_baslik": {
        "tr": "**Tekil Satır İçin SHAP Açıklaması**",
        "en": "**SHAP Explanation for Single Row**",
        "de": "**SHAP-Erklärung für einzelne Zeile**",
    },
    "auto_satir_sec": {
        "tr": "Açıklanacak satır (index)",
        "en": "Row to explain (index)",
        "de": "Zu erklärende Zeile (Index)",
    },
    "auto_shap_caption": {
        "tr": "Not: SHAP açıklaması şu an sadece regresyon ve iki sınıflı (binary) sınıflandırma için gösteriliyor.",
        "en": "Note: SHAP explanation is currently shown only for regression and binary classification.",
        "de": "Hinweis: SHAP-Erklärung wird derzeit nur für Regression und binäre Klassifizierung angezeigt.",
    },
}


def t(key: str, **kwargs) -> str:
    """Aktif dile göre çeviriyi döndürür.

    Eğer anahtar bulunamazsa anahtarın kendisini döndürür (fallback).
    kwargs ile string format parametreleri geçilebilir:
        t("ds_aktif", name="data.csv", rows=100, cols=5)
    """
    lang = st.session_state.get("lang", "tr")
    translations_for_key = TRANSLATIONS.get(key, {})
    text = translations_for_key.get(lang, translations_for_key.get("tr", key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
