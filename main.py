from ingestion.flights_batch import ingest_flights_incremental ,load_batch_flights_bronze_from_db
from ingestion.weather_stream import stream_weather_for_date
from transformation.clean_flights import clean_flights
from transformation.clean_weather import clean_weather
from datetime import timedelta
from transformation.gold_table import gold_table
from transformation.agg_delay_by_prcp import prcp_avg_rate
from transformation.agg_delay_by_wspd import wspd_avg_rate
from transformation.agg_delay_by_snow import snow_avg_rate
from transformation.agg_Wcombination_ByAirport import Wcombinations_byairport
from transformation.airport_with_bad_weather import top_3_bad_weather_airports,bottom_3_bad_weather_airports,top_3_bad_weather_airports_affected,buttom_3_bad_weather_airports_affected
from transformation.agg_Wcombination_ByAirline import Wcombinations_byairline
from transformation.airline_with_bad_weather import top_3_bad_weather_airlines_affected,buttom_3_bad_weather_airlines_affected
from transformation.airline_recovery import buttom_3_airlines_recovery_rate,top_3_airlines_recovery_rate
from transformation.agg_delay_by_airport_month import agg_delay_by_airport_month_avg
from transformation.agg_delay_by_airport_season import agg_delay_by_airport_season_avg
from transformation.agg_delay_by_airport_weekend import agg_delay_by_airport_weekend_avg
from transformation.airline_airport_bad_weather import agg_delay_by_airline_airport_bad_weather_avg_best,agg_delay_by_airline_airport_bad_weather_avg_worst
from transformation.delay_predection import predict_delay

if __name__ == "__main__":
    ingested_flights_date= ingest_flights_incremental("data/US_flights_2023_final.csv")
    
    if ingested_flights_date is None:
        print("Aucun nouveau batch flights → pas de cleaning")
    else:
        print(f"Batch flight ingéré : {ingested_flights_date}")

        ingested_weather_date = stream_weather_for_date("data/weather_meteo_by_airport.csv", ingested_flights_date)
        print(f"Streamming weather ingéré : {ingested_weather_date}")

        df_batch_flights_bronze = load_batch_flights_bronze_from_db(ingested_flights_date)
        clean_flights()
        clean_weather()
        
        gold_table()
        print("*****************************Pluie***************************")
        prcp_avg_rate()
        print("*****************************vent***************************")
        wspd_avg_rate()
        print("*****************************Snow***************************")
        snow_avg_rate()
        print("*****************************Airports***************************")
        Wcombinations_byairport()
        top_3_bad_weather_airports()
        bottom_3_bad_weather_airports()
        top_3_bad_weather_airports_affected()
        buttom_3_bad_weather_airports_affected()
        agg_delay_by_airport_month_avg()
        agg_delay_by_airport_season_avg()
        agg_delay_by_airport_weekend_avg()
        print("*****************************Airlines***************************")
        Wcombinations_byairline()
        top_3_bad_weather_airlines_affected()
        buttom_3_bad_weather_airlines_affected()
        top_3_airlines_recovery_rate()
        buttom_3_airlines_recovery_rate()
        print("*****************************Airports/Airlines***************************")
        agg_delay_by_airline_airport_bad_weather_avg_best()
        agg_delay_by_airline_airport_bad_weather_avg_worst()
        print("*****************************Predction***************************")
        print("*** avec Airports seulement")
        predict_delay("LAX", airline=None)
        print("*** avec Airports et airline")
        predict_delay("LAX", "Skywest Airlines Inc.")
        
        