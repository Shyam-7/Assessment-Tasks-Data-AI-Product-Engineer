"""
Step 2 — Transform raw Open-Meteo API responses into a clean, flat DataFrame.

Responsibilities:
 • Flatten the nested hourly arrays into tabular rows
 • Parse and type-cast all columns
 • Handle nulls and missing data without silent row drops
 • Compute derived fields that add analytical value
"""

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

import config

logger = logging.getLogger(__name__)

# WMO weather codes considered "severe" (heavy rain, heavy snow,
# freezing rain, thunderstorms, etc.)
_SEVERE_WEATHER_CODES = frozenset(range(65, 100))


def _flatten_single_response(
    city_meta: dict[str, Any], response: dict[str, Any]
) -> pd.DataFrame:
    """
    Convert one city's API response into a flat DataFrame.

    The API returns hourly data as parallel arrays:
        { "time": [...], "temperature_2m": [...], ... }
    We unpack them into rows (one per hour) and attach city metadata.
    """
    hourly = response.get("hourly", {})

    # Ensure the time array exists — it is the backbone of every row.
    if "time" not in hourly or not hourly["time"]:
        logger.warning("No hourly time data for %s — skipping", city_meta["name"])
        return pd.DataFrame()

    # Build a dict of columns from the hourly arrays.
    records: dict[str, list] = {"timestamp": hourly["time"]}
    for var in config.HOURLY_VARIABLES:
        if var in hourly:
            records[var] = hourly[var]
        else:
            logger.warning(
                "Variable '%s' missing in response for %s — filling with NaN",
                var, city_meta["name"],
            )
            records[var] = [np.nan] * len(hourly["time"])

    df = pd.DataFrame(records)

    # Attach city metadata from our config (not the API's rounded coords).
    df.insert(0, "city_name", city_meta["name"])
    df.insert(1, "latitude", city_meta["latitude"])
    df.insert(2, "longitude", city_meta["longitude"])

    return df


def _cast_types(df: pd.DataFrame) -> pd.DataFrame:
    """Parse timestamps and enforce correct dtypes."""
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["timestamp"].dt.date
    df["hour"] = df["timestamp"].dt.hour

    # Numeric columns — coerce so bad values become NaN instead of crashing.
    float_cols = [
        "temperature_2m", "apparent_temperature", "relative_humidity_2m",
        "precipitation", "wind_speed_10m", "wind_gusts_10m",
        "pressure_msl", "cloud_cover",
    ]
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "weather_code" in df.columns:
        df["weather_code"] = pd.to_numeric(df["weather_code"], errors="coerce")
        # Keep as nullable integer so NaN doesn't force float.
        df["weather_code"] = df["weather_code"].astype("Int64")

    return df


def _compute_heat_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derived field 1 — Heat Index.

    Uses the simplified NOAA formula when temperature >= 27 °C and
    relative humidity >= 40 %. Below that threshold, the heat index
    equals the actual temperature because the formula is not meaningful.

    This is a genuinely useful comfort metric that the raw API does not
    provide.
    """
    temp = df["temperature_2m"]
    rh = df["relative_humidity_2m"]

    # Steadman / NOAA regression (Celsius version)
    hi = (
        -8.784695
        + 1.61139411 * temp
        + 2.338549   * rh
        - 0.14611605 * temp * rh
        - 0.012308094 * temp ** 2
        - 0.016424828 * rh ** 2
        + 0.002211732 * temp ** 2 * rh
        + 0.00072546  * temp * rh ** 2
        - 0.000003582 * temp ** 2 * rh ** 2
    )

    # Only apply the formula where it is physically meaningful.
    applies = (temp >= 27) & (rh >= 40)
    df["heat_index"] = np.where(applies, hi.round(1), temp)

    return df


def _compute_temp_deviation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derived field 2 — Hourly temperature deviation from daily city mean.

    For each (city, date), we compute the mean temperature and then
    calculate how much each hourly reading deviates from it. High
    positive values flag unusually warm hours; negative values flag
    cool spells. Useful for spotting intra-day volatility.
    """
    daily_mean = df.groupby(["city_name", "date"])["temperature_2m"].transform("mean")
    df["temp_deviation_from_daily_mean"] = (df["temperature_2m"] - daily_mean).round(2)
    return df


def _compute_severe_weather_flag(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derived field 3 — Is Severe Weather.

    Maps WMO weather interpretation codes to a boolean flag. Codes >= 65
    cover heavy rain, heavy snow, freezing rain, and thunderstorms. This
    turns a cryptic numeric code into an actionable indicator.
    """
    df["is_severe_weather"] = df["weather_code"].isin(_SEVERE_WEATHER_CODES)
    return df


def _add_pipeline_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Stamp each row with the pipeline run time for audit / lineage."""
    df["fetched_at"] = datetime.now(timezone.utc)
    return df


def transform(raw_results: list[dict[str, Any]]) -> pd.DataFrame:
    """
    Main entry point — takes the list of (city_meta, response) dicts
    from the fetch step and returns a single clean DataFrame ready for
    BigQuery.
    """
    if not raw_results:
        logger.error("No raw data to transform.")
        return pd.DataFrame()

    logger.info("Transforming data for %d cities …", len(raw_results))

    # 1. Flatten each city's response into a DataFrame and concatenate.
    frames = []
    for item in raw_results:
        city_df = _flatten_single_response(item["city"], item["response"])
        if not city_df.empty:
            frames.append(city_df)

    if not frames:
        logger.error("All city responses produced empty DataFrames.")
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    logger.info("Flattened %d total rows across %d cities", len(df), len(frames))

    # 2. Cast types and parse timestamps.
    df = _cast_types(df)

    # 3. Compute derived fields.
    df = _compute_heat_index(df)
    df = _compute_temp_deviation(df)
    df = _compute_severe_weather_flag(df)

    # 4. Add pipeline metadata.
    df = _add_pipeline_metadata(df)

    # 5. Final null audit (log, don't drop).
    null_counts = df.isnull().sum()
    cols_with_nulls = null_counts[null_counts > 0]
    if not cols_with_nulls.empty:
        logger.warning("Columns with null values after transform:\n%s", cols_with_nulls.to_string())
    else:
        logger.info("No null values in the final DataFrame")

    logger.info(
        "Transform complete — %d rows, %d columns. Schema:\n%s",
        len(df), len(df.columns), df.dtypes.to_string(),
    )
    return df
