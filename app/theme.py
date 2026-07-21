"""Uygulama genelinde kullanılan renk paleti (dataviz skill referans paletinden).

Grafik veri renkleri (CATEGORICAL/SEQUENTIAL_BLUE/STATUS) CVD-güvenli olarak
doğrulanmıştır ve temaya göre değişmez. Grafik "chrome" renkleri (arkaplan,
ızgara, metin) aktif Streamlit temasına (açık/koyu, bkz. .streamlit/config.toml)
göre otomatik seçilir.
"""
import streamlit as st

CATEGORICAL = [
    "#2a78d6",  # blue
    "#008300",  # green
    "#e87ba4",  # magenta
    "#eda100",  # yellow
    "#1baf7a",  # aqua
    "#eb6834",  # orange
    "#4a3aa7",  # violet
    "#e34948",  # red
]

SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]

STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

MUTED = "#898781"  # eksen/etiket rengi; açık ve koyu temada aynı

_CHROME = {
    "light": {
        "surface": "#f5f3e4",
        "grid": "#ddd6b8",
        "baseline": "#c3bb92",
        "text_primary": "#1a1a12",
    },
    "dark": {
        "surface": "#1c1c14",
        "grid": "#33321f",
        "baseline": "#4a4832",
        "text_primary": "#f5f3e4",
    },
}


def get_theme_type() -> str:
    """Kullanıcının aktif Streamlit temasını döndürür ("light" veya "dark")."""
    try:
        theme_type = st.context.theme.type
    except Exception:
        theme_type = None
    return theme_type or "light"


def _build_plotly_layout(theme_type: str) -> dict:
    chrome = _CHROME[theme_type]
    return dict(
        plot_bgcolor=chrome["surface"],
        paper_bgcolor=chrome["surface"],
        font=dict(color=chrome["text_primary"], family="system-ui, -apple-system, Segoe UI, sans-serif"),
        xaxis=dict(gridcolor=chrome["grid"], linecolor=chrome["baseline"], zerolinecolor=chrome["baseline"], automargin=True),
        yaxis=dict(gridcolor=chrome["grid"], linecolor=chrome["baseline"], zerolinecolor=chrome["baseline"], automargin=True),
        margin=dict(l=10, r=10, t=40, b=10),
    )


def apply_layout(fig, **overrides):
    layout = {**_build_plotly_layout(get_theme_type()), **overrides}
    fig.update_layout(**layout)
    return fig


def risk_status(prob: float) -> str:
    if prob < 0.25:
        return "good"
    if prob < 0.5:
        return "warning"
    if prob < 0.75:
        return "serious"
    return "critical"
