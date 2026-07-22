"""Anasayfa paneli — uygulama ilk açıldığında karşılanan tanıtım/karşılama ekranı.

Diğer panellerin kısa açıklamalarını kart olarak listeler; bir karta tıklanınca
ilgili panele geçiş yapılır (session_state["active_panel"] güncellenir). Kartların
ve kahraman (hero) bölümünün stili, st.container(key=...) ile üretilen sabit
`st-key-*` CSS sınıfları üzerinden hedeflenir (Streamlit'in dahili DOM yapısına
değil, resmi/kararlı API'sine dayanır).
"""
import streamlit as st

from i18n import t
from theme import CATEGORICAL

MODULE_CARD_KEYS = [
    {"key": "dataset", "icon": "📁", "title_key": "home_card_dataset_title", "desc_key": "home_card_dataset_desc", "color": CATEGORICAL[1]},
    {"key": "cv",      "icon": "📄", "title_key": "home_card_cv_title",      "desc_key": "home_card_cv_desc",      "color": CATEGORICAL[4]},
    {"key": "company", "icon": "🌐", "title_key": "home_card_company_title", "desc_key": "home_card_company_desc", "color": CATEGORICAL[5]},
]

QUICK_FACT_KEYS = [
    ("🧩", "3",        "modul_analiz_sayisi"),
    ("🔒", "0",        "modul_ai_bagimlilik"),
    ("🌳", "LightGBM", "modul_ml_model"),
]


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def _inject_css():
    st.markdown(
        """
        <style>
        div.st-key-home_hero > div {
            padding: 2.2rem 2rem 1.8rem 2rem;
            border-radius: 18px;
            background: linear-gradient(135deg, #3a3d22, #565a34);
            border: 1px solid rgba(163, 165, 117, 0.35);
            box-shadow: 0 8px 28px rgba(20, 21, 10, 0.35);
            text-align: center;
        }
        .home-hero-icon { font-size: 2.6rem; line-height: 1; }
        .home-hero-title {
            font-size: 2.1rem;
            font-weight: 800;
            margin: 0.3rem 0 0.4rem 0;
            letter-spacing: -0.02em;
            background: linear-gradient(90deg, #c9cc94, #e3e5c4, #a9ad72);
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .home-hero-sub {
            font-size: 1.05rem;
            color: #d6d8b9;
            max-width: 640px;
            margin: 0 auto;
        }
        div[class^="st-key-home_card_"] > div {
            border-radius: 16px;
            transition: box-shadow 0.18s ease, transform 0.18s ease;
            height: 100%;
        }
        div[class^="st-key-home_card_"] > div:hover {
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.10);
            transform: translateY(-3px);
        }
        .home-icon-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 46px;
            height: 46px;
            border-radius: 12px;
            font-size: 22px;
            margin-bottom: 0.5rem;
        }
        .home-card-title {
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 0.3rem;
            background: linear-gradient(90deg, #6b6f3f, #8a8b5c);
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render():
    _inject_css()

    with st.container(key="home_hero"):
        st.markdown(
            f"""
            <div class="home-hero-icon">🧪</div>
            <div class="home-hero-title">Genel Analiz Platformu</div>
            <div class="home-hero-sub">{t("hero_subtitle")}</div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    fact_cols = st.columns(len(QUICK_FACT_KEYS))
    for col, (icon, value, label_key) in zip(fact_cols, QUICK_FACT_KEYS):
        col.metric(f"{icon} {t(label_key)}", value)

    st.write("")
    st.markdown(t("moduller_baslik"))
    st.caption(t("moduller_caption"))

    cols = st.columns(2)
    for i, module in enumerate(MODULE_CARD_KEYS):
        with cols[i % 2]:
            with st.container(border=True, key=f"home_card_{module['key']}"):
                badge_bg = _hex_to_rgba(module["color"], 0.15)
                st.markdown(
                    f'<div class="home-icon-badge" style="background:{badge_bg};">{module["icon"]}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(f'<div class="home-card-title">{t(module["title_key"])}</div>', unsafe_allow_html=True)
                st.caption(t(module["desc_key"]))
                if st.button(t("ac_btn"), key=f"home_open_{module['key']}", width="stretch"):
                    st.session_state["active_panel"] = module["key"]
                    st.rerun()

    st.divider()
    st.caption(t("home_caption"))
