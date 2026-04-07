import pandas as pd
from transformation.gold_table import load_gold_table, get_gold_table_dates
from db.postgresConnection import get_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import Table, MetaData,text


def build_weekend_airport_delay_dataset(df):
    # CAS 2 → départ uniquement
    df_dep_only = df[df['delay_scenario'] == 2][
        ['Dep_Airport', 'is_weekend' ,'Dep_Delay']
    ].rename(columns={
        'Dep_Airport': 'airport',
        'is_weekend': 'is_weekend',
        'Dep_Delay': 'delay'
    })
    # CAS 3 → arrivée uniquement
    df_arr_only = df[df['delay_scenario'] == 3][
        ['Arr_Airport',  'is_weekend' , 'Arr_Delay']
    ].rename(columns={
        'Arr_Airport': 'airport',
        'is_weekend': 'is_weekend',
        'Arr_Delay': 'delay'
    })
    # CAS 1 → les deux (départ)
    df_both_dep = df[df['delay_scenario'] == 1][
        ['Dep_Airport', 'is_weekend' , 'Dep_Delay']
    ].rename(columns={
        'Dep_Airport': 'airport',
        'is_weekend': 'is_weekend',
        'Dep_Delay': 'delay'
    })
    # CAS 1 → les deux (arrivée)
    df_both_arr = df[df['delay_scenario'] == 1][
        ['Arr_Airport',  'is_weekend' ,'delay_change']
    ].rename(columns={
        'Arr_Airport': 'airport',
        'is_weekend': 'is_weekend',
        'delay_change': 'delay'
    })
    # concat
    dataset = pd.concat(
        [df_dep_only, df_arr_only, df_both_dep, df_both_arr],
        ignore_index=True
    )
    return dataset

def compute_airport_weekend_agg(df):
    df['is_delay'] = (df['delay'] > 0).astype(int)
    agg = df.groupby(['airport', 'is_weekend'],observed=True).agg(
        sum_delay=('delay', 'sum'),
        flight_count=('delay', 'count'),
        delay_count=('is_delay', 'sum')
    ).reset_index()
    return agg

def get_agg_airport_weekend_processed_dates(engine):
    try:
        query = 'SELECT DISTINCT "FlightDate" FROM agg_airport_weekend_processed_dates'
        df = pd.read_sql(query, engine)
        return set(pd.to_datetime(df["FlightDate"]).dt.date)
    except Exception as e:
        print("agg_airport_weekend_processed_dates table not found, first run.")
        return set()

def create_agg_airport_weekend_table(engine):
    query = text("""
    CREATE TABLE IF NOT EXISTS agg_delay_by_airport_weekend (
        airport TEXT,
        is_weekend BOOLEAN ,
        sum_delay FLOAT,
        flight_count INT,
        delay_count INT,
        PRIMARY KEY (airport, is_weekend)
    );
    """)

    with engine.begin() as conn:
        conn.execute(query)

def upsert_agg_airport_weekend(batch_df, engine):
    metadata = MetaData()
    table = Table("agg_delay_by_airport_weekend", metadata, autoload_with=engine)
    records = batch_df.to_dict(orient="records")
    stmt = insert(table).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["airport","is_weekend"],
        set_={
            "sum_delay": table.c.sum_delay + stmt.excluded.sum_delay,
            "flight_count": table.c.flight_count + stmt.excluded.flight_count,
            "delay_count": table.c.delay_count + stmt.excluded.delay_count,
        }
    )
    with engine.begin() as conn:
        conn.execute(stmt)

def agg_delay_by_airport_weekend():
    engine = get_engine()
    create_agg_airport_weekend_table(engine)
    # chercher les dates non encore traiter dans agg_airport_weekend_processed_dates
    global_table_dates= get_gold_table_dates(engine)
    agg_airport_weekend_processed_dates= get_agg_airport_weekend_processed_dates(engine)
    
    new_dates = global_table_dates-agg_airport_weekend_processed_dates
    if not new_dates:
        print("Pas de nouvelle date pour agg_delay_by_airport_weekend ")
        return

    # Apporter les donner de gold table non encore traitr dans agg_delay_by_airport_weekend
    df = load_gold_table(engine,new_dates)

    dataset=build_weekend_airport_delay_dataset(df)
    agg= compute_airport_weekend_agg(dataset)

    if agg.empty:
        print("Batch vide après agrégation")
        return
    
    
    upsert_agg_airport_weekend(agg,engine)
    print("mise a jour de agg_delay_by_airport_weekend ")
    print("Nombre de lignes :", agg.shape)

    dates_df = pd.DataFrame({'FlightDate': list(new_dates)})
    dates_df.to_sql(
            "agg_airport_weekend_processed_dates",
            engine,
            if_exists="append",
            index=False
        )
    dates_df = sorted(new_dates)
    print("mise a jour de agg_airport_weekend_processed_dates avec dates : ", dates_df)

# pour analyse et pas le stokage
def compute_final_metrics(engine):
    query = text("""
        SELECT
            airport,

            SUM(CASE WHEN is_weekend = TRUE THEN sum_delay ELSE 0 END)
                / NULLIF(SUM(CASE WHEN is_weekend = TRUE THEN flight_count ELSE 0 END), 0)
                AS avg_delay_weekend,

            SUM(CASE WHEN is_weekend = TRUE THEN flight_count ELSE 0 END)
                AS flights_weekend,

            SUM(CASE WHEN is_weekend = FALSE THEN sum_delay ELSE 0 END)
                / NULLIF(SUM(CASE WHEN is_weekend = FALSE THEN flight_count ELSE 0 END), 0)
                AS avg_delay_non_weekend,

            SUM(CASE WHEN is_weekend = FALSE THEN flight_count ELSE 0 END)
                AS flights_non_weekend

        FROM agg_delay_by_airport_weekend
        GROUP BY airport
        ORDER BY airport;
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()
        df = pd.DataFrame(rows, columns=result.keys())

    return df

def agg_delay_by_airport_weekend_avg():
    agg_delay_by_airport_weekend()
    engine=get_engine()
    df_result = compute_final_metrics(engine)
    print("Average delay per airport by weekend: ")
    print(df_result)


