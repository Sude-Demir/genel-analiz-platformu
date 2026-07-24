"""Çalışan Kaybı (Attrition) Tahmini alt modülü."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from export_utils import build_pdf, to_json_bytes
from translator import tr, trf
from model import CATEGORICAL_FEATURES, NUMERIC_FEATURES, explain_instance, get_feature_importances
from theme import CATEGORICAL, MUTED, SEQUENTIAL_BLUE, STATUS, apply_layout, risk_status


def render_risk_calculator(emp: pd.DataFrame, pipeline, explainer, key_prefix: str = "attr"):
    st.subheader(tr("Varsayımsal Çalışan İçin Risk Skoru Hesapla"))

    defaults = {}
    for col in NUMERIC_FEATURES:
        defaults[col] = float(emp[col].median())
    for col in CATEGORICAL_FEATURES:
        defaults[col] = emp[col].mode()[0]

    c1, c2, c3 = st.columns(3)
    with c1:
        departman = st.selectbox(tr("Departman"), emp["Departman"].unique(), key=f"{key_prefix}_dept")
        pozisyon_options = emp[emp["Departman"] == departman]["Pozisyon"].unique()
        pozisyon = st.selectbox(tr("Pozisyon"), pozisyon_options, key=f"{key_prefix}_pos")
        overtime = st.selectbox(tr("Fazla Mesai"), ["Evet", "Hayır"], key=f"{key_prefix}_ot")
        medeni = st.selectbox(tr("Medeni Durum"), emp["MedeniDurum"].unique(), key=f"{key_prefix}_medeni")
    with c2:
        yas = st.slider(tr("Yaş"), 18, 60, 32, key=f"{key_prefix}_yas")
        gelir = st.number_input(tr("Aylık Gelir ($)"), 1000, 20000, 5000, step=500, key=f"{key_prefix}_gelir")
        kidem = st.slider(tr("Şirkette Kıdem (Yıl)"), 0, 40, 3, key=f"{key_prefix}_kidem")
        rol_kidem = st.slider(tr("Mevcut Roldeki Kıdem (Yıl)"), 0, 20, 2, key=f"{key_prefix}_rolkidem")
    with c3:
        is_tatmini = st.slider(tr("İş Tatmini (1-4)"), 1, 4, 3, key=f"{key_prefix}_tatmin")
        wlb = st.slider(tr("İş-Yaşam Dengesi (1-4)"), 1, 4, 3, key=f"{key_prefix}_wlb")
        mesafe = st.slider(tr("Ev Uzaklığı (km)"), 1, 30, 10, key=f"{key_prefix}_mesafe")
        seyahat = st.selectbox(tr("Seyahat Sıklığı"), emp["SeyahatSikligi"].unique(), key=f"{key_prefix}_seyahat")

    overrides = {
        "Departman": departman, "Pozisyon": pozisyon, "FazlaMesai": overtime,
        "MedeniDurum": medeni, "SeyahatSikligi": seyahat,
        "Yas": yas, "AylikGelir": gelir, "SirketteKidemYili": kidem,
        "MevcutRoldeKidemYili": rol_kidem, "EvUzakligiKm": mesafe,
        "IsTatmini": is_tatmini, "IsYasamDengesi": wlb,
    }
    input_row = pd.DataFrame([{**defaults, **overrides}])[CATEGORICAL_FEATURES + NUMERIC_FEATURES]

    prob = pipeline.predict_proba(input_row)[0, 1]
    status = risk_status(prob)

    status_labels = {
        "good": tr("Düşük Risk"),
        "warning": tr("Orta Risk"),
        "serious": tr("Yüksek Risk"),
        "critical": tr("Kritik Risk"),
    }

    with st.container(border=True):
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=prob * 100,
            number={"suffix": "%"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": STATUS[status]},
                "steps": [
                    {"range": [0, 25], "color": "#f0efec"},
                    {"range": [25, 50], "color": "#f5e6c8"},
                    {"range": [50, 75], "color": "#f7dccb"},
                    {"range": [75, 100], "color": "#f6d3d3"},
                ],
            },
            title={"text": tr("Ayrılma Olasılığı")},
        ))
        apply_layout(fig, height=320)
        st.plotly_chart(fig, width="stretch", theme=None)

        color_map = {"good": "green", "warning": "orange", "serious": "orange", "critical": "red"}
        st.markdown(f"**{tr('Durum')}:** :{color_map[status]}[{status_labels[status]}]")

        contributions = None
        if explainer is not None:
            st.subheader(tr("Bu Tahmini Etkileyen Faktörler"))
            contributions = explain_instance(pipeline, explainer, input_row)
            top_idx = contributions.abs().sort_values(ascending=False).head(8).index
            top_contrib = contributions[top_idx].sort_values()
            colors = [STATUS["critical"] if v > 0 else STATUS["good"] for v in top_contrib.values]
            fig3 = go.Figure(go.Bar(
                x=top_contrib.values, y=top_contrib.index, orientation="h",
                marker_color=colors,
            ))
            apply_layout(fig3, showlegend=False, xaxis_title=tr("Risk Skoruna Etkisi (SHAP)"))
            st.plotly_chart(fig3, width="stretch", theme=None)

    st.markdown(tr("### Dışa Aktar"))
    result_data = {
        "girdi": overrides,
        "risk_skoru": float(prob),
        "durum": status_labels[status],
        "en_etkili_faktorler": contributions.abs().sort_values(ascending=False).head(8).to_dict() if contributions is not None else None,
    }
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            tr("JSON indir"), data=to_json_bytes(result_data),
            file_name="risk_skoru_sonucu.json", mime="application/json", key=f"{key_prefix}_json",
        )
    with c2:
        pdf_bytes = build_pdf(tr("Çalışan Kaybı Risk Skoru Raporu"), [
            {"heading": tr("Girdi"), "type": "table", "content": ([tr("Alan"), tr("Değer")], list(overrides.items()))},
            {"heading": tr("Sonuç"), "type": "paragraph", "content": trf(
                "Risk Skoru: %{skor:.1f} — Durum: {durum}", skor=prob * 100, durum=status_labels[status],
            )},
        ])
        st.download_button(
            tr("PDF indir"), data=pdf_bytes,
            file_name="risk_skoru_raporu.pdf", mime="application/pdf", key=f"{key_prefix}_pdf",
        )


def render(emp: pd.DataFrame, pipeline, explainer, metrics: dict | None = None):
    X_all = emp[CATEGORICAL_FEATURES + NUMERIC_FEATURES]
    emp = emp.copy()
    with st.spinner(tr("Tüm çalışanlar için risk skorları hesaplanıyor...")):
        emp["RiskSkoru"] = pipeline.predict_proba(X_all)[:, 1]

    tab1, tab2, tab3 = st.tabs([tr("Model Özeti"), tr("Risk Skoru Hesaplayıcı"), tr("En Riskli Çalışanlar")])

    with tab1:
        st.subheader(tr("Modeli Etkileyen En Önemli Faktörler"))
        with st.container(border=True):
            importances = get_feature_importances(pipeline).head(15).sort_values()
            fig = px.bar(
                importances, x=importances.values, y=importances.index, orientation="h",
                labels={"x": tr("Önem Derecesi"), "y": ""},
                color_discrete_sequence=[CATEGORICAL[0]],
            )
            apply_layout(fig, showlegend=False)
            st.plotly_chart(fig, width="stretch", theme=None)
            if metrics:
                st.caption(trf(
                    "Model: {model} sınıflandırıcı — CV ile karşılaştırılan adaylar arasından seçildi, "
                    "IBM HR Analytics Employee Attrition veri seti üzerinde eğitildi.",
                    model=metrics["selected_model"],
                ))
            else:
                st.caption(tr("Model: LightGBM (Gradient Boosting) sınıflandırıcı, IBM HR Analytics Employee Attrition veri seti üzerinde eğitildi."))

        if metrics is None:
            st.caption(tr("Model karşılaştırma ve değerlendirme detayları için modeli `python src/model.py` ile yeniden eğitin."))
        else:
            st.subheader(tr("Model Karşılaştırması"))
            with st.container(border=True):
                comp_df = pd.DataFrame(metrics["model_comparison"])[["model", "cv_roc_auc"]]
                comp_df.columns = [tr("Model"), "CV ROC-AUC"]
                st.dataframe(comp_df.style.format({"CV ROC-AUC": "{:.3f}"}), width="stretch", hide_index=True)
                st.caption(trf("Seçilen model: **{model}**", model=metrics["selected_model"]))

            st.subheader(tr("Test Seti Performansı"))
            with st.container(border=True):
                m1, m2 = st.columns(2)
                m1.metric(tr("Doğruluk (Accuracy)"), f"{metrics['test_metrics']['accuracy']:.1%}")
                m2.metric("ROC-AUC", f"{metrics['test_metrics']['roc_auc']:.3f}")

                labels = [tr("Kalıyor"), tr("Ayrılıyor")]
                eval_cols = st.columns(2)
                with eval_cols[0]:
                    st.markdown(tr("**Karışıklık Matrisi (Confusion Matrix)**"))
                    fig_cm = px.imshow(
                        metrics["confusion_matrix"], x=labels, y=labels, text_auto=True,
                        labels={"x": tr("Tahmin Edilen"), "y": tr("Gerçek"), "color": tr("Adet")},
                        color_continuous_scale=SEQUENTIAL_BLUE,
                    )
                    apply_layout(fig_cm)
                    st.plotly_chart(fig_cm, width="stretch", theme=None)
                with eval_cols[1]:
                    st.markdown(tr("**ROC Eğrisi**"))
                    roc = metrics["roc_curve"]
                    fig_roc = go.Figure()
                    fig_roc.add_trace(go.Scatter(
                        x=roc["fpr"], y=roc["tpr"], mode="lines",
                        name="ROC", line=dict(color=CATEGORICAL[0]),
                    ))
                    fig_roc.add_trace(go.Scatter(
                        x=[0, 1], y=[0, 1], mode="lines",
                        name=tr("Rastgele"), line=dict(color=MUTED, dash="dash"),
                    ))
                    apply_layout(fig_roc, xaxis_title=tr("Yanlış Pozitif Oranı"), yaxis_title=tr("Doğru Pozitif Oranı"))
                    st.plotly_chart(fig_roc, width="stretch", theme=None)

            st.subheader(tr("Öğrenme ve Kalibrasyon Eğrileri"))
            with st.container(border=True):
                curve_cols = st.columns(2)
                with curve_cols[0]:
                    st.markdown(tr("**Öğrenme Eğrisi (Learning Curve)**"))
                    lc = metrics["learning_curve"]
                    fig_lc = go.Figure()
                    fig_lc.add_trace(go.Scatter(
                        x=lc["train_sizes"], y=lc["train_scores_mean"], mode="lines+markers",
                        name=tr("Eğitim Skoru"), line=dict(color=CATEGORICAL[0]),
                    ))
                    fig_lc.add_trace(go.Scatter(
                        x=lc["train_sizes"], y=lc["test_scores_mean"], mode="lines+markers",
                        name=tr("Doğrulama Skoru"), line=dict(color=CATEGORICAL[1]),
                    ))
                    apply_layout(fig_lc, xaxis_title=tr("Eğitim Örneği Sayısı"), yaxis_title="ROC-AUC")
                    st.plotly_chart(fig_lc, width="stretch", theme=None)
                with curve_cols[1]:
                    st.markdown(tr("**Kalibrasyon Eğrisi**"))
                    cal = metrics["calibration_curve"]
                    fig_cal = go.Figure()
                    fig_cal.add_trace(go.Scatter(
                        x=cal["prob_pred"], y=cal["prob_true"], mode="lines+markers",
                        name=tr("Model"), line=dict(color=CATEGORICAL[0]),
                    ))
                    fig_cal.add_trace(go.Scatter(
                        x=[0, 1], y=[0, 1], mode="lines",
                        name=tr("Mükemmel Kalibrasyon"), line=dict(color=MUTED, dash="dash"),
                    ))
                    apply_layout(fig_cal, xaxis_title=tr("Tahmin Edilen Olasılık"), yaxis_title=tr("Gözlenen Sıklık"))
                    st.plotly_chart(fig_cal, width="stretch", theme=None)

    with tab2:
        render_risk_calculator(emp, pipeline, explainer, key_prefix="attr")

    with tab3:
        st.subheader(tr("Mevcut Çalışanlar Arasında En Yüksek Riskli 20 Kişi"))
        top_risk = emp.sort_values("RiskSkoru", ascending=False).head(20)
        display_cols = ["CalisanID", "Departman", "Pozisyon", "SirketteKidemYili", "IsTatmini", "RiskSkoru"]
        with st.container(border=True):
            st.dataframe(
                top_risk[display_cols].style.format({"RiskSkoru": "{:.1%}"}),
                width="stretch", hide_index=True,
            )
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                tr("CSV indir"), data=top_risk[display_cols].to_csv(index=False).encode("utf-8"),
                file_name="en_riskli_calisanlar.csv", mime="text/csv", key="attr_top_csv",
            )
        with c2:
            st.download_button(
                tr("JSON indir"), data=to_json_bytes(top_risk[display_cols].to_dict(orient="records")),
                file_name="en_riskli_calisanlar.json", mime="application/json", key="attr_top_json",
            )
