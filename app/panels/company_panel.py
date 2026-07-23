"""Şirket Analizi paneli."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from company_analysis import build_dataframe, extract_topics, reputation_score, segment_outlook, sentiment_timeline
from export_utils import build_pdf, to_json_bytes
from translator import tr
from theme import CATEGORICAL, MUTED, STATUS, apply_layout

CACHE_TTL_SECONDS = 1800
ORNEK_SIRKET = "Turkcell"


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _cached_scan(company: str):
    df, warnings = build_dataframe(company)
    topics = extract_topics((df["başlık"] + " " + df["özet"]).tolist(), company) if not df.empty else []
    outlooks = segment_outlook(df, company)
    return df, topics, warnings, outlooks


def render():
    st.subheader(tr("Şirket Adı ile Web / Sosyal Medya Analizi"))
    st.caption(tr(
        "Google/Bing Haberler, Reddit ve genel web araması üzerinden şirketle ilgili "
        "haber/yorum/gönderi başlıklarını tarar, sözlük tabanlı duygu analizi yapar ve öne çıkan "
        "konuları çıkarır. İnternet bağlantısı gerektirir."
    ))

    c1, c2 = st.columns([3, 1])
    with c1:
        company = st.text_input(tr("Şirket Adı"), placeholder=tr("Örn: Turkcell"), key="company_name_input")
    with c2:
        st.write("")
        st.write("")
        ornek_clicked = st.button(tr("🔎 Örnek Dene"), key="company_example_btn", use_container_width=True)
    analyze_clicked = st.button(tr("Analiz Et"), type="primary", disabled=not company.strip(), key="company_analyze_btn")

    if ornek_clicked:
        company = ORNEK_SIRKET

    if (analyze_clicked and company.strip()) or ornek_clicked:
        target = company.strip() or ORNEK_SIRKET
        with st.spinner(tr(f"'{target}' için web ve haber kaynakları taranıyor...")):
            df, topics, warnings, outlooks = _cached_scan(target)
        st.session_state["company_name"] = target
        st.session_state["company_df"] = df
        st.session_state["company_topics"] = topics
        st.session_state["company_warnings"] = warnings
        st.session_state["company_outlooks"] = outlooks

    if "company_df" not in st.session_state:
        st.info(tr("Analiz başlatmak için bir şirket adı girip 'Analiz Et' butonuna tıklayın veya 'Örnek Dene' ile hemen deneyin."))
        return

    company_name = st.session_state["company_name"]
    df = st.session_state["company_df"]
    topics = st.session_state["company_topics"]
    warnings = st.session_state["company_warnings"]
    outlooks = st.session_state["company_outlooks"]

    if df.empty:
        st.warning(tr(f"'{company_name}' için hiçbir kaynak bulunamadı. Şirket adını farklı yazarak tekrar deneyin."))
        return

    st.success(tr(f"'{company_name}' için {len(df)} kaynak bulundu."))

    score, status = reputation_score(df)

    with st.container(border=True):
        counts = df["duygu"].value_counts()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(tr("Toplam Kaynak"), len(df))
        c2.metric(tr("Pozitif"), int(counts.get("Pozitif", 0)))
        c3.metric(tr("Nötr"), int(counts.get("Nötr", 0)))
        c4.metric(tr("Negatif"), int(counts.get("Negatif", 0)))

        st.markdown(tr("**İtibar Puanı**"))
        fig_score = go.Figure(go.Indicator(
            mode="gauge+number", value=score,
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": STATUS[status]}},
        ))
        apply_layout(fig_score, height=220)
        st.plotly_chart(fig_score, width="stretch", theme=None)

        left, right = st.columns(2)
        with left:
            st.markdown(tr("**Duygu Dağılımı**"))
            sentiment_colors = {"Pozitif": STATUS["good"], "Nötr": MUTED, "Negatif": STATUS["critical"]}
            order = [s for s in ["Pozitif", "Nötr", "Negatif"] if s in counts.index]
            fig = px.bar(
                x=order, y=[counts[s] for s in order],
                color=order, color_discrete_map=sentiment_colors,
                labels={"x": tr("Duygu"), "y": tr("Kaynak Sayısı")},
            )
            apply_layout(fig, showlegend=False)
            st.plotly_chart(fig, width="stretch", theme=None)
        with right:
            st.markdown(tr("**Öne Çıkan Konular**"))
            if topics:
                topic_col = tr("Frekans")
                topic_df = pd.DataFrame(topics, columns=["Konu", topic_col]).sort_values(topic_col)
                fig = px.bar(topic_df, x=topic_col, y="Konu", orientation="h", color_discrete_sequence=[CATEGORICAL[4]])
                apply_layout(fig, showlegend=False)
                st.plotly_chart(fig, width="stretch", theme=None)
            else:
                st.info(tr("Öne çıkan konu tespit edilemedi."))

    timeline = sentiment_timeline(df)
    if not timeline.empty:
        st.markdown(tr("### 📈 Zaman İçinde İtibar Trendi"))
        with st.container(border=True):
            sentiment_colors = {"Pozitif": STATUS["good"], "Nötr": MUTED, "Negatif": STATUS["critical"]}
            fig_trend = px.bar(
                timeline, x="tarih", y="adet", color="duygu",
                color_discrete_map=sentiment_colors,
                labels={"tarih": tr("Tarih"), "adet": tr("Kaynak Sayısı"), "duygu": tr("Duygu")},
            )
            apply_layout(fig_trend, barmode="stack")
            st.plotly_chart(fig_trend, width="stretch", theme=None)
            st.caption(tr("Yalnızca tarih bilgisi taşıyan kaynaklar (haber siteleri ve Reddit) bu grafiğe dahildir."))

    if outlooks:
        st.markdown(tr("### 🔮 Bölüm Bazlı Sektör Görünümü"))
        st.caption(tr(
            "Toplanan haber/gönderilerin sözlük tabanlı olarak iş kolu/bölümlere ayrıştırılıp her biri için "
            "duygu dağılımı, zaman içindeki eğilim ve öne çıkan konulara dayalı sezgisel bir görünüm üretir. "
            "Bu bir istatistiksel tahmin değil, toplanan örneklemin yorumudur."
        ))
        outlook_status = {"Olumlu": "good", "Riskli": "critical", "Belirsiz / Dengeli": "warning"}
        for o in outlooks:
            status_key = outlook_status.get(o["görünüm"], "warning")
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{tr(o['bölüm'])}**")
                c2.markdown(
                    f"<span style='color:{STATUS[status_key]}; font-weight:600;'>{tr(o['görünüm'])}</span>",
                    unsafe_allow_html=True,
                )
                st.caption(tr(f"{o['kaynak_sayısı']} kaynaktan üretildi."))
                st.write(tr(o["gerekçe"]))

    st.markdown(tr("### Kaynaklar"))
    st.dataframe(
        df[["duygu", "başlık", "kaynak", "tür", "tarih", "link"]],
        width="stretch", hide_index=True,
        column_config={"link": st.column_config.LinkColumn(tr("Kaynak Linki"), display_text=tr("Aç"))},
    )

    if warnings:
        with st.expander(tr("Tarama Uyarıları")):
            for w in warnings:
                st.caption(f"⚠️ {tr(w)}")

    st.markdown(tr("### Dışa Aktar"))
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            tr("Kaynak Listesini CSV indir"), data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"{company_name}_kaynaklar.csv", mime="text/csv", key="company_csv",
        )
    with c2:
        json_payload = {
            "sirket": company_name,
            "toplam_kaynak": len(df),
            "itibar_puani": score,
            "duygu_dagilimi": {k: int(v) for k, v in counts.to_dict().items()},
            "one_cikan_konular": topics,
            "bolum_bazli_gorunum": outlooks,
            "kaynaklar": df.to_dict(orient="records"),
            "uyarilar": warnings,
        }
        st.download_button(
            tr("JSON indir"), data=to_json_bytes(json_payload),
            file_name=f"{company_name}_analiz.json", mime="application/json", key="company_json",
        )
    with c3:
        blocks = [
            {"heading": tr("Genel Özet"), "type": "bullets", "content": [
                tr(f"Toplam taranan kaynak: {len(df)}"),
                tr(f"İtibar Puanı: {score}/100"),
                tr(f"Pozitif: {int(counts.get('Pozitif', 0))}"),
                tr(f"Nötr: {int(counts.get('Nötr', 0))}"),
                tr(f"Negatif: {int(counts.get('Negatif', 0))}"),
            ]},
            {"heading": tr("Öne Çıkan Konular"), "type": "bullets",
             "content": [f"{w} ({c})" for w, c in topics] or ["—"]},
            {"heading": tr("Bölüm Bazlı Sektör Görünümü"), "type": "bullets", "content": (
                [f"{o['bölüm']} — {o['görünüm']}: {o['gerekçe']}" for o in outlooks]
                or [tr("Yeterli veri toplanamadığı için bölüm bazlı görünüm üretilemedi.")]
            )},
            {"heading": tr("Kaynaklar"), "type": "table", "content": (
                [tr("Duygu"), tr("Başlık"), tr("Kaynak"), tr("Link")],
                df[["duygu", "başlık", "kaynak", "link"]].astype(str).values.tolist()[:40],
            )},
        ]
        if warnings:
            blocks.append({"heading": tr("Tarama Uyarıları"), "type": "bullets", "content": warnings})
        pdf_bytes = build_pdf(tr(f"Şirket Analiz Raporu — {company_name}"), blocks)
        st.download_button(
            tr("PDF indir"), data=pdf_bytes,
            file_name=f"{company_name}_analiz.pdf", mime="application/pdf", key="company_pdf",
        )

    st.caption(tr(
        "Not: Duygu analizi sözlük tabanlı sezgisel bir yöntemle hesaplanmıştır; "
        "nihai yorum için kaynakların incelenmesi önerilir."
    ))
