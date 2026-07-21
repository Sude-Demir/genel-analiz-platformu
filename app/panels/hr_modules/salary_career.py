"""Maaş ve Kariyer Analizi alt modülü."""
import pandas as pd
import plotly.express as px
import streamlit as st

from export_utils import build_pdf, to_json_bytes
from theme import CATEGORICAL, SEQUENTIAL_BLUE, apply_layout


def render(emp: pd.DataFrame):
    col1, col2, col3 = st.columns(3)
    col1.metric("Ortalama Aylık Gelir", f"{emp['AylikGelir'].mean():,.0f} $")
    col2.metric("Ortalama Maaş Artış Oranı", f"%{emp['MaasArtisYuzdesi'].mean():.1f}")
    col3.metric("Son Terfiden Beri Ortalama Yıl", f"{emp['SonTerfidenBeriGecenYil'].mean():.1f}")

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Departmana Göre Aylık Gelir Dağılımı")
        fig = px.box(
            emp, x="Departman", y="AylikGelir",
            labels={"AylikGelir": "Aylık Gelir ($)"},
            color="Departman", color_discrete_sequence=CATEGORICAL,
        )
        apply_layout(fig, showlegend=False)
        st.plotly_chart(fig, width="stretch", theme=None)

    with right:
        st.subheader("Kademeye Göre Aylık Gelir Dağılımı")
        fig = px.box(
            emp.sort_values("IsSeviyesi"), x="IsSeviyesi", y="AylikGelir",
            labels={"IsSeviyesi": "Kademe", "AylikGelir": "Aylık Gelir ($)"},
            color="IsSeviyesi", color_discrete_sequence=SEQUENTIAL_BLUE,
        )
        fig.update_xaxes(dtick=1)
        apply_layout(fig, showlegend=False)
        st.plotly_chart(fig, width="stretch", theme=None)

    st.divider()
    left2, right2 = st.columns(2)

    with left2:
        st.subheader("Kıdem ile Aylık Gelir İlişkisi")
        fig = px.scatter(
            emp, x="SirketteKidemYili", y="AylikGelir", color="Departman",
            labels={"SirketteKidemYili": "Şirkette Kıdem (Yıl)", "AylikGelir": "Aylık Gelir ($)"},
            color_discrete_sequence=CATEGORICAL, opacity=0.7,
        )
        apply_layout(fig)
        st.plotly_chart(fig, width="stretch", theme=None)

    with right2:
        st.subheader("Son Terfiden Beri Geçen Yıl Dağılımı")
        fig = px.histogram(
            emp, x="SonTerfidenBeriGecenYil",
            labels={"SonTerfidenBeriGecenYil": "Son Terfiden Beri Geçen Yıl"},
            color_discrete_sequence=[CATEGORICAL[5]],
        )
        fig.update_yaxes(title="Çalışan Sayısı")
        apply_layout(fig, showlegend=False)
        st.plotly_chart(fig, width="stretch", theme=None)

    st.divider()
    st.subheader("Kademeye Göre Ortalama Hisse Opsiyonu Seviyesi")
    level_stock = emp.groupby("IsSeviyesi")["HisseOpsiyonSeviyesi"].mean().reset_index()
    level_stock.columns = ["Kademe", "Ortalama Hisse Opsiyonu Seviyesi"]
    fig = px.bar(
        level_stock, x="Kademe", y="Ortalama Hisse Opsiyonu Seviyesi",
        color_discrete_sequence=[CATEGORICAL[0]],
    )
    fig.update_xaxes(dtick=1)
    apply_layout(fig, showlegend=False)
    st.plotly_chart(fig, width="stretch", theme=None)

    st.markdown("### Dışa Aktar")
    summary = {
        "ortalama_aylik_gelir": float(emp["AylikGelir"].mean()),
        "ortalama_maas_artis_yuzdesi": float(emp["MaasArtisYuzdesi"].mean()),
        "son_terfiden_beri_ortalama_yil": float(emp["SonTerfidenBeriGecenYil"].mean()),
        "kademeye_gore_hisse_opsiyonu": level_stock.to_dict(orient="records"),
    }
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "JSON indir", data=to_json_bytes(summary),
            file_name="maas_kariyer_analizi.json", mime="application/json", key="salary_json",
        )
    with c2:
        pdf_bytes = build_pdf("Maaş ve Kariyer Analizi Raporu", [
            {"heading": "Özet", "type": "bullets", "content": [
                f"Ortalama aylık gelir: {emp['AylikGelir'].mean():,.0f} $",
                f"Ortalama maaş artış oranı: %{emp['MaasArtisYuzdesi'].mean():.1f}",
                f"Son terfiden beri ortalama yıl: {emp['SonTerfidenBeriGecenYil'].mean():.1f}",
            ]},
            {"heading": "Kademeye Göre Ortalama Hisse Opsiyonu", "type": "table", "content": (
                ["Kademe", "Ort. Hisse Opsiyonu"], level_stock.round(2).values.tolist(),
            )},
        ])
        st.download_button(
            "PDF indir", data=pdf_bytes,
            file_name="maas_kariyer_analizi.pdf", mime="application/pdf", key="salary_pdf",
        )
