from transformation.agg_delay_by_prcp import prcp_avg_rate
from transformation.agg_delay_by_wspd import wspd_avg_rate
from transformation.agg_delay_by_snow import snow_avg_rate

if __name__ == "__main__":
        print("*****************************Pluie***************************")
        prcp_avg_rate()
        print("*****************************vent***************************")
        wspd_avg_rate()
        print("*****************************Snow***************************")
        snow_avg_rate()