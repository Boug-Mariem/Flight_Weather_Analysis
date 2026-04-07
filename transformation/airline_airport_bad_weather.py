import pandas as pd
from transformation.gold_table import load_gold_table, get_gold_table_dates
from db.postgresConnection import get_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import Table, MetaData,text


def build_airline_airport_bad_weather_delay_dataset(df):
    # CAS 2 → départ uniquement
    df_dep_only = df[(df['delay_scenario'] == 2) & (df['bad_weather_dep'] == True)][
        ['Dep_Airport', 'Airline', 'Dep_Delay']
    ].rename(columns={
        'Dep_Airport': 'airport',
        'Airline': 'airline',
        'Dep_Delay': 'delay'
    })
    # CAS 3 → arrivée uniquement
    df_arr_only = df[(df['delay_scenario'] == 3 ) & (df['bad_weather_arr'] == True)][
        ['Arr_Airport', 'Airline', 'Arr_Delay']
    ].rename(columns={
        'Arr_Airport': 'airport',
        'Airline': 'airline',
        'Arr_Delay': 'delay'
    })
    # CAS 1 → les deux (départ)
    df_both_dep = df[(df['delay_scenario'] == 1)& (df['bad_weather_dep'] == True)][
        ['Dep_Airport', 'Airline', 'Dep_Delay']
    ].rename(columns={
        'Dep_Airport': 'airport',
        'Airline': 'airline',
        'Dep_Delay': 'delay'
    })
    # CAS 1 → les deux (arrivée)
    df_both_arr = df[(df['delay_scenario'] == 1) & (df['bad_weather_arr'] == True)][
        ['Arr_Airport', 'Airline', 'delay_change']
    ].rename(columns={
        'Arr_Airport': 'airport',
        'Airline': 'airline',
        'delay_change': 'delay'
    })
    # concat
    dataset = pd.concat(
        [df_dep_only, df_arr_only, df_both_dep, df_both_arr],
        ignore_index=True
    )
    return dataset

def compute_airline_airport_bad_weather(df):
    df['is_delay'] = (df['delay'] > 0).astype(int)
    agg = df.groupby(['airport', 'airline'],observed=True).agg(
        sum_delay=('delay', 'sum'),
        flight_count=('delay', 'count'),
        delay_count=('is_delay', 'sum')
    ).reset_index()
    return agg

def get_agg_airline_airport_bad_weather_processed_dates(engine):
    try:
        query = 'SELECT DISTINCT "FlightDate" FROM agg_airline_airport_bad_weather_processed_dates'
        df = pd.read_sql(query, engine)
        return set(pd.to_datetime(df["FlightDate"]).dt.date)
    except Exception as e:
        print("agg_airline_airport_bad_weather_processed_dates table not found, first run.")
        return set()

def create_agg_airline_airport_bad_weather_table(engine):
    query = text("""
    CREATE TABLE IF NOT EXISTS agg_airline_airport_bad_weather (
        airport TEXT,
        airline TEXT,
        sum_delay FLOAT,
        flight_count INT,
        delay_count INT,
        PRIMARY KEY (airport, airline)
    );
    """)

    with engine.begin() as conn:
        conn.execute(query)

def upsert_agg_airline_airport_bad_weather(batch_df, engine):
    metadata = MetaData()
    table = Table("agg_airline_airport_bad_weather", metadata, autoload_with=engine)
    records = batch_df.to_dict(orient="records")
    stmt = insert(table).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["airport","airline"],
        set_={
            "sum_delay": table.c.sum_delay + stmt.excluded.sum_delay,
            "flight_count": table.c.flight_count + stmt.excluded.flight_count,
            "delay_count": table.c.delay_count + stmt.excluded.delay_count,
        }
    )
    with engine.begin() as conn:
        conn.execute(stmt)

def agg_delay_by_airline_airport_bad_weather():
    engine = get_engine()
    create_agg_airline_airport_bad_weather_table(engine)
    # chercher les dates non encore traiter dans agg_airline_airport_bad_weather_processed_dates
    global_table_dates= get_gold_table_dates(engine)
    agg_airline_airport_bad_weather_processed_dates= get_agg_airline_airport_bad_weather_processed_dates(engine)
    
    new_dates = global_table_dates-agg_airline_airport_bad_weather_processed_dates
    if not new_dates:
        print("Pas de nouvelle date pour agg_airline_airport_bad_weather ")
        return

    # Apporter les donner de gold table non encore traitr dans agg_airline_airport_bad_weather
    df = load_gold_table(engine,new_dates)

    dataset=build_airline_airport_bad_weather_delay_dataset(df)
    agg= compute_airline_airport_bad_weather(dataset)

    if agg.empty:
        print("Batch vide après agrégation")
        return
    
    
    upsert_agg_airline_airport_bad_weather(agg,engine)
    print("mise a jour de airline_airport_bad_weather")
    print("Nombre de lignes :", agg.shape)

    dates_df = pd.DataFrame({'FlightDate': list(new_dates)})
    dates_df.to_sql(
            "agg_airline_airport_bad_weather_processed_dates",
            engine,
            if_exists="append",
            index=False
        )
    dates_df = sorted(new_dates)
    print("mise a jour de agg_airline_airport_bad_weather_processed_dates avec dates : ", dates_df)

# pour analyse et pas le stokage
def compute_final_metrics(engine, top=False):
    order = "DESC" if top else "ASC"

    query = text(f"""
        WITH agg AS (
            SELECT 
                airport,
                airline,
                SUM(sum_delay) / SUM(flight_count) AS avg_delay,
                SUM(flight_count) AS total_flights
            FROM agg_airline_airport_bad_weather
            GROUP BY airport, airline
            HAVING SUM(flight_count) >= 5
        ),
        ranked AS (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY airport 
                       ORDER BY avg_delay {order}
                   ) AS rn
            FROM agg
        )
        SELECT *
        FROM ranked
        WHERE rn <= 3
        ORDER BY airport, avg_delay {order};
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()
        df = pd.DataFrame(rows, columns=result.keys())

    return df
def agg_delay_by_airline_airport_bad_weather_avg_best():
    agg_delay_by_airline_airport_bad_weather()
    engine=get_engine()
    df_result = compute_final_metrics(engine,False)
    print("Top 3 Airlines with Lowest Average Delay per Airport during Bad Weather (only airlines with at least 5 flights): ")
    print(df_result)

def agg_delay_by_airline_airport_bad_weather_avg_worst():
    agg_delay_by_airline_airport_bad_weather()
    engine=get_engine()
    df_result = compute_final_metrics(engine,True)
    print("Bottom 3 Airlines with Highest Average Delay per Airport during Bad Weather(only airlines with at least 5 flights) : ")
    print(df_result)


