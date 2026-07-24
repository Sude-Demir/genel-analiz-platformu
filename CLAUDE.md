# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proje Özeti

"Analiz Platformu" — Streamlit tabanlı, tek sayfa (SPA benzeri) çok modüllü bir analiz aracı. Beş ana panel içerir: Dataset Analizi (genel + İK'ya özgü alt modüller), CV Analizi, Şirket Analizi (web/sosyal medya duygu analizi), Borsa Analizi (hisse/endeks teknik analizi) ve YZ Karşılaştırma (yapay zeka modellerini fiyat/bağlam/benchmark açısından karşılaştırma). Tüm UI metinleri, kolon adları ve kod içi yorumlar Türkçedir. Harici bir LLM/AI API'sine bağımlılık yoktur — tüm "akıllı" analizler (CV değerlendirme, duygu analizi) kural/sözlük tabanlı sezgisel yöntemlerle yapılır; sadece çalışan kaybı (attrition) tahmini gerçek bir ML modeli (LightGBM, cross-validation ile optimize edilmiş hiperparametrelerle) kullanır. Tek istisna: CV Analizi'nde, tamamen **opsiyonel ve varsayılan kapalı** olarak kullanıcının kendi makinesinde çalışan **yerel** bir Ollama sunucusu (`localhost:11434`) kullanılabilir — anahtar gerektirmez, veri makineden dışarı çıkmaz, bu yüzden "harici API" sayılmaz. Ollama erişilemezse sistem hatasız şekilde mevcut kural/sözlük tabanlı yönteme sessizce döner. Uzak/anahtarlı LLM API'leri hâlâ yasaktır.

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

Streamlit'in çoklu-sayfa (multipage) gezinmesi **kullanılmaz**. Bunun yerine tek script + `st.session_state["active_panel"]` deseniyle sol menüden paneller arasında geçiş yapılır (sayfa/URL değişmez). Panel metadata'sı iki yerde tutulur ve **yeni bir üst düzey panel eklerken ikisi de güncellenmeli**:
- `app/Home.py` — `PANELS` sözlüğüne `{"render": ...}` (modül import'u gerektirdiğinden render eşlemesi burada kalır).
- `app/panel_registry.py` — `PANEL_REGISTRY` listesine `{"key", "icon", "title", "desc", "color"}` kaydı. Bu tek kayıt hem sidebar etiketini (`PANEL_LABELS_TR`, `Home.py` içinde otomatik türetilir) hem de anasayfadaki modül kartını (`home_panel.py`'nin `MODULE_CARDS`'ı, doğrudan `PANEL_REGISTRY`'yi kullanır) besler — `home_panel.py`'de ayrıca manuel bir kart eklemeye gerek yoktur, "Anasayfa" panel anahtarı bu listeye dahil edilmez. Etiketler `tr()` ile çevrilir, ayrıca çeviri için ayrı bir kayıt gerekmez.

### İki ayrı modelleme yolu (kasıtlı olarak birbirinden bağımsız)

1. **`src/model.py`** — yalnızca dahili İK veri setine (`data/employees.csv`) özel, sabit kodlanmış Türkçe kolon listeleri (`NUMERIC_FEATURES`, `CATEGORICAL_FEATURES`) kullanır. `train()`, aday modelleri (`build_candidate_pipelines()`: LightGBM + RandomForest — kasıtlı olarak yalnızca ağaç tabanlı modellerle sınırlıdır, ikisi de `.feature_importances_`/`shap.TreeExplainer` ile uyumludur) `RandomizedSearchCV` + `StratifiedKFold` ile karşılaştırıp CV ROC-AUC'si en yüksek olanı seçer. Seçilen pipeline `models/attrition_model.joblib` içine `{pipeline, model_name, numeric_features, categorical_features}` olarak kaydedilir; model karşılaştırma tablosu, test metrikleri, confusion matrix, ROC/öğrenme/kalibrasyon eğrileri ise `models/attrition_model_metrics.json`'a yazılır (`app/data_loader.py:load_model_metrics()` ile okunur, dosya yoksa None döner) ve Dataset Analizi → Çalışan Kaybı Tahmini → Model Özeti sekmesinde gösterilir.
2. **`src/auto_model.py`** — kullanıcının yüklediği **herhangi bir** veri setinde, kolon tiplerini çalışma zamanında algılayıp (`infer_column_types`) sınıflandırma/regresyon görevini otomatik seçen (`detect_task_type`) genel amaçlı model eğitici. Bu ikisi kasıtlı olarak ayrı tutulmuştur — attrition modeline özgü mantığı genelleştirmeye çalışma.

Her iki yol da SHAP `TreeExplainer` ile açıklanabilirlik sağlar; SHAP değerleri pozitif sınıfa (attrition="Evet" / sınıflandırmada kod=1) göre yorumlanır.

### Panel/modül hiyerarşisi

- `app/panels/dataset_panel.py`, `cv_panel.py`, `company_panel.py`, `borsa_panel.py`, `ai_panel.py` — beş ana panel, `Home.py`'deki `PANELS` sözlüğünden çağrılır. `company_panel.py`, `borsa_panel.py` ve `ai_panel.py`'nin her biri, tekil analizin altında `_render_compare_section()` ile ayrı bir karşılaştırma kısmı da render eder (sırasıyla "⚖️ Şirket Karşılaştır", "⚖️ Sembol Karşılaştır", model çoklu-seçim tablosu; `company_panel`/`borsa_panel` aynı `_cached_scan`/`_cached_fetch` önbelleğini paylaşır) — bunlar bağımsız birer üst düzey panel değildir.
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

- **CV analizi** (`src/cv_analysis.py`): regex + anahtar kelime sözlükleri (`SKILL_GROUPS`, `POSITION_MAP`, `EDUCATION_LEVELS`) ile çalışır; varsayılan olarak LLM kullanmaz. Yeni beceri/pozisyon eklemek için bu sözlükleri genişlet. `match_cv_to_job()` aynı `SKILL_GROUPS` sözlüğünü hem ilan hem CV metnine uygulayarak (kesişim/fark) ilana özel eşleştirme yüzdesi üretir.
- **Yerel LLM istisnası (Ollama)** (`src/ollama_client.py`): yalnızca `match_cv_to_job()`'ı `use_llm=True` ile çağırıldığında zenginleştirir (CV panelindeki toggle ile kullanıcı açıkça açar), yalnızca `localhost:11434` üzerinden. Erişilemezlik durumunda tüm fonksiyonlar sessizce `None`/`False`/`[]` döner, exception yaymaz; `match_cv_to_job()`'ın kural tabanlı alanları (`matched_skills` vb.) bundan hiç etkilenmez, sonuç yalnızca ek bir `llm_insight` anahtarı kazanır. `app/data_loader.py:ollama_ready()` sunucunun erişilebilirliğini `st.cache_resource` ile önbellekler.
- **Şirket analizi** (`src/company_analysis.py`): API anahtarı gerektirmeyen Google/Bing News RSS + Reddit RSS + DuckDuckGo HTML scraping kullanır; varsayılan duygu analizi `POSITIVE_WORDS`/`NEGATIVE_WORDS` sözlük tabanlıdır (`analyze_sentiment()`). Bu scraping dış servislerin HTML/RSS yapısına bağımlı olduğundan kırılgandır — hata durumunda sessizce boş liste döner ve `warnings` listesine eklenir (exception fırlatmaz). Instagram/X gibi platformlar kasıtlı olarak desteklenmez (bkz. modül docstring'i) — anahtarsız/girişsiz çekilemezler ve kullanım şartlarına aykırıdır. `collect_mentions()` (tarama) ve `label_mentions()` (etiketleme) kasıtlı olarak ayrıdır — `build_dataframe(company, sentiment_fn=analyze_sentiment)` ikisini birleştiren ince bir sarmalayıcıdır; bu ayrım, `company_panel.py`'nin aynı taranmış kayıtları yeniden ağ çağrısı yapmadan hem sözlük hem ML yöntemiyle etiketleyebilmesini sağlar.
- **Şirket duygu ML modeli** (`src/sentiment_model.py`): `analyze_sentiment()`'tan kasıtlı olarak AYRIDIR — kullanıcının sağladığı etiketli bir Türkçe metin veri setinden (`data/raw/test.csv`, 48.965 satır: ürün/mağaza yorumları, tweet'ler, HUMIR film yorumu derlemi, Wikipedia cümleleri) TF-IDF + LogisticRegression/MultinomialNB karşılaştırılıp (`build_candidate_pipelines()`, CV `f1_macro`'ya göre seçim — sınıflar dengesiz olduğundan accuracy değil f1_macro kullanılır) gerçek bir sınıflandırıcı EĞİTİLİR (`train()`). TfidfVectorizer, negasyon kelimelerini (`hiç`, `değil`, `yok`) hiçbir stop-word listesiyle elemez ve `ngram_range=(1,2)` kullanır — sözlük yönteminin kaçırdığı "hiç iyi değil" gibi örüntüleri yakalayabilmesi içindir. Dürüstlük notu: "Nötr" sınıfının büyük çoğunluğu Wikipedia cümlelerinden gelir (yapısal olarak haber/yorumdan farklıdır); bu sınırlılık hem `train()`'in ürettiği metrik JSON'unda hem de `company_panel.py`'deki "🧠 ML Model Bilgisi" panelinde açıkça belirtilir. `predict_batch()`'in ürettiği skor (P(Pozitif)-P(Negatif)) kasıtlı olarak sözlük skoruyla aynı mertebede (-1..+1) tutulur ki `_segment_trend()` gibi eşik tabanlı fonksiyonlar değişmeden çalışsın. `company_panel.py`'de bir checkbox ile opsiyonel olarak (varsayılan kapalı, model dosyası yoksa sessizce sözlük yöntemine döner) çalıştırılır.
- **Borsa analizi** (`src/borsa_analysis.py`): API anahtarı gerektirmeyen Yahoo Finance'in herkese açık `v8/finance/chart` JSON ucunu kullanır (BIST, ABD/global hisseler, endeksler tek biçimde desteklenir); trend yorumu SMA20 karşılaştırmasına dayalı kural tabanlı bir sezgiseldir, harici bir AI/istatistiksel model kullanmaz.
- **Borsa ML tahmini** (`src/borsa_model.py`): `borsa_analysis.py`'deki kural tabanlı sezgiselden kasıtlı olarak AYRIDIR — burada `compute_technical_indicators()` çıktısından türetilen özelliklerle (lag getiri, rolling volatilite, RSI/MACD/SMA oranları) gerçek bir RandomForest sınıflandırıcısı EĞİTİLİR (`train_price_direction_model()`) ve ertesi gün yön tahmini üretir. Zaman serisi disiplinine kesinlikle uyulur: doğrulama asla rastgele bölme ile değil, `TimeSeriesSplit` ile walk-forward backtest olarak yapılır (`_walk_forward_backtest()`), sonuç daima naif bir çoğunluk-sınıfı baseline'ıyla karşılaştırılır ve model baseline'ı geçemese bile bu dürüstçe raporlanır (`beats_baseline`). `borsa_panel.py`'de "🧠 ML Tabanlı Ertesi Gün Tahmini" bölümü altında bir checkbox ile opsiyonel olarak (varsayılan kapalı) çalıştırılır — hesaplama maliyeti olduğundan `_cached_train_ml()` ile `df` üzerinden cache'lenir.
- **YZ Karşılaştırma** (`src/ai_comparison.py`): model fiyat/bağlam penceresi/benchmark verisi (`AI_MODELS`) elle küratörlüğü yapılmış, sabit kodlanmış referans veridir — sağlayıcı duyurularına dayanır ve zamanla eskiyebilir, güncel tutmak için sözlüğün elle güncellenmesi gerekir (`PRICING_REFERENCE_TIMESTAMP` de birlikte güncellenmeli). Haber taraması `company_analysis.py`'deki aynı anahtarsız RSS desenini kullanır ama kasıtlı olarak ondan bağımsız bir kopya olarak tutulur (modüller birbirine bağımlı değildir).
