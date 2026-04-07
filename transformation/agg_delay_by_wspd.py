import pandas as pd
from transformation.gold_table import load_gold_table, get_gold_table_dates
from db.postgresConnection import get_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import Table, MetaData,text


def build_wspd_delay_dataset(df):
    # CAS 2 → départ uniquement
    df_dep_only = df[df['delay_scenario'] == 2][['wspd_dep', 'Dep_Delay']].rename(
        columns={'wspd_dep': 'wspd', 'Dep_Delay': 'delay'}
    )
    # CAS 3 → arrivée uniquement
    df_arr_only = df[df['delay_scenario'] == 3][['wspd_arr', 'Arr_Delay']].rename(
        columns={'wspd_arr': 'wspd', 'Arr_Delay': 'delay'}
    )
    # CAS 1 → les deux (mais seulement si delay > 0)
    df_both_dep = df[df['delay_scenario'] == 1][['wspd_dep', 'Dep_Delay']].rename(
        columns={'wspd_dep': 'wspd', 'Dep_Delay': 'delay'}
    )
    df_both_arr = df[df['delay_scenario'] == 1][['wspd_arr', 'delay_change']].rename(
        columns={'wspd_arr': 'wspd', 'delay_change': 'delay'}
    )
    # concat tout
    weather_delay_df = pd.concat(
        [df_dep_only, df_arr_only, df_both_dep, df_both_arr],
        ignore_index=True
    )
    return weather_delay_df

def add_wspd_bins(weather_delay_df):
    bins = [-0.01, 0, 10, 20, 30, float('inf')]
    labels = ['0', '0-10', '10-20', '20-30', '>30']

    weather_delay_df['wspd_bin'] = pd.cut(
        weather_delay_df['wspd'],
        bins=bins,
        labels=labels
    )
    weather_delay_df = weather_delay_df.dropna(subset=['wspd_bin'])
    return weather_delay_df

def compute_batch_wspd(weather_delay_df):
    weather_delay_df['is_delay'] = (weather_delay_df['delay'] > 0).astype(int)

    batch = weather_delay_df.groupby('wspd_bin', observed=True).agg(
        sum_delay=('delay', 'sum'),
        flight_count=('delay', 'count'),
        delay_count=('is_delay', 'sum')
    ).reset_index()
    return batch

def get_agg_wspd_processed_dates(engine):
    try:
        query = 'SELECT DISTINCT "FlightDate" FROM agg_wspd_processed_dates'
        df = pd.read_sql(query, engine)
        return set(pd.to_datetime(df["FlightDate"]).dt.date)
    except Exception as e:
        print("agg_wspd_processed_dates table not found, first run.")
        return set()

def create_agg_wspd_table(engine):
    query = text("""
    CREATE TABLE IF NOT EXISTS agg_delay_by_wspd (
        wspd_bin TEXT PRIMARY KEY,
        sum_delay FLOAT,
        flight_count INT,
        delay_count INT
    );
    """)

    with engine.begin() as conn:
        conn.execute(query)

def upsert_agg_wspd(batch_df, engine):
    metadata = MetaData()
    table = Table("agg_delay_by_wspd", metadata, autoload_with=engine)
    records = batch_df.to_dict(orient="records")
    stmt = insert(table).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["wspd_bin"],
        set_={
            "sum_delay": table.c.sum_delay + stmt.excluded.sum_delay,
            "flight_count": table.c.flight_count + stmt.excluded.flight_count,
            "delay_count": table.c.delay_count + stmt.excluded.delay_count,
        }
    )
    with engine.begin() as conn:
        conn.execute(stmt)

def agg_delay_by_wspd():
    engine = get_engine()
    # chercher les dates non encore traiter dans agg_wspd_processed_dates
    global_table_dates= get_gold_table_dates(engine)
    agg_wspd_processed_dates= get_agg_wspd_processed_dates(engine)
    new_dates = global_table_dates-agg_wspd_processed_dates
    if not new_dates:
        print("Pas de nouvelle date pour agg_delay_by_wspd ")
        return

    # Apporter les donner de gold table non encore traitr dans agg_delay_by_wspd
    df = load_gold_table(engine,new_dates)
    
    weather_delay_df = build_wspd_delay_dataset(df)
    weather_delay_df = add_wspd_bins(weather_delay_df)
    batch = compute_batch_wspd(weather_delay_df)
    if batch.empty:
        print("Batch vide après agrégation")
        return
    
    create_agg_wspd_table(engine)
    upsert_agg_wspd(batch,engine)
    print("mise a jour de agg_delay_by_wspd ")
    print("Nombre de lignes :", batch.shape)

    dates_df = pd.DataFrame({'FlightDate': list(new_dates)})
    dates_df.to_sql(
            "agg_wspd_processed_dates",
            engine,
            if_exists="append",
            index=False
        )
    dates_df = sorted(new_dates)
    print("mise a jour de agg_wspd_processed_dates avec dates : ", dates_df)



# pour analyse et pas le stokage
def compute_final_metrics_wspd(engine):
    #delay_count::float / flight_count AS delay_rate,
    query = text("""
        SELECT 
            wspd_bin,
            sum_delay / flight_count AS avg_delay,
            
            flight_count AS total_flights
        FROM agg_delay_by_wspd
        ORDER BY avg_delay ASC;
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()
        df = pd.DataFrame(rows, columns=result.keys())

    return df
def wspd_avg_rate():
    agg_delay_by_wspd()
    engine=get_engine()
    df_result = compute_final_metrics_wspd(engine)
    print("Vent:")
    print(df_result)