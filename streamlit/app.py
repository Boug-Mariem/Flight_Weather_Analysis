from pathlib import Path
import sys

import altair as alt
import pandas as pd
import streamlit as st

# Ensure project root is importable when running: streamlit run streamlit/app.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analytics_adapter import (  # noqa: E402
    collect_all_analytics,
    run_full_pipeline_with_logs,
    run_prediction,
)


st.set_page_config(page_title="Flight & Weather Analytics", layout="wide")
st.title("Flight and Weather Analytics")
st.caption("Dashboard generated from existing pipeline outputs without changing current function implementations.")

with st.sidebar:
    st.header("Pipeline Control")
    flights_csv = st.text_input("Flights CSV path", value="data/US_flights_2023_final.csv")
    weather_csv = st.text_input("Weather CSV path", value="data/weather_meteo_by_airport.csv")

    run_pipeline_clicked = st.button("Run Incremental Pipeline")
    refresh_clicked = st.button("Refresh Analytics")

if "analytics" not in st.session_state:
    st.session_state.analytics = {}
if "pipeline_logs" not in st.session_state:
    st.session_state.pipeline_logs = ""
if "pipeline_status" not in st.session_state:
    st.session_state.pipeline_status = {}

if run_pipeline_clicked:
    with st.spinner("Running ingestion, cleaning, gold, and aggregate updates..."):
        status = run_full_pipeline_with_logs(flights_csv, weather_csv)
        st.session_state.pipeline_logs = status.get("logs", "")
        st.session_state.pipeline_status = status
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


def show_chart(
    title: str,
    key: str,
    x_col: str,
    y_col: str,
    kind: str = "bar",
    top_n: int = 30,
    sort_mode: str = "metric_desc",
    chart_height: int = 320,
):
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

    # Aggregate repeated categories for cleaner charts.
    plot_df = plot_df.groupby(x_col, as_index=False)[y_col].mean()
    weather_order = None

    if sort_mode == "month_asc" or x_col == "month":
        plot_df = plot_df.sort_values(x_col)
    elif sort_mode == "weather_bin":
        bin_order = {
            "prcp_bin": ["0", "0-1", "1-3", "3-5", "5-10", ">10"],
            "wspd_bin": ["0", "0-10", "10-20", "20-30", ">30"],
            "snow_bin": ["0", "0-50", "50-200", "200-500", ">500"],
        }
        weather_order = bin_order.get(x_col)
        if weather_order:
            plot_df[x_col] = pd.Categorical(plot_df[x_col], categories=weather_order, ordered=True)
            plot_df = plot_df.sort_values(x_col)
        else:
            plot_df = plot_df.sort_values(y_col, ascending=False)
    else:
        plot_df = plot_df.sort_values(y_col, ascending=False)

    plot_df = plot_df.head(top_n)
    plot_df[x_col] = plot_df[x_col].astype(str)

    if kind == "line":
        if sort_mode == "month_asc" or x_col == "month":
            x_encoding = alt.X(f"{x_col}:O", sort="ascending", title=x_col)
        elif sort_mode == "weather_bin" and weather_order:
            x_encoding = alt.X(f"{x_col}:O", sort=weather_order, title=x_col)
        else:
            x_encoding = alt.X(f"{x_col}:N", title=x_col)

        chart = (
            alt.Chart(plot_df)
            .mark_line(point=True)
            .encode(
                x=x_encoding,
                y=alt.Y(f"{y_col}:Q", title=y_col),
                tooltip=[x_col, y_col],
            )
            .properties(height=chart_height)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        if sort_mode == "weather_bin" and weather_order:
            x_encoding = alt.X(f"{x_col}:O", sort=weather_order, title=x_col)
        elif sort_mode == "month_asc" or x_col == "month":
            x_encoding = alt.X(f"{x_col}:O", sort="ascending", title=x_col)
        else:
            x_encoding = alt.X(f"{x_col}:N", sort="-y", title=x_col)

        chart = (
            alt.Chart(plot_df)
            .mark_bar()
            .encode(
                x=x_encoding,
                y=alt.Y(f"{y_col}:Q", title=y_col),
                tooltip=[x_col, y_col],
            )
            .properties(height=chart_height)
        )
        st.altair_chart(chart, use_container_width=True)


weather_tab, airport_tab, airline_tab, airline_airport_tab, prediction_tab = st.tabs(
    [
        "Weather Impact",
        "Airport Analytics",
        "Airline Analytics",
        "Airline-Airport",
        "Prediction",
    ]
)

with weather_tab:
    show_chart(
        "Precipitation Delay Metrics",
        "weather_prcp",
        "prcp_bin",
        "avg_delay",
        kind="bar",
        sort_mode="weather_bin",
    )
    show_chart(
        "Wind Speed Delay Metrics",
        "weather_wspd",
        "wspd_bin",
        "avg_delay",
        kind="bar",
        sort_mode="weather_bin",
    )
    show_chart(
        "Snow Delay Metrics",
        "weather_snow",
        "snow_bin",
        "avg_delay",
        kind="bar",
        sort_mode="weather_bin",
    )

with airport_tab:
    show_chart(
        "Best Airport per Weather Combination",
        "airport_wcomb_best",
        "weather_combination",
        "avg_delay",
        chart_height=520,
    )
    show_chart("Top 3 Airports with Most Frequent Bad Weather", "airport_bad_weather_top3_count", "airport", "bad_weather_count")
    show_chart("Bottom 3 Airports with Least Frequent Bad Weather", "airport_bad_weather_bottom3_count", "airport", "bad_weather_count")
    show_chart("Top 3 Airports Most Affected by Bad Weather", "airport_bad_weather_top3_affected", "airport", "avg_delay_weather")
    show_chart("Bottom 3 Airports Least Affected by Bad Weather", "airport_bad_weather_bottom3_affected", "airport", "avg_delay_weather")
    show_chart("Average Delay per Airport by Month", "airport_month", "month", "avg_delay", kind="line")
    show_chart("Average Delay per Airport by Season", "airport_season", "season", "avg_delay")
    show_chart("Average Delay per Airport by Weekend", "airport_weekend", "airport", "avg_delay_weekend")
    show_chart("Average Delay per Airport on Non-Weekend", "airport_weekend", "airport", "avg_delay_non_weekend")

with airline_tab:
    show_chart("Best Airline per Weather Combination", "airline_wcomb_best", "weather_combination", "avg_delay")
    show_chart("Top 3 Airlines Most Affected by Bad Weather", "airline_bad_weather_top3_affected", "airline", "avg_delay_weather")
    show_chart("Bottom 3 Airlines Least Affected by Bad Weather", "airline_bad_weather_bottom3_affected", "airline", "avg_delay_weather")
    show_chart("Top 3 Airlines by Recovery Rate", "airline_recovery_top3", "Airline", "recovery_rate")
    show_chart("Bottom 3 Airlines by Recovery Rate", "airline_recovery_bottom3", "Airline", "recovery_rate")

with airline_airport_tab:
    show_chart("Top 3 Best Airlines per Airport during Bad Weather", "airline_airport_best", "airline", "avg_delay")
    show_chart("Top 3 Worst Airlines per Airport during Bad Weather", "airline_airport_worst", "airline", "avg_delay")

with prediction_tab:
    st.subheader("Delay Prediction")
    col1, col2 = st.columns(2)

    with col1:
        airport = st.text_input("Airport", value="LAX")
    with col2:
        airline = st.text_input("Airline (optional)", value="Skywest Airlines Inc.")

    if st.button("Run prediction"):
        with st.spinner("Computing prediction from historical gold table..."):
            value = run_prediction(airport=airport.strip(), airline=airline.strip() or None)

        if value is None:
            st.warning("No prediction available for the selected input.")
        else:
            st.success(f"Predicted average delay: {value:.2f} minutes")
