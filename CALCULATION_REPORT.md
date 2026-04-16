# Flight & Weather Analysis - Calculation Logic Report

## 1) Objective of this report
This report explains how each analytical result is calculated from raw data to final dashboard metrics.

Scope of this report:
- Data content and column-level meaning
- Bronze -> Silver -> Gold data evolution
- Feature engineering logic
- Exact aggregation logic used to answer each graph question
- Why each calculation is appropriate for the business question

Out of scope:
- Infrastructure or technical architecture details (Kafka, orchestration framework, deployment)

---

## 2) Source data overview

### 2.1 Flights source dataset
Source file: `data/US_flights_2023_final.csv`

Columns:
- `FlightDate`: flight date
- `Day_Of_Week`: day index used to derive weekend
- `Airline`: airline name
- `Dep_Airport`: departure airport code
- `Dep_Delay`: departure delay (minutes)
- `Arr_Airport`: arrival airport code
- `Arr_Delay`: arrival delay (minutes)
- `Flight_Duration`: flight duration
- `Delay_Carrier`: delay minutes attributed to carrier
- `Delay_Weather`: delay minutes attributed to weather
- `Delay_NAS`: delay minutes attributed to NAS/airspace system
- `Delay_Security`: delay minutes attributed to security
- `Delay_LastAircraft`: delay minutes attributed to previous aircraft rotation

### 2.2 Weather source dataset
Source file: `data/weather_meteo_by_airport.csv`

Columns:
- `time`: weather date
- `tavg`: average temperature
- `tmin`: minimum temperature
- `tmax`: maximum temperature
- `prcp`: precipitation quantity
- `snow`: snow quantity
- `wdir`: wind direction
- `wspd`: wind speed
- `pres`: pressure
- `airport_id`: airport code

---

## 3) Bronze -> Silver -> Gold data evolution

### 3.1 Bronze layer (raw, minimally transformed)
Purpose: store ingested raw records by date.

Tables:
- `flights_bronze`
- `weather_stream_bronze`

Behavior:
- Flights: next available date is ingested from source file.
- Weather: same-date historical backfill + stream of next date.
- Bronze keeps original business values for downstream cleaning.

### 3.2 Silver layer (cleaned, typed, standardized)
Purpose: ensure data quality and consistency before analytics.

Tables:
- `flights_silver`
- `weather_silver`

Flights cleaning rules:
- Drop sentinel invalid delays where `Arr_Delay == -99` or `Dep_Delay == -99`.
- Convert date and numeric columns to valid types.
- Drop rows missing critical fields:
  - `Arr_Delay`, `Dep_Airport`, `Arr_Airport`, `Dep_Delay`, `FlightDate`, `Flight_Duration`
- Fill nullable delay-cause columns with `0`.
- Fill missing `Airline` with `UNKNOWN`.

Weather cleaning rules:
- Convert date and weather measures to numeric/time types.
- Drop rows missing `time` or `airport_id`.
- Fill `prcp`, `snow` with `0` (assumed no rain/snow when null).
- Fill `tavg` with airport-level mean.
- Fill `wspd`, `pres`, `wdir` with airport-level median.
- Fill missing `tmax`, `tmin` with `tavg`.

### 3.3 Gold layer (joined and feature-rich analytics base)
Purpose: produce one integrated analytical fact table for all KPIs.

Table:
- `gold_table`

Join logic:
1. Keep flights whose departure and arrival airports both exist in weather data.
2. Join weather at departure side on (`Dep_Airport`, `FlightDate`).
3. Join weather at arrival side on (`Arr_Airport`, `FlightDate`).

Result: each flight row has both departure-weather and arrival-weather context.

---

## 4) Gold feature engineering logic

### 4.1 Delay decomposition features
- `delay_change = Arr_Delay - Dep_Delay`

Interpretation:
- Positive `delay_change`: delay worsened between departure and arrival.
- Negative `delay_change`: part of delay recovered during flight.

### 4.2 Delay scenario classification
`delay_scenario` values:
- `1`: both departure delay and in-flight worsening (`Dep_Delay > 0` and `delay_change > 0`)
- `2`: departure-only delay (`Dep_Delay > 0`, no worsening)
- `3`: arrival-side worsening only (`delay_change > 0`, no departure delay)
- `0`: no delay issue for this decomposition

Why this matters:
- It avoids mixing distinct delay mechanisms.
- Aggregations later use scenario-specific delay measures.

### 4.3 Recovery features
- `recovery_status`:
  - `no_delay` if `Dep_Delay <= 0`
  - `no_recovery` if `Dep_Delay > 0` and `Dep_Delay - Arr_Delay <= 0`
  - `partial_recovery` if recovered minutes > 0 and arrival still delayed
  - `total_recovery` if recovered minutes > 0 and arrival on-time/early
- `recovery_minutes = max(Dep_Delay - Arr_Delay, 0)` when `Dep_Delay > 0`, else `0`
- `recovery_flag = 1` if `recovery_minutes > 0`, else `0`

### 4.4 Time context features
- `month = month(FlightDate)`
- `season` mapping:
  - winter: 12, 1, 2
  - spring: 3, 4, 5
  - summer: 6, 7, 8
  - autumn: 9, 10, 11
- `is_weekend = Day_Of_Week >= 6`

### 4.5 Weather intensity flags and combinations
Departure and arrival side flags are built separately.

Strong-condition flags:
- `wind_strong_*: wspd_* > 30`
- `prcp_strong_*: prcp_* > 5`
- `snow_strong_*: snow_* > 200`
- `is_freezing_*: tmin_* <= 0`
- `is_extreme_heat_*: tmax_* >= 35`
- `is_low_pressure_*: pres_* < 1000`

Categorical weather bins for combinations:
- Wind:
  - low: `<= 10`
  - medium: `<= 20`
  - high: `> 20`
- Rain:
  - low: `== 0`
  - medium: `<= 3`
  - high: `> 3`
- Snow:
  - low: `== 0`
  - medium: `<= 1`
  - high: `> 1`

Combined labels:
- `weather_combination_dep = wind_dep + rain_dep + snow_dep`
- `weather_combination_arr = wind_arr + rain_arr + snow_arr`

### 4.6 Bad weather boolean
- `bad_weather_dep = OR(prcp_strong_dep, snow_strong_dep, wind_strong_dep, is_extreme_heat_dep, is_freezing_dep, is_low_pressure_dep)`
- `bad_weather_arr = OR(prcp_strong_arr, snow_strong_arr, wind_strong_arr, is_extreme_heat_arr, is_freezing_arr, is_low_pressure_arr)`

---

## 5) Core aggregation principle used across analytics

A repeated pattern appears in many metrics:
1. Reconstruct a normalized delay dataset from flight rows using `delay_scenario`:
   - scenario 2 uses departure delay
   - scenario 3 uses arrival delay
   - scenario 1 contributes twice:
     - departure side with `Dep_Delay`
     - arrival side with `delay_change`
2. Aggregate with:
- `sum_delay`
- `flight_count`
- `delay_count` where delay > 0
3. Compute final average delay as:

$$
\text{avg_delay} = \frac{\sum \text{delay}}{\sum \text{flight_count}}
$$

Why this is used:
- It aligns each weather/airport/airline context with the relevant delay signal.
- It avoids over-attributing full arrival delay when only additional in-flight worsening is needed.

---

## 6) Calculation logic behind each dashboard question

## 6.1 Weather Impact panel

### Q1: How does precipitation affect delay?
Dataset construction:
- Build records with `prcp` and corresponding delay based on scenario logic.

Bin definition (`prcp_bin`):
- `0`, `0-1`, `1-3`, `3-5`, `5-10`, `>10`

Aggregation per bin:
- `sum_delay`, `flight_count`, `delay_count`
- Final metric shown: `avg_delay = sum_delay / flight_count`

Why it answers the question:
- Binning converts continuous rain into interpretable severity bands.
- Mean delay by band reveals monotonic or non-monotonic impact trends.

### Q2: How does wind speed affect delay?
Same logic as above, replacing variable with `wspd`.

Bins (`wspd_bin`):
- `0`, `0-10`, `10-20`, `20-30`, `>30`

Output metric:
- `avg_delay` per wind-speed bin.

### Q3: How does snow quantity affect delay?
Same logic as above, replacing variable with `snow`.

Bins (`snow_bin`):
- `0`, `0-50`, `50-200`, `200-500`, `>500`

Output metric:
- `avg_delay` per snow bin.

---

## 6.2 Airport Analytics panel

### Q4: Best airport per weather combination
Dataset construction:
- Normalize delay contributions by scenario.
- Group by (`airport`, `weather_combination`).

Aggregation:
- `sum_delay`, `flight_count`, `delay_count`
- `avg_delay = SUM(sum_delay) / SUM(flight_count)`

Selection logic:
- For each weather combination, rank airports by `avg_delay` ascending.
- Keep rank 1 only.

Why it answers the question:
- Compares airports under the same weather context.
- Picks the airport with lowest average delay for each condition profile.

### Q5: Airports with most/least frequent bad weather
From `gold_table` only:
- Count rows where `bad_weather_dep = TRUE` by departure airport
- Union with rows where `bad_weather_arr = TRUE` by arrival airport
- Group by airport and count events

Result:
- Top 3 and bottom 3 by `bad_weather_count`

Why it answers the question:
- Measures exposure frequency to adverse weather, not delay severity.

### Q6: Airports most/least affected by bad weather
Construct bad-weather delay dataset using scenario logic with bad-weather filters:
- scenario 2 + bad departure -> use `Dep_Delay`
- scenario 3 + bad arrival -> use `Arr_Delay`
- scenario 1 + bad departure -> use `Dep_Delay`
- scenario 1 + bad arrival -> use `delay_change`

Aggregate by airport:
- `bad_weather_flights`
- `delay_count`
- `avg_delay_weather = AVG(delay)`
- `total_delay_weather = SUM(delay)`

Result:
- Top 3 (highest avg delay) and bottom 3 (lowest avg delay)

Why it answers the question:
- Separates weather frequency (Q5) from weather impact severity.

### Q7: Average airport delay by month
Normalized scenario delay dataset grouped by (`airport`, `month`).

Metrics:
- `sum_delay`, `flight_count`, `delay_count`
- `avg_delay` from aggregated sums

Why it answers the question:
- Captures seasonality and monthly operational behavior per airport.

### Q8: Average airport delay by season
Same method, grouped by (`airport`, `season`).

Why it answers the question:
- Smooths month-level noise into broader seasonal patterns.

### Q9: Weekend vs non-weekend delay by airport
Same normalized delay dataset grouped by (`airport`, `is_weekend`).

Final output per airport:
- `avg_delay_weekend`
- `flights_weekend`
- `avg_delay_non_weekend`
- `flights_non_weekend`

Why it answers the question:
- Provides direct operational comparison between weekend and weekday conditions.

---

## 6.3 Airline Analytics panel

### Q10: Best airline per weather combination
Dataset logic mirrors airport weather-combination logic, grouped by (`airline`, `weather_combination`).

Selection:
- For each weather combination, choose airline with lowest `avg_delay`.

Why it answers the question:
- Compares airline performance under identical weather contexts.

### Q11: Airlines most/least affected by bad weather
Construct bad-weather delay dataset by airline (scenario-aware, same idea as airport).

Aggregate by airline:
- `bad_weather_flights`
- `delay_count`
- `avg_delay_weather`
- `total_delay_weather`

Result:
- Top 3 and bottom 3 by `avg_delay_weather`

Why it answers the question:
- Identifies carriers with high/low sensitivity to adverse weather.

### Q12: Airline recovery capability
Input subset:
- Flights with `Dep_Delay > 0`

Aggregate by airline:
- `avg_recovery = AVG(recovery_minutes)`
- `recovery_rate = SUM(1 if recovery_minutes > 0 else 0) / COUNT(*)`
- `total_delayed_flights = COUNT(*)`

Result:
- Top 3 and bottom 3 by `recovery_rate`

Why it answers the question:
- Measures ability to absorb initial delay and recover before arrival.

---

## 6.4 Airline-Airport panel

### Q13: Best/worst airlines per airport during bad weather
Dataset:
- Only bad-weather, scenario-aware delay rows.
- Group by (`airport`, `airline`).

Aggregate:
- `sum_delay`, `flight_count`, `delay_count`
- `avg_delay = SUM(sum_delay)/SUM(flight_count)`

Stability rule:
- Keep only airline-airport groups with at least 5 flights.

Ranking per airport:
- Best view: ascending avg delay, top 3
- Worst view: descending avg delay, top 3

Why it answers the question:
- Gives route-local airline benchmarking under difficult weather.
- Minimum-flight filter avoids misleading results from tiny samples.

---

## 6.5 Prediction panel

### Q14: Delay estimate for airport (optionally airline)
Step 1: get latest weather row for the airport from `weather_silver`.

Step 2: convert latest weather to one categorical weather combination using the same binning logic used in gold.

Step 3: retrieve historical records from `gold_table`:
- With airline: (`Dep_Airport`, `Airline`, `weather_combination_dep`)
- Fallback without airline if no records.

Step 4: compute:

$$
\text{predicted_delay} = \text{mean}(Dep\_Delay \mid \text{matching historical subset})
$$

Also report sample size `n = count(subset)`.

Why it answers the question:
- Uses historical analogs under same airport-weather (and optionally airline) context.
- Produces an interpretable baseline estimate.

---

## 7) Processed-date incremental logic and metric consistency
Most aggregate tables maintain a separate `processed_dates` table.

Implication:
- New analytics are computed only for new `FlightDate` values not previously processed.
- Upsert strategy accumulates aggregate components (`sum_delay`, `flight_count`, `delay_count`) instead of reprocessing entire history.

Why this matters for calculations:
- Final averages remain consistent with full-history aggregation:

$$
\frac{\sum_d \text{sum_delay}_d}{\sum_d \text{flight_count}_d}
$$

- This is mathematically equivalent to recomputing from raw, as long as each date is processed once.

---

## 8) Interpretation guide for readers
- `avg_delay` reflects delay severity per observation context.
- `bad_weather_count` reflects exposure frequency, not severity.
- `recovery_rate` reflects resilience after initial departure delay.
- Weather-combination winners indicate comparative performance under specific weather mixes, not overall airport/airline quality.
- For airline-airport rankings, the 5-flight threshold improves robustness.

---

## 9) Summary
The project answers operational delay questions by:
1. Cleaning and standardizing flights/weather data into Silver,
2. Building a feature-rich Gold table with scenario-aware delay decomposition,
3. Computing context-specific aggregates (weather, airport, airline, airline-airport, temporal),
4. Ranking or summarizing these aggregates to match each graph question.

The central methodological choice is scenario-aware delay attribution (`Dep_Delay`, `Arr_Delay`, `delay_change`) combined with grouped aggregate metrics (`sum_delay`, `flight_count`, `delay_count`) and explicit ranking logic.
