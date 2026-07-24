# Analiz Platformu

![CI](https://github.com/Sude-Demir/genel-analiz-platformu/actions/workflows/ci.yml/badge.svg)

Streamlit tabanlı, tek sayfa (SPA benzeri) çok modüllü bir analiz aracı. Beş ana panel içerir:
**Dataset Analizi** (genel + İK'ya özgü alt modüller), **CV Analizi**, **Şirket Analizi**
(web/sosyal medya duygu analizi), **Borsa Analizi** (hisse/endeks teknik analizi) ve
**YZ Karşılaştırma** (yapay zeka modellerini fiyat/bağlam/benchmark açısından karşılaştırma).

Harici bir LLM/AI API'sine bağımlılık yoktur — tüm "akıllı" analizler (CV değerlendirme,
duygu analizi) kural/sözlük tabanlı sezgisel yöntemlerle yapılır; sadece çalışan kaybı
(attrition) tahmini gerçek bir ML modeli (LightGBM, cross-validation ile optimize edilmiş
hiperparametrelerle) kullanır. Tek istisna: CV Analizi'nde, tamamen **opsiyonel ve
varsayılan kapalı** olarak kullanıcının kendi makinesinde çalışan **yerel** bir Ollama
sunucusu (`localhost:11434`) kullanılabilir — anahtar gerektirmez, veri makineden dışarı
çıkmaz. Ollama erişilemezse sistem hatasız şekilde mevcut kural/sözlük tabanlı yönteme
sessizce döner.

## Özellikler

- **📁 Dataset Analizi**
  - Genel amaçlı veri keşfi ve görselleştirme (herhangi bir yüklenen veri setinde çalışır)
  - Otomatik veri kalitesi & içgörü raporu (`src/data_insights.py`): eksik değer, aykırı değer,
    yinelenen satır, yüksek kardinaliteli kolon tespiti ve öne çıkan otomatik içgörüler
  - Veri seti dahili İK şemasına uyuyorsa ek alt modüller açılır:
    - **Çalışan Kaybı Tahmini** — LightGBM ile risk skoru, SHAP açıklamaları
    - **Performans Analizi**
    - **Maaş / Kariyer Analizi**
    - **Aksiyon Merkezi** — SHAP katkılarını Türkçe İK aksiyon önerilerine çevirir
    - **Auto Model** — herhangi bir veri setinde otomatik sınıflandırma/regresyon modeli eğitir
- **📄 CV Analizi** — regex + anahtar kelime sözlükleriyle beceri/pozisyon/eğitim çıkarımı;
  ayrıca bir iş ilanı metnine karşı CV'yi eşleştirip uygunluk yüzdesi ve eksik/eşleşen
  beceri listesi üretir
- **🌐 Şirket Analizi** — Google/Bing News RSS + Reddit RSS + DuckDuckGo araması üzerinden
  haber/başlık toplama, sözlük tabanlı duygu analizi ve öne çıkan konu çıkarımı; ayrı bir
  "⚖️ Şirket Karşılaştır" bölümüyle iki şirketi yan yana kıyaslar
- **📈 Borsa Analizi** — Yahoo Finance'in herkese açık ucundan (anahtarsız) hisse/endeks
  fiyat geçmişi çeker, teknik göstergelerle (SMA20 vb.) kısa vadeli görünüm tahmini üretir;
  ayrı bir "⚖️ Sembol Karşılaştır" bölümüyle iki sembolü yan yana kıyaslar
- **🤖 YZ Karşılaştırma** — Güncel yapay zeka modellerini fiyatlandırma, bağlam penceresi ve
  benchmark skorlarına göre karşılaştırır (elle küratörlüğü yapılmış referans veri); her
  model için RSS tabanlı güncel haber/duyuru taraması da yapar

Her panelin sonucu JSON / PDF / CSV olarak dışa aktarılabilir.

## Dil Desteği

Uygulama arayüzü Türkçe (varsayılan), İngilizce ve Almanca olarak kullanılabilir
(`app/translator.py`, deep-translator/Google Translate tabanlı, sonuçlar diske
önbelleğe alınır). **Yalnızca TR/EN/DE arayüz çevirisi internet ve dış bir servis
gerektirir** — dil "Türkçe" iken uygulama tamamen çevrimdışı çalışabilir (Şirket Analizi,
Borsa Analizi ve YZ Karşılaştırma panelleri hariç, bunlar zaten internet gerektirir).

## Tema

`.streamlit/config.toml` açık ve koyu tema tanımlarını içerir (sağ üstteki ayarlar
menüsünden geçiş yapılabilir). Grafikler (`app/theme.py`) aktif temayı
`st.context.theme.type` ile algılayıp uygun renk setini otomatik seçer; grafik veri
renkleri (kategorik/durum paleti) CVD-güvenli olduğu için temadan bağımsız sabit kalır.

## Teknoloji Yığını

- **Dil:** Python 3.13
- **UI:** Streamlit
- **Veri işleme:** pandas, numpy
- **ML:** scikit-learn (pipeline/CV) + LightGBM (gradient boosting), SHAP (açıklanabilirlik)
- **Görselleştirme:** Plotly
- **Dosya I/O:** openpyxl, pdfplumber, python-docx, fpdf2 (Türkçe karakter destekli PDF export)
- **Web scraping:** requests, BeautifulSoup4
- **Çeviri:** deep-translator (Google Translate, TR/EN/DE arayüz desteği)

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
