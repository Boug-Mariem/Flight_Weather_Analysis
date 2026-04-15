import pandas as pd
import numpy as np
from db.postgresConnection import get_engine
from ingestion.flights_batch import get_flights_silver_dates , load_flights_silver
from ingestion.weather_stream import load_weather_silver
from sqlalchemy import Table, MetaData,text

def jointure(df_flights, df_weather):
    flights = df_flights.copy()
    weather = df_weather.copy()

    # Suppression des lignes de vols ou 
    valid_airports = set(df_weather['airport_id'])
    flights = df_flights[
        df_flights['Dep_Airport'].isin(valid_airports) &
        df_flights['Arr_Airport'].isin(valid_airports)
    ]

    #Jointure météo DEPART
    weather_dep = weather.rename(columns={
        'tavg': 'tavg_dep',
        'tmin': 'tmin_dep',
        'tmax': 'tmax_dep',
        'prcp': 'prcp_dep',
        'snow': 'snow_dep',
        'wdir': 'wdir_dep',
        'wspd': 'wspd_dep',
        'pres': 'pres_dep'
    })

    df = flights.merge(
        weather_dep,
        left_on=['Dep_Airport', 'FlightDate'],
        right_on=['airport_id', 'time'],
        how='left'
    )

    # Jointure météo ARRIVEE
    weather_arr = weather.rename(columns={
        'tavg': 'tavg_arr',
        'tmin': 'tmin_arr',
        'tmax': 'tmax_arr',
        'prcp': 'prcp_arr',
        'snow': 'snow_arr',
        'wdir': 'wdir_arr',
        'wspd': 'wspd_arr',
        'pres': 'pres_arr'
    })

    df = df.merge(
        weather_arr,
        left_on=['Arr_Airport', 'FlightDate'],
        right_on=['airport_id', 'time'],
        how='left',
        suffixes=('', '_arr_dup')
    )

    #Nettoyage colonnes inutiles
    df = df.drop(columns=[
        'airport_id', 'time','airport_id_arr_dup', 'time_arr_dup'
    ], errors='ignore')

    return df

def classify_delay(row):
    # probleme de dep et arrive
    if row["Dep_Delay"] > 0 and row["delay_change"] > 0:
        return 1
    # probleme de dep
    elif row["Dep_Delay"] > 0:
        return 2
    # probleme de arrive
    elif row["delay_change"] > 0:
        return 3
    # pas de probleme
    else:
        return 0
    
def get_season(m):
    if m in [12, 1, 2]:
        return 'winter'
    elif m in [3, 4, 5]:
        return 'spring'
    elif m in [6, 7, 8]:
        return 'summer'
    else:
        return 'autumn' 
    
# def calculate_recovery(row):
#     # Cas 1 : Sort à l'heure ou en avance (Dep_Delay <= 0)
#     if row['Dep_Delay'] <= 0:
#         return "-1"    
#     # Calcul du gain de temps théorique
#     recovery_val = row['Dep_Delay'] - row['Arr_Delay']
#     # Cas 2 : Pas de récupération (le retard a stagné ou empiré)
#     if recovery_val <= 0:
#         return "0"
#     # Cas 3 : Récupération
#     if row['Arr_Delay'] <= 0:
#         return f"Total ({recovery_val} min)"
#     else:
#         return f"Partial ({recovery_val} min)"
    
def calculate_recovery_status(row):
    # Cas 1 : Sort à l'heure ou en avance (Dep_Delay <= 0)
    if row['Dep_Delay'] <= 0:
        return "no_delay"
    recovery_val = row['Dep_Delay'] - row['Arr_Delay']
    # Cas 2 : Pas de récupération (le retard a stagné ou empiré)
    if recovery_val <= 0:
        return "no_recovery"
    # Cas 3 : Récupération
    if row['Arr_Delay'] <= 0:
        return "total_recovery"
    return "partial_recovery"

def calculate_recovery_minutes(row):
    if row['Dep_Delay'] <= 0:
        return 0
    return max(row['Dep_Delay'] - row['Arr_Delay'], 0)

def categorize_weather_levels(row):
    # DEP 
    if row['wspd_dep'] <= 10:
        wind_dep = 'low-wind'
    elif row['wspd_dep'] <= 20:
        wind_dep = 'medium-wind'
    else:
        wind_dep = 'high-wind'

    if row['prcp_dep'] == 0:
        prcp_dep = 'low-rain'
    elif row['prcp_dep'] <= 3:
        prcp_dep = 'medium-rain'
    else:
        prcp_dep = 'high-rain'

    if row['snow_dep'] == 0:
        snow_dep = 'low-snow'
    elif row['snow_dep'] <= 1:
        snow_dep = 'medium-snow'
    else:
        snow_dep = 'high-snow'
    # ARR 
    if row['wspd_arr'] <= 10:
        wind_arr = 'low-wind'
    elif row['wspd_arr'] <= 20:
        wind_arr = 'medium-wind'
    else:
        wind_arr = 'high-wind'

    if row['prcp_arr'] == 0:
        prcp_arr = 'low-rain'
    elif row['prcp_arr'] <= 3:
        prcp_arr = 'medium-rain'
    else:
        prcp_arr = 'high-rain'

    if row['snow_arr'] == 0:
        snow_arr = 'low-snow'
    elif row['snow_arr'] <= 1:
        snow_arr = 'medium-snow'
    else:
        snow_arr = 'high-snow'
    weather_dep = f"{wind_dep}_{prcp_dep}_{snow_dep}"
    weather_arr = f"{wind_arr}_{prcp_arr}_{snow_arr}"
    return weather_dep, weather_arr
       
def new_features(df_g):
    df = df_g.copy()
    # si delay_change>0 alors il a passer du temps en l aire plus qu il n est suppose 
    df["delay_change"] = df["Arr_Delay"] - df["Dep_Delay"]
    df["delay_scenario"] = df.apply(classify_delay, axis=1) # 1 analyse arr et dep / 2 analyse que dep /3 analyse que arr /0 pas d analyse
    
    df['recovery_status'] = df.apply(calculate_recovery_status, axis=1)
    df['recovery_minutes'] = df.apply(calculate_recovery_minutes, axis=1)
    df['recovery_flag'] = (df['recovery_minutes'] > 0).astype(int) 
    
    df['is_delayed_dep'] = df['Dep_Delay'] > 0
    df['is_delayed_arr'] = df['Arr_Delay'] > 0

    df['month'] = df['FlightDate'].dt.month
    df['season'] = df['month'].apply(get_season)
    df['is_weekend'] = df['Day_Of_Week'] >= 6 #1 - Monday

    df['wind_strong_dep'] = df['wspd_dep'] > 30
    df['wind_strong_arr'] = df['wspd_arr'] > 30

    df['prcp_strong_dep'] = df['prcp_dep']>5
    df['prcp_strong_arr'] = df['prcp_arr']>5

    df['snow_strong_dep'] = df['snow_dep']>200
    df['snow_strong_arr'] = df['snow_arr']>200

    df['is_freezing_dep'] = df['tmin_dep'] <= 0
    df['is_freezing_arr'] = df['tmin_arr'] <= 0

    df['is_extreme_heat_dep'] = df['tmax_dep'] >= 35
    df['is_extreme_heat_arr'] = df['tmax_arr'] >= 35

    df['is_low_pressure_dep'] = df['pres_dep'] < 1000
    df['is_low_pressure_arr'] = df['pres_arr'] < 1000
    #wind_prcp_snow

    result = df.apply(categorize_weather_levels, axis=1, result_type='expand')
    print("DEBUG result shape:", result.shape)
    print(result.head())
    df[['weather_combination_dep', 'weather_combination_arr']] = result#df.apply(categorize_weather_levels,axis=1,result_type='expand')

    df['bad_weather_dep'] = ( (df['prcp_strong_dep']) | (df['snow_strong_dep']) | (df['wind_strong_dep']) |(df['is_extreme_heat_dep']) | (df['is_freezing_dep']) |(df['is_low_pressure_dep']) )
    df['bad_weather_arr'] = ( (df['prcp_strong_arr']) | (df['snow_strong_arr']) | (df['wind_strong_arr']) |(df['is_extreme_heat_arr']) | (df['is_freezing_arr']) |(df['is_low_pressure_arr']) )

    df['Route'] = df['Dep_Airport'] + '-' + df['Arr_Airport']
    return df



def gold_table():
    engine = get_engine()
    silver_flights_dates = get_flights_silver_dates(engine)
    gold_dates = get_gold_table_dates(engine)
    new_dates = silver_flights_dates - gold_dates

    df_flights = load_flights_silver(engine,new_dates)
    df_weather = load_weather_silver(engine,new_dates)

    #on va faire double jointure 
    df= jointure(df_flights, df_weather)
    # ajout de nouvelles features
    df = new_features(df )

    df.to_sql(
            "gold_table",
            get_engine(),
            if_exists="append",
            index=False
        )
    dates_df = sorted(df["FlightDate"].unique())
    print("join flights et weather avec date = ", dates_df)
    print("Nombre de lignes :", df.shape)

    return df

def get_gold_table_dates(engine):
    try:
        query = 'SELECT DISTINCT "FlightDate" FROM gold_table'
        df = pd.read_sql(query, engine)
        return set(pd.to_datetime(df["FlightDate"]).dt.date)
    except Exception as e:
        print("gold table not found, first run.")
        return set()
    
# un set de date 
def load_gold_table(engine, new_dates):
    if not new_dates:
        return pd.DataFrame()
    dates_str = "', '".join([str(d) for d in new_dates])
    query = f"""
        SELECT *
        FROM gold_table
        WHERE "FlightDate" IN ('{dates_str}')
    """
    df = pd.read_sql(query, engine)
    return df

def load_gold_table_predction_airport(engine, airport,wcombination):
    query = """
        SELECT *
        FROM gold_table
        WHERE "Dep_Airport" = :airport 
        AND "weather_combination_dep" = :wcombination
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), {
            "airport": airport,
            "wcombination": wcombination
        })
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    return df

def load_gold_table_predction_airport_airline(engine, airport , airline , wcombination):
    query = """
        SELECT *
        FROM gold_table
        WHERE "Dep_Airport" = :airport 
        AND "weather_combination_dep" = :wcombination 
        AND "Airline" = :airline
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), {
            "airport": airport,
            "airline": airline,
            "wcombination": wcombination
        })
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    return df 