"""YZ (Yapay Zeka) Karşılaştırma paneli."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ai_comparison import (
    AI_MODELS,
    BENCHMARK_COLUMNS,
    PRICING_REFERENCE_TIMESTAMP,
    SONNET5_PRICE_CHANGE_NOTE,
    build_comparison_table,
    collect_model_news,
    get_model_names,
)
from export_utils import build_pdf, to_json_bytes
from translator import tr, trf
from theme import CATEGORICAL, apply_layout

CACHE_TTL_SECONDS = 1800
_DEFAULT_SELECTION = list(AI_MODELS.keys())[:3]
_BENCHMARK_LABELS = {"mmlu": "MMLU", "humaneval": "HumanEval", "gpqa": "GPQA"}


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _cached_news(model_name: str):
    return collect_model_news(model_name)


def render():
    """Panelin iki bağımsız kısmını sırayla render eder (company_panel.py/borsa_panel.py'deki
    aynı desen): statik referans verisine dayalı karşılaştırma ile ağ isteği gerektiren
    güncel haber taraması ayrı fonksiyonlarda tutulur."""
    _render_compare_section()
    st.divider()
    _render_news_section()


def _render_compare_section():
    st.subheader(tr("Model Karşılaştırma"))
    st.caption(tr(
        "Fiyatlandırma, bağlam penceresi ve benchmark skorları elle küratörlüğü yapılmış "
        "referans verisidir; sağlayıcıların resmi duyurularına dayanır ancak zamanla "
        "eskiyebilir. Kesin/güncel rakamlar için resmi kaynakları kontrol edin."
    ))

    selected = st.multiselect(
        tr("Karşılaştırılacak Modeller"), get_model_names(),
        default=_DEFAULT_SELECTION, key="ai_selected_models",
    )

    if not selected:
        st.info(tr("Karşılaştırmak için en az bir model seçin."))
        return

    table = build_comparison_table(selected)
    colors = {name: CATEGORICAL[i % len(CATEGORICAL)] for i, name in enumerate(selected)}

    with st.container(border=True):
        st.markdown(tr("**Fiyatlandırma (USD / 1M token)**"))
        st.caption(trf(
            "Fiyatlandırma verileri sağlayıcıların resmi fiyatlandırma sayfalarından {tarih} "
            "itibarıyla doğrulanmıştır.", tarih=PRICING_REFERENCE_TIMESTAMP,
        ))
        if "Claude Sonnet 5 (Anthropic)" in selected:
            st.caption(f"ℹ️ {tr(SONNET5_PRICE_CHANGE_NOTE)}")
        price_rows = []
        for _, row in table.iterrows():
            price_rows.append({"Model": row["Model"], "Tür": tr("Giriş"), "Fiyat": row["giriş_fiyat_1m_usd"]})
            price_rows.append({"Model": row["Model"], "Tür": tr("Çıkış"), "Fiyat": row["çıkış_fiyat_1m_usd"]})
        price_df = pd.DataFrame(price_rows)
        fig_price = px.bar(
            price_df, x="Model", y="Fiyat", color="Tür", barmode="group",
            labels={"Fiyat": tr("USD / 1M token")},
        )
        apply_layout(fig_price)
        st.plotly_chart(fig_price, width="stretch", theme=None)

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown(tr("**Bağlam Penceresi (bin token)**"))
            fig_ctx = px.bar(
                table, x="Model", y="bağlam_penceresi_bin_token",
                color="Model", color_discrete_map=colors,
                labels={"bağlam_penceresi_bin_token": tr("Bin Token")},
            )
            apply_layout(fig_ctx, showlegend=False)
            st.plotly_chart(fig_ctx, width="stretch", theme=None)
    with right:
        with st.container(border=True):
            st.markdown(tr("**Benchmark Skorları**"))
            fig_radar = go.Figure()
            for _, row in table.iterrows():
                fig_radar.add_trace(go.Scatterpolar(
                    r=[row[c] for c in BENCHMARK_COLUMNS] + [row[BENCHMARK_COLUMNS[0]]],
                    theta=[_BENCHMARK_LABELS[c] for c in BENCHMARK_COLUMNS] + [_BENCHMARK_LABELS[BENCHMARK_COLUMNS[0]]],
                    name=row["Model"], line=dict(color=colors[row["Model"]]), fill="toself", opacity=0.6,
                ))
            apply_layout(fig_radar, polar=dict(radialaxis=dict(range=[0, 100])))
            st.plotly_chart(fig_radar, width="stretch", theme=None)

    st.markdown(tr("### Özellik Tablosu"))
    display_table = table.rename(columns={
        "sağlayıcı": tr("Sağlayıcı"), "açık_kaynak": tr("Açık Kaynak"), "çoklu_modal": tr("Çoklu-Modal"),
        "bağlam_penceresi_bin_token": tr("Bağlam Penceresi (bin token)"),
        "giriş_fiyat_1m_usd": tr("Giriş Fiyatı (USD/1M)"), "çıkış_fiyat_1m_usd": tr("Çıkış Fiyatı (USD/1M)"),
        "mmlu": "MMLU", "humaneval": "HumanEval", "gpqa": "GPQA",
    })
    st.dataframe(display_table, width="stretch", hide_index=True)

    st.markdown(tr("### Dışa Aktar"))
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            tr("Karşılaştırmayı CSV indir"), data=table.to_csv(index=False).encode("utf-8"),
            file_name="yz_karsilastirma.csv", mime="text/csv", key="ai_csv",
        )
    with c2:
        st.download_button(
            tr("JSON indir"), data=to_json_bytes({"karsilastirma": table.to_dict(orient="records")}),
            file_name="yz_karsilastirma.json", mime="application/json", key="ai_json",
        )
    with c3:
        blocks = [
            {"heading": tr("Özellik ve Benchmark Karşılaştırması"), "type": "table", "content": (
                list(display_table.columns), display_table.astype(str).values.tolist(),
            )},
        ]
        pdf_bytes = build_pdf(tr("YZ Model Karşılaştırma Raporu"), blocks)
        st.download_button(
            tr("PDF indir"), data=pdf_bytes,
            file_name="yz_karsilastirma.pdf", mime="application/pdf", key="ai_pdf",
        )

    st.caption(tr(
        "Not: Bu tablo elle küratörlüğü yapılmış referans verisidir; yatırım veya satın "
        "alma tavsiyesi niteliği taşımaz."
    ))


def _render_news_section():
    st.markdown(tr("## 📰 Güncel Haberler"))
    st.caption(tr(
        "Google/Bing Haberler RSS üzerinden seçilen model hakkındaki güncel haber ve "
        "duyuru başlıklarını tarar. İnternet bağlantısı gerektirir."
    ))

    model_name = st.selectbox(tr("Model"), get_model_names(), key="ai_news_model")
    search_clicked = st.button(tr("Haberleri Getir"), type="primary", key="ai_news_btn")

    if search_clicked:
        with st.spinner(trf("'{model}' için güncel haberler taranıyor...", model=model_name)):
            records, warnings = _cached_news(model_name)
        st.session_state["ai_news_model_name"] = model_name
        st.session_state["ai_news_records"] = records
        st.session_state["ai_news_warnings"] = warnings

    if "ai_news_records" not in st.session_state:
        st.info(tr("Bir model seçip 'Haberleri Getir' butonuna tıklayın."))
        return

    news_model_name = st.session_state["ai_news_model_name"]
    records = st.session_state["ai_news_records"]
    warnings = st.session_state["ai_news_warnings"]

    if not records:
        st.warning(trf("'{model}' için hiçbir haber bulunamadı.", model=news_model_name))
    else:
        st.success(trf("'{model}' için {n} haber bulundu.", model=news_model_name, n=len(records)))
        news_df = pd.DataFrame(records)
        st.dataframe(
            news_df, width="stretch", hide_index=True,
            column_config={"link": st.column_config.LinkColumn(tr("Kaynak Linki"), display_text=tr("Aç"))},
        )

    if warnings:
        with st.expander(tr("Tarama Uyarıları")):
            for w in warnings:
                st.caption(f"⚠️ {tr(w)}")
