# 📋 Genel Analiz Platformu — Şu Ana Kadar Ne Yapıldı?

*Bu doküman, projeyi hiç kod bilmeyen birine anlatır gibi hazırlanmıştır. Teknik bir kelime geçtiğinde yanına parantez içinde sade açıklaması eklenmiştir.*

---

## 1) Bu proje tek cümlede ne?

Elindeki bir Excel/CSV tablosunu, bir özgeçmişi (CV) ya da bir şirketin adını verdiğinde, sana onun hakkında **otomatik, anlaşılır bir analiz raporu** çıkaran; tamamen Türkçe, tek ekranda çalışan bir web uygulaması.

Bir çeşit **"3'ü 1 arada analiz masası"** gibi düşünebilirsin: bir tarafta veri tabloların, bir tarafta özgeçmişler, bir tarafta da şirketlerle ilgili internet yorumları için ayrı ayrı "danışman" köşeleri var.

---

## 2) En önemli özelliği: Dışarıya muhtaç değil

Bugün pek çok "akıllı" uygulama, işi ChatGPT gibi ücretli bir yapay zekâ servisine gönderip cevabı ondan alır. **Bu proje öyle çalışmıyor.**

- "Akıllı" görünen neredeyse her şey (CV değerlendirme, şirket yorumlarının olumlu/olumsuz olduğunu anlama) aslında **kural ve kelime listeleriyle** yapılıyor. Yani sistem, önceden hazırlanmış "bu kelimeler iyi anlama gelir, bu kelimeler kötü anlama gelir" gibi sözlüklere bakarak karar veriyor.
- Projede **gerçek anlamda öğrenen** tek bir yapay zekâ modeli var: bir çalışanın işten ayrılma ihtimalini tahmin eden model. Bu model geçmiş verilerden gerçekten "öğreniyor".

Bunun faydası: internet bağlantısı olmasa da (şirket analizi ve Türkçe dışındaki bir arayüz dili seçilmesi hariç), aylık ücret ödemeden, verilerini dışarıya göndermeden çalışabiliyor.

---

## 3) Uygulama neye benziyor?

Uygulamayı açtığında **tek bir ekran** görürsün — sekmeler arasında sayfa yenilenmeden geçiş yapılır (buna teknik olarak **SPA — tek sayfa uygulama** deniyor). Solda bir menü, menüde şu bölümler var:

- 🏠 **Anasayfa** — karşılama ve tanıtım ekranı
- 📊 **Dataset Analizi** — herhangi bir veri tablosunu incelemek için (çalışan ayrılma tahmini de bu sekmenin altındaki bir alt modül)
- 📄 **CV Analizi** — özgeçmiş değerlendirmek için
- 🏢 **Şirket Analizi** — bir şirketin internetteki imajını ölçmek için
- 📈 **Borsa Analizi** — bir hisse/endeks sembolünün fiyat geçmişini ve kısa vadeli görünümünü incelemek için
- 🤖 **YZ Karşılaştırma** — güncel yapay zeka modellerini fiyat/özellik açısından kıyaslamak için

Ayrıca menüden **Türkçe / İngilizce / Almanca** arasında anlık dil değişimi yapılabilir (bkz. Madde 7).

Aşağıdaki maddeler, projenin kalbini oluşturan büyük özelliklerdir.

---

## 4) Ana işler, tek tek

### 📊 A) Dataset (Veri) Analizi — "Herhangi bir tabloyu yükle, keşfet"

- CSV, Excel ya da JSON dosyanı yükleyebilirsin, ya da projenin içinde hazır gelen örnek bir İK (İnsan Kaynakları) veri setini kullanabilirsin.
- Uygulama otomatik olarak: verinin ilk birkaç satırını gösterir, kaç sayısal / kaç kategorik (kategori bazlı, örn. "Departman: Satış/Üretim") kolon olduğunu söyler, özet istatistikler (ortalama, en düşük/en yüksek değer vb.) ve eksik veri tablosu çıkarır.
- Otomatik grafikler üretir: sayısal kolonların dağılımı, kategorilerin çubuk grafiği, kolonlar arasındaki ilişki (korelasyon) haritası.
- **Otomatik veri kalitesi & içgörü raporu**: yinelenen satırları, sabit/tek değerli kolonları, ID benzeri (neredeyse her satırda farklı) kolonları, aykırı değerleri ve eksik veri oranı yüksek kolonları kendiliğinden tespit edip düz Türkçe cümlelerle özetler — kullanıcının tabloyu tek tek incelemesine gerek kalmaz.
- Sonuçları CSV, JSON veya PDF olarak indirebilirsin.
- Eğer yüklediğin veri, projenin bildiği İK şemasına (kolon isimlerine) uyuyorsa, aşağıda anlatılan **özel İK modülleri** de otomatik olarak açılır (bkz. Madde 5).

### 📄 B) CV Analizi — "Özgeçmişi oku, değerlendir"

Üç farklı kullanım şekli var:

1. **Tek CV Analizi** — Bir özgeçmiş (PDF/Word/TXT) yüklersin; sistem deneyim yılını, eğitim düzeyini, sahip olunan becerileri çıkarır; güçlü ve zayıf yönleri listeler; uygun olabilecek pozisyonları önerir. İstersen bir iş ilanı metni de yapıştırırsın, sistem CV'nin o ilana **kaç yüzde uygun** olduğunu gösterge (gauge) grafiğiyle gösterir.
2. **Çoklu CV Karşılaştırma** — Birden fazla adayın CV'sini birden yüklersin, sistem hepsini sıralar ve "en uygun aday kim, neden" sorusuna gerekçeli cevap verir.
3. **ATS & Derin Analiz** — Daha gelişmiş bir inceleme sunar:
   - **ATS uyumluluğu** *(ATS = şirketlerin kullandığı, CV'leri otomatik tarayan "başvuru takip sistemi")*: CV'nin böyle bir sistem tarafından düzgün okunup okunamayacağını kontrol eder (tablo kullanımı, standart olmayan başlıklar, bozuk karakterler gibi sorunları yakalar) ve 0-100 arası bir uyum puanı verir.
   - **Tutarsızlık tespiti**: Örneğin CV'de "Kıdemli Yönetici" unvanı yazıyor ama deneyim/detaylar bunu desteklemiyorsa, sistem bunu fark edip "bu CV'yi bir insanın da gözden geçirmesi iyi olur" diye uyarır.
   - **Kopya/yinelenen aday tespiti**: Aynı e-posta, telefon numarası ya da neredeyse aynı metne sahip iki CV'nin aday havuzuna girip girmediğini kontrol eder.

### 🏢 C) Şirket Analizi — "Şirketin adını yaz, internetteki havayı ölç"

- Bir şirket adı girersin, sistem Google/Bing Haberler, Reddit ve DuckDuckGo arama sonuçlarını tarayarak o şirketle ilgili haber ve yorumları toplar.
- Topladığı her metni Pozitif / Nötr / Negatif olarak etiketler (yine kelime sözlüğü yöntemiyle, yapay zekâ API'si kullanmadan).
- Bunlardan **0-100 arası bir "itibar puanı"** hesaplar (İyi / Uyarı / Ciddi / Kritik gibi durumlarla birlikte).
- En sık geçen konuları ve kaynaklara tıklanabilir linkleri de listeler.
- Not: Bu özellik internet bağlantısı gerektirir; dış siteler bazen yanıt vermeyebilir — böyle durumlarda uygulama hata vermek yerine kullanıcıyı nazikçe uyarır.
- Ayrıca ayrı bir **"⚖️ Şirket Karşılaştır"** bölümüyle iki şirketi yan yana kıyaslayabilirsin.

### 📈 D) Borsa Analizi — "Bir sembol yaz, fiyat geçmişini ve görünümü gör"

- Bir hisse senedi ya da endeks sembolü girersin (örn. BIST için "THYAO.IS", ABD hisseleri için "AAPL", endeksler için "^GSPC"); sistem Yahoo Finance'in herkese açık, anahtar gerektirmeyen veri ucundan fiyat geçmişini çeker.
- Açılış/yüksek/düşük/kapanış ve hacim grafiklerini, hareketli ortalama gibi teknik göstergeleri gösterir.
- Basit bir kural tabanlı yöntemle (yapay zekâ modeli değil) kısa vadeli bir "görünüm" (trend yorumu) üretir.
- Ayrı bir **"⚖️ Sembol Karşılaştır"** bölümüyle iki sembolü yan yana kıyaslayabilirsin.

### 🤖 E) YZ Karşılaştırma — "Yapay zekâ modellerini kıyasla"

- Güncel yapay zeka (LLM) modellerini fiyatlandırma, bağlam penceresi büyüklüğü ve benchmark (karşılaştırma testi) skorlarına göre yan yana gösterir.
- Bu veriler elle küratörlüğü yapılmış, sağlayıcıların resmi duyurularına dayanan referans verilerdir — zamanla eskiyebileceği için kesin rakamlar için resmi kaynaklar kontrol edilmelidir.
- Seçilen her model için Google/Bing Haberler üzerinden güncel haber/duyuru taraması da yapar.

---

## 5) İK'ya özel ekstra modüller (bonus bölüm)

Yüklediğin veri, projenin tanıdığı İK şemasına uyuyorsa ve model eğitilmişse, **Dataset Analizi** sekmesinin altında şu ekstra araçlar da açılır:

- **🔮 Çalışan Kaybı Tahmini (Attrition)** — Bir çalışanın bilgilerini (yaş, maaş, mesai durumu, kıdem, iş tatmini vb.) girersin, sistem o çalışanın **işten ayrılma olasılığını** yüzde olarak hesaplar ve bu tahmine hangi faktörlerin ne kadar etki ettiğini açıklar (bu açıklama yöntemine **SHAP** deniyor — yani "model bu kararı şu sebeplerden verdi" diyen bir teknik). Ayrıca mevcut çalışanlar arasında en riskli 20 kişiyi de listeler.
- **📈 Performans Analizi** — Departmanlara göre ortalama performans, yüksek performanslı çalışan oranı gibi metrikleri ve ilişkili grafikleri gösterir.
- **💰 Maaş & Kariyer Analizi** — Ortalama gelir, maaş artış oranları, son terfiden bu yana geçen süre gibi bilgileri departman/kademe bazında karşılaştırır.
- **🎯 Aksiyon Merkezi** — "Peki şimdi ne yapmalıyız?" sorusuna cevap verir: riskli çalışanları listeler ve her biri için somut Türkçe İK önerileri sunar (örn. "fazla mesaiyi azalt", "ücret gözden geçirilsin"). Ayrıca "eğer maaşları %10 artırsak risk ne kadar düşer?" gibi **senaryo simülasyonları** yapabilirsin. Not: yaş, cinsiyet gibi değiştirilemeyecek özellikler bilinçli olarak öneri dışı bırakılmıştır — öneriler hep değiştirilebilir şeyler üzerine kurulu.
- **🤖 Otomatik Model** — Bu, İK verisine özel değil; **yüklediğin her türlü veri setinde** çalışan genel bir araçtır. Hangi kolonu tahmin etmek istediğini seçersin, sistem otomatik olarak uygun bir model kurup eğitir ve sonuçları açıklar.

---

## 6) Perde arkası: Dosyalar nasıl bölünmüş?

Projenin kod tarafı, kolay anlaşılsın diye iki ana bölüme ayrılmış:

- **`src/` klasörü = "Beyin"** → Hesaplamaların, kuralların, modelin yaşadığı yer. Ekranla hiç ilgilenmez, sadece "girdi al, sonucu hesapla" işini yapar.
- **`app/` klasörü = "Yüz"** → Ekranda gördüğün her şey (menüler, butonlar, grafikler) burada. Bu katman, "beyin" katmanına sorup cevabı ekrana döker.

Veri, projede şu sırayla akar:

```
Ham İK verisi (İngilizce, ham hâliyle)
        ↓  Türkçeye çevrilir, temizlenir
Temiz İK verisi (Türkçe kolon adları)
        ↓  Bu veriyle model eğitilir (LightGBM adlı bir makine öğrenmesi yöntemiyle,
        ↓  en iyi ayarları bulmak için birden çok deneme/çapraz doğrulama yapılarak)
Eğitilmiş tahmin modeli
        ↓  Uygulama bu modeli kullanarak canlı tahmin üretir
```

---

## 7) Kalite ve güven için yapılanlar

- **Otomatik testler**: Projenin her önemli parçası (veri temizleme, model, CV analizi, şirket analizi, çeviri altyapısı, hatta CV ekranının kendisi) için otomatik testler yazılmış. Yani bir değişiklik yapıldığında, "hâlâ doğru çalışıyor mu?" sorusu makine tarafından otomatik kontrol ediliyor.
- **CI (Sürekli Entegrasyon)**: GitHub'a her kod gönderildiğinde bu testler otomatik olarak çalıştırılıyor — insan unutsa bile testler unutmuyor.
- **Çok dilli arayüz (TR/EN/DE)**: Uygulama menüden Türkçe, İngilizce veya Almanca'ya anında geçebiliyor. Çeviriler Google Translate üzerinden yapılıp diske kaydediliyor (önbelleğe alınıyor); böylece aynı metin ikinci kez görüntülendiğinde tekrar internete çıkılmıyor, anında görünüyor. Bu, yalnızca dil Türkçe değilken devreye giren, internet gerektiren tek özelliktir.
- **Açık/Koyu tema desteği**: Kullanıcı isterse uygulamayı açık, isterse koyu temada kullanabiliyor.
- **Türkçe karakter desteği**: PDF raporlarında "ş, ğ, ı, ö, ü, ç" harfleri düzgün basılıyor (özel bir font gömülü).
- **Renk körlüğüne uygun grafikler**: Grafiklerdeki renkler, renk körü kullanıcılar da ayırt edebilsin diye seçilmiş.

---

## 8) Proje nasıl gelişti? (Kısa hikâye)

Proje, 21 Temmuz 2026 tarihinde, tek geliştirici tarafından adım adım şu şekilde büyütüldü:

1. **Kuruluş** — Projenin tüm iskeleti (kod klasörleri, ilk testler, örnek veri) tek seferde kuruldu.
2. **Belgeler ve otomatik kontrol** — README (tanıtım dosyası) ve GitHub üzerinde otomatik test çalıştırma sistemi eklendi.
3. **Modelin güçlendirilmesi** — Çalışan ayrılma tahmininde kullanılan model, daha basit bir yöntemden (Random Forest) daha güçlü bir yönteme (**LightGBM**) yükseltildi ve en iyi ayarları otomatik bulan bir arama süreci eklendi.
4. **CV analizinin akıllanması** — CV'yi bir iş ilanına göre eşleştirme özelliği eklendi.
5. **İnce bir hata düzeltmesi** — Türkçe'de büyük "İ" harfinin bilgisayarlar tarafından yanlış küçültülmesi yüzünden bazı kelime eşleşmeleri kaçıyordu; bu özel olarak düzeltildi (örn. "İyi" kelimesinin doğru tanınması gibi).
6. **Uçtan uca test** — CV ekranının gerçek bir kullanıcı gibi baştan sona test edilmesini sağlayan bir test paketi eklendi.
7. **Görsel yenilenme** — Grafiklerdeki okunmayan yazı ve üst üste binen etiket sorunları düzeltildi, ardından **açık/koyu tema ve kart bazlı** kapsamlı bir görsel yenileme yapıldı.
8. **Mimari yenilenme (SPA'ya geçiş)** — Uygulama, bugünkü "tek ekran, sol menüden geçiş" yapısına kavuştu; ayrı bir "Tahmin" kısayol ekranı eklendi.
9. **En güncel eklemeler** — CV Analizi'ne **ATS uyumluluğu** ve **tutarsızlık kontrolü**, Şirket Analizi'ne **itibar puanı**, anasayfaya yeni bir tasarım ve genel temaya haki renk getirildi.
10. **Veri içgörüleri ve sadeleşme** (22 Temmuz 2026) — Yüklenen her veri setinde eksik değer, aykırı değer ve veri kalitesi sorunlarını otomatik tespit eden yeni bir modül eklendi; kullanımı azalan ayrı "Tahmin" kısayol ekranı kaldırıldı (işlevi Dataset Analizi altındaki ilgili modüle taşındı).
11. **Çok dilli arayüz** (22-23 Temmuz 2026) — Uygulamaya Türkçe/İngilizce/Almanca dil desteği eklendi. Önce sabit bir çeviri sözlüğüyle başlandı, ardından bunun yerine Google Translate tabanlı, sonuçları önbelleğe alan daha esnek bir çeviri sistemine (`translator.py`) geçildi; bu sırada Şirket Analizi'nin haber kaynakları genişletildi (Bing Haberler, Reddit eklendi) ve Bing'den gelen kaynak isimlerinin/linklerinin doğru ayrıştırılmadığı bir hata giderildi.
12. **CV ve karşılaştırma iyileştirmeleri** (23 Temmuz 2026) — CV Analizi'ne somut iyileştirme önerileri ve yeni bir "Bulut/DevOps" beceri grubu eklendi; Auto Model modülüne confusion matrix/ROC eğrisi grafikleri getirildi; Şirket Analizi'ne "⚖️ Şirket Karşılaştır" bölümü eklendi.
13. **Borsa Analizi ve YZ Karşılaştırma panelleri** (24 Temmuz 2026) — İki yeni ana panel eklendi: **Borsa Analizi** (Yahoo Finance'in anahtarsız veri ucundan hisse/endeks fiyat geçmişi ve teknik gösterge analizi, ayrıca "⚖️ Sembol Karşılaştır" bölümü) ve **YZ Karşılaştırma** (güncel yapay zeka modellerini fiyat/bağlam/benchmark açısından kıyaslama, model başına güncel haber taraması). Bu vesileyle panel metadata'sı (`panel_registry.py`) tek bir merkezi listeye taşındı — yeni bir panel eklerken artık sidebar etiketi ve anasayfa kartı otomatik senkron kalıyor.

Genel yön özetle: *önce sağlam bir temel → sonra modeli güçlendirme → sonra CV tarafını akıllandırma → sonra görselleri güzelleştirme → sonra mimariyi sadeleştirme → sonra ileri düzey analiz özellikleri → sonra çok dilli erişilebilirlik → en son borsa ve yapay zekâ karşılaştırma panelleri.*

---

## 9) Nasıl çalıştırılır?

Teknik bilgisi olan biri için, projeyi ayağa kaldırma adımları:

```bash
# 1. Gerekli kütüphaneleri kur
pip install -r requirements.lock

# 2. Ham İK verisini işleyip Türkçeleştir
python src/data_prep.py

# 3. Çalışan kaybı tahmin modelini eğit (2. adımdan SONRA çalıştırılmalı)
python src/model.py

# 4. Uygulamayı başlat
streamlit run app/Home.py

# (İsteğe bağlı) Otomatik testleri çalıştır
python -m pytest tests/ -v
```

---

## 10) Kullanılan araçlar (kütüphaneler) ne işe yarıyor?

| Araç | Ne işe yarıyor |
|---|---|
| **Streamlit** | Uygulamanın web ekranını (menü, buton, grafik alanları) oluşturur |
| **pandas, numpy** | Veri tablolarını okuma, temizleme, hesaplama |
| **scikit-learn** | Model eğitimi altyapısı ve doğrulama araçları |
| **LightGBM** | Çalışan ayrılma tahmininde kullanılan gerçek öğrenen model |
| **SHAP** | Modelin "neden bu tahmini verdiğini" açıklayan yöntem |
| **Plotly** | Tüm interaktif grafikler |
| **pdfplumber, python-docx** | PDF ve Word formatındaki CV'lerden metin çıkarma |
| **openpyxl** | Excel dosyalarını okuma |
| **fpdf2** | Türkçe karakter destekli PDF rapor üretimi |
| **requests, BeautifulSoup4** | Şirket analizinde internetten haber/yorum toplama |
| **deep-translator** | Arayüzü Türkçe dışındaki dillere (EN/DE) çevirir (Google Translate üzerinden) |
| **pytest** | Otomatik testlerin çalıştırılması |

---

## Sonuç

Bu proje, dış AI servislerine bağlı kalmadan; veri, özgeçmiş, şirket itibarı, borsa fiyat hareketleri ve yapay zekâ modeli karşılaştırmasını tek bir Türkçe arayüzde birleştiren, test edilmiş ve düzenli olarak geliştirilen bir araç hâline geldi. Her panelin çıktısı istenirse CSV, JSON veya PDF olarak dışa aktarılabiliyor.
