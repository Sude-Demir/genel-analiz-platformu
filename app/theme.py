"""Uygulama genelinde kullanılan renk paleti (dataviz skill referans paletinden)."""

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

GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
MUTED = "#898781"
TEXT_SECONDARY = "#52514e"
TEXT_PRIMARY = "#0b0b0b"
SURFACE = "#fcfcfb"

PLOTLY_LAYOUT = dict(
    plot_bgcolor=SURFACE,
    paper_bgcolor=SURFACE,
    font=dict(color=TEXT_PRIMARY, family="system-ui, -apple-system, Segoe UI, sans-serif"),
    xaxis=dict(gridcolor=GRID, linecolor=BASELINE, zerolinecolor=BASELINE),
    yaxis=dict(gridcolor=GRID, linecolor=BASELINE, zerolinecolor=BASELINE),
    margin=dict(l=10, r=10, t=40, b=10),
)


def apply_layout(fig, **overrides):
    layout = {**PLOTLY_LAYOUT, **overrides}
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
