import pandas as pd
from transformation.gold_table import load_gold_table, get_gold_table_dates
from db.postgresConnection import get_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import Table, MetaData,text


def build_weather_airline_delay_dataset(df):
    # CAS 2 → départ uniquement
    df_dep_only = df[df['delay_scenario'] == 2][
        ['Airline', 'weather_combination_dep', 'Dep_Delay']
    ].rename(columns={
        'Airline': 'airline',
        'weather_combination_dep': 'weather_combination',
        'Dep_Delay': 'delay'
    })
    # CAS 3 → arrivée uniquement
    df_arr_only = df[df['delay_scenario'] == 3][
        ['Airline', 'weather_combination_arr', 'Arr_Delay']
    ].rename(columns={
        'Airline': 'airline',
        'weather_combination_arr': 'weather_combination',
        'Arr_Delay': 'delay'
    })
    # CAS 1 → les deux (départ)
    df_both_dep = df[df['delay_scenario'] == 1][
        ['Airline', 'weather_combination_dep', 'Dep_Delay']
    ].rename(columns={
        'Airline': 'airline',
        'weather_combination_dep': 'weather_combination',
        'Dep_Delay': 'delay'
    })
    # CAS 1 → les deux (arrivée)
    df_both_arr = df[df['delay_scenario'] == 1][
        ['Airline', 'weather_combination_arr', 'delay_change']
    ].rename(columns={
        'Airline': 'airline',
        'weather_combination_arr': 'weather_combination',
        'delay_change': 'delay'
    })
    # concat
    dataset = pd.concat(
        [df_dep_only, df_arr_only, df_both_dep, df_both_arr],
        ignore_index=True
    )
    return dataset

def compute_airline_weather_agg(df):
    df['is_delay'] = (df['delay'] > 0).astype(int)
    agg = df.groupby(['airline', 'weather_combination'],observed=True).agg(
        sum_delay=('delay', 'sum'),
        flight_count=('delay', 'count'),
        delay_count=('is_delay', 'sum')
    ).reset_index()
    return agg

def get_agg_Wcombination_processed_dates(engine):
    try:
        query = 'SELECT DISTINCT "FlightDate" FROM agg_wcombination_byairline_processed_dates'
        df = pd.read_sql(query, engine)
        return set(pd.to_datetime(df["FlightDate"]).dt.date)
    except Exception as e:
        print("agg_wcombination_byairline_processed_dates table not found, first run.")
        return set()

def create_agg_Wcombination_table(engine):
    query = text("""
    CREATE TABLE IF NOT EXISTS agg_delay_by_wcombination_byairline (
        airline TEXT,
        weather_combination TEXT,
        sum_delay FLOAT,
        flight_count INT,
        delay_count INT,
        PRIMARY KEY (airline, weather_combination)
    );
    """)

    with engine.begin() as conn:
        conn.execute(query)

def upsert_agg_Wcombination(batch_df, engine):
    metadata = MetaData()
    table = Table("agg_delay_by_wcombination_byairline", metadata, autoload_with=engine)
    records = batch_df.to_dict(orient="records")
    stmt = insert(table).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["airline","weather_combination"],
        set_={
            "sum_delay": table.c.sum_delay + stmt.excluded.sum_delay,
            "flight_count": table.c.flight_count + stmt.excluded.flight_count,
            "delay_count": table.c.delay_count + stmt.excluded.delay_count,
        }
    )
    with engine.begin() as conn:
        conn.execute(stmt)

def agg_delay_by_wcombination_byairline():
    engine = get_engine()
    create_agg_Wcombination_table(engine)
    # chercher les dates non encore traiter dans agg_wcombination_byairline_processed_dates
    global_table_dates= get_gold_table_dates(engine)
    agg_wcombination_byairline_processed_dates= get_agg_Wcombination_processed_dates(engine)
    
    new_dates = global_table_dates-agg_wcombination_byairline_processed_dates
    if not new_dates:
        print("Pas de nouvelle date pour agg_delay_by_wcombination_byairline ")
        return

    # Apporter les donner de gold table non encore traitr dans agg_delay_by_wcombination_byairline
    df = load_gold_table(engine,new_dates)

    dataset=build_weather_airline_delay_dataset(df)
    agg= compute_airline_weather_agg(dataset)

    if agg.empty:
        print("Batch vide après agrégation")
        return
    
    
    upsert_agg_Wcombination(agg,engine)
    print("mise a jour de agg_delay_by_wcombination_byairline ")
    print("Nombre de lignes :", agg.shape)

    dates_df = pd.DataFrame({'FlightDate': list(new_dates)})
    dates_df.to_sql(
            "agg_wcombination_byairline_processed_dates",
            engine,
            if_exists="append",
            index=False
        )
    dates_df = sorted(new_dates)
    print("mise a jour de agg_wcombination_byairline_processed_dates avec dates : ", dates_df)

# pour analyse et pas le stokage
def compute_final_metrics(engine):
    #SUM(delay_count)::float / SUM(flight_count) AS delay_rate,
    query = text("""
        SELECT *
            FROM (
                SELECT 
                    airline,
                    weather_combination,
                    SUM(sum_delay) / SUM(flight_count) AS avg_delay,
                    
                    SUM(flight_count) AS total_flights,
                    ROW_NUMBER() OVER (
                        PARTITION BY weather_combination
                        ORDER BY SUM(sum_delay) / SUM(flight_count) ASC
                    ) AS rn
                FROM agg_delay_by_wcombination_byairline
                GROUP BY airline, weather_combination
            ) t
            WHERE rn = 1;
    """)
    # ORDER BY avg_delay_weather
    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()
        df = pd.DataFrame(rows, columns=result.keys())

    return df

def Wcombinations_byairline():
    agg_delay_by_wcombination_byairline()
    engine=get_engine()
    df_result = compute_final_metrics(engine)
    print("la meilleure compagnie dans chaque condition météo:")
    print(df_result)


