from sqlalchemy import text
from db.postgresConnection import get_engine
import pandas as pd

def airline_recovery(engine, limit=3, top=True):
    order = "DESC" if top else "ASC"
    query = text(f"""SELECT 
            "Airline",
            AVG(recovery_minutes) AS avg_recovery,
            SUM(CASE WHEN recovery_minutes > 0 THEN 1 ELSE 0 END)::float 
                / COUNT(*) AS recovery_rate,
            COUNT(*) AS total_delayed_flights
            FROM gold_table
            WHERE "Dep_Delay" > 0
            GROUP BY "Airline"
            ORDER BY recovery_rate {order}
            LIMIT :limit;
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"limit": limit})
        rows = result.fetchall()

        df = pd.DataFrame(rows, columns=result.keys())

    return df

def top_3_airlines_recovery_rate():
    engine=get_engine()
    top3= airline_recovery(engine, limit=3,top=True)
    print("3 airlines with the highest recovery rate:")
    print(top3)
    return top3

def buttom_3_airlines_recovery_rate():
    engine=get_engine()
    buttom3= airline_recovery(engine, limit=3,top=False)
    print("3 airlines with the lowest recovery rate:")
    print(buttom3)
    return buttom3