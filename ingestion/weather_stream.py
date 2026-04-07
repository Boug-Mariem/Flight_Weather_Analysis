import pandas as pd
import time
from db.postgresConnection import get_engine
from ingestion.producer_weather import stream_weather_to_kafka
from sqlalchemy import Table, MetaData,text

def get_weather_silver_dates(engine):
    try:
        query = 'SELECT DISTINCT "time" FROM weather_silver'
        df = pd.read_sql(query, engine)
        return set(pd.to_datetime(df["time"]).dt.date)
    except Exception as e:
        print("Silver weather table not found, first run.")
        return set()
    
def get_weather_bronze_dates(engine):
    try:
        query = 'SELECT DISTINCT "time" FROM weather_stream_bronze'
        df = pd.read_sql(query, engine)
        return set(pd.to_datetime(df["time"]).dt.date)
    except Exception as e:
        print("Bronze table not found")
        return set()

# une seul date de bronze     
def load_batch_weather_bronze_from_db(date):
    engine = get_engine()
    query = f"""
        SELECT * FROM weather_stream_bronze
        WHERE "time" = '{date}'
    """
    df = pd.read_sql(query, engine)
    return df

# un set de date de silver 
def load_weather_silver(engine, new_dates):
    if not new_dates:
        return pd.DataFrame()

    dates_str = "', '".join([str(d) for d in new_dates])

    query = f"""
        SELECT *
        FROM weather_silver
        WHERE "time" IN ('{dates_str}')
    """

    df = pd.read_sql(query, engine)
    return df

def load_weather_silver_predection(engine, airport):

    query = f"""
        SELECT *
        FROM weather_silver
        WHERE airport_id = :airport
        AND time = (
            SELECT MAX(time)
            FROM weather_silver
            WHERE airport_id = :airport
        );
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), {"airport": airport})
        rows = result.fetchall()
        df = pd.DataFrame(rows, columns=result.keys())

    return df 


def get_weather_dates_bronze_in_db(engine):
    try:
        df = pd.read_sql("SELECT DISTINCT time FROM weather_stream_bronze", engine)
        return set(pd.to_datetime(df["time"]).dt.date)
    except:
        return set()

def stream_weather_for_date(file_path, flights_date):
    engine = get_engine()
    df = pd.read_csv(file_path)
    df["time"] = pd.to_datetime(df["time"]).dt.date
    existing_dates = get_weather_dates_bronze_in_db(engine)
    # BACKFILL (≤ flights_date)
    df_backfill = df[
        (df["time"] <= flights_date) &
        (~df["time"].isin(existing_dates))
    ]
    if not df_backfill.empty:
        print("Backfill weather...")
        df_backfill.to_sql(
            "weather_stream_bronze",
            engine,
            if_exists="append",
            index=False
        )
        dates_backfill = sorted(df_backfill["time"].unique())
        print("Backfill weather pour les dates :", dates_backfill)
        print("Nombre de lignes :", df_backfill.shape)

    # STREAMING via Kafka (> flights_date) dans un thread
    date_ingested=stream_weather_to_kafka(file_path, flights_date)
    return date_ingested