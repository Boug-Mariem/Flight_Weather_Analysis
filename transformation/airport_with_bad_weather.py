from sqlalchemy import text
from db.postgresConnection import get_engine
import pandas as pd

def get_bad_weather_airports(engine, limit=3, top=True):
    order = "DESC" if top else "ASC"

    query = text(f"""
        SELECT airport, COUNT(*) AS bad_weather_count
        FROM (
            SELECT "Dep_Airport" AS airport
            FROM gold_table
            WHERE bad_weather_dep = TRUE

            UNION ALL

            SELECT "Arr_Airport" AS airport
            FROM gold_table
            WHERE bad_weather_arr = TRUE
        ) t
        GROUP BY airport
        ORDER BY bad_weather_count {order}
        LIMIT :limit
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"limit": limit})
        rows = result.fetchall()

    return rows

# utilisation 
def top_3_bad_weather_airports():
    engine=get_engine()
    top3= get_bad_weather_airports(engine, limit=3, top=True)
    print("Top 3 airports with the most frequent bad weather:")
    for r in top3:
        print(r)
    return top3

def bottom_3_bad_weather_airports():
    engine=get_engine()
    bottom3= get_bad_weather_airports(engine, limit=3, top=False)
    print("3 airports with the least frequent bad weather:")
    for r in bottom3:
        print(r)
    return bottom3


# lors du bad weather quelles airports ont un avg delay plus grand 
def bad_weather_airport_metrics(engine, limit=3, top=True):
    order = "DESC" if top else "ASC"
    query = text(f"""
        SELECT airport,
               COUNT(*) AS bad_weather_flights,
               COUNT(*) FILTER (WHERE delay > 0) AS delay_count,
               AVG(delay) AS avg_delay_weather,
               SUM(delay) AS total_delay_weather
        FROM (
            -- Scenario 2 → DEP uniquement
            SELECT "Dep_Airport" AS airport,
                "Dep_Delay" AS delay
            FROM gold_table
            WHERE delay_scenario = 2
            AND bad_weather_dep = TRUE

            UNION ALL

            -- Scenario 3 → ARR uniquement
            SELECT "Arr_Airport" AS airport,
                "Arr_Delay" AS delay
            FROM gold_table
            WHERE delay_scenario = 3
            AND bad_weather_arr = TRUE

            UNION ALL

            -- Scenario 1 → DEP (si bad weather)
            SELECT "Dep_Airport" AS airport,
                "Dep_Delay" AS delay
            FROM gold_table
            WHERE delay_scenario = 1
            AND bad_weather_dep = TRUE

            UNION ALL

            -- Scenario 1 → ARR (si bad weather)
            SELECT "Arr_Airport" AS airport,
                "delay_change" AS delay
            FROM gold_table
            WHERE delay_scenario = 1
            AND bad_weather_arr = TRUE


        ) t
        GROUP BY airport
        ORDER BY avg_delay_weather {order}
        LIMIT :limit
    """)
    # ORDER BY delay_count DESC si on veut voir les airport qui tombe plus dans le delay (sans ce soussier si c est un garmd delay ou pas )
    with engine.connect() as conn:
        result = conn.execute(query, {"limit": limit})
        rows = result.fetchall()

        df = pd.DataFrame(rows, columns=result.keys())

    return df

def top_3_bad_weather_airports_affected():
    engine=get_engine()
    top3= bad_weather_airport_metrics(engine, limit=3,top=True)
    print("3 airports with the highest delay due to the bad weather:")
    print(top3)
    return top3

def buttom_3_bad_weather_airports_affected():
    engine=get_engine()
    buttom3= bad_weather_airport_metrics(engine, limit=3,top=False)
    print("3 airports with the lowest delay due to the bad weather:")
    print(buttom3)
    return buttom3
    