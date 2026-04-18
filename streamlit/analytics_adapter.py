import io
from contextlib import redirect_stdout
from typing import Any, Dict, List, Optional

import pandas as pd

from ingestion.flights_batch import ingest_flights_incremental
from ingestion.weather_stream import stream_weather_for_date
from transformation.clean_flights import clean_flights
from transformation.clean_weather import clean_weather
from transformation.gold_table import gold_table

from transformation.agg_delay_by_prcp import agg_delay_by_prcp, compute_final_metrics_prcp
from transformation.agg_delay_by_wspd import agg_delay_by_wspd, compute_final_metrics_wspd
from transformation.agg_delay_by_snow import agg_delay_by_snow, compute_final_metrics_snow

from transformation.agg_Wcombination_ByAirport import (
    agg_delay_by_wcombination_byairport,
    compute_final_metrics as compute_wcombo_airport_metrics,
)
from transformation.airport_with_bad_weather import (
    top_3_bad_weather_airports,
    bottom_3_bad_weather_airports,
    top_3_bad_weather_airports_affected,
    buttom_3_bad_weather_airports_affected,
)
from transformation.agg_delay_by_airport_month import (
    agg_delay_by_airport_month,
    compute_final_metrics as compute_airport_month_metrics,
)
from transformation.agg_delay_by_airport_season import (
    agg_delay_by_airport_season,
    compute_final_metrics as compute_airport_season_metrics,
)
from transformation.agg_delay_by_airport_weekend import (
    agg_delay_by_airport_weekend,
    compute_final_metrics as compute_airport_weekend_metrics,
)

from transformation.agg_Wcombination_ByAirline import (
    agg_delay_by_wcombination_byairline,
    compute_final_metrics as compute_wcombo_airline_metrics,
)
from transformation.airline_with_bad_weather import (
    top_3_bad_weather_airlines_affected,
    buttom_3_bad_weather_airlines_affected,
)
from transformation.airline_recovery import (
    top_3_airlines_recovery_rate,
    buttom_3_airlines_recovery_rate,
)

from transformation.airline_airport_bad_weather import (
    agg_delay_by_airline_airport_bad_weather,
    compute_final_metrics as compute_airline_airport_bad_weather_metrics,
)

from transformation.delay_predection import predict_delay
from db.postgresConnection import get_engine
import pandas as pd

def get_pipeline_last_update():
    engine = get_engine()
    df = pd.read_sql("SELECT last_update FROM pipeline_status WHERE id=1", engine)
    return df.iloc[0, 0]

def _rows_to_df(rows: Any, columns: List[str]) -> pd.DataFrame:
    if rows is None:
        return pd.DataFrame(columns=columns)
    if isinstance(rows, pd.DataFrame):
        return rows
    return pd.DataFrame(rows, columns=columns)


def _safe_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception:
        return None


def _as_df(value: Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value
    return pd.DataFrame()


def run_full_pipeline_with_logs(
    flights_csv: str,
    weather_csv: str,
) -> Dict[str, Any]:
    """Run a flow equivalent to main.py and capture print outputs."""
    logs = io.StringIO()

    with redirect_stdout(logs):
        ingested_flights_date = ingest_flights_incremental(flights_csv)

        if ingested_flights_date is None:
            print("Aucun nouveau batch flights -> pas de cleaning")
            return {
                "logs": logs.getvalue(),
                "ingested_flights_date": None,
                "ingested_weather_date": None,
            }

        print(f"Batch flight ingere : {ingested_flights_date}")
        ingested_weather_date = stream_weather_for_date(weather_csv, ingested_flights_date)
        print(f"Streaming weather ingere : {ingested_weather_date}")

        clean_flights()
        clean_weather()
        gold_table()

        agg_delay_by_prcp()
        agg_delay_by_wspd()
        agg_delay_by_snow()

        agg_delay_by_wcombination_byairport()
        agg_delay_by_airport_month()
        agg_delay_by_airport_season()
        agg_delay_by_airport_weekend()

        agg_delay_by_wcombination_byairline()

        agg_delay_by_airline_airport_bad_weather()

    return {
        "logs": logs.getvalue(),
        "ingested_flights_date": ingested_flights_date,
        "ingested_weather_date": ingested_weather_date,
    }


def collect_all_analytics() -> Dict[str, pd.DataFrame]:
    """Collect all analytics displayed in main.py print statements."""
    engine = get_engine()

    # Keep aggregates up-to-date before reading final metrics.
    _safe_call(agg_delay_by_prcp)
    _safe_call(agg_delay_by_wspd)
    _safe_call(agg_delay_by_snow)
    _safe_call(agg_delay_by_wcombination_byairport)
    _safe_call(agg_delay_by_airport_month)
    _safe_call(agg_delay_by_airport_season)
    _safe_call(agg_delay_by_airport_weekend)
    _safe_call(agg_delay_by_wcombination_byairline)
    _safe_call(agg_delay_by_airline_airport_bad_weather)

    top_airports_weather_count = _rows_to_df(
        _safe_call(top_3_bad_weather_airports), ["airport", "bad_weather_count"]
    )
    bottom_airports_weather_count = _rows_to_df(
        _safe_call(bottom_3_bad_weather_airports), ["airport", "bad_weather_count"]
    )

    return {
        "weather_prcp": _as_df(_safe_call(compute_final_metrics_prcp, engine)),
        "weather_wspd": _as_df(_safe_call(compute_final_metrics_wspd, engine)),
        "weather_snow": _as_df(_safe_call(compute_final_metrics_snow, engine)),
        "airport_wcomb_best": _as_df(_safe_call(compute_wcombo_airport_metrics, engine)),
        "airport_bad_weather_top3_count": top_airports_weather_count,
        "airport_bad_weather_bottom3_count": bottom_airports_weather_count,
        "airport_bad_weather_top3_affected": _as_df(_safe_call(top_3_bad_weather_airports_affected)),
        "airport_bad_weather_bottom3_affected": _as_df(_safe_call(buttom_3_bad_weather_airports_affected)),
        "airport_month": _as_df(_safe_call(compute_airport_month_metrics, engine)),
        "airport_season": _as_df(_safe_call(compute_airport_season_metrics, engine)),
        "airport_weekend": _as_df(_safe_call(compute_airport_weekend_metrics, engine)),
        "airline_wcomb_best": _as_df(_safe_call(compute_wcombo_airline_metrics, engine)),
        "airline_bad_weather_top3_affected": _as_df(_safe_call(top_3_bad_weather_airlines_affected)),
        "airline_bad_weather_bottom3_affected": _as_df(_safe_call(buttom_3_bad_weather_airlines_affected)),
        "airline_recovery_top3": _as_df(_safe_call(top_3_airlines_recovery_rate)),
        "airline_recovery_bottom3": _as_df(_safe_call(buttom_3_airlines_recovery_rate)),
        "airline_airport_best": _as_df(_safe_call(compute_airline_airport_bad_weather_metrics, engine, False)),
        "airline_airport_worst": _as_df(_safe_call(compute_airline_airport_bad_weather_metrics, engine, True)),
    }


def run_prediction(airport: str, airline: Optional[str] = None) -> Optional[float]:
    if not airport:
        return None
    if airline:
        return predict_delay(airport, airline)
    return predict_delay(airport, airline=None)
