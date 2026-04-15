from ingestion.flights_batch import ingest_flights_incremental
from ingestion.weather_stream import stream_weather_for_date
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if __name__ == "__main__":
    ingested_flights_date= ingest_flights_incremental("data/US_flights_2023_final.csv")
    
    if ingested_flights_date is None:
        print("Aucun nouveau batch flights → pas de cleaning")
    else:
        print(f"Batch flight ingéré : {ingested_flights_date}")

        ingested_weather_date = stream_weather_for_date("data/weather_meteo_by_airport.csv", ingested_flights_date)
        print(f"Streamming weather ingéré : {ingested_weather_date}")