import pandas as pd
from ingestion.weather_stream import get_weather_silver_dates, get_weather_bronze_dates,load_batch_weather_bronze_from_db
from db.postgresConnection import get_engine

def clean_batch_weather(df):
    # Conversion des types
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    numeric_cols = ["tavg", "tmin", "tmax", "prcp", "snow", "wdir", "wspd", "pres"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Suppression lignes critiques
    df = df.dropna(subset=["time", "airport_id"])

    #  Gestion valeurs manquantes météo
    df["prcp"] = df["prcp"].fillna(0)   # pas de pluie = 0
    df["snow"] = df["snow"].fillna(0)   # pas de neige = 0
    #tavg :température moyenne du jours /wspd: vitesse du vent /pres:pression atmosphérique
    df["tavg"] = df["tavg"].fillna(df.groupby("airport_id")["tavg"].transform("mean"))
    df["wspd"] = df["wspd"].fillna(df.groupby("airport_id")["wspd"].transform("median"))
    df["pres"] = df["pres"].fillna(df.groupby("airport_id")["pres"].transform("median"))
    df["wdir"] = df["wdir"].fillna(df.groupby("airport_id")["wdir"].transform("median"))

    df["tmax"] = df["tmax"].fillna(df["tavg"])
    df["tmin"] = df["tmin"].fillna(df["tavg"])

    # ajout dans la base
    df.to_sql(
            "weather_silver",
            get_engine(),
            if_exists="append",
            index=False
        )
    dates_df = sorted(df["time"].unique())
    print("Clean de batch weather avec date = ", dates_df)
    print("Nombre de lignes :", df.shape)

    return df

def clean_weather():
    engine=get_engine()
    bronze_dates=get_weather_bronze_dates(engine)
    silver_dates= get_weather_silver_dates(engine)
    dates_to_process = bronze_dates - silver_dates
    for d in sorted(dates_to_process):
        df = load_batch_weather_bronze_from_db(d)
        df_clean = clean_batch_weather(df)