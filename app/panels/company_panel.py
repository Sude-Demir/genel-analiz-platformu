"""Şirket Analizi paneli."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from company_analysis import (
    analyze_sentiment,
    collect_mentions,
    extract_topics,
    label_mentions,
    reputation_score,
    segment_outlook,
    sentiment_timeline,
)
from data_loader import load_sentiment_model, load_sentiment_model_metrics
from sentiment_model import predict_batch
from export_utils import build_pdf, to_json_bytes
from translator import tr, trf
from theme import CATEGORICAL, MUTED, SEQUENTIAL_BLUE, STATUS, apply_layout

CACHE_TTL_SECONDS = 1800
ORNEK_SIRKET = "Turkcell"
ORNEK_SIRKET_B = "Türk Telekom"


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _cached_collect(company: str):
    """Ham tarama (ağ çağrıları) — sözlük ve ML etiketleme yollarının ikisi de aynı
    taranmış kayıtları kullanır, böylece ML toggle'ı açıp kapatmak yeniden tarama
    tetiklemez."""
    return collect_mentions(company)


def _build_scan(company: str, sentiment_fn):
    records, warnings = _cached_collect(company)
    df = label_mentions(records, sentiment_fn)
    topics = extract_topics((df["başlık"] + " " + df["özet"]).tolist(), company) if not df.empty else []
    outlooks = segment_outlook(df, company)
    return df, topics, warnings, outlooks


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _cached_scan(company: str):
    return _build_scan(company, analyze_sentiment)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _cached_scan_ml(company: str):
    """ML tabanlı duygu sınıflandırmasıyla tarama. Model dosyası yoksa None döner;
    çağıran taraf (_render_single_section) bu durumda sözlük yöntemine sessizce döner."""
    bundle = load_sentiment_model()
    if bundle is None:
        return None
    pipeline = bundle["pipeline"]

    def _ml_sentiment_fn(text: str):
        if not text.strip():
            return "Nötr", 0.0
        return predict_batch(pipeline, [text])[0]

    return _build_scan(company, _ml_sentiment_fn)


def render():
    """Panelin iki bağımsız kısmını sırayla render eder. _render_single_section()
    içindeki erken "return"lerin (henüz analiz yapılmamışsa) _render_compare_section()
    çağrısını engellememesi için ikisi ayrı fonksiyonlarda tutulur."""
    _render_single_section()
    st.divider()
    _render_compare_section()


def _render_single_section():
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
    use_ml = st.checkbox(
        tr("🧠 ML Tabanlı Duygu Sınıflandırması Kullan (Deneysel)"),
        key="company_use_ml_sentiment",
        help=tr(
            "TF-IDF + LogisticRegression/MultinomialNB ile eğitilmiş bir sınıflandırıcı "
            "kullanır (bkz. src/sentiment_model.py). Kapalıyken varsayılan sözlük tabanlı "
            "yöntem (analyze_sentiment) kullanılır."
        ),
    )
    analyze_clicked = st.button(tr("Analiz Et"), type="primary", disabled=not company.strip(), key="company_analyze_btn")

    if ornek_clicked:
        company = ORNEK_SIRKET

    if (analyze_clicked and company.strip()) or ornek_clicked:
        target = company.strip() or ORNEK_SIRKET
        with st.spinner(trf("'{target}' için web ve haber kaynakları taranıyor...", target=target)):
            used_ml = False
            if use_ml:
                scan_result = _cached_scan_ml(target)
                if scan_result is not None:
                    df, topics, warnings, outlooks = scan_result
                    used_ml = True
                else:
                    st.warning(tr(
                        "ML modeli bulunamadı; önce `python src/sentiment_model.py` çalıştırın. "
                        "Sözlük tabanlı yönteme geri dönülüyor."
                    ))
                    df, topics, warnings, outlooks = _cached_scan(target)
            else:
                df, topics, warnings, outlooks = _cached_scan(target)
        st.session_state["company_name"] = target
        st.session_state["company_df"] = df
        st.session_state["company_topics"] = topics
        st.session_state["company_warnings"] = warnings
        st.session_state["company_outlooks"] = outlooks
        st.session_state["company_used_ml"] = used_ml

    if "company_df" not in st.session_state:
        st.info(tr("Analiz başlatmak için bir şirket adı girip 'Analiz Et' butonuna tıklayın veya 'Örnek Dene' ile hemen deneyin."))
        return

    company_name = st.session_state["company_name"]
    df = st.session_state["company_df"]
    topics = st.session_state["company_topics"]
    warnings = st.session_state["company_warnings"]
    outlooks = st.session_state["company_outlooks"]
    used_ml = st.session_state.get("company_used_ml", False)

    if df.empty:
        st.warning(trf("'{company_name}' için hiçbir kaynak bulunamadı. Şirket adını farklı yazarak tekrar deneyin.", company_name=company_name))
        return

    st.success(trf("'{company_name}' için {n} kaynak bulundu.", company_name=company_name, n=len(df)))

    if used_ml:
        ml_metrics = load_sentiment_model_metrics()
        if ml_metrics:
            with st.expander(tr("🧠 ML Model Bilgisi")):
                st.caption(trf(
                    "Duygu etiketleri, {model} ile eğitilmiş bir sınıflandırıcı tarafından üretildi "
                    "(bkz. src/sentiment_model.py). Test seti f1_macro: {f1:.3f}, doğruluk: {acc:.1%}.",
                    model=ml_metrics["selected_model"],
                    f1=ml_metrics["test_metrics"]["f1_macro"],
                    acc=ml_metrics["test_metrics"]["accuracy"],
                ))
                st.caption(f"⚠️ {tr(ml_metrics['veri_seti_notu'])}")
                labels = ml_metrics["labels"]
                fig_cm = px.imshow(
                    ml_metrics["confusion_matrix"], x=labels, y=labels, text_auto=True,
                    labels={"x": tr("Tahmin Edilen"), "y": tr("Gerçek"), "color": tr("Adet")},
                    color_continuous_scale=SEQUENTIAL_BLUE,
                )
                apply_layout(fig_cm)
                st.plotly_chart(fig_cm, width="stretch", theme=None)

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
                st.caption(trf("{n} kaynaktan üretildi.", n=o['kaynak_sayısı']))
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
            "duygu_analiz_yontemi": tr("ML (TF-IDF + sınıflandırıcı)") if used_ml else tr("Sözlük Tabanlı"),
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
                trf("Toplam taranan kaynak: {n}", n=len(df)),
                trf("İtibar Puanı: {score}/100", score=score),
                trf("Pozitif: {n}", n=int(counts.get('Pozitif', 0))),
                trf("Nötr: {n}", n=int(counts.get('Nötr', 0))),
                trf("Negatif: {n}", n=int(counts.get('Negatif', 0))),
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
        pdf_bytes = build_pdf(trf("Şirket Analiz Raporu — {company_name}", company_name=company_name), blocks)
        st.download_button(
            tr("PDF indir"), data=pdf_bytes,
            file_name=f"{company_name}_analiz.pdf", mime="application/pdf", key="company_pdf",
        )

    if used_ml:
        st.caption(tr(
            "Not: Duygu analizi, eğitilmiş bir ML sınıflandırıcısı (deneysel) ile hesaplanmıştır; "
            "nihai yorum için kaynakların incelenmesi önerilir."
        ))
    else:
        st.caption(tr(
            "Not: Duygu analizi sözlük tabanlı sezgisel bir yöntemle hesaplanmıştır; "
            "nihai yorum için kaynakların incelenmesi önerilir."
        ))


def _render_compare_section():
    """Şirket Analizi panelinin içindeki ayrı bir kısım: iki şirketi yan yana
    karşılaştırır. Yukarıdaki tekil şirket analizinden bağımsız çalışır;
    tarama/önbellekleme için aynı _cached_scan'i yeniden kullanır."""
    st.markdown(tr("## ⚖️ Şirket Karşılaştır"))
    st.caption(tr(
        "İki şirket adı girin; her ikisi için ayrı ayrı taranan haber/yorum kaynakları "
        "itibar puanı ve duygu dağılımı açısından yan yana karşılaştırılır."
    ))

    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        company_a = st.text_input(tr("1. Şirket"), placeholder=tr("Örn: Turkcell"), key="compare_company_a")
    with c2:
        company_b = st.text_input(tr("2. Şirket"), placeholder=tr("Örn: Türk Telekom"), key="compare_company_b")
    with c3:
        st.write("")
        st.write("")
        ornek_clicked = st.button(tr("🔎 Örnek Dene"), key="compare_example_btn", use_container_width=True)

    if ornek_clicked:
        company_a, company_b = ORNEK_SIRKET, ORNEK_SIRKET_B

    compare_clicked = st.button(
        tr("Karşılaştır"), type="primary",
        disabled=not (company_a.strip() and company_b.strip()),
        key="company_compare_btn",
    )

    if (compare_clicked and company_a.strip() and company_b.strip()) or ornek_clicked:
        target_a, target_b = company_a.strip(), company_b.strip()
        with st.spinner(trf("'{a}' ve '{b}' için kaynaklar taranıyor...", a=target_a, b=target_b)):
            df_a, _, warnings_a, _ = _cached_scan(target_a)
            df_b, _, warnings_b, _ = _cached_scan(target_b)
        st.session_state["compare_data"] = {
            "a": {"name": target_a, "df": df_a, "warnings": warnings_a},
            "b": {"name": target_b, "df": df_b, "warnings": warnings_b},
        }

    if "compare_data" not in st.session_state:
        st.info(tr("Karşılaştırmak için iki şirket adı girip 'Karşılaştır' butonuna tıklayın veya 'Örnek Dene' ile hemen deneyin."))
        return

    data = st.session_state["compare_data"]
    a, b = data["a"], data["b"]

    if a["df"].empty and b["df"].empty:
        st.warning(tr("Her iki şirket için de hiçbir kaynak bulunamadı. Şirket adlarını farklı yazarak tekrar deneyin."))
        return
    if a["df"].empty:
        st.warning(trf("'{name}' için hiçbir kaynak bulunamadı; yalnızca diğer şirket gösteriliyor.", name=a["name"]))
    if b["df"].empty:
        st.warning(trf("'{name}' için hiçbir kaynak bulunamadı; yalnızca diğer şirket gösteriliyor.", name=b["name"]))

    color_a, color_b = CATEGORICAL[0], CATEGORICAL[6]
    score_a, _ = reputation_score(a["df"])
    score_b, _ = reputation_score(b["df"])

    with st.container(border=True):
        st.markdown(tr("**İtibar Puanı Karşılaştırması**"))
        fig_scores = px.bar(
            x=[a["name"], b["name"]], y=[score_a, score_b],
            color=[a["name"], b["name"]], color_discrete_map={a["name"]: color_a, b["name"]: color_b},
            text=[score_a, score_b],
            labels={"x": tr("Şirket"), "y": tr("İtibar Puanı")},
        )
        fig_scores.update_traces(textposition="outside")
        apply_layout(fig_scores, showlegend=False)
        fig_scores.update_yaxes(range=[0, 105])
        st.plotly_chart(fig_scores, width="stretch", theme=None)

        cols = st.columns(2)
        for col, entry, score in [(cols[0], a, score_a), (cols[1], b, score_b)]:
            with col:
                st.markdown(f"**{entry['name']}**")
                counts = entry["df"]["duygu"].value_counts()
                st.metric(tr("İtibar Puanı"), f"{score}/100")
                st.metric(tr("Toplam Kaynak"), len(entry["df"]))
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric(tr("Pozitif"), int(counts.get("Pozitif", 0)))
                mc2.metric(tr("Nötr"), int(counts.get("Nötr", 0)))
                mc3.metric(tr("Negatif"), int(counts.get("Negatif", 0)))

    with st.container(border=True):
        st.markdown(tr("**Duygu Dağılımı Karşılaştırması**"))
        sentiment_order = ["Pozitif", "Nötr", "Negatif"]
        sentiment_colors = {"Pozitif": STATUS["good"], "Nötr": MUTED, "Negatif": STATUS["critical"]}
        rows = []
        for entry in (a, b):
            counts = entry["df"]["duygu"].value_counts()
            for s in sentiment_order:
                rows.append({"Şirket": entry["name"], "Duygu": tr(s), "Adet": int(counts.get(s, 0)), "_raw_duygu": s})
        comp_df = pd.DataFrame(rows)
        fig_sent = px.bar(
            comp_df, x="Şirket", y="Adet", color="_raw_duygu", barmode="group",
            color_discrete_map=sentiment_colors,
            labels={"Adet": tr("Kaynak Sayısı"), "_raw_duygu": tr("Duygu")},
        )
        apply_layout(fig_sent)
        st.plotly_chart(fig_sent, width="stretch", theme=None)

    all_warnings = a["warnings"] + b["warnings"]
    if all_warnings:
        with st.expander(tr("Tarama Uyarıları")):
            for w in all_warnings:
                st.caption(f"⚠️ {tr(w)}")

    st.markdown(tr("### Dışa Aktar"))
    c1, c2 = st.columns(2)
    with c1:
        json_payload = {
            "karsilastirma": [
                {
                    "sirket": entry["name"], "itibar_puani": score,
                    "toplam_kaynak": len(entry["df"]),
                    "duygu_dagilimi": {k: int(v) for k, v in entry["df"]["duygu"].value_counts().to_dict().items()},
                }
                for entry, score in [(a, score_a), (b, score_b)]
            ],
        }
        st.download_button(
            tr("JSON indir"), data=to_json_bytes(json_payload),
            file_name=f"{a['name']}_vs_{b['name']}_karsilastirma.json", mime="application/json",
            key="company_compare_json",
        )
    with c2:
        blocks = [
            {"heading": tr("İtibar Puanları"), "type": "table", "content": (
                [tr("Şirket"), tr("İtibar Puanı"), tr("Toplam Kaynak")],
                [[a["name"], score_a, len(a["df"])], [b["name"], score_b, len(b["df"])]],
            )},
        ]
        pdf_bytes = build_pdf(
            trf("Şirket Karşılaştırma Raporu — {a} vs {b}", a=a["name"], b=b["name"]), blocks,
        )
        st.download_button(
            tr("PDF indir"), data=pdf_bytes,
            file_name=f"{a['name']}_vs_{b['name']}_karsilastirma.pdf", mime="application/pdf",
            key="company_compare_pdf",
        )

    st.caption(tr(
        "Not: Duygu analizi sözlük tabanlı sezgisel bir yöntemle hesaplanmıştır; "
        "nihai yorum için kaynakların incelenmesi önerilir."
    ))
