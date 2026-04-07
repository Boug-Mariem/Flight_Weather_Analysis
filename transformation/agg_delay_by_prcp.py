import pandas as pd
from transformation.gold_table import load_gold_table, get_gold_table_dates
from db.postgresConnection import get_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import Table, MetaData,text


def build_prcp_delay_dataset(df):
    # CAS 2 → départ uniquement
    df_dep_only = df[df['delay_scenario'] == 2][['prcp_dep', 'Dep_Delay']].rename(
        columns={'prcp_dep': 'prcp', 'Dep_Delay': 'delay'}
    )
    # CAS 3 → arrivée uniquement
    df_arr_only = df[df['delay_scenario'] == 3][['prcp_arr', 'Arr_Delay']].rename(
        columns={'prcp_arr': 'prcp', 'Arr_Delay': 'delay'}
    )
    # CAS 1 → les deux (mais seulement si delay > 0)
    df_both_dep = df[df['delay_scenario'] == 1][['prcp_dep', 'Dep_Delay']].rename(
        columns={'prcp_dep': 'prcp', 'Dep_Delay': 'delay'}
    )
    df_both_arr = df[df['delay_scenario'] == 1][['prcp_arr', 'delay_change']].rename(
        columns={'prcp_arr': 'prcp', 'delay_change': 'delay'}
    )
    # concat tout
    weather_delay_df = pd.concat(
        [df_dep_only, df_arr_only, df_both_dep, df_both_arr],
        ignore_index=True
    )
    return weather_delay_df

def add_prcp_bins(weather_delay_df):
    bins = [-0.01, 0, 1 , 3 , 5, 10, float('inf')]
    labels = ['0', '0-1', '1-3' ,'3-5', '5-10', '>10']
    weather_delay_df['prcp_bin'] = pd.cut(
        weather_delay_df['prcp'],
        bins=bins,
        labels=labels
    )
    weather_delay_df = weather_delay_df.dropna(subset=['prcp_bin'])
    return weather_delay_df

def compute_batch_prcp(weather_delay_df):
    weather_delay_df['is_delay'] = (weather_delay_df['delay'] > 0).astype(int)

    batch = weather_delay_df.groupby('prcp_bin', observed=True).agg(
        sum_delay=('delay', 'sum'),
        flight_count=('delay', 'count'),
        delay_count=('is_delay', 'sum')
    ).reset_index()
    return batch

def get_agg_prcp_processed_dates(engine):
    try:
        query = 'SELECT DISTINCT "FlightDate" FROM agg_prcp_processed_dates'
        df = pd.read_sql(query, engine)
        return set(pd.to_datetime(df["FlightDate"]).dt.date)
    except Exception as e:
        print("agg_prcp_processed_dates table not found, first run.")
        return set()

def create_agg_prcp_table(engine):
    query = text("""
    CREATE TABLE IF NOT EXISTS agg_delay_by_prcp (
        prcp_bin TEXT PRIMARY KEY,
        sum_delay FLOAT,
        flight_count INT,
        delay_count INT
    );
    """)

    with engine.begin() as conn:
        conn.execute(query)

def upsert_agg_prcp(batch_df, engine):
    metadata = MetaData()
    table = Table("agg_delay_by_prcp", metadata, autoload_with=engine)
    records = batch_df.to_dict(orient="records")
    stmt = insert(table).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["prcp_bin"],
        set_={
            "sum_delay": table.c.sum_delay + stmt.excluded.sum_delay,
            "flight_count": table.c.flight_count + stmt.excluded.flight_count,
            "delay_count": table.c.delay_count + stmt.excluded.delay_count,
        }
    )
    with engine.begin() as conn:
        conn.execute(stmt)

def agg_delay_by_prcp():
    engine = get_engine()
    # chercher les dates non encore traiter dans agg_prcp_processed_dates
    global_table_dates= get_gold_table_dates(engine)
    agg_prcp_processed_dates= get_agg_prcp_processed_dates(engine)
    new_dates = global_table_dates-agg_prcp_processed_dates
    if not new_dates:
        print("Pas de nouvelle date pour agg_delay_by_prcp ")
        return

    # Apporter les donner de gold table non encore traitr dans agg_delay_by_prcp
    df = load_gold_table(engine,new_dates)
    
    weather_delay_df = build_prcp_delay_dataset(df)
    weather_delay_df = add_prcp_bins(weather_delay_df)
    batch = compute_batch_prcp(weather_delay_df)
    if batch.empty:
        print("Batch vide après agrégation")
        return
    
    create_agg_prcp_table(engine)
    upsert_agg_prcp(batch,engine)
    print("mise a jour de agg_delay_by_prcp ")
    print("Nombre de lignes :", batch.shape)

    dates_df = pd.DataFrame({'FlightDate': list(new_dates)})
    dates_df.to_sql(
            "agg_prcp_processed_dates",
            engine,
            if_exists="append",
            index=False
        )
    dates_df = sorted(new_dates)
    print("mise a jour de agg_prcp_processed_dates avec dates : ", dates_df)



# pour analyse et pas le stokage
def compute_final_metrics_prcp(engine):
    #delay_count::float / flight_count AS delay_rate,
    query = text("""
        SELECT 
            prcp_bin,
            sum_delay / flight_count AS avg_delay,
            
            flight_count AS total_flights
        FROM agg_delay_by_prcp
        ORDER BY avg_delay ASC;
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()
        df = pd.DataFrame(rows, columns=result.keys())

    return df
def prcp_avg_rate():
    agg_delay_by_prcp()
    engine=get_engine()
    df_result = compute_final_metrics_prcp(engine)
    print("Pluie:")
    print(df_result)


