"""Genel Analiz Platformu — tek sayfa, sol menüden sekme geçişli SPA kabuğu.

Sol kenar çubuğundaki sekmeler (Anasayfa / Dataset Analizi / CV Analizi /
Şirket Analizi) arasında geçiş yapıldığında sağ içerik alanı session_state
üzerinden koşullu olarak yeniden çizilir; sayfa/URL değişmez (Streamlit'in
çoklu-sayfa gezinmesi yerine tek script + session_state deseni kullanılır).
"""
import os
import sys

import streamlit as st

APP_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(APP_DIR, ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
for _p in (SRC_DIR, APP_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from i18n import t  # noqa: E402
from panels import company_panel, cv_panel, dataset_panel, home_panel  # noqa: E402

st.set_page_config(page_title="Genel Analiz Platformu", page_icon="🧪", layout="wide")

# Dil seçimi varsayılan
if "lang" not in st.session_state:
    st.session_state["lang"] = "tr"

PANELS = {
    "home": {"key": "home", "render": home_panel.render},
    "dataset": {"key": "dataset", "render": dataset_panel.render},
    "cv": {"key": "cv", "render": cv_panel.render},
    "company": {"key": "company", "render": company_panel.render},
}

PANEL_LABEL_KEYS = {
    "home": "panel_home",
    "dataset": "panel_dataset",
    "cv": "panel_cv",
    "company": "panel_company",
}

if "active_panel" not in st.session_state:
    st.session_state["active_panel"] = "home"

with st.sidebar:
    with st.container(border=True):
        st.markdown(t("uygulama_adi"))
        st.caption(t("uygulama_alt_baslik"))

    # ── Dil Seçici ──────────────────────────────────────────────────────────
    st.write("")
    lang_options = {"🇹🇷 Türkçe": "tr", "🇬🇧 English": "en", "🇩🇪 Deutsch": "de"}
    lang_labels = list(lang_options.keys())
    current_lang_label = next(
        (lbl for lbl, code in lang_options.items() if code == st.session_state["lang"]),
        lang_labels[0],
    )
    selected_lang_label = st.selectbox(
        t("dil_sec"),
        options=lang_labels,
        index=lang_labels.index(current_lang_label),
        key="lang_selectbox",
    )
    selected_lang_code = lang_options[selected_lang_label]
    if selected_lang_code != st.session_state["lang"]:
        st.session_state["lang"] = selected_lang_code
        st.rerun()

    st.write("")
    for key in PANELS:
        is_active = st.session_state["active_panel"] == key
        label = t(PANEL_LABEL_KEYS[key])
        if st.button(label, key=f"nav_{key}", type="primary" if is_active else "secondary", width="stretch"):
            st.session_state["active_panel"] = key
            st.rerun()
    st.divider()
    st.caption(t("sidebar_caption"))

active_key = st.session_state["active_panel"]
active_panel = PANELS[active_key]
if active_key != "home":
    st.title(t(PANEL_LABEL_KEYS[active_key]))
active_panel["render"]()
