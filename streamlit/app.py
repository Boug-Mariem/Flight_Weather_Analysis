from pathlib import Path
import sys
import requests

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analytics_adapter import (  # noqa: E402
    collect_all_analytics,
    run_full_pipeline_with_logs,
    run_prediction,
    get_pipeline_last_update,
)

# ── Page config (Streamlit 1.12 compatible) ───────────────────────────────────
st.set_page_config(
    page_title="Flight & Weather Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Altair aviation theme ─────────────────────────────────────────────────────
def _altair_flight_theme():
    return {
        "config": {
            "background": "transparent",
            "view": {"strokeOpacity": 0, "fill": "transparent"},
            "axis": {
                "labelColor": "#8ab4d4",
                "titleColor": "#8ab4d4",
                "gridColor": "rgba(74,158,255,0.10)",
                "domainColor": "rgba(74,158,255,0.25)",
                "tickColor": "rgba(74,158,255,0.25)",
                "labelFontSize": 11,
                "titleFontSize": 12,
            },
            "title": {"color": "#e8f4fd", "fontSize": 14, "fontWeight": "600"},
            "legend": {
                "labelColor": "#8ab4d4",
                "titleColor": "#8ab4d4",
                "labelFontSize": 11,
                "titleFontSize": 12,
            },
        }
    }


alt.themes.register("flight", _altair_flight_theme)
alt.themes.enable("flight")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Base ── */
.stApp {
    background: linear-gradient(160deg, #06101f 0%, #0a1a33 60%, #081526 100%);
    font-family: 'Inter', sans-serif !important;
}
.block-container {
    padding-top: 0.75rem !important;
    max-width: 100% !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

/* ── Hero banner ── */
.hero-banner {
    background: linear-gradient(135deg, #091d3a 0%, #0e2d58 50%, #091d3a 100%);
    border: 1px solid rgba(74,158,255,0.28);
    border-radius: 14px;
    padding: 1.4rem 2rem;
    margin-bottom: 1.25rem;
}
.hero-line { display: flex; align-items: center; gap: 1rem; }
.hero-rule {
    height: 2px;
    background: linear-gradient(90deg, #4a9eff 0%, transparent 100%);
    border: none;
    margin: 6px 0 10px 0;
}
.hero-title {
    color: #4a9eff !important;
    font-size: 1.85rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.10em !important;
    text-transform: uppercase !important;
    margin: 0 !important;
    line-height: 1.2 !important;
}
.hero-badge {
    background: rgba(74,158,255,0.15);
    border: 1px solid rgba(74,158,255,0.35);
    color: #4a9eff;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 20px;
}
.hero-subtitle { color: #7aa5c8; font-size: 0.85rem; letter-spacing: 0.03em; margin: 0; }

/* ── Section heading ── */
.section-title {
    color: #ddeeff;
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    border-bottom: 1px solid rgba(74,158,255,0.20);
    padding-bottom: 0.4rem;
    margin: 1.1rem 0 0.9rem 0;
}

/* ── Streamlit headings ── */
h1 { color: #4a9eff !important; }
h2, h3, [data-testid="stHeading"] {
    color: #ddeeff !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    border-bottom: 1px solid rgba(74,158,255,0.18);
    padding-bottom: 0.35rem;
    margin-top: 1.1rem !important;
}

/* ── Flight-themed HTML table ── */
.table-card {
    background: rgba(8, 21, 40, 0.85);
    border: 1px solid rgba(74,158,255,0.25);
    border-radius: 12px;
    overflow: hidden;
    width: 100%;
    margin-bottom: 0.5rem;
}
.flight-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Inter', sans-serif;
}
.flight-table thead tr {
    background: rgba(74,158,255,0.14);
}
.flight-table thead th {
    color: #4a9eff;
    font-size: 0.74rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    padding: 0.8rem 1.1rem;
    text-align: left;
    border-bottom: 1px solid rgba(74,158,255,0.28);
    white-space: nowrap;
}
.flight-table tbody tr {
    border-bottom: 1px solid rgba(74,158,255,0.07);
    transition: background 0.15s ease;
}
.flight-table tbody tr:last-child { border-bottom: none; }
.flight-table tbody tr:nth-child(even) { background: rgba(74,158,255,0.03); }
.flight-table tbody tr:hover { background: rgba(74,158,255,0.10) !important; }
.flight-table tbody td {
    color: #c8dff0;
    font-size: 0.85rem;
    padding: 0.6rem 1.1rem;
}
.flight-table tbody td:first-child { color: #8ab4d4; font-weight: 500; }

/* ── Scrollable table variant ── */
.table-card-scroll {
    background: rgba(8, 21, 40, 0.85);
    border: 1px solid rgba(74,158,255,0.25);
    border-radius: 12px;
    overflow: hidden;
    width: 100%;
    margin-bottom: 0.5rem;
}
.table-scroll-body {
    max-height: 400px;
    overflow-y: auto;
    overflow-x: hidden;
}
.table-card-scroll .flight-table thead tr {
    background: rgba(6, 16, 40, 0.98);
    position: sticky;
    top: 0;
    z-index: 2;
}
.table-scroll-body::-webkit-scrollbar { width: 6px; }
.table-scroll-body::-webkit-scrollbar-track { background: rgba(74,158,255,0.04); }
.table-scroll-body::-webkit-scrollbar-thumb {
    background: rgba(74,158,255,0.28);
    border-radius: 3px;
}
.table-scroll-body::-webkit-scrollbar-thumb:hover { background: rgba(74,158,255,0.50); }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #06101f 0%, #0a1a33 100%) !important;
    border-right: 1px solid rgba(74,158,255,0.18) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] small { color: #c0d8ee !important; }
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #4a9eff !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.13em !important;
    border-bottom: 1px solid rgba(74,158,255,0.25) !important;
    padding-bottom: 0.5rem !important;
    margin-bottom: 0.8rem !important;
}
[data-testid="stSidebar"] input {
    background: rgba(74,158,255,0.07) !important;
    border: 1px solid rgba(74,158,255,0.28) !important;
    color: #e8f4fd !important;
    border-radius: 7px !important;
    font-size: 0.84rem !important;
}
[data-testid="stSidebar"] input:focus {
    border-color: #4a9eff !important;
    box-shadow: 0 0 0 2px rgba(74,158,255,0.18) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #162f5c 0%, #1e4080 100%) !important;
    color: #ddeeff !important;
    border: 1px solid rgba(74,158,255,0.38) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
    letter-spacing: 0.04em !important;
    padding: 0.55rem 1rem !important;
    transition: all 0.22s ease !important;
    width: 100% !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #1e4080 0%, #4a9eff 100%) !important;
    border-color: #4a9eff !important;
    box-shadow: 0 4px 18px rgba(74,158,255,0.30) !important;
    transform: translateY(-1px) !important;
    color: #fff !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(8,21,40,0.7) !important;
    border-radius: 10px !important;
    padding: 5px !important;
    gap: 3px !important;
    border: 1px solid rgba(74,158,255,0.15) !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #7aa5c8 !important;
    border-radius: 7px !important;
    font-weight: 500 !important;
    font-size: 0.86rem !important;
    padding: 8px 20px !important;
    border: none !important;
    letter-spacing: 0.025em !important;
    transition: all 0.18s !important;
}
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(74,158,255,0.09) !important;
    color: #c8e0f4 !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(74,158,255,0.18) !important;
    color: #4a9eff !important;
    font-weight: 700 !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background-color: #4a9eff !important;
    height: 2px !important;
    border-radius: 2px !important;
}
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: rgba(74,158,255,0.07) !important;
    border: 1px solid rgba(74,158,255,0.22) !important;
    border-radius: 11px !important;
    padding: 1rem 1.3rem !important;
}
[data-testid="stMetricLabel"] > div {
    color: #7aa5c8 !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}
[data-testid="stMetricValue"] > div { color: #4a9eff !important; font-weight: 700 !important; }

/* ── Alerts / text ── */
.stAlert {
    background: rgba(74,158,255,0.07) !important;
    border-left: 3px solid #4a9eff !important;
    border-radius: 8px !important;
}
.stTextInput input {
    background: rgba(74,158,255,0.07) !important;
    border: 1px solid rgba(74,158,255,0.28) !important;
    color: #e8f4fd !important;
    border-radius: 7px !important;
}
.stTextInput input:focus {
    border-color: #4a9eff !important;
    box-shadow: 0 0 0 2px rgba(74,158,255,0.18) !important;
}
.stTextInput label {
    color: #7aa5c8 !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
details summary {
    background: rgba(74,158,255,0.07) !important;
    border: 1px solid rgba(74,158,255,0.20) !important;
    border-radius: 8px !important;
    color: #8ab4d4 !important;
    padding: 0.5rem 1rem !important;
    font-size: 0.84rem !important;
}
[data-testid="stSpinner"] > div { border-top-color: #4a9eff !important; }
.stCaption, small { color: #7aa5c8 !important; }
p { color: #c0d8ee !important; }

.stTextInput input {
    color: #0d2d5e !important;   /* ← change ici */
}
header[data-testid="stHeader"] {
    display: none;
}

/* Remove top spacing caused by header */
.block-container {
    padding-top: 0rem !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="hero-banner">
  <div class="hero-line">
    <span class="hero-title">Flight &amp; Weather Analytics</span>
    <span class="hero-badge">Live Dashboard</span>
  </div>
  <div class="hero-rule"></div>
  <p class="hero-subtitle">
    Flight delay analysis &nbsp;|&nbsp; Weather impact &nbsp;|&nbsp;
    Airline &amp; airport performance &nbsp;|&nbsp; Delay prediction
  </p>
</div>
""",
    unsafe_allow_html=True,
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Pipeline Control")
    flights_csv = st.text_input("Flights CSV path", value="data/US_flights_2023_final.csv")
    weather_csv = st.text_input("Weather CSV path", value="data/weather_meteo_by_airport.csv")
    st.markdown("")
    run_pipeline_clicked = st.button("Run Incremental Pipeline")
    refresh_clicked = st.button("Refresh Analytics")

# ── Session state ─────────────────────────────────────────────────────────────
for _k, _v in [
    ("analytics", {}),
    ("pipeline_logs", ""),
    ("pipeline_status", {}),
    ("pred_value", None),
    ("pred_done", False),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

if run_pipeline_clicked:
    with st.spinner("Running ingestion, cleaning, gold, and aggregate updates..."):
        _s = run_full_pipeline_with_logs(flights_csv, weather_csv)
        st.session_state.pipeline_logs = _s.get("logs", "")
        st.session_state.pipeline_status = _s
        st.session_state.analytics = collect_all_analytics()

if refresh_clicked or not st.session_state.analytics:
    with st.spinner("Loading analytics from database..."):
        st.session_state.analytics = collect_all_analytics()

status = st.session_state.pipeline_status
if status:
    c1, c2 = st.columns(2)
    c1.metric("Last ingested flights date", str(status.get("ingested_flights_date")))
    c2.metric("Last ingested weather date", str(status.get("ingested_weather_date")))

if st.session_state.pipeline_logs:
    with st.expander("Pipeline print output", expanded=False):
        st.text(st.session_state.pipeline_logs)

analytics = st.session_state.analytics

# ── Helpers ───────────────────────────────────────────────────────────────────
_PALETTES = {
    "blue":   ("#0d2d5e", "#4a9eff"),
    "teal":   ("#064e3b", "#2dd4bf"),
    "amber":  ("#78350f", "#f0b429"),
    "red":    ("#7f1d1d", "#f87171"),
    "purple": ("#3b0764", "#a78bfa"),
}
_DONUT_COLORS = ["#4a9eff", "#2dd4bf", "#f0b429", "#f87171", "#a78bfa", "#fb923c"]


def _divider():
    st.markdown(
        "<hr style='border:none;border-top:1px solid rgba(74,158,255,0.18);margin:1.2rem 0;'>",
        unsafe_allow_html=True,
    )


def show_table(
    title: str,
    key: str,
    columns: list,
    rename: dict = None,
    round_cols: dict = None,
    scrollable: bool = False,
):
    """Render a fully themed HTML table — wide, integrated, dark-navy styled."""
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

    df = analytics.get(key, pd.DataFrame())
    if not isinstance(df, pd.DataFrame) or df.empty:
        st.info("No data available.")
        return

    available = [c for c in columns if c in df.columns]
    if not available:
        st.info("Data columns not available.")
        return

    display_df = df[available].copy()

    if round_cols:
        for col, decimals in round_cols.items():
            if col in display_df.columns:
                display_df[col] = display_df[col].round(decimals)

    if rename:
        display_df = display_df.rename(columns=rename)

    headers = "".join(f"<th>{c}</th>" for c in display_df.columns)
    rows = ""
    for _, row in display_df.iterrows():
        cells = "".join(f"<td>{v}</td>" for v in row)
        rows += f"<tr>{cells}</tr>"

    if scrollable:
        html = f"""
<div class="table-card-scroll">
  <div class="table-scroll-body">
    <table class="flight-table">
      <thead><tr>{headers}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>
"""
    else:
        html = f"""
<div class="table-card">
  <table class="flight-table">
    <thead><tr>{headers}</tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
"""

    st.markdown(html, unsafe_allow_html=True)


# ── show_chart ────────────────────────────────────────────────────────────────
def show_chart(
    title: str,
    key: str,
    x_col: str,
    y_col: str,
    kind: str = "bar",
    top_n: int = 30,
    sort_mode: str = "metric_desc",
    chart_height: int = 340,
    palette: str = "blue",
):
    """
    kind: bar | bar_scale | hbar | hbar_scale | lollipop | line | area | donut
    """
    st.subheader(title)
    df = analytics.get(key, pd.DataFrame())

    if not isinstance(df, pd.DataFrame) or df.empty:
        st.info("No data available.")
        return
    if x_col not in df.columns or y_col not in df.columns:
        st.info("Chart columns are not available in this dataset.")
        return

    plot_df = df[[x_col, y_col]].dropna().copy()
    if plot_df.empty:
        st.info("No data available.")
        return

    plot_df = plot_df.groupby(x_col, as_index=False)[y_col].mean()
    weather_order = None

    if sort_mode == "month_asc" or x_col == "month":
        plot_df = plot_df.sort_values(x_col)
    elif sort_mode == "weather_bin":
        _bins = {
            "prcp_bin": ["0", "0-1", "1-3", "3-5", "5-10", ">10"],
            "wspd_bin": ["0", "0-10", "10-20", "20-30", ">30"],
            "snow_bin": ["0", "0-50", "50-200", "200-500", ">500"],
        }
        weather_order = _bins.get(x_col)
        if weather_order:
            plot_df[x_col] = pd.Categorical(plot_df[x_col], categories=weather_order, ordered=True)
            plot_df = plot_df.sort_values(x_col)
        else:
            plot_df = plot_df.sort_values(y_col, ascending=False)
    else:
        plot_df = plot_df.sort_values(y_col, ascending=False)

    plot_df = plot_df.head(top_n)
    plot_df[x_col] = plot_df[x_col].astype(str)

    c_dark, c_bright = _PALETTES.get(palette, _PALETTES["blue"])

    # ── encoding builders ─────────────────────────────────────────────────────
    def _x_cat():
        _ang = 0 if (sort_mode in ("weather_bin", "month_asc") or x_col == "month") else -32
        if sort_mode == "weather_bin" and weather_order:
            return alt.X(f"{x_col}:O", sort=weather_order, title=x_col, axis=alt.Axis(labelAngle=_ang))
        if sort_mode == "month_asc" or x_col == "month":
            return alt.X(f"{x_col}:O", sort="ascending", title=x_col, axis=alt.Axis(labelAngle=_ang))
        return alt.X(f"{x_col}:N", sort="-y", title=x_col, axis=alt.Axis(labelAngle=_ang))

    def _x_ord():
        if sort_mode == "weather_bin" and weather_order:
            return alt.X(f"{x_col}:O", sort=weather_order, title=x_col)
        if sort_mode == "month_asc" or x_col == "month":
            return alt.X(f"{x_col}:O", sort="ascending", title=x_col)
        return alt.X(f"{x_col}:N", title=x_col)

    def _y_hbar():
        if sort_mode == "weather_bin" and weather_order:
            return alt.Y(f"{x_col}:O", sort=weather_order, title=x_col, axis=alt.Axis(labelAngle=0))
        if sort_mode == "month_asc" or x_col == "month":
            return alt.Y(f"{x_col}:O", sort="ascending", title=x_col, axis=alt.Axis(labelAngle=0))
        return alt.Y(
            f"{x_col}:N",
            sort=alt.EncodingSortField(field=y_col, order="descending"),
            title=x_col,
            axis=alt.Axis(labelAngle=0),
        )

    # ── chart kinds ──────────────────────────────────────────────────────────
    if kind == "bar":
        chart = (
            alt.Chart(plot_df)
            .mark_bar(color=c_bright, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=_x_cat(),
                y=alt.Y(f"{y_col}:Q", title=y_col),
                color=alt.value(c_bright),
                tooltip=[x_col, y_col],
            )
            .properties(height=chart_height)
        )

    elif kind == "bar_scale":
        chart = (
            alt.Chart(plot_df)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=_x_cat(),
                y=alt.Y(f"{y_col}:Q", title=y_col),
                color=alt.Color(f"{y_col}:Q", scale=alt.Scale(range=[c_dark, c_bright]), legend=None),
                tooltip=[x_col, y_col],
            )
            .properties(height=chart_height)
        )

    elif kind == "hbar":
        chart = (
            alt.Chart(plot_df)
            .mark_bar(color=c_bright, cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                y=_y_hbar(),
                x=alt.X(f"{y_col}:Q", title=y_col),
                color=alt.value(c_bright),
                tooltip=[x_col, y_col],
            )
            .properties(height=chart_height)
        )

    elif kind == "hbar_scale":
        chart = (
            alt.Chart(plot_df)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                y=_y_hbar(),
                x=alt.X(f"{y_col}:Q", title=y_col),
                color=alt.Color(f"{y_col}:Q", scale=alt.Scale(range=[c_dark, c_bright]), legend=None),
                tooltip=[x_col, y_col],
            )
            .properties(height=chart_height)
        )

    elif kind == "lollipop":
        _ye = _y_hbar()
        _xe = alt.X(f"{y_col}:Q", title=y_col)
        rule = (
            alt.Chart(plot_df)
            .mark_rule(color=c_bright, strokeWidth=2, opacity=0.50)
            .encode(y=_xe, x=_ye)
        )
        dot = (
            alt.Chart(plot_df)
            .mark_point(filled=True, color=c_bright, size=110, opacity=1)
            .encode(y=_xe, x=_ye, tooltip=[x_col, y_col])
        )
        chart = (rule + dot).properties(height=chart_height)

    elif kind == "line":
        chart = (
            alt.Chart(plot_df)
            .mark_line(
                point={"filled": True, "fill": c_bright, "size": 65},
                color=c_bright,
                strokeWidth=2.5,
            )
            .encode(
                x=_x_ord(),
                y=alt.Y(f"{y_col}:Q", title=y_col),
                tooltip=[x_col, y_col],
            )
            .properties(height=chart_height)
        )

    elif kind == "area":
        _enc = dict(x=_x_ord(), y=alt.Y(f"{y_col}:Q", title=y_col))
        area_l = (
            alt.Chart(plot_df)
            .mark_area(
                line={"color": c_bright, "strokeWidth": 2.5},
                opacity=0.22,
                color=c_bright,
            )
            .encode(**_enc)
        )
        dot_l = (
            alt.Chart(plot_df)
            .mark_point(filled=True, color=c_bright, size=65)
            .encode(**_enc, tooltip=[x_col, y_col])
        )
        chart = (area_l + dot_l).properties(height=chart_height)

    elif kind == "donut":
        arc_l = (
            alt.Chart(plot_df)
            .mark_arc(innerRadius=58, outerRadius=120, padAngle=0.015, cornerRadius=4)
            .encode(
                theta=alt.Theta(f"{y_col}:Q", stack=True),
                color=alt.Color(
                    f"{x_col}:N",
                    scale=alt.Scale(range=_DONUT_COLORS[: len(plot_df)]),
                    legend=alt.Legend(orient="right", labelFontSize=11),
                ),
                tooltip=[x_col, alt.Tooltip(f"{y_col}:Q", format=".2f")],
            )
        )
        txt_l = (
            alt.Chart(plot_df)
            .mark_text(radius=142, fontSize=10, fontWeight="600")
            .encode(
                theta=alt.Theta(f"{y_col}:Q", stack=True),
                text=alt.Text(f"{x_col}:N"),
                color=alt.value("#8ab4d4"),
            )
        )
        chart = (arc_l + txt_l).properties(height=chart_height)

    else:
        st.warning(f"Unknown chart kind: {kind}")
        return

    st.altair_chart(chart, use_container_width=True)


# ── Tabs ──────────────────────────────────────────────────────────────────────
weather_tab, airport_tab, airline_tab, airline_airport_tab, prediction_tab = st.tabs(
    ["Weather Impact", "Airport Analytics", "Airline Analytics", "Airline — Airport", "Delay Prediction"]
)

# ── Weather Impact ────────────────────────────────────────────────────────────
with weather_tab:
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        show_chart(
            "Precipitation vs Avg Delay", "weather_prcp", "prcp_bin", "avg_delay",
            kind="bar_scale", sort_mode="weather_bin", palette="blue",
        )
    with col_b:
        show_chart(
            "Wind Speed vs Avg Delay", "weather_wspd", "wspd_bin", "avg_delay",
            kind="bar_scale", sort_mode="weather_bin", palette="teal",
        )
    with col_c:
        show_chart(
            "Snowfall vs Avg Delay", "weather_snow", "snow_bin", "avg_delay",
            kind="bar_scale", sort_mode="weather_bin", palette="purple",
        )

# ── Airport Analytics ─────────────────────────────────────────────────────────
with airport_tab:
    show_table(
        "Best Airport per Weather Combination",
        "airport_wcomb_best",
        columns=["weather_combination", "airport", "avg_delay"],
        rename={"weather_combination": "Weather Combination", "airport": "Airport", "avg_delay": "Avg Delay (min)"},
        round_cols={"avg_delay": 2},
    )
    _divider()

    col1, col2 = st.columns(2)
    with col1:
        show_chart(
            "Airports — Most Frequent Bad Weather (Top 3)",
            "airport_bad_weather_top3_count", "airport", "bad_weather_count",
            kind="lollipop", palette="teal",
        )
        show_chart(
            "Airports — Most Delayed by Bad Weather (Top 3)",
            "airport_bad_weather_top3_affected", "airport", "avg_delay_weather",
            kind="lollipop", palette="purple",
        )
        show_chart(
            "Avg Delay per Month",
            "airport_month", "month", "avg_delay",
            kind="bar_scale", sort_mode="month_asc", palette="blue",
        )
    with col2:
        show_chart(
            "Airports — Least Frequent Bad Weather (Bottom 3)",
            "airport_bad_weather_bottom3_count", "airport", "bad_weather_count",
            kind="lollipop", palette="purple",
        )
        show_chart(
            "Airports — Least Delayed by Bad Weather (Bottom 3)",
            "airport_bad_weather_bottom3_affected", "airport", "avg_delay_weather",
            kind="lollipop", palette="teal",
        )
        show_chart(
            "Avg Delay per Season",
            "airport_season", "season", "avg_delay",
            kind="bar_scale", palette="blue",
        )

    _divider()
    col3, col4 = st.columns(2)
    with col3:
        show_chart(
            "Avg Delay on Weekends by Airport",
            "airport_weekend", "airport", "avg_delay_weekend",
            kind="bar_scale", palette="purple",
        )
    with col4:
        show_chart(
            "Avg Delay on Weekdays by Airport",
            "airport_weekend", "airport", "avg_delay_non_weekend",
            kind="bar_scale", palette="blue",
        )

# ── Airline Analytics ─────────────────────────────────────────────────────────
with airline_tab:
    show_table(
        "Best Airline per Weather Combination",
        "airline_wcomb_best",
        columns=["weather_combination", "airline", "avg_delay"],
        rename={"weather_combination": "Weather Combination", "airline": "Airline", "avg_delay": "Avg Delay (min)"},
        round_cols={"avg_delay": 2},
    )
    _divider()

    col1, col2 = st.columns(2)
    with col1:
        show_chart(
            "Airlines Most Affected by Bad Weather (Top 3)",
            "airline_bad_weather_top3_affected", "airline", "avg_delay_weather",
            kind="lollipop", palette="purple",
        )
        show_chart(
            "Best Recovery Rate (Top 3)",
            "airline_recovery_top3", "Airline", "recovery_rate",
            kind="lollipop", palette="teal",
        )
    with col2:
        show_chart(
            "Airlines Least Affected by Bad Weather (Bottom 3)",
            "airline_bad_weather_bottom3_affected", "airline", "avg_delay_weather",
            kind="lollipop", palette="teal",
        )
        show_chart(
            "Worst Recovery Rate (Bottom 3)",
            "airline_recovery_bottom3", "Airline", "recovery_rate",
            kind="lollipop", palette="purple",
        )

# ── Airline — Airport ─────────────────────────────────────────────────────────
with airline_airport_tab:
    show_table(
        "Top 3 Best Airlines per Airport during Bad Weather",
        "airline_airport_best",
        columns=["airport", "airline", "avg_delay"],
        rename={"airport": "Airport", "airline": "Airline", "avg_delay": "Avg Delay (min)"},
        round_cols={"avg_delay": 2},
        scrollable=True,
    )
    _divider()
    show_table(
        "Top 3 Worst Airlines per Airport during Bad Weather",
        "airline_airport_worst",
        columns=["airport", "airline", "avg_delay"],
        rename={"airport": "Airport", "airline": "Airline", "avg_delay": "Avg Delay (min)"},
        round_cols={"avg_delay": 2},
        scrollable=True,
    )

# ── Delay Prediction ──────────────────────────────────────────────────────────
with prediction_tab:
    st.subheader("Delay Prediction")
    st.markdown(
        "<p style='color:#7aa5c8;font-size:0.85rem;margin-bottom:1rem;'>"
        "Estimate expected average delay based on historical gold-table data.</p>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        airport = st.text_input("Airport", value="LAX")
    with col2:
        airline = st.text_input("Airline (optional)", value="Skywest Airlines Inc.")

    st.markdown("")
    _, btn_col, _ = st.columns([2, 1, 2])
    with btn_col:
        predict_clicked = st.button("Run Prediction")

    if predict_clicked:
        with st.spinner("Computing prediction from historical gold table..."):
            st.session_state.pred_value = run_prediction(
                airport=airport.strip(), airline=airline.strip() or None
            )
        st.session_state.pred_done = True
        # Re-click the Delay Prediction tab after the rerun so the page doesn't jump
        components.html(
            """
<script>
(function tryClick() {
    var tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
    for (var i = 0; i < tabs.length; i++) {
        var txt = tabs[i].innerText || tabs[i].textContent || "";
        if (txt.indexOf("Delay Prediction") !== -1) {
            tabs[i].click();
            return;
        }
    }
    setTimeout(tryClick, 80);
})();
</script>
""",
            height=0,
        )

    # Always render the result from session_state — persists across tab switches
    if st.session_state.pred_done:
        if st.session_state.pred_value is None:
            st.warning("No prediction available for the selected input.")
        else:
            st.success(f"Predicted average delay: **{st.session_state.pred_value:.2f} minutes**")


import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=10 * 1000, key="refresh")

if "last_update" not in st.session_state:
    st.session_state.last_update = get_pipeline_last_update()

current_update = get_pipeline_last_update()

# if current_update != st.session_state.last_update:
#     st.session_state.last_update = current_update
#     st.session_state.analytics = collect_all_analytics()

#     st.experimental_rerun()
if current_update != st.session_state.last_update:
    st.session_state.last_update = current_update
    st.session_state.analytics = collect_all_analytics()
    
    # stocker info de refresh
    st.session_state.last_refresh_time = datetime.now()
    st.session_state.show_toast = True

    st.experimental_rerun()

# affichage après rerun
if st.session_state.get("show_toast"):
    st.success("🔄 Données mises à jour")
    print("REFRESH TRIGGERED")
    st.session_state.show_toast = False

if "last_refresh_time" in st.session_state:
    st.success(f"Dernier refresh : {st.session_state.last_refresh_time}")    