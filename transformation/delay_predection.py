from sqlalchemy import text
from db.postgresConnection import get_engine
import pandas as pd
from ingestion.weather_stream import load_weather_silver_predection
from transformation.gold_table import load_gold_table_predction_airport,load_gold_table_predction_airport_airline

def categorize_weather_levels(row): 
    if row['wspd'] <= 10:
        wind = 'low-wind'
    elif row['wspd'] <= 20:
        wind = 'medium-wind'
    else:
        wind = 'high-wind'

    if row['prcp'] == 0:
        prcp = 'low-rain'
    elif row['prcp'] <= 3:
        prcp = 'medium-rain'
    else:
        prcp = 'high-rain'

    if row['snow'] == 0:
        snow = 'low-snow'
    elif row['snow'] <= 1:
        snow = 'medium-snow'
    else:
        snow = 'high-snow'
    weather = f"{wind}_{prcp}_{snow}"
    return weather

def predict_delay(airport, airline=None):
    engine = get_engine()
    # récupérer météo
    df_weather = load_weather_silver_predection(engine, airport)
    if df_weather.empty:
        print("⚠️ No weather data available")
        return None
    
    # construire weather_combination
    weather_combination = categorize_weather_levels(df_weather.iloc[0])

    # charger historique
    if airline:
        df_hist = load_gold_table_predction_airport_airline(
            engine, airport, airline, weather_combination
        )

        # fallback si vide
        if df_hist.empty:
            print("No data for this airline !! → fallback airport only")
            df_hist = load_gold_table_predction_airport(
                engine, airport, weather_combination
            )
    else:
        df_hist = load_gold_table_predction_airport(
            engine, airport, weather_combination
        )

    if df_hist.empty:
        print("No historical data available !!")
        return None

    # calcul métriques
    avg_delay = df_hist["Dep_Delay"].mean()
    total_flights = len(df_hist)

    print(f"Prediction for {airport} ({weather_combination})")
    if airline:
        print(f"Airline: {airline}")

    print(f"Avg delay: {avg_delay:.2f} min")
    print(f"Based on {total_flights} flights")

    return avg_delay


