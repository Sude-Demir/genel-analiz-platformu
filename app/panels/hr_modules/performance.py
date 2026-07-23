"""Performans Analizi alt modülü."""
import pandas as pd
import plotly.express as px
import streamlit as st

from export_utils import build_pdf, to_json_bytes
from translator import tr
from theme import CATEGORICAL, SEQUENTIAL_BLUE, apply_layout


def render(emp: pd.DataFrame):
    tumu = tr("Tümü")
    departmanlar = [tumu] + sorted(emp["Departman"].unique().tolist())
    secilen_departman = st.selectbox(tr("Departman Filtrele"), departmanlar, key="perf_dept")
    df = emp if secilen_departman == tumu else emp[emp["Departman"] == secilen_departman]

    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        col1.metric(tr("Ortalama Performans Puanı"), f"{df['PerformansPuani'].mean():.2f} / 4")
        col2.metric(tr("Yüksek Performanslı Oranı (Puan≥4)"), f"%{(df['PerformansPuani'] >= 4).mean() * 100:.1f}")
        col3.metric(tr("Ortalama Eğitim Sayısı (Yıllık)"), f"{df['GecenYilEgitimSayisi'].mean():.1f}")

    ort_perf_col = tr("Ortalama Performans")
    calisan_col = tr("Çalışan Sayısı")

    with st.container(border=True):
        left, right = st.columns(2)

        with left:
            st.subheader(tr("Performans Puanı Dağılımı"))
            counts = df["PerformansPuani"].value_counts().sort_index()
            ramp = [SEQUENTIAL_BLUE[i] for i in [1, 3, 5, 6]][: len(counts)]
            fig = px.bar(
                x=counts.index.astype(str), y=counts.values,
                labels={"x": tr("Performans Puanı"), "y": calisan_col},
                color=counts.index.astype(str), color_discrete_sequence=ramp,
            )
            apply_layout(fig, showlegend=False)
            st.plotly_chart(fig, width="stretch", theme=None)

        with right:
            st.subheader(tr("Departmana Göre Ortalama Performans"))
            dept_perf = emp.groupby("Departman")["PerformansPuani"].mean().reset_index()
            dept_perf.columns = ["Departman", ort_perf_col]
            dept_perf = dept_perf.sort_values(ort_perf_col)
            fig = px.bar(
                dept_perf, x=ort_perf_col, y="Departman", orientation="h",
                color_discrete_sequence=[CATEGORICAL[0]],
            )
            apply_layout(fig, showlegend=False)
            st.plotly_chart(fig, width="stretch", theme=None)

    with st.container(border=True):
        st.subheader(tr("İş Tatmini ile Performans İlişkisi"))
        scatter_df = df.groupby(["IsTatmini", "PerformansPuani"]).size().reset_index(name=calisan_col)
        fig = px.scatter(
            scatter_df, x="IsTatmini", y="PerformansPuani", size=calisan_col,
            labels={"IsTatmini": tr("İş Tatmini (1-4)"), "PerformansPuani": tr("Performans Puanı (1-4)")},
            color_discrete_sequence=[CATEGORICAL[0]],
        )
        fig.update_xaxes(dtick=1, range=[0.5, 4.5])
        fig.update_yaxes(dtick=1, range=[0.5, 4.5])
        apply_layout(fig, showlegend=False)
        st.plotly_chart(fig, width="stretch", theme=None)

    with st.container(border=True):
        st.subheader(tr("Pozisyona Göre Ortalama Performans (En İyi 10)"))
        role_perf = (
            df.groupby("Pozisyon")
            .agg(**{ort_perf_col: ("PerformansPuani", "mean"), calisan_col: ("CalisanID", "count")})
            .reset_index()
        )
        role_perf = role_perf[role_perf[calisan_col] >= 3].sort_values(ort_perf_col, ascending=False).head(10)
        fig = px.bar(
            role_perf.sort_values(ort_perf_col), x=ort_perf_col, y="Pozisyon", orientation="h",
            labels={ort_perf_col: tr("Ortalama Performans"), "Pozisyon": ""},
            color_discrete_sequence=[CATEGORICAL[4]],
        )
        apply_layout(fig, showlegend=False)
        st.plotly_chart(fig, width="stretch", theme=None)

    st.markdown(tr("### Dışa Aktar"))
    summary = {
        "departman_filtresi": secilen_departman,
        "ortalama_performans": float(df["PerformansPuani"].mean()),
        "yuksek_performansli_orani": float((df["PerformansPuani"] >= 4).mean()),
        "ortalama_egitim_sayisi": float(df["GecenYilEgitimSayisi"].mean()),
        "pozisyona_gore_en_iyi_10": role_perf.to_dict(orient="records"),
    }
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            tr("Pozisyon Tablosunu CSV indir"),
            data=role_perf[["Pozisyon", ort_perf_col, calisan_col]].to_csv(index=False).encode("utf-8"),
            file_name="performans_pozisyon_tablosu.csv", mime="text/csv", key="perf_csv",
        )
    with c2:
        st.download_button(
            tr("JSON indir"), data=to_json_bytes(summary),
            file_name="performans_analizi.json", mime="application/json", key="perf_json",
        )
    with c3:
        pdf_bytes = build_pdf(tr("Performans Analizi Raporu"), [
            {"heading": tr("Özet"), "type": "bullets", "content": [
                tr(f"Departman filtresi: {secilen_departman}"),
                tr(f"Ortalama performans puanı: {df['PerformansPuani'].mean():.2f} / 4"),
                tr(f"Yüksek performanslı oranı: %{(df['PerformansPuani'] >= 4).mean() * 100:.1f}"),
                tr(f"Ortalama yıllık eğitim sayısı: {df['GecenYilEgitimSayisi'].mean():.1f}"),
            ]},
            {"heading": tr("Pozisyona Göre En İyi 10"), "type": "table", "content": (
                ["Pozisyon", ort_perf_col, calisan_col],
                role_perf[["Pozisyon", ort_perf_col, calisan_col]].round(2).values.tolist(),
            )},
        ])
        st.download_button(
            tr("PDF indir"), data=pdf_bytes,
            file_name="performans_analizi.pdf", mime="application/pdf", key="perf_pdf",
        )
