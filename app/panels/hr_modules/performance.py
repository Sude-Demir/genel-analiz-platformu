"""Performans Analizi alt modülü."""
import pandas as pd
import plotly.express as px
import streamlit as st

from export_utils import build_pdf, to_json_bytes
from theme import CATEGORICAL, SEQUENTIAL_BLUE, apply_layout


def render(emp: pd.DataFrame):
    departmanlar = ["Tümü"] + sorted(emp["Departman"].unique().tolist())
    secilen_departman = st.selectbox("Departman Filtrele", departmanlar, key="perf_dept")
    df = emp if secilen_departman == "Tümü" else emp[emp["Departman"] == secilen_departman]

    col1, col2, col3 = st.columns(3)
    col1.metric("Ortalama Performans Puanı", f"{df['PerformansPuani'].mean():.2f} / 4")
    col2.metric("Yüksek Performanslı Oranı (Puan≥4)", f"%{(df['PerformansPuani'] >= 4).mean() * 100:.1f}")
    col3.metric("Ortalama Eğitim Sayısı (Yıllık)", f"{df['GecenYilEgitimSayisi'].mean():.1f}")

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Performans Puanı Dağılımı")
        counts = df["PerformansPuani"].value_counts().sort_index()
        ramp = [SEQUENTIAL_BLUE[i] for i in [1, 3, 5, 6]][: len(counts)]
        fig = px.bar(
            x=counts.index.astype(str), y=counts.values,
            labels={"x": "Performans Puanı", "y": "Çalışan Sayısı"},
            color=counts.index.astype(str), color_discrete_sequence=ramp,
        )
        apply_layout(fig, showlegend=False)
        st.plotly_chart(fig, width="stretch")

    with right:
        st.subheader("Departmana Göre Ortalama Performans")
        dept_perf = emp.groupby("Departman")["PerformansPuani"].mean().reset_index()
        dept_perf.columns = ["Departman", "Ortalama Performans"]
        dept_perf = dept_perf.sort_values("Ortalama Performans")
        fig = px.bar(
            dept_perf, x="Ortalama Performans", y="Departman", orientation="h",
            color_discrete_sequence=[CATEGORICAL[0]],
        )
        fig.update_xaxes(range=[0, 4])
        apply_layout(fig, showlegend=False)
        st.plotly_chart(fig, width="stretch")

    st.divider()
    st.subheader("İş Tatmini ile Performans İlişkisi")
    scatter_df = df.groupby(["IsTatmini", "PerformansPuani"]).size().reset_index(name="Çalışan Sayısı")
    fig = px.scatter(
        scatter_df, x="IsTatmini", y="PerformansPuani", size="Çalışan Sayısı",
        labels={"IsTatmini": "İş Tatmini (1-4)", "PerformansPuani": "Performans Puanı (1-4)"},
        color_discrete_sequence=[CATEGORICAL[0]],
    )
    fig.update_xaxes(dtick=1, range=[0.5, 4.5])
    fig.update_yaxes(dtick=1, range=[0.5, 4.5])
    apply_layout(fig, showlegend=False)
    st.plotly_chart(fig, width="stretch")

    st.divider()
    st.subheader("Pozisyona Göre Ortalama Performans (En İyi 10)")
    role_perf = (
        df.groupby("Pozisyon")
        .agg(OrtalamaPerformans=("PerformansPuani", "mean"), CalisanSayisi=("CalisanID", "count"))
        .reset_index()
    )
    role_perf = role_perf[role_perf["CalisanSayisi"] >= 3].sort_values("OrtalamaPerformans", ascending=False).head(10)
    fig = px.bar(
        role_perf.sort_values("OrtalamaPerformans"), x="OrtalamaPerformans", y="Pozisyon", orientation="h",
        labels={"OrtalamaPerformans": "Ortalama Performans", "Pozisyon": ""},
        color_discrete_sequence=[CATEGORICAL[4]],
    )
    apply_layout(fig, showlegend=False)
    st.plotly_chart(fig, width="stretch")

    st.markdown("### Dışa Aktar")
    summary = {
        "departman_filtresi": secilen_departman,
        "ortalama_performans": float(df["PerformansPuani"].mean()),
        "yuksek_performansli_orani": float((df["PerformansPuani"] >= 4).mean()),
        "ortalama_egitim_sayisi": float(df["GecenYilEgitimSayisi"].mean()),
        "pozisyona_gore_en_iyi_10": role_perf.to_dict(orient="records"),
    }
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "JSON indir", data=to_json_bytes(summary),
            file_name="performans_analizi.json", mime="application/json", key="perf_json",
        )
    with c2:
        pdf_bytes = build_pdf("Performans Analizi Raporu", [
            {"heading": "Özet", "type": "bullets", "content": [
                f"Departman filtresi: {secilen_departman}",
                f"Ortalama performans puanı: {df['PerformansPuani'].mean():.2f} / 4",
                f"Yüksek performanslı oranı: %{(df['PerformansPuani'] >= 4).mean() * 100:.1f}",
                f"Ortalama yıllık eğitim sayısı: {df['GecenYilEgitimSayisi'].mean():.1f}",
            ]},
            {"heading": "Pozisyona Göre En İyi 10", "type": "table", "content": (
                ["Pozisyon", "Ort. Performans", "Çalışan Sayısı"],
                role_perf[["Pozisyon", "OrtalamaPerformans", "CalisanSayisi"]].round(2).values.tolist(),
            )},
        ])
        st.download_button(
            "PDF indir", data=pdf_bytes,
            file_name="performans_analizi.pdf", mime="application/pdf", key="perf_pdf",
        )
