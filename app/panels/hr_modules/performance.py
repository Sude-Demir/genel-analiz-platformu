"""Performans Analizi alt modülü."""
import pandas as pd
import plotly.express as px
import streamlit as st

from export_utils import build_pdf, to_json_bytes
from i18n import t
from theme import CATEGORICAL, SEQUENTIAL_BLUE, apply_layout


def render(emp: pd.DataFrame):
    all_label = t("perf_tumü")
    departmanlar = [all_label] + sorted(emp["Departman"].unique().tolist())
    secilen_departman = st.selectbox(t("perf_dept_filtre"), departmanlar, key="perf_dept")
    df = emp if secilen_departman == all_label else emp[emp["Departman"] == secilen_departman]

    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        col1.metric(t("perf_ort_puan"), f"{df['PerformansPuani'].mean():.2f} / 4")
        col2.metric(t("perf_yuksek_oran"), f"%{(df['PerformansPuani'] >= 4).mean() * 100:.1f}")
        col3.metric(t("perf_ort_egitim"), f"{df['GecenYilEgitimSayisi'].mean():.1f}")

    with st.container(border=True):
        left, right = st.columns(2)

        with left:
            st.subheader(t("perf_dagilim"))
            counts = df["PerformansPuani"].value_counts().sort_index()
            ramp = [SEQUENTIAL_BLUE[i] for i in [1, 3, 5, 6]][: len(counts)]
            fig = px.bar(
                x=counts.index.astype(str), y=counts.values,
                labels={"x": "Performans Puanı", "y": "Çalışan Sayısı"},
                color=counts.index.astype(str), color_discrete_sequence=ramp,
            )
            apply_layout(fig, showlegend=False)
            st.plotly_chart(fig, width="stretch", theme=None)

        with right:
            st.subheader(t("perf_dept_ort"))
            dept_perf = emp.groupby("Departman")["PerformansPuani"].mean().reset_index()
            dept_perf.columns = ["Departman", "Ortalama Performans"]
            dept_perf = dept_perf.sort_values("Ortalama Performans")
            fig = px.bar(
                dept_perf, x="Ortalama Performans", y="Departman", orientation="h",
                color_discrete_sequence=[CATEGORICAL[0]],
            )
            fig.update_xaxes(range=[0, 4])
            apply_layout(fig, showlegend=False)
            st.plotly_chart(fig, width="stretch", theme=None)

    with st.container(border=True):
        st.subheader(t("perf_tatmin_iliski"))
        scatter_df = df.groupby(["IsTatmini", "PerformansPuani"]).size().reset_index(name="Çalışan Sayısı")
        fig = px.scatter(
            scatter_df, x="IsTatmini", y="PerformansPuani", size="Çalışan Sayısı",
            labels={"IsTatmini": "İş Tatmini (1-4)", "PerformansPuani": "Performans Puanı (1-4)"},
            color_discrete_sequence=[CATEGORICAL[0]],
        )
        fig.update_xaxes(dtick=1, range=[0.5, 4.5])
        fig.update_yaxes(dtick=1, range=[0.5, 4.5])
        apply_layout(fig, showlegend=False)
        st.plotly_chart(fig, width="stretch", theme=None)

    with st.container(border=True):
        st.subheader(t("perf_pozisyon_en_iyi"))
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
        st.plotly_chart(fig, width="stretch", theme=None)

    st.markdown(t("dis_aktar"))
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
            t("perf_csv"),
            data=role_perf[["Pozisyon", "OrtalamaPerformans", "CalisanSayisi"]].to_csv(index=False).encode("utf-8"),
            file_name="performans_pozisyon_tablosu.csv", mime="text/csv", key="perf_csv",
        )
    with c2:
        st.download_button(
            t("json_indir"), data=to_json_bytes(summary),
            file_name="performans_analizi.json", mime="application/json", key="perf_json",
        )
    with c3:
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
            t("pdf_indir"), data=pdf_bytes,
            file_name="performans_analizi.pdf", mime="application/pdf", key="perf_pdf",
        )
