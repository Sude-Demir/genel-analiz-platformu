"""Anasayfa dışındaki tüm panellerin ortak metadata kaynağı.

Home.py (sidebar navigasyon etiketleri) ve home_panel.py (anasayfa modül kartları)
bu listeyi paylaşır — yeni bir panel eklerken sadece buraya bir kayıt eklemek yeterli,
sidebar etiketi ve anasayfa kartı otomatik olarak senkronize kalır. `PANELS` sözlüğündeki
render callable eşlemesi (app/Home.py) modül import'u gerektirdiğinden burada tutulmaz.
"""
from theme import CATEGORICAL

PANEL_REGISTRY = [
    {
        "key": "dataset", "icon": "📁",
        "title": "Dataset Analizi",
        "desc": "Herhangi bir veri setini yükleyip genel istatistik, görselleştirme ve İK'ya özgü alt analizler yapar.",
        "color": CATEGORICAL[1],
    },
    {
        "key": "cv", "icon": "📄",
        "title": "CV Analizi",
        "desc": "CV metnini beceri/pozisyon/eğitim sözlükleriyle değerlendirir, ilanla eşleştirme yüzdesi üretir.",
        "color": CATEGORICAL[4],
    },
    {
        "key": "company", "icon": "🌐",
        "title": "Şirket Analizi",
        "desc": "Google/Bing News RSS, Reddit ve DuckDuckGo taramasıyla şirket haberlerinde duygu analizi yapar.",
        "color": CATEGORICAL[5],
    },
    {
        "key": "borsa", "icon": "📈",
        "title": "Borsa Analizi",
        "desc": "Hisse/endeks fiyat geçmişini teknik göstergelerle analiz eder, kısa vadeli görünüm tahmini üretir.",
        "color": CATEGORICAL[0],
    },
    {
        "key": "ai", "icon": "🤖",
        "title": "YZ Karşılaştırma",
        "desc": "Yapay zekâ modellerini fiyatlandırma, bağlam penceresi ve benchmark skorlarına göre karşılaştırır.",
        "color": CATEGORICAL[6],
    },
]
