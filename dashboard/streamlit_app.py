import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(layout="wide")
st.title("✈️ Flight & Weather Analytics Dashboard")

engine = create_engine("postgresql://admin:admin@localhost:5433/flightWeather_db")

# -------------------------
# MENU
# -------------------------
menu = st.sidebar.selectbox(
    "Choisir une analyse",
    [
        "Weather Impact",
        "Airport Analytics",
        "Airline Analytics",
        "Airline-Airport",
        "Prediction"
    ]
)

# =========================
# 1. WEATHER IMPACT
# =========================
if menu == "Weather Impact":
    st.header("🌦 Impact de la météo sur les retards")

    choice = st.selectbox(
        "Choisir variable météo",
        ["prcp", "wspd", "snow"]
    )

    if choice == "prcp":
        df = pd.read_sql("SELECT * FROM agg_delay_by_prcp", engine)
        x = "prcp_bin"

    elif choice == "wspd":
        df = pd.read_sql("SELECT * FROM agg_delay_by_wspd", engine)
        x = "wspd_bin"

    else:
        df = pd.read_sql("SELECT * FROM agg_delay_by_snow", engine)
        x = "snow_bin"

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Courbe")
        st.line_chart(df.set_index(x)["avg_delay"])

    with col2:
        st.subheader("📋 Tableau")
        st.dataframe(df)


# =========================
# 2. AIRPORT ANALYTICS
# =========================
elif menu == "Airport Analytics":
    st.header("🛫 Analyse par aéroport")

    df = pd.read_sql("SELECT * FROM agg_delay_by_airport_month", engine)

    airport = st.selectbox("Choisir un aéroport", df["airport"].unique())

    df_filtered = df[df["airport"] == airport]

    st.subheader(f"Retard moyen pour {airport}")

    st.bar_chart(df_filtered.set_index("month")["avg_delay"])

    st.dataframe(df_filtered)


# =========================
# 3. AIRLINE ANALYTICS
# =========================
elif menu == "Airline Analytics":
    st.header("🛩 Analyse des compagnies")

    df = pd.read_sql("SELECT * FROM agg_delay_by_wcombination_byairline", engine)

    st.dataframe(df)

    st.subheader("Top compagnies (meilleure performance)")
    st.bar_chart(df.groupby("airline")["avg_delay"].mean().sort_values().head(10))


# =========================
# 4. AIRLINE + AIRPORT
# =========================
elif menu == "Airline-Airport":
    st.header("🔗 Analyse combinée")

    df = pd.read_sql("SELECT * FROM airline_airport_bad_weather", engine)

    airport = st.selectbox("Airport", df["airport"].unique())
    df_filtered = df[df["airport"] == airport]

    st.dataframe(df_filtered)

    st.bar_chart(df_filtered.set_index("airline")["avg_delay"])


# =========================
# 5. PREDICTION
# =========================
elif menu == "Prediction":
    st.header("🔮 Prédiction des retards")

    airport = st.text_input("Airport (ex: LAX)")
    weather = st.text_input("Weather combination")

    if st.button("Predict"):
        query = f"""
        SELECT AVG("Dep_Delay") as avg_delay, COUNT(*) as n
        FROM gold_table
        WHERE "Dep_Airport" = '{airport}'
        AND "weather_combination_dep" = '{weather}'
        """

        df = pd.read_sql(query, engine)

        st.metric("Average Delay", round(df["avg_delay"][0], 2))
        st.metric("Number of Flights", int(df["n"][0]))