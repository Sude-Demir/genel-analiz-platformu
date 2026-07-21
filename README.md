# Analiz Platformu

![CI](https://github.com/Sude-Demir/genel-analiz-platformu/actions/workflows/ci.yml/badge.svg)

Streamlit tabanlı, tek sayfa (SPA benzeri) çok modüllü bir analiz aracı. Üç ana panel içerir:
**Dataset Analizi** (genel + İK'ya özgü alt modüller), **CV Analizi** ve **Şirket Analizi**
(web/sosyal medya duygu analizi).

Harici bir LLM/AI API'sine bağımlılık yoktur — tüm "akıllı" analizler (CV değerlendirme,
duygu analizi) kural/sözlük tabanlı sezgisel yöntemlerle yapılır; sadece çalışan kaybı
(attrition) tahmini gerçek bir ML modeli (LightGBM, cross-validation ile optimize edilmiş
hiperparametrelerle) kullanır.

## Özellikler

- **📁 Dataset Analizi**
  - Genel amaçlı veri keşfi ve görselleştirme (herhangi bir yüklenen veri setinde çalışır)
  - Veri seti dahili İK şemasına uyuyorsa ek alt modüller açılır:
    - **Çalışan Kaybı Tahmini** — LightGBM ile risk skoru, SHAP açıklamaları
    - **Performans Analizi**
    - **Maaş / Kariyer Analizi**
    - **Aksiyon Merkezi** — SHAP katkılarını Türkçe İK aksiyon önerilerine çevirir
    - **Auto Model** — herhangi bir veri setinde otomatik sınıflandırma/regresyon modeli eğitir
- **📄 CV Analizi** — regex + anahtar kelime sözlükleriyle beceri/pozisyon/eğitim çıkarımı
- **🌐 Şirket Analizi** — Google News RSS + DuckDuckGo araması üzerinden haber/başlık toplama,
  sözlük tabanlı duygu analizi ve öne çıkan konu çıkarımı

Her panelin sonucu JSON / PDF / CSV olarak dışa aktarılabilir.

## Teknoloji Yığını

- **Dil:** Python 3.13
- **UI:** Streamlit
- **Veri işleme:** pandas, numpy
- **ML:** scikit-learn (pipeline/CV) + LightGBM (gradient boosting), SHAP (açıklanabilirlik)
- **Görselleştirme:** Plotly
- **Dosya I/O:** openpyxl, pypdf, python-docx, fpdf2 (Türkçe karakter destekli PDF export)
- **Web scraping:** requests, BeautifulSoup4

## Kurulum

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.lock   # kilitli, doğrulanmış sürümler (önerilen)
# veya: pip install -r requirements.txt
```

## Çalıştırma

```bash
# 1. Ham İK verisini işleyip Türkçeleştirir: data/raw/HR-Employee-Attrition.csv -> data/employees.csv
python src/data_prep.py

# 2. Çalışan kaybı tahmin modelini eğitir (data_prep.py'den SONRA çalıştırılmalı)
python src/model.py

# 3. Uygulamayı başlatır
streamlit run app/Home.py
```

## Test

```bash
python -m pytest tests/ -v
```

## Proje Yapısı

```
src/    framework'ten bağımsız iş mantığı (veri hazırlama, model eğitimi, CV/şirket analizi)
app/    Streamlit UI katmanı (src/ modüllerini import eder)
tests/  pytest test paketi
data/   ham ve işlenmiş veri (üretilen employees.csv git'e dahil değildir)
models/ eğitilmiş model dosyaları (git'e dahil değildir, model.py ile yeniden üretilir)
```

Daha ayrıntılı mimari dokümantasyonu için [CLAUDE.md](CLAUDE.md) dosyasına bakın.

## Not

Dahili İK veri seti, IBM'in herkese açık örnek veri seti olan
[HR Analytics Employee Attrition](https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset)
üzerinden Türkçeleştirilmiştir; gerçek çalışan verisi içermez.
