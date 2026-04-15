from transformation.airline_recovery import buttom_3_airlines_recovery_rate,top_3_airlines_recovery_rate
from transformation.agg_Wcombination_ByAirline import Wcombinations_byairline
from transformation.airline_with_bad_weather import top_3_bad_weather_airlines_affected,buttom_3_bad_weather_airlines_affected

if __name__ == "__main__":
        print("*****************************Airlines***************************")
        Wcombinations_byairline()
        top_3_bad_weather_airlines_affected()
        buttom_3_bad_weather_airlines_affected()
        top_3_airlines_recovery_rate()
        buttom_3_airlines_recovery_rate()