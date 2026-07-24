"""Borsa Analizi paneli."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from borsa_analysis import (
    POPULAR_SYMBOLS,
    RANGE_OPTIONS,
    compute_technical_indicators,
    fetch_price_history,
    predict_short_term_outlook,
    summarize,
)
from borsa_model import train_price_direction_model
from export_utils import build_pdf, to_json_bytes
from translator import tr, trf
from theme import CATEGORICAL, MUTED, SEQUENTIAL_BLUE, STATUS, apply_layout

CACHE_TTL_SECONDS = 900
ORNEK_SEMBOL = "THYAO.IS"
ORNEK_ENDEKS = "^XU100.IS"
_DEFAULT_RANGE_LABEL = "1 Yıl"
_POPULER_PLACEHOLDER = "— Popüler sembollerden seçin —"
_VOLATILITY_LABELS = {"good": "Düşük Oynaklık", "warning": "Orta Oynaklık", "critical": "Yüksek Oynaklık"}


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _cached_fetch(symbol: str, range_: str):
    df, meta, warnings = fetch_price_history(symbol, range_)
    result = summarize(df, meta)
    return df, result, warnings


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _cached_train_ml(df: pd.DataFrame):
    """Fiyat geçmişi (df) değişmediği sürece modeli yeniden eğitmez — checkbox
    açıkken sayfadaki başka bir widget'ın tetiklediği her rerun'da RandomForest'ı
    yeniden eğitmemek için."""
    return train_price_direction_model(df)


def _run_analysis(target: str, range_value: str):
    df, result, warnings = _cached_fetch(target, range_value)
    st.session_state["borsa_symbol"] = target
    st.session_state["borsa_df"] = df
    st.session_state["borsa_result"] = result
    st.session_state["borsa_warnings"] = warnings


def _on_popular_symbol_change():
    """Popüler sembol seçilince metin kutusunu doldurur ve analizi otomatik tetikler."""
    label = st.session_state.get("borsa_popular_select")
    if not label or label == _POPULER_PLACEHOLDER:
        return
    target = POPULAR_SYMBOLS[label]
    st.session_state["borsa_symbol_input"] = target
    range_label = st.session_state.get("borsa_range_select", _DEFAULT_RANGE_LABEL)
    _run_analysis(target, RANGE_OPTIONS[range_label])


def _fill_from_popular(input_key: str, select_key: str):
    """Karşılaştırma bölümündeki popüler sembol seçicileri için: yalnızca ilgili
    metin kutusunu doldurur, analizi otomatik tetiklemez (iki sembol de dolduktan
    sonra kullanıcı 'Karşılaştır' butonuna basar)."""
    label = st.session_state.get(select_key)
    if not label or label == _POPULER_PLACEHOLDER:
        return
    st.session_state[input_key] = POPULAR_SYMBOLS[label]


def render():
    """Panelin iki bağımsız kısmını sırayla render eder (company_panel.py'deki
    aynı desen): _render_single_section() içindeki erken "return"lerin
    _render_compare_section() çağrısını engellememesi için ikisi ayrı
    fonksiyonlarda tutulur."""
    _render_single_section()
    st.divider()
    _render_compare_section()


def _style_subplot_axes(fig):
    """apply_layout() yalnızca ilk eksen çiftini (xaxis/yaxis) stiller; çok satırlı
    (subplot) grafiklerde diğer satırların eksenleri varsayılan (temaya uymayan)
    renklerde kalır. Bu, ilk eksenin aldığı chrome renklerini tüm eksenlere yayar."""
    fig.update_xaxes(
        gridcolor=fig.layout.xaxis.gridcolor, linecolor=fig.layout.xaxis.linecolor,
        zerolinecolor=fig.layout.xaxis.zerolinecolor, automargin=True,
    )
    fig.update_yaxes(
        gridcolor=fig.layout.xaxis.gridcolor, linecolor=fig.layout.xaxis.linecolor,
        zerolinecolor=fig.layout.xaxis.zerolinecolor, automargin=True,
    )


def _render_single_section():
    st.subheader(tr("Sembol ile Güncel ve Geçmiş Fiyat Analizi"))
    st.caption(tr(
        "Yahoo Finance'in herkese açık ucu üzerinden hisse senedi/endeks fiyat geçmişini "
        "çeker; BIST hisseleri için sembole \".IS\" ekleyin (örn. THYAO.IS), global "
        "hisseler için doğrudan yazın (örn. AAPL). İnternet bağlantısı gerektirir."
    ))

    c1, c2, c3, c4 = st.columns([2, 1.6, 1.1, 1])
    with c1:
        symbol = st.text_input(tr("Sembol"), placeholder=tr("Örn: THYAO.IS veya AAPL"), key="borsa_symbol_input")
    with c2:
        st.selectbox(
            tr("Popüler Semboller"), [_POPULER_PLACEHOLDER] + list(POPULAR_SYMBOLS.keys()),
            key="borsa_popular_select", on_change=_on_popular_symbol_change,
        )
    with c3:
        range_label = st.selectbox(
            tr("Zaman Aralığı"), list(RANGE_OPTIONS.keys()),
            index=list(RANGE_OPTIONS.keys()).index(_DEFAULT_RANGE_LABEL),
            key="borsa_range_select",
        )
    with c4:
        st.write("")
        st.write("")
        ornek_clicked = st.button(tr("🔎 Örnek Dene"), key="borsa_example_btn", use_container_width=True)

    show_indicators = st.checkbox(tr("Teknik göstergeleri göster (SMA / RSI / MACD)"), key="borsa_show_indicators")
    analyze_clicked = st.button(tr("Analiz Et"), type="primary", disabled=not symbol.strip(), key="borsa_analyze_btn")

    if ornek_clicked:
        symbol = ORNEK_SEMBOL

    if (analyze_clicked and symbol.strip()) or ornek_clicked:
        target = symbol.strip() or ORNEK_SEMBOL
        range_value = RANGE_OPTIONS[range_label]
        with st.spinner(trf("'{target}' için fiyat verisi çekiliyor...", target=target)):
            _run_analysis(target, range_value)

    if "borsa_df" not in st.session_state:
        st.info(tr("Analiz başlatmak için bir sembol girip 'Analiz Et' butonuna tıklayın, popüler listeden seçin veya 'Örnek Dene' ile hemen deneyin."))
        return

    symbol_name = st.session_state["borsa_symbol"]
    df = st.session_state["borsa_df"]
    result = st.session_state["borsa_result"]
    warnings = st.session_state["borsa_warnings"]

    if df.empty:
        st.warning(trf("'{symbol}' için fiyat verisi bulunamadı. Sembolü kontrol edip tekrar deneyin.", symbol=symbol_name))
        if warnings:
            with st.expander(tr("Uyarılar")):
                for w in warnings:
                    st.caption(f"⚠️ {tr(w)}")
        return

    st.success(trf("'{symbol}' için {n} günlük fiyat verisi bulundu.", symbol=symbol_name, n=len(df)))

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            trf("Güncel Fiyat ({para})", para=result["para_birimi"]),
            f"{result['güncel_fiyat']:.2f}",
            delta=f"{result['değişim']:+.2f} ({result['değişim_yüzde']:+.2f}%)",
        )
        c2.metric(tr("Dönem Yüksek"), f"{result['dönem_yüksek']:.2f}")
        c3.metric(tr("Dönem Düşük"), f"{result['dönem_düşük']:.2f}")
        c4.metric(tr("Ortalama Hacim"), f"{result['ortalama_hacim']:,.0f}")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric(tr("Dönem Getirisi"), f"{result['dönem_getiri_yüzde']:+.2f}%")
        c6.metric(tr("52 Hafta Yüksek"), f"{result['hafta52_yüksek']:.2f}")
        c7.metric(tr("52 Hafta Düşük"), f"{result['hafta52_düşük']:.2f}")
        c8.metric(tr("Volatilite (Günlük)"), f"{result['volatilite_yüzde']:.2f}%")

        st.markdown(
            f"<span style='color:{STATUS[result['trend_durum']]}; font-weight:600;'>{tr(result['trend_yorum'])}</span> "
            f"&nbsp;·&nbsp; "
            f"<span style='color:{STATUS[result['volatilite_durum']]}; font-weight:600;'>{tr(_VOLATILITY_LABELS[result['volatilite_durum']])}</span>",
            unsafe_allow_html=True,
        )

    outlook = predict_short_term_outlook(df)
    with st.container(border=True):
        st.markdown(tr("### 🔮 Kısa Vadeli Yön Sezgiseli"))
        st.caption(tr(
            "Bu bir istatistiksel tahmin veya yatırım tavsiyesi DEĞİLDİR — yalnızca SMA20/SMA50, "
            "RSI14 ve MACD gibi standart teknik göstergelerin kural tabanlı bir özetidir. Harici "
            "bir AI/istatistiksel model kullanılmaz."
        ))
        st.markdown(
            f"<span style='color:{STATUS[outlook['durum']]}; font-size:1.3em; font-weight:700;'>{tr(outlook['yön'])}</span>",
            unsafe_allow_html=True,
        )
        st.caption(tr(outlook["gerekçe"]))
        for s in outlook["sinyaller"]:
            icon = "🟢" if s["yön"] == 1 else ("🔴" if s["yön"] == -1 else "⚪")
            st.caption(f"{icon} **{s['ad']}** — {tr(s['açıklama'])}")

    with st.container(border=True):
        st.markdown(tr("### 🧠 ML Tabanlı Ertesi Gün Tahmini (Deneysel)"))
        st.caption(tr(
            "Yukarıdaki sezgiselden farklı olarak, geçmiş fiyat davranışından ÖĞRENEN gerçek "
            "bir sınıflandırma modelidir (RandomForest). Zaman serisine uygun 'geçmişte eğit → "
            "gelecekte test et' yöntemiyle (walk-forward backtest, bkz. TimeSeriesSplit) sınanır "
            "ve daima naif bir temel çizgiyle (baseline: çoğunluk sınıfını tahmin et) "
            "karşılaştırılır — ertesi gün yön tahmini doğası gereği zordur, bu karşılaştırma "
            "modelin gerçekten işe yarayıp yaramadığını dürüstçe gösterir. Yatırım tavsiyesi "
            "DEĞİLDİR."
        ))
        run_ml = st.checkbox(tr("Modeli eğit ve backtest et"), key="borsa_ml_toggle")
        ml_result = None
        if run_ml:
            with st.spinner(tr("Model eğitiliyor ve geçmiş üzerinde test ediliyor...")):
                ml_result = _cached_train_ml(df)

            if not ml_result["ok"]:
                for w in ml_result["warnings"]:
                    st.warning(tr(w))
            else:
                bt = ml_result["backtest"]
                next_day = ml_result["next_day"]

                beat_label = tr("✅ Baseline'ı geçiyor") if ml_result["beats_baseline"] else tr("⚠️ Baseline'ı geçemiyor")
                m1, m2, m3 = st.columns(3)
                m1.metric(tr("Backtest Doğruluğu"), f"{bt['accuracy']:.1%}")
                m2.metric(tr("Naif Baseline Doğruluğu"), f"{bt['baseline_accuracy']:.1%}")
                m3.metric(tr("Değerlendirme"), beat_label)
                st.caption(trf(
                    "{n_oos} örnek üzerinde {n_folds} kat walk-forward backtest yapıldı; model her "
                    "katta yalnızca kendisinden önceki veriyle eğitildi (veri sızıntısı yok).",
                    n_oos=bt["n_oos_samples"], n_folds=bt["n_folds"],
                ))

                direction_color = STATUS["good"] if next_day["yön"] == "Yükseliş" else STATUS["critical"]
                st.markdown(
                    f"<span style='color:{direction_color}; font-size:1.2em; font-weight:700;'>"
                    f"{tr('Ertesi Gün Tahmini')}: {tr(next_day['yön'])}</span> "
                    f"&nbsp;({next_day['yükseliş_olasılığı']:.0%} {tr('yükseliş olasılığı')})",
                    unsafe_allow_html=True,
                )

                with st.expander(tr("Modeli Etkileyen En Önemli Özellikler")):
                    imp_series = pd.Series(ml_result["feature_importances"]).sort_values()
                    fig_imp = px.bar(
                        imp_series, x=imp_series.values, y=imp_series.index, orientation="h",
                        labels={"x": tr("Önem Derecesi"), "y": ""},
                        color_discrete_sequence=[CATEGORICAL[0]],
                    )
                    apply_layout(fig_imp, showlegend=False)
                    st.plotly_chart(fig_imp, width="stretch", theme=None)

                with st.expander(tr("Karışıklık Matrisi (Backtest, Out-of-Sample)")):
                    labels = [tr("Düşüş"), tr("Yükseliş")]
                    fig_cm = px.imshow(
                        bt["confusion_matrix"], x=labels, y=labels, text_auto=True,
                        labels={"x": tr("Tahmin Edilen"), "y": tr("Gerçek"), "color": tr("Adet")},
                        color_continuous_scale=SEQUENTIAL_BLUE,
                    )
                    apply_layout(fig_cm)
                    st.plotly_chart(fig_cm, width="stretch", theme=None)

                st.caption(tr(
                    "Not: Bu deneysel bir makine öğrenmesi modelidir; model baseline'ı "
                    "geçemeyebilir — bu durumda dürüstçe raporlanır. Yatırım tavsiyesi "
                    "niteliği taşımaz."
                ))

    st.markdown(tr("### 📈 Fiyat, Hacim ve Teknik Göstergeler") if show_indicators else tr("### 📈 Fiyat Grafiği"))
    chart_type = st.radio(tr("Grafik Tipi"), [tr("Çizgi"), tr("Mum")], horizontal=True, key="borsa_chart_type")

    chart_df = compute_technical_indicators(df) if show_indicators else df

    with st.container(border=True):
        if show_indicators:
            fig = make_subplots(
                rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                row_heights=[0.42, 0.16, 0.18, 0.24],
                subplot_titles=(tr("Fiyat"), tr("Hacim"), "RSI (14)", "MACD"),
            )
        else:
            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                row_heights=[0.75, 0.25],
                subplot_titles=(tr("Fiyat"), tr("Hacim")),
            )

        if chart_type == tr("Mum"):
            fig.add_trace(go.Candlestick(
                x=chart_df["tarih"], open=chart_df["açılış"], high=chart_df["yüksek"], low=chart_df["düşük"], close=chart_df["kapanış"],
                increasing_line_color=STATUS["good"], decreasing_line_color=STATUS["critical"], name=tr("Fiyat"),
            ), row=1, col=1)
        else:
            fig.add_trace(go.Scatter(
                x=chart_df["tarih"], y=chart_df["kapanış"], mode="lines", line=dict(color=CATEGORICAL[0]), name=tr("Kapanış"),
            ), row=1, col=1)

        if show_indicators:
            fig.add_trace(go.Scatter(x=chart_df["tarih"], y=chart_df["sma20"], mode="lines",
                                      line=dict(color=CATEGORICAL[3], width=1.5), name="SMA20"), row=1, col=1)
            fig.add_trace(go.Scatter(x=chart_df["tarih"], y=chart_df["sma50"], mode="lines",
                                      line=dict(color=CATEGORICAL[6], width=1.5), name="SMA50"), row=1, col=1)

        volume_colors = [
            STATUS["good"] if c >= o else STATUS["critical"]
            for o, c in zip(chart_df["açılış"], chart_df["kapanış"])
        ]
        fig.add_trace(go.Bar(x=chart_df["tarih"], y=chart_df["hacim"], marker_color=volume_colors, name=tr("Hacim")), row=2, col=1)

        if show_indicators:
            fig.add_trace(go.Scatter(x=chart_df["tarih"], y=chart_df["rsi14"], mode="lines",
                                      line=dict(color=CATEGORICAL[4]), name="RSI"), row=3, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color=MUTED, row=3, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color=MUTED, row=3, col=1)
            fig.update_yaxes(range=[0, 100], row=3, col=1)

            macd_colors = [STATUS["good"] if v >= 0 else STATUS["critical"] for v in chart_df["macd_hist"].fillna(0)]
            fig.add_trace(go.Bar(x=chart_df["tarih"], y=chart_df["macd_hist"], marker_color=macd_colors, name="MACD Hist"), row=4, col=1)
            fig.add_trace(go.Scatter(x=chart_df["tarih"], y=chart_df["macd"], mode="lines",
                                      line=dict(color=CATEGORICAL[0], width=1.5), name="MACD"), row=4, col=1)
            fig.add_trace(go.Scatter(x=chart_df["tarih"], y=chart_df["macd_sinyal"], mode="lines",
                                      line=dict(color=CATEGORICAL[5], width=1.5), name=tr("Sinyal")), row=4, col=1)

        total_height = 700 if show_indicators else 460
        apply_layout(fig, height=total_height, xaxis_rangeslider_visible=False, showlegend=show_indicators)
        _style_subplot_axes(fig)
        st.plotly_chart(fig, width="stretch", theme=None)

    st.markdown(tr("### Fiyat Geçmişi"))
    display_df = df.copy()
    display_df["tarih"] = display_df["tarih"].dt.strftime("%Y-%m-%d")
    st.dataframe(display_df, width="stretch", hide_index=True)

    if warnings:
        with st.expander(tr("Uyarılar")):
            for w in warnings:
                st.caption(f"⚠️ {tr(w)}")

    st.markdown(tr("### Dışa Aktar"))
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            tr("Fiyat Geçmişini CSV indir"), data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"{symbol_name}_fiyat_gecmisi.csv", mime="text/csv", key="borsa_csv",
        )
    with c2:
        json_payload = {
            "sembol": symbol_name,
            "ozet": result,
            "kisa_vadeli_yon_sezgiseli": outlook,
            "ml_ertesi_gun_tahmini": ml_result if ml_result and ml_result.get("ok") else None,
            "fiyat_gecmisi": display_df.to_dict(orient="records"),
            "uyarilar": warnings,
        }
        st.download_button(
            tr("JSON indir"), data=to_json_bytes(json_payload),
            file_name=f"{symbol_name}_borsa_analiz.json", mime="application/json", key="borsa_json",
        )
    with c3:
        blocks = [
            {"heading": tr("Genel Özet"), "type": "bullets", "content": [
                trf("Güncel Fiyat: {fiyat:.2f} {para}", fiyat=result["güncel_fiyat"], para=result["para_birimi"]),
                trf("Günlük Değişim: {degisim:+.2f} ({yuzde:+.2f}%)", degisim=result["değişim"], yuzde=result["değişim_yüzde"]),
                trf("Dönem Yüksek: {v:.2f}", v=result["dönem_yüksek"]),
                trf("Dönem Düşük: {v:.2f}", v=result["dönem_düşük"]),
                trf("Dönem Getirisi: {v:+.2f}%", v=result["dönem_getiri_yüzde"]),
                trf("52 Hafta Yüksek: {v:.2f}", v=result["hafta52_yüksek"]),
                trf("52 Hafta Düşük: {v:.2f}", v=result["hafta52_düşük"]),
                trf("Ortalama Hacim: {v:,.0f}", v=result["ortalama_hacim"]),
                trf("Volatilite (Günlük): {v:.2f}%", v=result["volatilite_yüzde"]),
                tr(result["trend_yorum"]),
            ]},
            {"heading": tr("Kısa Vadeli Yön Sezgiseli (yatırım tavsiyesi değildir)"), "type": "bullets", "content": [
                trf("Yön: {yon} (skor: {skor:+d}/4)", yon=outlook["yön"], skor=outlook["skor"]),
                tr(outlook["gerekçe"]),
            ] + [tr(s["açıklama"]) for s in outlook["sinyaller"]]},
            {"heading": tr("Fiyat Geçmişi"), "type": "table", "content": (
                [tr("Tarih"), tr("Açılış"), tr("Yüksek"), tr("Düşük"), tr("Kapanış"), tr("Hacim")],
                display_df.astype(str).values.tolist()[-40:],
            )},
        ]
        if ml_result and ml_result.get("ok"):
            bt = ml_result["backtest"]
            blocks.insert(2, {
                "heading": tr("ML Tabanlı Ertesi Gün Tahmini (deneysel, yatırım tavsiyesi değildir)"),
                "type": "bullets", "content": [
                    trf("Yön: {yon} ({olasilik:.0%} yükseliş olasılığı)",
                        yon=ml_result["next_day"]["yön"], olasilik=ml_result["next_day"]["yükseliş_olasılığı"]),
                    trf("Backtest doğruluğu: {acc:.1%} (naif baseline: {base:.1%})",
                        acc=bt["accuracy"], base=bt["baseline_accuracy"]),
                    tr("Baseline'ı geçiyor.") if ml_result["beats_baseline"] else tr("Baseline'ı geçemiyor."),
                ],
            })
        if warnings:
            blocks.append({"heading": tr("Uyarılar"), "type": "bullets", "content": warnings})
        pdf_bytes = build_pdf(trf("Borsa Analiz Raporu — {symbol}", symbol=symbol_name), blocks)
        st.download_button(
            tr("PDF indir"), data=pdf_bytes,
            file_name=f"{symbol_name}_borsa_analiz.pdf", mime="application/pdf", key="borsa_pdf",
        )

    st.caption(tr(
        "Not: Trend, volatilite, teknik göstergeler ve kısa vadeli yön sezgiseli kural "
        "tabanlı hesaplamalardır; yatırım tavsiyesi niteliği taşımaz."
    ))


def _render_compare_section():
    """Borsa Analizi panelinin içindeki ayrı bir kısım: iki sembolü dönem başına
    göre normalize edilmiş getiri üzerinden karşılaştırır (bir endeks sembolü
    girilirse bu, doğal olarak 'endeksle karşılaştırma' işlevini de görür).
    Yukarıdaki tekil analizden bağımsız çalışır; aynı _cached_fetch'i paylaşır."""
    st.markdown(tr("## ⚖️ Sembol Karşılaştır"))
    st.caption(tr(
        "İki sembolü (örn. bir hisseyi bir endeksle) dönem başı 100 kabul edilerek "
        "normalize edilmiş getiri üzerinden yan yana karşılaştırır."
    ))

    c1, c2, c3, c4 = st.columns([2, 2, 1.2, 1])
    with c1:
        symbol_a = st.text_input(tr("1. Sembol"), placeholder=tr("Örn: THYAO.IS"), key="borsa_compare_symbol_a")
        st.selectbox(
            tr("Popüler (1. Sembol)"), [_POPULER_PLACEHOLDER] + list(POPULAR_SYMBOLS.keys()),
            key="borsa_compare_popular_a", on_change=_fill_from_popular,
            args=("borsa_compare_symbol_a", "borsa_compare_popular_a"),
        )
    with c2:
        symbol_b = st.text_input(tr("2. Sembol"), placeholder=tr("Örn: ^XU100.IS"), key="borsa_compare_symbol_b")
        st.selectbox(
            tr("Popüler (2. Sembol)"), [_POPULER_PLACEHOLDER] + list(POPULAR_SYMBOLS.keys()),
            key="borsa_compare_popular_b", on_change=_fill_from_popular,
            args=("borsa_compare_symbol_b", "borsa_compare_popular_b"),
        )
    with c3:
        range_label = st.selectbox(
            tr("Zaman Aralığı"), list(RANGE_OPTIONS.keys()),
            index=list(RANGE_OPTIONS.keys()).index(_DEFAULT_RANGE_LABEL),
            key="borsa_compare_range_select",
        )
    with c4:
        st.write("")
        st.write("")
        ornek_clicked = st.button(tr("🔎 Örnek Dene"), key="borsa_compare_example_btn", use_container_width=True)

    if ornek_clicked:
        symbol_a, symbol_b = ORNEK_SEMBOL, ORNEK_ENDEKS

    compare_clicked = st.button(
        tr("Karşılaştır"), type="primary",
        disabled=not (symbol_a.strip() and symbol_b.strip()),
        key="borsa_compare_btn",
    )

    if (compare_clicked and symbol_a.strip() and symbol_b.strip()) or ornek_clicked:
        target_a = symbol_a.strip() or ORNEK_SEMBOL
        target_b = symbol_b.strip() or ORNEK_ENDEKS
        range_value = RANGE_OPTIONS[range_label]
        with st.spinner(trf("'{a}' ve '{b}' için fiyat verileri çekiliyor...", a=target_a, b=target_b)):
            df_a, result_a, warnings_a = _cached_fetch(target_a, range_value)
            df_b, result_b, warnings_b = _cached_fetch(target_b, range_value)
        st.session_state["borsa_compare_data"] = {
            "a": {"name": target_a, "df": df_a, "result": result_a, "warnings": warnings_a},
            "b": {"name": target_b, "df": df_b, "result": result_b, "warnings": warnings_b},
        }

    if "borsa_compare_data" not in st.session_state:
        st.info(tr("Karşılaştırmak için iki sembol girip 'Karşılaştır' butonuna tıklayın, popüler listeden seçin veya 'Örnek Dene' ile hemen deneyin."))
        return

    data = st.session_state["borsa_compare_data"]
    a, b = data["a"], data["b"]

    if a["df"].empty and b["df"].empty:
        st.warning(tr("Her iki sembol için de fiyat verisi bulunamadı. Sembolleri kontrol edip tekrar deneyin."))
        return
    if a["df"].empty:
        st.warning(trf("'{name}' için fiyat verisi bulunamadı; yalnızca diğer sembol gösteriliyor.", name=a["name"]))
    if b["df"].empty:
        st.warning(trf("'{name}' için fiyat verisi bulunamadı; yalnızca diğer sembol gösteriliyor.", name=b["name"]))

    color_a, color_b = CATEGORICAL[0], CATEGORICAL[6]

    with st.container(border=True):
        st.markdown(tr("**Normalize Edilmiş Getiri Karşılaştırması (dönem başı = 100)**"))
        fig = go.Figure()
        for entry, color in [(a, color_a), (b, color_b)]:
            if entry["df"].empty:
                continue
            base = float(entry["df"]["kapanış"].iloc[0])
            normalized = entry["df"]["kapanış"] / base * 100
            fig.add_trace(go.Scatter(x=entry["df"]["tarih"], y=normalized, mode="lines", name=entry["name"], line=dict(color=color)))
        apply_layout(fig, height=380)
        st.plotly_chart(fig, width="stretch", theme=None)

        cols = st.columns(2)
        for col, entry in [(cols[0], a), (cols[1], b)]:
            with col:
                st.markdown(f"**{entry['name']}**")
                if entry["df"].empty:
                    st.caption(tr("Veri yok."))
                    continue
                r = entry["result"]
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric(tr("Dönem Getirisi"), f"{r['dönem_getiri_yüzde']:+.2f}%")
                mc2.metric(trf("Güncel Fiyat ({para})", para=r["para_birimi"]), f"{r['güncel_fiyat']:.2f}")
                mc3.metric(tr("Volatilite"), f"{r['volatilite_yüzde']:.2f}%")

    all_warnings = a["warnings"] + b["warnings"]
    if all_warnings:
        with st.expander(tr("Uyarılar")):
            for w in all_warnings:
                st.caption(f"⚠️ {tr(w)}")

    st.markdown(tr("### Dışa Aktar"))
    c1, c2 = st.columns(2)
    with c1:
        json_payload = {
            "karsilastirma": [
                {"sembol": entry["name"], "ozet": entry["result"]}
                for entry in (a, b) if not entry["df"].empty
            ],
        }
        st.download_button(
            tr("JSON indir"), data=to_json_bytes(json_payload),
            file_name=f"{a['name']}_vs_{b['name']}_karsilastirma.json", mime="application/json",
            key="borsa_compare_json",
        )
    with c2:
        blocks = [
            {"heading": tr("Dönem Getirisi Karşılaştırması"), "type": "table", "content": (
                [tr("Sembol"), tr("Dönem Getirisi %"), tr("Güncel Fiyat"), tr("Volatilite %")],
                [
                    [entry["name"], f"{entry['result']['dönem_getiri_yüzde']:+.2f}",
                     f"{entry['result']['güncel_fiyat']:.2f}", f"{entry['result']['volatilite_yüzde']:.2f}"]
                    for entry in (a, b) if not entry["df"].empty
                ],
            )},
        ]
        pdf_bytes = build_pdf(trf("Sembol Karşılaştırma Raporu — {a} vs {b}", a=a["name"], b=b["name"]), blocks)
        st.download_button(
            tr("PDF indir"), data=pdf_bytes,
            file_name=f"{a['name']}_vs_{b['name']}_karsilastirma.pdf", mime="application/pdf",
            key="borsa_compare_pdf",
        )

    st.caption(tr(
        "Not: Volatilite ve trend göstergeleri kural tabanlı sezgisellerdir; "
        "yatırım tavsiyesi niteliği taşımaz."
    ))
