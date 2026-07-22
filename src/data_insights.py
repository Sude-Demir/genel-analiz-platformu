"""Herhangi bir veri seti için otomatik veri kalitesi kontrolü, aykırı değer
tespiti ve metinsel (Türkçe) içgörü üretimi.

`auto_model.py`'daki kolon tipi algılamasını (`infer_column_types`) yeniden
kullanır; framework'ten (Streamlit) bağımsızdır, tek başına da çalıştırılabilir.
Tüm sonuçlar kural/istatistik tabanlıdır, harici bir servise bağımlı değildir.
"""
import pandas as pd

from auto_model import infer_column_types

HIGH_MISSING_THRESHOLD = 0.3  # bu oranın üzerinde eksik veri içeren kolonlar uyarılır
HIGH_CARDINALITY_RATIO = 0.9  # benzersiz değer / satır oranı bu eşiği aşarsa "yüksek kardinalite"
HIGH_CARDINALITY_MIN_ROWS = 20  # küçük veri setlerinde yanlış alarmı önlemek için minimum satır sayısı
IMBALANCE_RATIO_THRESHOLD = 0.9  # bir kategorinin toplam içindeki payı bu eşiği aşarsa "dengesiz"
SKEW_THRESHOLD = 1.0  # |çarpıklık| bu eşiği aşarsa "çarpık dağılım" olarak raporlanır
IQR_MULTIPLIER = 1.5


def data_quality_report(df: pd.DataFrame) -> dict:
    """Veri setinin genel kalitesine dair kural tabanlı bir özet üretir.

    Döndürülen sözlük: yinelenen satır sayısı, sabit/tek-değerli kolonlar,
    yüksek kardinaliteli kategorik kolonlar ve yüksek oranda eksik veri
    içeren kolonlar.
    """
    numeric_cols, categorical_cols = infer_column_types(df)

    yinelenen_satir = int(df.duplicated().sum())

    sabit_kolonlar = [col for col in df.columns if df[col].nunique(dropna=False) <= 1]

    yuksek_kardinalite = []
    if len(df) >= HIGH_CARDINALITY_MIN_ROWS:
        for col in categorical_cols:
            oran = df[col].nunique(dropna=True) / len(df)
            if oran >= HIGH_CARDINALITY_RATIO:
                yuksek_kardinalite.append(col)

    eksik_oranlari = (df.isna().sum() / len(df)) if len(df) else pd.Series(dtype=float)
    yuksek_eksiklik = {
        col: round(float(oran), 3)
        for col, oran in eksik_oranlari.items()
        if oran >= HIGH_MISSING_THRESHOLD
    }

    return {
        "yinelenen_satir": yinelenen_satir,
        "sabit_kolonlar": sabit_kolonlar,
        "yuksek_kardinaliteli_kolonlar": yuksek_kardinalite,
        "yuksek_eksiklikli_kolonlar": yuksek_eksiklik,
    }


def detect_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Sayısal kolonlarda IQR (çeyrekler arası açıklık) yöntemiyle aykırı değer sayar.

    Her sayısal kolon için Q1 - 1.5*IQR / Q3 + 1.5*IQR sınırlarının dışında
    kalan değerlerin sayısını ve oranını döndürür. Aykırı değeri olmayan
    kolonlar sonuçta yer almaz.
    """
    numeric_cols, _ = infer_column_types(df)
    rows = []
    for col in numeric_cols:
        seri = df[col].dropna()
        if len(seri) < 4:
            continue
        q1, q3 = seri.quantile(0.25), seri.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        alt_sinir = q1 - IQR_MULTIPLIER * iqr
        ust_sinir = q3 + IQR_MULTIPLIER * iqr
        aykiri_sayisi = int(((seri < alt_sinir) | (seri > ust_sinir)).sum())
        if aykiri_sayisi > 0:
            rows.append({
                "Kolon": col,
                "Aykırı Değer Sayısı": aykiri_sayisi,
                "Oran (%)": round(aykiri_sayisi / len(seri) * 100, 1),
                "Alt Sınır": round(float(alt_sinir), 2),
                "Üst Sınır": round(float(ust_sinir), 2),
            })
    return pd.DataFrame(rows).sort_values("Aykırı Değer Sayısı", ascending=False).reset_index(drop=True) if rows else pd.DataFrame(
        columns=["Kolon", "Aykırı Değer Sayısı", "Oran (%)", "Alt Sınır", "Üst Sınır"]
    )


def generate_insights(df: pd.DataFrame) -> list[str]:
    """Veri setine dair kısa, Türkçe, metinsel otomatik içgörüler üretir.

    En güçlü korelasyon çifti, en çarpık sayısal dağılım, en yüksek eksiklik
    oranına sahip kolon ve en dengesiz kategorik kolon gibi bulguları
    okunabilir cümlelere çevirir. Yeterli veri olmayan durumlarda o içgörü
    sessizce atlanır (boş liste dönebilir).
    """
    numeric_cols, categorical_cols = infer_column_types(df)
    insights: list[str] = []

    if len(numeric_cols) >= 2 and len(df) >= 3:
        corr = df[numeric_cols].corr().abs()
        best_pair, best_val = None, 0.0
        cols = corr.columns.tolist()
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                val = corr.iloc[i, j]
                if pd.notna(val) and val > best_val:
                    best_val = val
                    best_pair = (cols[i], cols[j])
        if best_pair and best_val >= 0.5:
            yon = "pozitif" if df[best_pair[0]].corr(df[best_pair[1]]) > 0 else "negatif"
            insights.append(
                f"{best_pair[0]} ile {best_pair[1]} arasında güçlü bir {yon} ilişki var "
                f"(korelasyon: {round(df[best_pair[0]].corr(df[best_pair[1]]), 2)})."
            )

    if numeric_cols and len(df) >= 5:
        skew = df[numeric_cols].skew(numeric_only=True).dropna()
        skew = skew[skew.abs() >= SKEW_THRESHOLD]
        if not skew.empty:
            en_carpik = skew.abs().idxmax()
            yon = "sağa" if skew[en_carpik] > 0 else "sola"
            insights.append(
                f"{en_carpik} kolonu belirgin şekilde {yon} çarpık dağılıyor; "
                "ortalama yerine medyan ile yorumlamak daha güvenilir olabilir."
            )

    missing = df.isna().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        en_eksik = missing.idxmax()
        oran = round(missing[en_eksik] / len(df) * 100, 1)
        insights.append(f"{en_eksik} kolonunda verinin %{oran}'i eksik; bu kolona dayalı analizlerde dikkatli olun.")

    if categorical_cols and len(df) > 0:
        best_col, best_ratio, best_val = None, 0.0, None
        for col in categorical_cols:
            counts = df[col].value_counts(normalize=True, dropna=True)
            if counts.empty:
                continue
            top_ratio = counts.iloc[0]
            if top_ratio > best_ratio:
                best_ratio, best_col, best_val = top_ratio, col, counts.index[0]
        if best_col and best_ratio >= IMBALANCE_RATIO_THRESHOLD:
            insights.append(
                f"{best_col} kolonunun %{round(best_ratio * 100, 1)}'i tek bir değere "
                f"(\"{best_val}\") ait; bu kolon dengesiz dağılıyor."
            )

    dup = int(df.duplicated().sum())
    if dup > 0:
        insights.append(f"Veri setinde {dup} adet birebir yinelenen satır tespit edildi.")

    return insights
