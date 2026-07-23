# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proje Özeti

"Analiz Platformu" — Streamlit tabanlı, tek sayfa (SPA benzeri) çok modüllü bir analiz aracı. Üç ana panel içerir: Dataset Analizi (genel + İK'ya özgü alt modüller), CV Analizi, Şirket Analizi (web/sosyal medya duygu analizi). Tüm UI metinleri, kolon adları ve kod içi yorumlar Türkçedir. Harici bir LLM/AI API'sine bağımlılık yoktur — tüm "akıllı" analizler (CV değerlendirme, duygu analizi) kural/sözlük tabanlı sezgisel yöntemlerle yapılır; sadece çalışan kaybı (attrition) tahmini gerçek bir ML modeli (LightGBM, cross-validation ile optimize edilmiş hiperparametrelerle) kullanır.

Bu bir git deposudur ve GitHub'a bağlıdır (https://github.com/Sude-Demir/genel-analiz-platformu).

## Sık Kullanılan Komutlar

```bash
# Bağımlılıkları kur (venv/ zaten mevcut)
pip install -r requirements.lock   # kilitli, doğrulanmış sürümler (önerilen)
# pip install -r requirements.txt  # veya gevşek sürüm aralıklarıyla

# Ham İK verisini işleyip Türkçeleştirir: data/raw/HR-Employee-Attrition.csv -> data/employees.csv
python src/data_prep.py

# Çalışan kaybı tahmin modelini eğitir: data/employees.csv -> models/attrition_model.joblib
# (data_prep.py'den SONRA çalıştırılmalı)
python src/model.py

# Uygulamayı başlatır
streamlit run app/Home.py

# Test paketini çalıştırır (tests/ altında pytest ile)
python -m pytest tests/ -v
```

Lint konfigürasyonu (flake8, ruff vb.) bulunmamaktadır.

## Mimari

### Katman ayrımı: `src/` vs `app/`

- **`src/`** — framework'ten bağımsız iş mantığı (veri hazırlama, model eğitimi/açıklama, CV/şirket analiz algoritmaları). Streamlit'e hiç referans vermez, bağımsız script olarak da çalıştırılabilir.
- **`app/`** — Streamlit UI katmanı. `src/` modüllerini `sys.path` manipülasyonu ile import eder (paket kurulumu değil, `app/Home.py` ve `app/data_loader.py` her ikisi de `SRC_DIR`'i `sys.path`'e ekler). `src/` içindeki modüller doğrudan modül adıyla import edilir (örn. `from model import ...`, `from auto_model import ...`), `src.` prefix'i ile değil.

### SPA kabuğu (`app/Home.py`)

Streamlit'in çoklu-sayfa (multipage) gezinmesi **kullanılmaz**. Bunun yerine tek script + `st.session_state["active_panel"]` deseniyle sol menüden 3 panel arasında geçiş yapılır (sayfa/URL değişmez). Yeni bir üst düzey panel eklerken bu deseni takip et: `PANELS` sözlüğüne `{"label", "render"}` ekle.

### İki ayrı modelleme yolu (kasıtlı olarak birbirinden bağımsız)

1. **`src/model.py`** — yalnızca dahili İK veri setine (`data/employees.csv`) özel, sabit kodlanmış Türkçe kolon listeleri (`NUMERIC_FEATURES`, `CATEGORICAL_FEATURES`) kullanan LGBMClassifier (LightGBM). `train()`, `RandomizedSearchCV` + `StratifiedKFold` ile hiperparametre araması yapar. `models/attrition_model.joblib` içine `{pipeline, numeric_features, categorical_features}` olarak kaydedilir.
2. **`src/auto_model.py`** — kullanıcının yüklediği **herhangi bir** veri setinde, kolon tiplerini çalışma zamanında algılayıp (`infer_column_types`) sınıflandırma/regresyon görevini otomatik seçen (`detect_task_type`) genel amaçlı model eğitici. Bu ikisi kasıtlı olarak ayrı tutulmuştur — attrition modeline özgü mantığı genelleştirmeye çalışma.

Her iki yol da SHAP `TreeExplainer` ile açıklanabilirlik sağlar; SHAP değerleri pozitif sınıfa (attrition="Evet" / sınıflandırmada kod=1) göre yorumlanır.

### Panel/modül hiyerarşisi

- `app/panels/dataset_panel.py`, `cv_panel.py`, `company_panel.py` — üç ana panel, `Home.py`'deki `PANELS` sözlüğünden çağrılır.
- `app/panels/hr_modules/` — yalnızca **Dataset Analizi** panelinin altında, aktif veri seti gerekli İK şemasını (`REQUIRED_HR_COLUMNS` = `CATEGORICAL_FEATURES + NUMERIC_FEATURES + ["CalisanID", "Attrition"]`) sağladığında **ve** eğitilmiş model dosyası mevcut olduğunda görünen alt modüller: `attrition.py` (risk skoru hesaplayıcı), `performance.py`, `salary_career.py`, `action_center.py` (SHAP → aksiyon önerisi), `auto_model_module.py` (şemadan bağımsız, her veri setinde çalışır).
- Yeni bir İK'ya özgü alt modül eklerken `dataset_panel.py` içindeki `options` listesine ve `secim ==` dallanmasına eklemeyi unutma; şema kontrolü zaten `has_hr_schema` ile yapılıyor.

### Veri akışı

```
data/raw/HR-Employee-Attrition.csv (orijinal, İngilizce kolonlar)
  → src/data_prep.py (COLUMN_MAP + VALUE_MAP ile Türkçeleştirir)
  → data/employees.csv (Türkçe kolon adları/değerleri, uygulamanın "dahili İK veri seti" seçeneği)
  → src/model.py (LightGBM eğitir, RandomizedSearchCV ile hiperparametre araması yapar)
  → models/attrition_model.joblib
```

Kolon adı eşlemesini (`COLUMN_MAP`) veya değer eşlemesini (`VALUE_MAP`) değiştirirsen, `src/model.py`'deki `NUMERIC_FEATURES`/`CATEGORICAL_FEATURES` listelerini ve `app/panels/dataset_panel.py`'deki `REQUIRED_HR_COLUMNS`'u senkron tut.

### Ortak yardımcılar

- `app/theme.py` — tüm grafiklerde kullanılan renk paleti ve `apply_layout()` ile uygulanan ortak Plotly layout'u; yeni bir grafik eklerken buradaki renkleri/`apply_layout`'u kullan.
- `app/export_utils.py` — tüm panellerde JSON (`to_json_bytes`) ve PDF (`build_pdf` + blok listesi deseni: `{"heading", "type": "paragraph"|"bullets"|"table", "content"}`) dışa aktarım için tek ortak yol. PDF üretimi `fpdf2` + gömülü `DejaVuSans.ttf` (Türkçe karakter desteği için) kullanır; harici bir servise bağımlı değildir.
- `app/actions.py` — SHAP pozitif katkılarını Türkçe aksiyon önerilerine çevirir (`ACTIONABLE_SUGGESTIONS`). Yaş, cinsiyet, medeni durum, departman gibi değiştirilemez/demografik özellikler **kasıtlı olarak** dışarıda tutulur — yeni öneri eklerken bu prensibi koru.
- `app/data_loader.py` — `st.cache_data`/`st.cache_resource` ile veri/model/explainer yükleme; pahalı SHAP explainer kurulumu burada cache'lenir.
- `app/translator.py` — TR/EN/DE arayüz çevirisi (`tr()`/`trf()`, deep-translator/Google Translate tabanlı, disk önbellekli). Sabit metinler için `tr("...")` kullan; **çalışma zamanı verisi içeren metinlerde `tr(f"...")` kullanma** — bu, `warm_cache()`'in önceden çeviremeyeceği, her render'da canlı API isteğine yol açan bir performans hatasıdır. Bunun yerine `trf("Sabit şablon {ad}", ad=deger)` kullan (yer tutucular çeviriden sonra `.format()` ile doldurulur, aynı şablon önbellekten anında döner).

### Harici bağımlılık yok, önemli kısıtlar

- **CV analizi** (`src/cv_analysis.py`): regex + anahtar kelime sözlükleri (`SKILL_GROUPS`, `POSITION_MAP`, `EDUCATION_LEVELS`) ile çalışır; LLM kullanmaz. Yeni beceri/pozisyon eklemek için bu sözlükleri genişlet. `match_cv_to_job()` aynı `SKILL_GROUPS` sözlüğünü hem ilan hem CV metnine uygulayarak (kesişim/fark) ilana özel eşleştirme yüzdesi üretir.
- **Şirket analizi** (`src/company_analysis.py`): API anahtarı gerektirmeyen Google/Bing News RSS + Reddit RSS + DuckDuckGo HTML scraping kullanır; duygu analizi `POSITIVE_WORDS`/`NEGATIVE_WORDS` sözlük tabanlıdır. Bu scraping dış servislerin HTML/RSS yapısına bağımlı olduğundan kırılgandır — hata durumunda sessizce boş liste döner ve `warnings` listesine eklenir (exception fırlatmaz). Instagram/X gibi platformlar kasıtlı olarak desteklenmez (bkz. modül docstring'i) — anahtarsız/girişsiz çekilemezler ve kullanım şartlarına aykırıdır.
