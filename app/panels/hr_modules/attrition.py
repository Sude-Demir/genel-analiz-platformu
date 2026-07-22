"""Çalışan Kaybı (Attrition) Tahmini alt modülü — Dataset Analizi panelinin altında,
dahili İK veri seti aktifken listelenen özel analiz modüllerinden biridir.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from export_utils import build_pdf, to_json_bytes
from model import CATEGORICAL_FEATURES, NUMERIC_FEATURES, explain_instance, get_feature_importances
from theme import CATEGORICAL, STATUS, apply_layout, risk_status


def render_risk_calculator(emp: pd.DataFrame, pipeline, explainer, key_prefix: str = "attr"):
    """Varsayımsal/gerçek bir çalışan için elle veri girip anlık risk skoru tahmini alınan form.

    Hem Dataset Analizi panelindeki "Çalışan Kaybı Tahmini" alt modülünden hem de öne çıkan
    Tahmin panelinden çağrılır (tek kaynak, `key_prefix` ile widget anahtar çakışması önlenir).
    """
    st.subheader("Varsayımsal Çalışan İçin Risk Skoru Hesapla")

    defaults = {}
    for col in NUMERIC_FEATURES:
        defaults[col] = float(emp[col].median())
    for col in CATEGORICAL_FEATURES:
        defaults[col] = emp[col].mode()[0]

    c1, c2, c3 = st.columns(3)
    with c1:
        departman = st.selectbox("Departman", emp["Departman"].unique(), key=f"{key_prefix}_dept")
        pozisyon_options = emp[emp["Departman"] == departman]["Pozisyon"].unique()
        pozisyon = st.selectbox("Pozisyon", pozisyon_options, key=f"{key_prefix}_pos")
        overtime = st.selectbox("Fazla Mesai", ["Evet", "Hayır"], key=f"{key_prefix}_ot")
        medeni = st.selectbox("Medeni Durum", emp["MedeniDurum"].unique(), key=f"{key_prefix}_medeni")
    with c2:
        yas = st.slider("Yaş", 18, 60, 32, key=f"{key_prefix}_yas")
        gelir = st.number_input("Aylık Gelir ($)", 1000, 20000, 5000, step=500, key=f"{key_prefix}_gelir")
        kidem = st.slider("Şirkette Kıdem (Yıl)", 0, 40, 3, key=f"{key_prefix}_kidem")
        rol_kidem = st.slider("Mevcut Roldeki Kıdem (Yıl)", 0, 20, 2, key=f"{key_prefix}_rolkidem")
    with c3:
        is_tatmini = st.slider("İş Tatmini (1-4)", 1, 4, 3, key=f"{key_prefix}_tatmin")
        wlb = st.slider("İş-Yaşam Dengesi (1-4)", 1, 4, 3, key=f"{key_prefix}_wlb")
        mesafe = st.slider("Ev Uzaklığı (km)", 1, 30, 10, key=f"{key_prefix}_mesafe")
        seyahat = st.selectbox("Seyahat Sıklığı", emp["SeyahatSikligi"].unique(), key=f"{key_prefix}_seyahat")

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
            title={"text": "Ayrılma Olasılığı"},
        ))
        apply_layout(fig, height=320)
        st.plotly_chart(fig, width="stretch", theme=None)

        status_labels = {"good": "Düşük Risk", "warning": "Orta Risk", "serious": "Yüksek Risk", "critical": "Kritik Risk"}
        st.markdown(f"**Durum:** :{'green' if status=='good' else 'orange' if status in ('warning','serious') else 'red'}[{status_labels[status]}]")

        contributions = None
        if explainer is not None:
            st.subheader("Bu Tahmini Etkileyen Faktörler")
            contributions = explain_instance(pipeline, explainer, input_row)
            top_idx = contributions.abs().sort_values(ascending=False).head(8).index
            top_contrib = contributions[top_idx].sort_values()
            colors = [STATUS["critical"] if v > 0 else STATUS["good"] for v in top_contrib.values]
            fig3 = go.Figure(go.Bar(
                x=top_contrib.values, y=top_contrib.index, orientation="h",
                marker_color=colors,
            ))
            apply_layout(fig3, showlegend=False, xaxis_title="Risk Skoruna Etkisi (SHAP)")
            st.plotly_chart(fig3, width="stretch", theme=None)

    st.markdown("### Dışa Aktar")
    result = {
        "girdi": overrides,
        "risk_skoru": float(prob),
        "durum": status_labels[status],
        "en_etkili_faktorler": contributions.abs().sort_values(ascending=False).head(8).to_dict() if contributions is not None else None,
    }
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "JSON indir", data=to_json_bytes(result),
            file_name="risk_skoru_sonucu.json", mime="application/json", key=f"{key_prefix}_json",
        )
    with c2:
        pdf_bytes = build_pdf("Çalışan Kaybı Risk Skoru Raporu", [
            {"heading": "Girdi", "type": "table", "content": (["Alan", "Değer"], list(overrides.items()))},
            {"heading": "Sonuç", "type": "paragraph", "content": f"Risk Skoru: %{prob*100:.1f} — Durum: {status_labels[status]}"},
        ])
        st.download_button(
            "PDF indir", data=pdf_bytes,
            file_name="risk_skoru_raporu.pdf", mime="application/pdf", key=f"{key_prefix}_pdf",
        )


def render(emp: pd.DataFrame, pipeline, explainer):
    X_all = emp[CATEGORICAL_FEATURES + NUMERIC_FEATURES]
    emp = emp.copy()
    with st.spinner("Tüm çalışanlar için risk skorları hesaplanıyor..."):
        emp["RiskSkoru"] = pipeline.predict_proba(X_all)[:, 1]

    tab1, tab2, tab3 = st.tabs(["Model Özeti", "Risk Skoru Hesaplayıcı", "En Riskli Çalışanlar"])

    with tab1:
        st.subheader("Modeli Etkileyen En Önemli Faktörler")
        with st.container(border=True):
            importances = get_feature_importances(pipeline).head(15).sort_values()
            fig = px.bar(
                importances, x=importances.values, y=importances.index, orientation="h",
                labels={"x": "Önem Derecesi", "y": ""},
                color_discrete_sequence=[CATEGORICAL[0]],
            )
            apply_layout(fig, showlegend=False)
            st.plotly_chart(fig, width="stretch", theme=None)
            st.caption(
                "Model: LightGBM (Gradient Boosting) sınıflandırıcı, IBM HR Analytics Employee Attrition veri seti üzerinde eğitildi."
            )

    with tab2:
        render_risk_calculator(emp, pipeline, explainer, key_prefix="attr")

    with tab3:
        st.subheader("Mevcut Çalışanlar Arasında En Yüksek Riskli 20 Kişi")
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
                "CSV indir", data=top_risk[display_cols].to_csv(index=False).encode("utf-8"),
                file_name="en_riskli_calisanlar.csv", mime="text/csv", key="attr_top_csv",
            )
        with c2:
            st.download_button(
                "JSON indir", data=to_json_bytes(top_risk[display_cols].to_dict(orient="records")),
                file_name="en_riskli_calisanlar.json", mime="application/json", key="attr_top_json",
            )
