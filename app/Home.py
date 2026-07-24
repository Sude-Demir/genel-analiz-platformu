"""Genel Analiz Platformu — tek sayfa SPA kabuğu.

Ana içerik alanının sağ üstündeki dil seçici (Türkçe / İngilizce / Almanca —
Streamlit'in yerleşik tema menüsüne yakın konumda, çünkü Streamlit o native
menüye özel widget eklemeye izin vermiyor) ile st.session_state["lang"]
güncellenir; translator.tr() fonksiyonu seçilen dile Google Translate
üzerinden otomatik çeviri yapar. Dil değiştirildiğinde translator.warm_cache()
tüm sabit metinleri paralel olarak önceden çevirip önbelleğe yazar, böylece
sonraki panel gezintileri anında (önbellekten) render edilir.
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

from translator import tr, warm_cache  # noqa: E402
from panel_registry import PANEL_REGISTRY  # noqa: E402
from panels import ai_panel, borsa_panel, company_panel, cv_panel, dataset_panel, home_panel  # noqa: E402

st.set_page_config(page_title="Genel Analiz Platformu", page_icon="🧪", layout="wide")

# ── Dil varsayılanı ───────────────────────────────────────────────────────────
if "lang" not in st.session_state:
    st.session_state["lang"] = "tr"

# Render callable eşlemesi modül import'u gerektirdiğinden burada; yeni panel eklerken
# hem buraya hem app/panel_registry.py'ye (metadata için) kayıt eklenmeli.
PANELS = {
    "home":    {"render": home_panel.render},
    "dataset": {"render": dataset_panel.render},
    "cv":      {"render": cv_panel.render},
    "company": {"render": company_panel.render},
    "borsa":   {"render": borsa_panel.render},
    "ai":      {"render": ai_panel.render},
}

# Sidebar etiketleri: "home" sabit, diğerleri PANEL_REGISTRY'den (app/panel_registry.py)
# türetilir — anasayfa modül kartlarıyla aynı kaynağı paylaşır, manuel senkronizasyon gerekmez.
PANEL_LABELS_TR = {"home": "🏠 Anasayfa"}
PANEL_LABELS_TR.update({p["key"]: f'{p["icon"]} {p["title"]}' for p in PANEL_REGISTRY})

if "active_panel" not in st.session_state:
    st.session_state["active_panel"] = "home"

with st.sidebar:
    with st.container(border=True):
        st.markdown(tr("## 🧪 Genel Analiz Platformu"))
        st.caption(tr("Genel amaçlı çok modüllü analiz aracı"))

    st.write("")
    for key, info in PANELS.items():
        is_active = st.session_state["active_panel"] == key
        label = tr(PANEL_LABELS_TR[key])
        if st.button(label, key=f"nav_{key}", type="primary" if is_active else "secondary", use_container_width=True):
            st.session_state["active_panel"] = key
            st.rerun()

    st.divider()
    st.caption(tr("Her panelin sonucu JSON / PDF / CSV olarak dışa aktarılabilir."))

active_key = st.session_state["active_panel"]

# ── Üst satır: sayfa başlığı (solda) + dil seçici (sağ üst) ───────────────────
# Dil seçici burada, ana içeriğin sağ üst köşesinde duruyor — Streamlit'in
# native "⋮" menüsündeki tema seçiciye (System/Light/Dark) en yakın konum,
# zira o yerleşik menüye özel bir widget eklemek Streamlit API'siyle mümkün değil.
header_left, header_right = st.columns([5, 1.4])
with header_right:
    lang_options = {"🇹🇷 Türkçe": "tr", "🇬🇧 English": "en", "🇩🇪 Deutsch": "de"}
    lang_labels = list(lang_options.keys())
    current_lang_label = next(
        (lbl for lbl, code in lang_options.items() if code == st.session_state["lang"]),
        lang_labels[0],
    )
    selected_lang_label = st.selectbox(
        "🌐 Dil / Language / Sprache",
        options=lang_labels,
        index=lang_labels.index(current_lang_label),
        key="lang_selectbox",
        label_visibility="collapsed",
    )
with header_left:
    if active_key != "home":
        st.title(tr(PANEL_LABELS_TR[active_key]))

selected_lang_code = lang_options[selected_lang_label]
if selected_lang_code != st.session_state["lang"]:
    st.session_state["lang"] = selected_lang_code
    if selected_lang_code != "tr":
        with st.spinner(tr("Çeviriler hazırlanıyor...")):
            warm_cache(selected_lang_code)
    st.rerun()

PANELS[active_key]["render"]()
