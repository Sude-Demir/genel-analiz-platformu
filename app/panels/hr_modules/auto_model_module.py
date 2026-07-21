"""Otomatik Model Eğitimi & Açıklama — herhangi bir yüklenen veri setinde çalışan genel amaçlı alt modül.

İK'ya özgü diğer alt modüllerin (Çalışan Kaybı Tahmini, Aksiyon Merkezi vb.) aksine
belirli bir şemaya bağlı değildir; kullanıcının seçtiği hedef kolona göre otomatik
bir sınıflandırma/regresyon modeli eğitir ve SHAP ile açıklar.
"""
import pandas as pd
import plotly.express as px
import shap
import streamlit as st

from auto_model import (
    detect_task_type,
    explain_batch,
    get_feature_importances,
    infer_column_types,
    train_auto_model,
)
from export_utils import build_pdf, to_json_bytes
from theme import CATEGORICAL, apply_layout


def render(df: pd.DataFrame, state_prefix: str):
    st.subheader("Otomatik Model Eğitimi ve Açıklama")
    st.caption("Seçtiğiniz hedef kolona göre otomatik bir sınıflandırma/regresyon modeli eğitir.")

    target_col = st.selectbox("Hedef Kolon (tahmin edilecek)", df.columns, index=len(df.columns) - 1, key=f"{state_prefix}_target")
    task_type = detect_task_type(df[target_col])
    st.caption(f"Otomatik algılanan görev türü: **{'Sınıflandırma' if task_type == 'classification' else 'Regresyon'}**")

    result_key = f"{state_prefix}_auto_model_result"

    if st.button("Modeli Eğit", type="primary", key=f"{state_prefix}_train_btn"):
        clean_df = df.dropna(subset=[target_col])
        numeric_cols, categorical_cols = infer_column_types(clean_df, exclude=[target_col])
        if not numeric_cols and not categorical_cols:
            st.error("Hedef kolon dışında kullanılabilir özellik kolonu bulunamadı.")
        else:
            with st.spinner("Model eğitiliyor..."):
                result = train_auto_model(clean_df, target_col, categorical_cols, numeric_cols)
            st.session_state[result_key] = result

    result = st.session_state.get(result_key)
    if not (result and result["target_col"] == target_col):
        return

    metrics = result["metrics"]
    if result["task_type"] == "classification":
        m1, m2 = st.columns(2)
        m1.metric("Doğruluk (Accuracy)", f"{metrics['accuracy']:.1%}")
        m2.metric("ROC-AUC", f"{metrics['roc_auc']:.3f}" if metrics["roc_auc"] is not None else "—")
    else:
        m1, m2 = st.columns(2)
        m1.metric("R²", f"{metrics['r2']:.3f}")
        m2.metric("RMSE", f"{metrics['rmse']:.2f}")

    st.markdown("**Özellik Önem Sırası**")
    importances = get_feature_importances(
        result["pipeline"], result["categorical_features"], result["numeric_features"]
    ).head(15).sort_values()
    fig = px.bar(
        importances, x=importances.values, y=importances.index, orientation="h",
        labels={"x": "Önem Derecesi", "y": ""},
        color_discrete_sequence=[CATEGORICAL[0]],
    )
    apply_layout(fig, showlegend=False)
    st.plotly_chart(fig, width="stretch", theme=None)

    explanation_row = None
    if result["task_type"] == "regression" or result.get("n_classes") == 2:
        st.markdown("**Tekil Satır İçin SHAP Açıklaması**")
        row_idx = st.selectbox("Açıklanacak satır (index)", df.index[:200], key=f"{state_prefix}_row_idx")
        X_row = df.loc[[row_idx], result["categorical_features"] + result["numeric_features"]]

        explainer = shap.TreeExplainer(result["pipeline"].named_steps["model"])
        contrib = explain_batch(
            result["pipeline"], explainer, X_row,
            result["categorical_features"], result["numeric_features"],
        ).iloc[0]
        top = contrib.reindex(contrib.abs().sort_values(ascending=False).index).head(10).sort_values()
        colors = ["#d03b3b" if v > 0 else "#0ca30c" for v in top.values]
        fig2 = px.bar(top, x=top.values, y=top.index, orientation="h", labels={"x": "Katkı", "y": ""})
        fig2.update_traces(marker_color=colors)
        apply_layout(fig2, showlegend=False)
        st.plotly_chart(fig2, width="stretch", theme=None)
        explanation_row = {"satir_index": str(row_idx), "shap_katkilari": top.to_dict()}
    else:
        st.caption("Not: SHAP açıklaması şu an sadece regresyon ve iki sınıflı (binary) sınıflandırma için gösteriliyor.")

    st.markdown("### Dışa Aktar")
    export_result = {
        "hedef_kolon": target_col,
        "gorev_turu": result["task_type"],
        "metrikler": metrics,
        "ozellik_onem_sirasi": importances.to_dict(),
        "shap_aciklamasi": explanation_row,
    }
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "JSON indir", data=to_json_bytes(export_result),
            file_name="otomatik_model_sonucu.json", mime="application/json", key=f"{state_prefix}_json",
        )
    with c2:
        metric_lines = [f"{k}: {v}" for k, v in metrics.items() if not isinstance(v, dict)]
        pdf_bytes = build_pdf("Otomatik Model & Açıklama Raporu", [
            {"heading": "Model Bilgisi", "type": "bullets", "content": [
                f"Hedef kolon: {target_col}", f"Görev türü: {result['task_type']}",
            ] + metric_lines},
            {"heading": "En Önemli Özellikler", "type": "table", "content": (
                ["Özellik", "Önem Derecesi"], [[k, round(v, 4)] for k, v in importances.sort_values(ascending=False).head(15).items()],
            )},
        ])
        st.download_button(
            "PDF indir", data=pdf_bytes,
            file_name="otomatik_model_raporu.pdf", mime="application/pdf", key=f"{state_prefix}_pdf",
        )
