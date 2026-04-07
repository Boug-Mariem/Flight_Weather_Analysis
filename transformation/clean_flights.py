import pandas as pd
from db.postgresConnection import get_engine
from ingestion.flights_batch import get_flights_silver_dates, get_flights_bronze_dates,load_batch_flights_bronze_from_db
from db.postgresConnection import get_engine
       
def clean_batch_flights(df):
    
    # suppression des valeur manquantes
    df = df[df["Arr_Delay"] != -99]
    df = df[df["Dep_Delay"] != -99]

    # Verification et Conversion des types
    df["FlightDate"] = pd.to_datetime(df["FlightDate"], errors="coerce")
    df["Arr_Delay"] = pd.to_numeric(df["Arr_Delay"], errors="coerce")
    df["Dep_Delay"] = pd.to_numeric(df["Dep_Delay"], errors="coerce")
    df["Delay_Weather"] = pd.to_numeric(df["Delay_Weather"], errors="coerce")
    df["Delay_Carrier"] = pd.to_numeric(df["Delay_Carrier"], errors="coerce")
    df["Delay_NAS"] = pd.to_numeric(df["Delay_NAS"], errors="coerce")
    df["Delay_Security"] = pd.to_numeric(df["Delay_Security"], errors="coerce")
    df["Delay_LastAircraft"] = pd.to_numeric(df["Delay_LastAircraft"], errors="coerce")
    df["Flight_Duration"] = pd.to_numeric(df["Flight_Duration"], errors="coerce")

    # Supprimer lignes avec valeurs nulles critiques
    df = df.dropna(subset=["Arr_Delay", "Dep_Airport", "Arr_Airport","Dep_Delay","FlightDate","Flight_Duration"])
 
    # Remplacer NaN par 0
    df["Delay_Weather"] = df["Delay_Weather"].fillna(0)
    df["Delay_Carrier"] = df["Delay_Carrier"].fillna(0)
    df["Delay_NAS"] = df["Delay_NAS"].fillna(0)
    df["Delay_Security"] = df["Delay_Security"].fillna(0)
    df["Delay_LastAircraft"] = df["Delay_LastAircraft"].fillna(0)
    df["Airline"] = df["Airline"].fillna("UNKNOWN")
    
    # ajout dans la base
    df.to_sql(
            "flights_silver",
            get_engine(),
            if_exists="append",
            index=False
        )
    dates_df = sorted(df["FlightDate"].unique())
    print("Clean de batch flights avec date = ", dates_df)
    print("Nombre de lignes :", df.shape)
       
    return df

def clean_flights():
    engine=get_engine()
    bronze_dates=get_flights_bronze_dates(engine)
    silver_dates= get_flights_silver_dates(engine)
    dates_to_process = bronze_dates - silver_dates
    for d in sorted(dates_to_process):
        df = load_batch_flights_bronze_from_db(d)
        df_clean = clean_batch_flights(df)