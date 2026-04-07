import pandas as pd
from db.postgresConnection import get_engine
from datetime import timedelta

def get_flights_silver_dates(engine):
    try:
        query = 'SELECT DISTINCT "FlightDate" FROM flights_silver'
        df = pd.read_sql(query, engine)
        return set(pd.to_datetime(df["FlightDate"]).dt.date)
    except Exception as e:
        print("Silver flights table not found, first run.")
        return set()
    
def get_flights_bronze_dates(engine):
    try:
        query = 'SELECT DISTINCT "FlightDate" FROM flights_bronze'
        df = pd.read_sql(query, engine)
        return set(pd.to_datetime(df["FlightDate"]).dt.date)
    except Exception as e:
        print("Bronze flights table not found")
        return set()

# une seul date  de bronze   
def load_batch_flights_bronze_from_db(date):
    engine = get_engine()
    query = f"""
        SELECT * FROM flights_bronze
        WHERE "FlightDate" = '{date}'
    """
    df = pd.read_sql(query, engine)
    return df

# un set de dates de silver
def load_flights_silver(engine, new_dates):
    if not new_dates:
        return pd.DataFrame()

    # Convert dates to SQL-friendly format
    dates_str = "', '".join([str(d) for d in new_dates])

    query = f"""
        SELECT *
        FROM flights_silver
        WHERE "FlightDate" IN ('{dates_str}')
    """

    df = pd.read_sql(query, engine)
    return df

def get_last_date(engine):
    try:
        query = 'SELECT MAX("FlightDate") as last_date FROM flights_bronze'
        df = pd.read_sql(query, engine)
        print("last date ",df["last_date"].iloc[0])
        return df["last_date"].iloc[0]
    except Exception as e:
        print("ERROR in get_last_date:", e)
        return None   

def get_next_available_date(file_path, last_date):
    dates = set()
    for chunk in pd.read_csv(file_path, chunksize=100000):
        chunk["FlightDate"] = pd.to_datetime(chunk["FlightDate"]).dt.date
        if last_date is None:
            dates.update(chunk["FlightDate"].unique())
        else:
            dates.update(chunk[chunk["FlightDate"] > last_date]["FlightDate"].unique())
    if not dates:
        return None
    return min(dates)

def ingest_flights_incremental(file_path):
    engine = get_engine()
    last_date = get_last_date(engine)
    chunksize = 100000
    target_date = get_next_available_date(file_path, last_date)
    if target_date is None:
        print("Aucune nouvelle date disponible")
        return None
    print(f"Target ingestion date: {target_date}")
    
    inserted = False
    for chunk in pd.read_csv(file_path, chunksize=chunksize):
        chunk["FlightDate"] = pd.to_datetime(chunk["FlightDate"]).dt.date
        df_filtered = chunk[chunk["FlightDate"] == target_date]
        if not df_filtered.empty:
            df_filtered.to_sql(
                "flights_bronze",
                engine,
                if_exists="append",
                index=False
            )
            inserted = True
    print("Ingestion terminée")
    if inserted:
        return target_date
    else:
        return None