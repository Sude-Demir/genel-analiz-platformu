"""Şirket Analizi paneli — şirket adı ile web/sosyal medya taraması, duygu analizi ve konu çıkarımı."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from company_analysis import build_dataframe, extract_topics, reputation_score, sentiment_timeline
from export_utils import build_pdf, to_json_bytes
from theme import CATEGORICAL, MUTED, STATUS, apply_layout

CACHE_TTL_SECONDS = 1800  # aynı şirket adı için tekrar tıklamada yeniden taramayı önler
ORNEK_SIRKET = "Turkcell"


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _cached_scan(company: str):
    df, warnings = build_dataframe(company)
    topics = extract_topics((df["başlık"] + " " + df["özet"]).tolist(), company) if not df.empty else []
    return df, topics, warnings


def render():
    st.subheader("Şirket Adı ile Web / Sosyal Medya Analizi")
    st.caption(
        "Google Haberler ve genel web araması üzerinden şirketle ilgili haber/yorum/gönderi başlıklarını tarar, "
        "sözlük tabanlı duygu analizi yapar ve öne çıkan konuları çıkarır. İnternet bağlantısı gerektirir."
    )

    c1, c2 = st.columns([3, 1])
    with c1:
        company = st.text_input("Şirket Adı", placeholder="Örn: Turkcell", key="company_name_input")
    with c2:
        st.write("")
        st.write("")
        ornek_clicked = st.button("🔎 Örnek Dene", key="company_example_btn", width="stretch")
    analyze_clicked = st.button("Analiz Et", type="primary", disabled=not company.strip(), key="company_analyze_btn")

    if ornek_clicked:
        company = ORNEK_SIRKET

    if (analyze_clicked and company.strip()) or ornek_clicked:
        target = company.strip() or ORNEK_SIRKET
        with st.spinner(f"'{target}' için web ve haber kaynakları taranıyor..."):
            df, topics, warnings = _cached_scan(target)
        st.session_state["company_name"] = target
        st.session_state["company_df"] = df
        st.session_state["company_topics"] = topics
        st.session_state["company_warnings"] = warnings

    if "company_df" not in st.session_state:
        st.info("Analiz başlatmak için bir şirket adı girip 'Analiz Et' butonuna tıklayın veya 'Örnek Dene' ile hemen deneyin.")
        return

    company_name = st.session_state["company_name"]
    df = st.session_state["company_df"]
    topics = st.session_state["company_topics"]
    warnings = st.session_state["company_warnings"]

    if df.empty:
        st.warning(f"'{company_name}' için hiçbir kaynak bulunamadı. Şirket adını farklı yazarak tekrar deneyin.")
        return

    st.success(f"'{company_name}' için {len(df)} kaynak bulundu.")

    score, status = reputation_score(df)

    with st.container(border=True):
        counts = df["duygu"].value_counts()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Toplam Kaynak", len(df))
        c2.metric("Pozitif", int(counts.get("Pozitif", 0)))
        c3.metric("Nötr", int(counts.get("Nötr", 0)))
        c4.metric("Negatif", int(counts.get("Negatif", 0)))

        st.markdown("**İtibar Puanı**")
        fig_score = go.Figure(go.Indicator(
            mode="gauge+number", value=score,
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": STATUS[status]}},
        ))
        apply_layout(fig_score, height=220)
        st.plotly_chart(fig_score, width="stretch", theme=None)

        left, right = st.columns(2)
        with left:
            st.markdown("**Duygu Dağılımı**")
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
            st.markdown("**Öne Çıkan Konular**")
            if topics:
                topic_df = pd.DataFrame(topics, columns=["Konu", "Frekans"]).sort_values("Frekans")
                fig = px.bar(topic_df, x="Frekans", y="Konu", orientation="h", color_discrete_sequence=[CATEGORICAL[4]])
                apply_layout(fig, showlegend=False)
                st.plotly_chart(fig, width="stretch", theme=None)
            else:
                st.info("Öne çıkan konu tespit edilemedi.")

    timeline = sentiment_timeline(df)
    if not timeline.empty:
        st.markdown("### 📈 Zaman İçinde İtibar Trendi")
        with st.container(border=True):
            sentiment_colors = {"Pozitif": STATUS["good"], "Nötr": MUTED, "Negatif": STATUS["critical"]}
            fig_trend = px.bar(
                timeline, x="tarih", y="adet", color="duygu",
                color_discrete_map=sentiment_colors,
                labels={"tarih": "Tarih", "adet": "Kaynak Sayısı", "duygu": "Duygu"},
            )
            apply_layout(fig_trend, barmode="stack")
            st.plotly_chart(fig_trend, width="stretch", theme=None)
            st.caption("Yalnızca tarih bilgisi taşıyan (esas olarak Google Haberler) kaynaklar bu grafiğe dahildir.")

    st.markdown("### Kaynaklar")
    st.dataframe(
        df[["duygu", "başlık", "kaynak", "tür", "tarih", "link"]],
        width="stretch", hide_index=True,
        column_config={"link": st.column_config.LinkColumn("Kaynak Linki", display_text="Aç")},
    )

    if warnings:
        with st.expander("Tarama Uyarıları"):
            for w in warnings:
                st.caption(f"⚠️ {w}")

    st.markdown("### Dışa Aktar")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "Kaynak Listesini CSV indir", data=df.to_csv(index=False).encode("utf-8"),
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
            "JSON indir", data=to_json_bytes(json_payload),
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
            "PDF indir", data=pdf_bytes,
            file_name=f"{company_name}_analiz.pdf", mime="application/pdf", key="company_pdf",
        )

    st.caption(
        "Not: Duygu analizi sözlük tabanlı sezgisel bir yöntemle hesaplanmıştır; "
        "nihai yorum için kaynakların incelenmesi önerilir."
    )
