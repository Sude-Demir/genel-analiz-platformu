"""Analiz Platformu — tek sayfa, sol menüden sekme geçişli SPA kabuğu.

Sol kenar çubuğundaki 3 sekme (Dataset Analizi / CV Analizi / Şirket Analizi)
arasında geçiş yapıldığında sağ içerik alanı session_state üzerinden koşullu
olarak yeniden çizilir; sayfa/URL değişmez (Streamlit'in çoklu-sayfa gezinmesi
yerine tek script + session_state deseni kullanılır).
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

from panels import company_panel, cv_panel, dataset_panel  # noqa: E402

st.set_page_config(page_title="Analiz Platformu", page_icon="🧪", layout="wide")

PANELS = {
    "dataset": {"label": "📁 Dataset Analizi", "render": dataset_panel.render},
    "cv": {"label": "📄 CV Analizi", "render": cv_panel.render},
    "company": {"label": "🌐 Şirket Analizi", "render": company_panel.render},
}

if "active_panel" not in st.session_state:
    st.session_state["active_panel"] = "dataset"

with st.sidebar:
    with st.container(border=True):
        st.markdown("## 🧪 Analiz Platformu")
        st.caption("Genel amaçlı çok modüllü analiz aracı")

    st.write("")
    for key, panel in PANELS.items():
        is_active = st.session_state["active_panel"] == key
        if st.button(panel["label"], key=f"nav_{key}", type="primary" if is_active else "secondary", width="stretch"):
            st.session_state["active_panel"] = key
            st.rerun()
    st.divider()
    st.caption("Her panelin sonucu kendi sekmesinde JSON / PDF / CSV olarak dışa aktarılabilir.")

active = PANELS[st.session_state["active_panel"]]
st.title(active["label"])
active["render"]()
