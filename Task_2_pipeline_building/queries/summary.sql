-- ============================================================================
-- Weather Data Pipeline — SQL Summary Queries
-- Run these against the BigQuery table: weather_pipeline.hourly_weather
-- ============================================================================


-- ---------------------------------------------------------------------------
-- Query 1: Daily Weather Summary by City (time-based trend + aggregation)
--
-- Purpose: Shows how weather evolved day-by-day across all cities over the
--          last 7 days. Combines aggregations (avg, min, max, sum) with the
--          derived severe-weather flag to produce a dashboard-ready summary.
-- ---------------------------------------------------------------------------
SELECT
    city_name,
    date,
    ROUND(AVG(temperature_2m), 1)           AS avg_temp_c,
    ROUND(MIN(temperature_2m), 1)           AS min_temp_c,
    ROUND(MAX(temperature_2m), 1)           AS max_temp_c,
    ROUND(MAX(temperature_2m) - MIN(temperature_2m), 1) AS temp_range_c,
    ROUND(AVG(relative_humidity_2m), 1)     AS avg_humidity_pct,
    ROUND(SUM(precipitation), 2)            AS total_precipitation_mm,
    ROUND(AVG(wind_speed_10m), 1)           AS avg_wind_speed_kmh,
    ROUND(MAX(wind_gusts_10m), 1)           AS max_wind_gust_kmh,
    COUNTIF(is_severe_weather)              AS severe_weather_hours,
    ROUND(AVG(heat_index), 1)               AS avg_heat_index
FROM
    `weather_pipeline.hourly_weather`
GROUP BY
    city_name, date
ORDER BY
    city_name, date;


-- ---------------------------------------------------------------------------
-- Query 2: Top 10 Most Extreme Weather Moments
--
-- Purpose: Surfaces the most noteworthy data points across all cities —
--          moments with severe weather, high winds, or heavy precipitation.
--          Demonstrates that the derived fields (is_severe_weather, heat_index)
--          make the data analytically actionable beyond what the raw API gives.
-- ---------------------------------------------------------------------------
SELECT
    city_name,
    timestamp,
    temperature_2m,
    apparent_temperature,
    wind_gusts_10m,
    precipitation,
    weather_code,
    heat_index,
    is_severe_weather
FROM
    `weather_pipeline.hourly_weather`
WHERE
    is_severe_weather = TRUE
    OR wind_gusts_10m > 50
    OR precipitation > 5
ORDER BY
    precipitation DESC,
    wind_gusts_10m DESC
LIMIT 10;
