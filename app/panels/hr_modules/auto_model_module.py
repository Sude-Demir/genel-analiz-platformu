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
from translator import tr, trf
from theme import CATEGORICAL, apply_layout


def render_manual_prediction(df: pd.DataFrame, result: dict, state_prefix: str):
    """Eğitilmiş otomatik modele elle girilen tek bir satır için tahmin alır.

    `result`, `train_auto_model()` çıktısıdır (bkz. `auto_model.py`). Kategorik özellikler
    için veri setindeki benzersiz değerlerden seçim, sayısal özellikler için medyan varsayılanlı
    giriş kutuları üretilir; ardından `result["pipeline"]` ile tahmin yapılır.
    """
    st.subheader(tr("Elle Veri Girerek Tahmin Al"))

    categorical_features = result["categorical_features"]
    numeric_features = result["numeric_features"]

    overrides = {}
    cols = st.columns(3) if (categorical_features or numeric_features) else []
    fields = list(categorical_features) + list(numeric_features)
    for i, col in enumerate(fields):
        target_col_widget = cols[i % 3] if cols else st
        with target_col_widget:
            if col in categorical_features:
                options = df[col].dropna().unique()
                overrides[col] = st.selectbox(col, options, key=f"{state_prefix}_manual_{col}")
            else:
                default_val = float(df[col].median()) if df[col].notna().any() else 0.0
                overrides[col] = st.number_input(col, value=default_val, key=f"{state_prefix}_manual_{col}")

    input_row = pd.DataFrame([overrides])[categorical_features + numeric_features]

    if st.button(tr("Tahmin Et"), type="primary", key=f"{state_prefix}_manual_predict_btn"):
        pipeline = result["pipeline"]
        with st.container(border=True):
            if result["task_type"] == "classification":
                pred_code = pipeline.predict(input_row)[0]
                proba = pipeline.predict_proba(input_row)[0]
                class_labels = result.get("class_labels")
                if class_labels:
                    # pred_code, hedef kategorikse cat-kod (0..n-1), sayısalsa ham değerdir;
                    # her iki durumda da classes_ içindeki konumu class_labels'taki karşılığını verir.
                    classes_ = list(pipeline.named_steps["model"].classes_)
                    pred_label = class_labels[classes_.index(pred_code)]
                else:
                    pred_label = pred_code
                st.metric(f"{tr('Tahmin Edilen')} {result['target_col']}", str(pred_label))
                if result.get("n_classes") == 2:
                    st.caption(trf("Pozitif sınıf olasılığı: %{val:.1f}", val=proba[1] * 100))
                else:
                    sinif_col, olasilik_col = tr("Sınıf"), tr("Olasılık")
                    proba_df = pd.DataFrame({
                        sinif_col: class_labels if class_labels else list(range(len(proba))),
                        olasilik_col: proba,
                    }).sort_values(olasilik_col, ascending=False)
                    st.dataframe(proba_df.style.format({olasilik_col: "{:.1%}"}), width="stretch", hide_index=True)
            else:
                pred_value = pipeline.predict(input_row)[0]
                st.metric(f"{tr('Tahmin Edilen')} {result['target_col']}", f"{pred_value:.2f}")

            if result["task_type"] == "regression" or result.get("n_classes") == 2:
                explainer = shap.TreeExplainer(pipeline.named_steps["model"])
                contrib = explain_batch(
                    pipeline, explainer, input_row, categorical_features, numeric_features,
                ).iloc[0]
                top = contrib.reindex(contrib.abs().sort_values(ascending=False).index).head(8).sort_values()
                colors = ["#d03b3b" if v > 0 else "#0ca30c" for v in top.values]
                fig = px.bar(top, x=top.values, y=top.index, orientation="h", labels={"x": tr("Katkı"), "y": ""})
                fig.update_traces(marker_color=colors)
                apply_layout(fig, showlegend=False)
                st.plotly_chart(fig, width="stretch", theme=None)


def render(df: pd.DataFrame, state_prefix: str):
    st.subheader(tr("Otomatik Model Eğitimi ve Açıklama"))
    st.caption(tr("Seçtiğiniz hedef kolona göre otomatik bir sınıflandırma/regresyon modeli eğitir."))

    target_col = st.selectbox(tr("Hedef Kolon (tahmin edilecek)"), df.columns, index=len(df.columns) - 1, key=f"{state_prefix}_target")
    task_type = detect_task_type(df[target_col])
    task_label = tr("Sınıflandırma") if task_type == "classification" else tr("Regresyon")
    st.caption(trf("Otomatik algılanan görev türü: **{label}**", label=task_label))

    result_key = f"{state_prefix}_auto_model_result"

    if st.button(tr("Modeli Eğit"), type="primary", key=f"{state_prefix}_train_btn"):
        clean_df = df.dropna(subset=[target_col])
        numeric_cols, categorical_cols = infer_column_types(clean_df, exclude=[target_col])
        if not numeric_cols and not categorical_cols:
            st.error(tr("Hedef kolon dışında kullanılabilir özellik kolonu bulunamadı."))
        else:
            with st.spinner(tr("Model eğitiliyor...")):
                result = train_auto_model(clean_df, target_col, categorical_cols, numeric_cols)
            st.session_state[result_key] = result

    result = st.session_state.get(result_key)
    if not (result and result["target_col"] == target_col):
        return

    metrics = result["metrics"]
    with st.container(border=True):
        if result["task_type"] == "classification":
            m1, m2 = st.columns(2)
            m1.metric(tr("Doğruluk (Accuracy)"), f"{metrics['accuracy']:.1%}")
            m2.metric("ROC-AUC", f"{metrics['roc_auc']:.3f}" if metrics["roc_auc"] is not None else "—")
        else:
            m1, m2 = st.columns(2)
            m1.metric("R²", f"{metrics['r2']:.3f}")
            m2.metric("RMSE", f"{metrics['rmse']:.2f}")

        st.markdown(tr("**Özellik Önem Sırası**"))
        importances = get_feature_importances(
            result["pipeline"], result["categorical_features"], result["numeric_features"]
        ).head(15).sort_values()
        fig = px.bar(
            importances, x=importances.values, y=importances.index, orientation="h",
            labels={"x": tr("Önem Derecesi"), "y": ""},
            color_discrete_sequence=[CATEGORICAL[0]],
        )
        apply_layout(fig, showlegend=False)
        st.plotly_chart(fig, width="stretch", theme=None)

    render_manual_prediction(df, result, state_prefix)

    explanation_row = None
    if result["task_type"] == "regression" or result.get("n_classes") == 2:
        with st.container(border=True):
            st.markdown(tr("**Tekil Satır İçin SHAP Açıklaması**"))
            row_idx = st.selectbox(tr("Açıklanacak satır (index)"), df.index[:200], key=f"{state_prefix}_row_idx")
            X_row = df.loc[[row_idx], result["categorical_features"] + result["numeric_features"]]

            explainer = shap.TreeExplainer(result["pipeline"].named_steps["model"])
            contrib = explain_batch(
                result["pipeline"], explainer, X_row,
                result["categorical_features"], result["numeric_features"],
            ).iloc[0]
            top = contrib.reindex(contrib.abs().sort_values(ascending=False).index).head(10).sort_values()
            colors = ["#d03b3b" if v > 0 else "#0ca30c" for v in top.values]
            fig2 = px.bar(top, x=top.values, y=top.index, orientation="h", labels={"x": tr("Katkı"), "y": ""})
            fig2.update_traces(marker_color=colors)
            apply_layout(fig2, showlegend=False)
            st.plotly_chart(fig2, width="stretch", theme=None)
            explanation_row = {"satir_index": str(row_idx), "shap_katkilari": top.to_dict()}
    else:
        st.caption(tr("Not: SHAP açıklaması şu an sadece regresyon ve iki sınıflı (binary) sınıflandırma için gösteriliyor."))

    st.markdown(tr("### Dışa Aktar"))
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
            tr("JSON indir"), data=to_json_bytes(export_result),
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
            tr("PDF indir"), data=pdf_bytes,
            file_name="otomatik_model_raporu.pdf", mime="application/pdf", key=f"{state_prefix}_pdf",
        )
