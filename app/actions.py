

"""SHAP katkılarını İK için uygulanabilir aksiyon önerilerine çevirir.

Not: Yaş, cinsiyet, medeni durum, departman gibi değiştirilemez veya
demografik özellikler kasıtlı olarak bu eşlemenin dışında tutulmuştur —
öneriler yalnızca değiştirilebilir, iş ile ilgili faktörlere dayanır.
"""
import pandas as pd

ACTIONABLE_SUGGESTIONS = {
    "FazlaMesai_Evet": "Fazla mesai yükünü azaltmayı değerlendirin.",
    "SeyahatSikligi_Sık Sık": "İş seyahati sıklığını azaltmayı değerlendirin.",
    "IsYasamDengesi": "İş-yaşam dengesini iyileştirecek esnek çalışma seçenekleri sunun.",
    "IsTatmini": "Görev/rol memnuniyetini artıracak bir geri bildirim görüşmesi planlayın.",
    "CalismaOrtamiTatmini": "Çalışma ortamı memnuniyetini artıracak iyileştirmeleri değerlendirin.",
    "IseBagliligi": "Görev sorumluluğunu/özerkliğini artıracak bir rol zenginleştirmesi planlayın.",
    "HisseOpsiyonSeviyesi": "Uzun dönemli teşvik (hisse opsiyonu) paketini gözden geçirin.",
    "SonTerfidenBeriGecenYil": "Kariyer gelişimi/terfi görüşmesi planlayın.",
    "AylikGelir": "Piyasa karşılaştırmalı ücret incelemesi yapın.",
    "MaasArtisYuzdesi": "Bir sonraki ücret artışı planlamasını öne çekmeyi değerlendirin.",
    "EvUzakligiKm": "Uzaktan/hibrit çalışma imkanı değerlendirin.",
    "YoneticiyleGecenYil": "Yönetici ile birebir görüşme sıklığını artırın.",
    "IliskiTatmini": "Takım içi ilişkileri güçlendirecek bir aksiyon planlayın.",
    "GecenYilEgitimSayisi": "Eğitim ve gelişim fırsatlarını artırın.",
}


def suggest_actions(contributions: pd.Series, top_n: int = 3) -> list[str]:
    """Riski artıran (pozitif SHAP) ve aksiyona dönüştürülebilir en önemli faktörler için öneri metinleri üretir."""
    risky = contributions[contributions > 0].sort_values(ascending=False)
    suggestions = []
    for name in risky.index:
        text = ACTIONABLE_SUGGESTIONS.get(name)
        if text and text not in suggestions:
            suggestions.append(text)
        if len(suggestions) >= top_n:
            break
    return suggestions
