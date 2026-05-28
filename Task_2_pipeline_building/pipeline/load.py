"""
Step 3 — Load transformed data into Google BigQuery.

Uses batch load jobs (load_table_from_dataframe) rather than DML or
streaming inserts, because the BigQuery Sandbox disables both of those.
Creates the dataset if it does not already exist.
"""

import logging

import pandas as pd
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema definition — explicit types for every column.
# This is deliberate: autodetect is convenient but fragile in pipelines.
# ---------------------------------------------------------------------------
SCHEMA = [
    bigquery.SchemaField("city_name",                     "STRING",    mode="REQUIRED"),
    bigquery.SchemaField("latitude",                      "FLOAT64",   mode="REQUIRED"),
    bigquery.SchemaField("longitude",                     "FLOAT64",   mode="REQUIRED"),
    bigquery.SchemaField("timestamp",                     "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("date",                          "DATE",      mode="REQUIRED"),
    bigquery.SchemaField("hour",                          "INT64",     mode="REQUIRED"),
    bigquery.SchemaField("temperature_2m",                "FLOAT64",   mode="NULLABLE"),
    bigquery.SchemaField("apparent_temperature",          "FLOAT64",   mode="NULLABLE"),
    bigquery.SchemaField("relative_humidity_2m",          "FLOAT64",   mode="NULLABLE"),
    bigquery.SchemaField("precipitation",                 "FLOAT64",   mode="NULLABLE"),
    bigquery.SchemaField("wind_speed_10m",                "FLOAT64",   mode="NULLABLE"),
    bigquery.SchemaField("wind_gusts_10m",                "FLOAT64",   mode="NULLABLE"),
    bigquery.SchemaField("pressure_msl",                  "FLOAT64",   mode="NULLABLE"),
    bigquery.SchemaField("cloud_cover",                   "FLOAT64",   mode="NULLABLE"),
    bigquery.SchemaField("weather_code",                  "INT64",     mode="NULLABLE"),
    bigquery.SchemaField("heat_index",                    "FLOAT64",   mode="NULLABLE"),
    bigquery.SchemaField("temp_deviation_from_daily_mean","FLOAT64",   mode="NULLABLE"),
    bigquery.SchemaField("is_severe_weather",             "BOOLEAN",   mode="NULLABLE"),
    bigquery.SchemaField("fetched_at",                    "TIMESTAMP", mode="REQUIRED"),
]


def _ensure_dataset(client: bigquery.Client) -> None:
    """Create the dataset if it does not exist (idempotent)."""
    dataset_ref = bigquery.DatasetReference(config.BQ_PROJECT_ID, config.BQ_DATASET_ID)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "US"

    dataset = client.create_dataset(dataset, exists_ok=True)
    logger.info("Dataset %s.%s ready", config.BQ_PROJECT_ID, config.BQ_DATASET_ID)


def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Coerce pandas types to match the BigQuery schema exactly.

    pyarrow (used under the hood by load_table_from_dataframe) is strict
    about type alignment. We make sure everything is in the right shape
    before handing it off.
    """
    df = df.copy()

    # Ensure timestamp columns are timezone-aware UTC.
    for col in ("timestamp", "fetched_at"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True)

    # Ensure date is a proper date type.
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date

    # Cast weather_code from nullable Int64 to regular int-compatible float
    # (pyarrow handles float-to-int conversion for nullable integers).
    if "weather_code" in df.columns:
        df["weather_code"] = df["weather_code"].astype("Int64")

    return df


def load_to_bigquery(df: pd.DataFrame) -> bool:
    """
    Load a DataFrame into BigQuery.

    Uses WRITE_TRUNCATE so each pipeline run replaces the table.
    This avoids duplicates when re-running and keeps the table
    at a predictable size (latest 7 days only).

    Returns True on success, False on failure.
    """
    if df.empty:
        logger.error("Empty DataFrame — nothing to load.")
        return False

    table_id = f"{config.BQ_PROJECT_ID}.{config.BQ_DATASET_ID}.{config.BQ_TABLE_ID}"
    logger.info("Loading %d rows into %s …", len(df), table_id)

    try:
        client = bigquery.Client(project=config.BQ_PROJECT_ID)
    except Exception as exc:
        logger.error("Failed to create BigQuery client: %s", exc)
        logger.error(
            "Make sure you've authenticated with: gcloud auth application-default login"
        )
        return False

    # Create the dataset if needed.
    try:
        _ensure_dataset(client)
    except GoogleAPIError as exc:
        logger.error("Failed to create/verify dataset: %s", exc)
        return False

    # Prepare the DataFrame for loading.
    df = _prepare_dataframe(df)

    # Configure the load job.
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    # Execute the load.
    try:
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()  # Block until the job completes.
    except GoogleAPIError as exc:
        logger.error("BigQuery load job failed: %s", exc)
        return False
    except Exception as exc:
        logger.error("Unexpected error during BigQuery load: %s", exc)
        return False

    # Verify.
    table = client.get_table(table_id)
    logger.info(
        "✓ Load complete — %d rows now in %s (table has %d rows total)",
        len(df), table_id, table.num_rows,
    )
    return True
