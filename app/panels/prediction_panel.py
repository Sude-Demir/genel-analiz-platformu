"""Tahmin paneli — öne çıkan, doğrudan elle veri girip anlık tahmin alınan panel.

İki mod sunar: (1) dahili İK modeliyle çalışan ayrılma (attrition) tahmini — mevcut
`hr_modules.attrition` içindeki hesaplayıcıyı yeniden kullanır; (2) kullanıcının yüklediği
herhangi bir veri setinde model eğitip elle satır girerek tahmin alma — mevcut
`hr_modules.auto_model_module` içindeki eğitim akışını ve yeni eklenen elle-tahmin
fonksiyonunu yeniden kullanır. Yeni bir modelleme mantığı içermez; sadece mevcut
`src/` fonksiyonlarını çağıran panellerin girişini tek bir öne çıkan yere toplar.
"""
import pandas as pd
import streamlit as st

from data_loader import data_ready, load_employees, load_explainer, load_model
from panels.dataset_panel import load_uploaded
from panels.hr_modules import attrition, auto_model_module


def render():
    st.caption("Elle veri girip anlık tahmin almak için aşağıdan bir mod seçin.")

    mod = st.radio(
        "Ne tahmin etmek istersiniz?",
        ["👤 Çalışan Ayrılma Tahmini", "📊 Genel Veri Seti Tahmini"],
        horizontal=True, key="predict_mode",
    )

    st.divider()

    if mod == "👤 Çalışan Ayrılma Tahmini":
        _render_attrition_mode()
    else:
        _render_general_mode()


def _render_attrition_mode():
    if not data_ready():
        st.warning("Dahili İK veri seti bulunamadı. Önce `python src/data_prep.py` çalıştırın.")
        return

    bundle = load_model()
    if bundle is None:
        st.warning("Eğitilmiş çalışan kaybı modeli bulunamadı; önce `python src/model.py` çalıştırın.")
        return

    emp = load_employees()
    explainer = load_explainer()
    attrition.render_risk_calculator(emp, bundle["pipeline"], explainer, key_prefix="pred_attr")


def _render_general_mode():
    st.subheader("Veri Seti Yükle")
    uploaded = st.file_uploader(
        "CSV, Excel veya JSON dosyası", type=["csv", "xlsx", "xls", "json"], key="pred_upload",
    )
    if uploaded is not None:
        try:
            st.session_state["pred_df"] = load_uploaded(uploaded)
            st.session_state["pred_name"] = uploaded.name
        except Exception as exc:
            st.error(f"Dosya okunamadı: {exc}")

    use_builtin = data_ready() and st.button("Dahili İK Veri Setini Kullan", key="pred_use_builtin")
    if use_builtin:
        st.session_state["pred_df"] = load_employees()
        st.session_state["pred_name"] = "İK Çalışan Verisi (dahili)"

    if "pred_df" not in st.session_state:
        st.info("Devam etmek için bir dosya yükleyin veya dahili İK veri setini kullanın.")
        return

    df: pd.DataFrame = st.session_state["pred_df"]
    st.success(f"Aktif veri seti: **{st.session_state['pred_name']}** — {len(df)} satır, {len(df.columns)} kolon")

    st.divider()
    auto_model_module.render(df, state_prefix="pred")
