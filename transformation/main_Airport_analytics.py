from transformation.agg_Wcombination_ByAirport import Wcombinations_byairport
from transformation.airport_with_bad_weather import top_3_bad_weather_airports,bottom_3_bad_weather_airports,top_3_bad_weather_airports_affected,buttom_3_bad_weather_airports_affected
from transformation.agg_delay_by_airport_month import agg_delay_by_airport_month_avg
from transformation.agg_delay_by_airport_season import agg_delay_by_airport_season_avg
from transformation.agg_delay_by_airport_weekend import agg_delay_by_airport_weekend_avg

if __name__ == "__main__":
        print("*****************************Airports***************************")
        Wcombinations_byairport()
        top_3_bad_weather_airports()
        bottom_3_bad_weather_airports()
        top_3_bad_weather_airports_affected()
        buttom_3_bad_weather_airports_affected()
        agg_delay_by_airport_month_avg()
        agg_delay_by_airport_season_avg()
        agg_delay_by_airport_weekend_avg()