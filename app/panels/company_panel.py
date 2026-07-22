"""Şirket Analizi paneli — şirket adı ile web/sosyal medya taraması, duygu analizi ve konu çıkarımı."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from company_analysis import build_dataframe, extract_topics, reputation_score, sentiment_timeline
from export_utils import build_pdf, to_json_bytes
from i18n import t
from theme import CATEGORICAL, MUTED, STATUS, apply_layout

CACHE_TTL_SECONDS = 1800  # aynı şirket adı için tekrar tıklamada yeniden taramayı önler
ORNEK_SIRKET = "Turkcell"


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _cached_scan(company: str):
    df, warnings = build_dataframe(company)
    topics = extract_topics((df["başlık"] + " " + df["özet"]).tolist(), company) if not df.empty else []
    return df, topics, warnings


def render():
    st.subheader(t("company_baslik"))
    st.caption(t("company_caption"))

    c1, c2 = st.columns([3, 1])
    with c1:
        company = st.text_input(t("company_sirket_adi"), placeholder=t("company_placeholder"), key="company_name_input")
    with c2:
        st.write("")
        st.write("")
        ornek_clicked = st.button(t("ornek_dene"), key="company_example_btn", width="stretch")
    analyze_clicked = st.button(t("analiz_et"), type="primary", disabled=not company.strip(), key="company_analyze_btn")

    if ornek_clicked:
        company = ORNEK_SIRKET

    if (analyze_clicked and company.strip()) or ornek_clicked:
        target = company.strip() or ORNEK_SIRKET
        with st.spinner(t("company_spinner", target=target)):
            df, topics, warnings = _cached_scan(target)
        st.session_state["company_name"] = target
        st.session_state["company_df"] = df
        st.session_state["company_topics"] = topics
        st.session_state["company_warnings"] = warnings

    if "company_df" not in st.session_state:
        st.info(t("company_info"))
        return

    company_name = st.session_state["company_name"]
    df = st.session_state["company_df"]
    topics = st.session_state["company_topics"]
    warnings = st.session_state["company_warnings"]

    if df.empty:
        st.warning(t("company_bos_uyari", name=company_name))
        return

    st.success(t("company_bulundu", name=company_name, n=len(df)))

    score, status = reputation_score(df)

    with st.container(border=True):
        counts = df["duygu"].value_counts()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t("company_toplam_kaynak"), len(df))
        c2.metric(t("company_pozitif"), int(counts.get("Pozitif", 0)))
        c3.metric(t("company_notr"), int(counts.get("Nötr", 0)))
        c4.metric(t("company_negatif"), int(counts.get("Negatif", 0)))

        st.markdown(t("company_itibar_puani"))
        fig_score = go.Figure(go.Indicator(
            mode="gauge+number", value=score,
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": STATUS[status]}},
        ))
        apply_layout(fig_score, height=220)
        st.plotly_chart(fig_score, width="stretch", theme=None)

        left, right = st.columns(2)
        with left:
            st.markdown(t("company_duygu_dagilim"))
            sentiment_colors = {"Pozitif": STATUS["good"], "Nötr": MUTED, "Negatif": STATUS["critical"]}
            order = [s for s in ["Pozitif", "Nötr", "Negatif"] if s in counts.index]
            fig = px.bar(
                x=order, y=[counts[s] for s in order],
                color=order, color_discrete_map=sentiment_colors,
                labels={"x": "Duygu", "y": "Kaynak Sayısı"},
            )
            apply_layout(fig, showlegend=False)
            st.plotly_chart(fig, width="stretch", theme=None)
        with right:
            st.markdown(t("company_one_cikan_konular"))
            if topics:
                topic_df = pd.DataFrame(topics, columns=["Konu", "Frekans"]).sort_values("Frekans")
                fig = px.bar(topic_df, x="Frekans", y="Konu", orientation="h", color_discrete_sequence=[CATEGORICAL[4]])
                apply_layout(fig, showlegend=False)
                st.plotly_chart(fig, width="stretch", theme=None)
            else:
                st.info(t("company_konu_yok"))

    timeline = sentiment_timeline(df)
    if not timeline.empty:
        st.markdown(t("company_trend_baslik"))
        with st.container(border=True):
            sentiment_colors = {"Pozitif": STATUS["good"], "Nötr": MUTED, "Negatif": STATUS["critical"]}
            fig_trend = px.bar(
                timeline, x="tarih", y="adet", color="duygu",
                color_discrete_map=sentiment_colors,
                labels={"tarih": "Tarih", "adet": "Kaynak Sayısı", "duygu": "Duygu"},
            )
            apply_layout(fig_trend, barmode="stack")
            st.plotly_chart(fig_trend, width="stretch", theme=None)
            st.caption(t("company_trend_caption"))

    st.markdown(t("company_kaynaklar"))
    st.dataframe(
        df[["duygu", "başlık", "kaynak", "tür", "tarih", "link"]],
        width="stretch", hide_index=True,
        column_config={"link": st.column_config.LinkColumn("Kaynak Linki", display_text="Aç")},
    )

    if warnings:
        with st.expander(t("company_tarama_uyarilari")):
            for w in warnings:
                st.caption(f"⚠️ {w}")

    st.markdown(t("dis_aktar"))
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            t("company_kaynak_csv"), data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"{company_name}_kaynaklar.csv", mime="text/csv", key="company_csv",
        )
    with c2:
        json_payload = {
            "sirket": company_name,
            "toplam_kaynak": len(df),
            "itibar_puani": score,
            "duygu_dagilimi": {k: int(v) for k, v in counts.to_dict().items()},
            "one_cikan_konular": topics,
            "kaynaklar": df.to_dict(orient="records"),
            "uyarilar": warnings,
        }
        st.download_button(
            t("json_indir"), data=to_json_bytes(json_payload),
            file_name=f"{company_name}_analiz.json", mime="application/json", key="company_json",
        )
    with c3:
        blocks = [
            {"heading": "Genel Özet", "type": "bullets", "content": [
                f"Toplam taranan kaynak: {len(df)}",
                f"İtibar Puanı: {score}/100",
                f"Pozitif: {int(counts.get('Pozitif', 0))}",
                f"Nötr: {int(counts.get('Nötr', 0))}",
                f"Negatif: {int(counts.get('Negatif', 0))}",
            ]},
            {"heading": "Öne Çıkan Konular", "type": "bullets", "content": [f"{w} ({c})" for w, c in topics] or ["—"]},
            {"heading": "Kaynaklar", "type": "table", "content": (
                ["Duygu", "Başlık", "Kaynak", "Link"],
                df[["duygu", "başlık", "kaynak", "link"]].astype(str).values.tolist()[:40],
            )},
        ]
        if warnings:
            blocks.append({"heading": "Tarama Uyarıları", "type": "bullets", "content": warnings})
        pdf_bytes = build_pdf(f"Şirket Analiz Raporu — {company_name}", blocks)
        st.download_button(
            t("pdf_indir"), data=pdf_bytes,
            file_name=f"{company_name}_analiz.pdf", mime="application/pdf", key="company_pdf",
        )

    st.caption(t("company_not"))
