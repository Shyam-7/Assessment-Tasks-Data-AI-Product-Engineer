# Weather Data Pipeline

A complete data pipeline that fetches weather data from the Open-Meteo API, transforms it into a clean analytical format, and loads it into Google BigQuery.

---

## Table of Contents

- [API Choice](#api-choice-open-meteo)
- [How to Run the Pipeline](#how-to-run-the-pipeline)
- [BigQuery Setup](#bigquery-setup)
- [Pipeline Architecture](#pipeline-architecture)
- [Data Transformations](#data-transformations)
- [SQL Summary Query](#sql-summary-query)
- [Production Thinking](#production-thinking)
- [Decisions and Trade-offs](#decisions-and-trade-offs)
- [What I Would Do Differently With More Time](#what-i-would-do-differently-with-more-time)

---

## API Choice: Open-Meteo

I chose [Open-Meteo](https://open-meteo.com/) for several deliberate reasons:

| Criterion | Why it matters |
|---|---|
| **No API key required** | Anyone cloning this repo can run the pipeline immediately — no signup, no secrets management, no `.env` files. This matters for reviewability. |
| **Structured, nested JSON** | The API returns nested objects with parallel arrays (`hourly.time[]`, `hourly.temperature_2m[]`, etc.), which gives the transform step real work to do. |
| **Rich enough for derived fields** | Multiple weather variables (temperature, humidity, wind, precipitation, weather codes) allow meaningful computed fields like heat index and severe weather flags. |
| **Reliable and fast** | 10,000 free calls per day, consistent response shape, no authentication failures. |
| **Universally understandable data** | Weather data needs no domain context to verify — anyone reviewing the output can immediately tell if the numbers make sense. |

### What the pipeline fetches

- **Endpoint:** `/v1/forecast` with `past_days=7` (last 7 days of hourly data)
- **Cities:** London, New York, Tokyo, Sydney, Mumbai (5 cities across multiple continents)
- **Variables:** temperature, apparent temperature, humidity, precipitation, wind speed, wind gusts, pressure, cloud cover, weather code
- **Result:** ~840 rows per run (5 cities × 168 hours)

---

## How to Run the Pipeline

### Prerequisites

- Python 3.9 or later
- A Google Cloud project with BigQuery enabled (free Sandbox is sufficient)
- `gcloud` CLI installed and authenticated

### Setup

```bash
# 1. Clone the repository and navigate to Task 2
cd Task_2_pipeline_building

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Authenticate with Google Cloud
gcloud auth application-default login

# 5. Set your GCP project ID
export GOOGLE_CLOUD_PROJECT="your-project-id"
# On Windows PowerShell: $env:GOOGLE_CLOUD_PROJECT="your-project-id"
```

### Run

```bash
python main.py
```

The pipeline will log every step to stdout:

```
2025-05-28 12:00:00  INFO      pipeline                   ============================================================
2025-05-28 12:00:00  INFO      pipeline                   Weather Data Pipeline — starting
2025-05-28 12:00:00  INFO      pipeline                   ============================================================
2025-05-28 12:00:00  INFO      pipeline                   STEP 1/3 — Fetching data from Open-Meteo API …
2025-05-28 12:00:00  INFO      pipeline.fetch             Starting data fetch for 5 cities …
2025-05-28 12:00:00  INFO      pipeline.fetch             Fetching data for London (51.51, -0.13) …
2025-05-28 12:00:01  INFO      pipeline.fetch             Received 168 hourly records for London
...
2025-05-28 12:00:05  INFO      pipeline                   STEP 2/3 — Transforming raw data …
...
2025-05-28 12:00:06  INFO      pipeline                   STEP 3/3 — Loading data to BigQuery …
...
2025-05-28 12:00:10  INFO      pipeline                   Pipeline completed successfully in 10.2 seconds
```

---

## BigQuery Setup

### Using the BigQuery Sandbox (Free)

1. Go to [console.cloud.google.com/bigquery](https://console.cloud.google.com/bigquery)
2. Sign in with any Google account — a default project is created automatically
3. No credit card or billing account is required

### Sandbox Limitations and How I Handled Them

The BigQuery Sandbox imposes restrictions compared to a full GCP account. These directly shaped the implementation:

| Sandbox Limitation | Impact | How I Handled It |
|---|---|---|
| **No DML** (INSERT, UPDATE, DELETE) | Cannot use SQL to insert rows | Used `load_table_from_dataframe()` — a **batch load job**, not DML. Fully supported in Sandbox. |
| **No streaming inserts** | Cannot use `insert_rows()` or `insert_rows_json()` | Same workaround — batch load jobs. |
| **60-day table expiration** | All tables auto-delete after 60 days | Acceptable for this assessment. In production, upgrading to a billing account removes this. |
| **No scheduled queries** | Cannot schedule SQL queries natively | Not needed — scheduling is addressed in the production thinking section below. |
| **10 GB storage / 1 TB queries per month** | Usage caps | Our data is tiny (~840 rows ≈ a few KB). No issue. |

### Schema

The pipeline creates a dataset called `weather_pipeline` and a table called `hourly_weather` with this schema:

| Column | Type | Description |
|---|---|---|
| `city_name` | STRING | City name |
| `latitude` | FLOAT64 | Latitude coordinate |
| `longitude` | FLOAT64 | Longitude coordinate |
| `timestamp` | TIMESTAMP | Hourly observation time (UTC) |
| `date` | DATE | Extracted date |
| `hour` | INT64 | Hour of day (0–23) |
| `temperature_2m` | FLOAT64 | Air temperature at 2m (°C) |
| `apparent_temperature` | FLOAT64 | Feels-like temperature (°C) |
| `relative_humidity_2m` | FLOAT64 | Relative humidity (%) |
| `precipitation` | FLOAT64 | Precipitation (mm) |
| `wind_speed_10m` | FLOAT64 | Wind speed at 10m (km/h) |
| `wind_gusts_10m` | FLOAT64 | Wind gusts at 10m (km/h) |
| `pressure_msl` | FLOAT64 | Mean sea level pressure (hPa) |
| `cloud_cover` | FLOAT64 | Cloud cover (%) |
| `weather_code` | INT64 | WMO weather interpretation code |
| `heat_index` | FLOAT64 | **Derived:** Comfort temperature (NOAA formula) |
| `temp_deviation_from_daily_mean` | FLOAT64 | **Derived:** Hourly deviation from city-day average |
| `is_severe_weather` | BOOLEAN | **Derived:** True if weather code ≥ 65 |
| `fetched_at` | TIMESTAMP | Pipeline execution time (audit trail) |

---

## Pipeline Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Open-Meteo │     │    Transform     │     │    BigQuery      │
│   API        │────▶│                  │────▶│                  │
│              │     │  • Flatten JSON  │     │  • Batch load    │
│  /v1/forecast│     │  • Cast types    │     │  • Explicit      │
│  ?past_days=7│     │  • Derived fields│     │    schema        │
│              │     │  • Null audit    │     │  • WRITE_TRUNCATE│
└──────────────┘     └──────────────────┘     └──────────────────┘
      fetch.py            transform.py              load.py
```

### Step 1: Fetch (`pipeline/fetch.py`)

- Calls the API once per city with all parameters from `config.py`
- Automatic retries (3×) with exponential backoff on 429/5xx errors
- If one city fails, the rest still run — errors are logged, not raised
- Returns a list of `{city_meta, raw_response}` dicts

### Step 2: Transform (`pipeline/transform.py`)

- Flattens nested parallel arrays into rows (one per city-hour)
- Parses timestamps to UTC, extracts `date` and `hour` columns
- Coerces numeric types with `errors="coerce"` (bad values → NaN, not crashes)
- Computes three derived fields (see next section)
- Logs null audit without dropping rows

### Step 3: Load (`pipeline/load.py`)

- Creates the dataset if it does not exist (idempotent)
- Defines an explicit schema (19 fields) — no autodetect
- Uses `WRITE_TRUNCATE` so each run replaces the table
- Verifies row count after load

---

## Data Transformations

### Flattening

The Open-Meteo API returns hourly data as nested parallel arrays:

```json
{
  "hourly": {
    "time": ["2025-05-21T00:00", "2025-05-21T01:00", ...],
    "temperature_2m": [12.3, 11.8, ...],
    "relative_humidity_2m": [78, 82, ...]
  }
}
```

This is unpacked into tabular rows where each row is one city at one hour, with city metadata attached from the config (not the API's rounded coordinates).

### Null Handling

The API can return `null` for some hours (e.g., missing sensor data). The pipeline:
- Keeps nulls as `NaN` — never silently drops rows
- Logs which columns have nulls and how many
- Uses `errors="coerce"` when casting types so unexpected values become `NaN` instead of crashing

### Derived Fields

Three computed fields that add analytical value beyond what the raw API provides:

#### 1. Heat Index

A comfort temperature metric combining temperature and humidity using the NOAA regression formula. Only applied when temperature ≥ 27°C and humidity ≥ 40% (below that, the formula is not physically meaningful, so the heat index equals the actual temperature). This is genuinely useful for understanding how weather *feels*, not just what the thermometer says.

#### 2. Temperature Deviation from Daily Mean

For each (city, date), computes the daily mean temperature and then calculates how much each hourly reading deviates from it. Positive values flag unusually warm hours; negative values flag cool spells. Useful for spotting intra-day volatility and unusual weather patterns.

#### 3. Severe Weather Flag

Maps WMO weather interpretation codes to a boolean. Codes ≥ 65 cover heavy rain, heavy snow, freezing rain, and thunderstorms. This turns a cryptic numeric code into an immediately actionable indicator — useful for filtering, counting, and alerting.

---

## SQL Summary Query

The query file is at [`queries/summary.sql`](queries/summary.sql). The primary query produces a daily weather summary by city:

```sql
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
```

### Sample Output

> **Note:** This table will be populated with actual query results after running the pipeline. The sample below illustrates the expected format:

| city_name | date | avg_temp_c | min_temp_c | max_temp_c | temp_range_c | avg_humidity_pct | total_precipitation_mm | avg_wind_speed_kmh | max_wind_gust_kmh | severe_weather_hours | avg_heat_index |
|---|---|---|---|---|---|---|---|---|---|---|---|
| London | 2025-05-21 | 14.2 | 9.1 | 19.8 | 10.7 | 72.3 | 0.00 | 12.4 | 28.3 | 0 | 14.2 |
| Mumbai | 2025-05-21 | 31.5 | 28.2 | 34.8 | 6.6 | 68.1 | 2.40 | 15.7 | 35.2 | 3 | 38.4 |
| New York | 2025-05-21 | 22.1 | 17.3 | 27.4 | 10.1 | 55.8 | 0.10 | 18.2 | 42.1 | 0 | 22.1 |
| Sydney | 2025-05-21 | 16.8 | 13.5 | 20.1 | 6.6 | 78.4 | 1.20 | 22.3 | 48.7 | 0 | 16.8 |
| Tokyo | 2025-05-21 | 20.3 | 16.9 | 24.2 | 7.3 | 62.5 | 0.30 | 10.1 | 22.4 | 0 | 20.3 |

---

## Production Thinking

### How would you schedule this pipeline to run automatically?

**Recommended: Google Cloud Scheduler + Cloud Run Jobs**

Cloud Scheduler triggers a Cloud Run job on a cron schedule (e.g., `0 6 * * *` for daily at 06:00 UTC). The Cloud Run job executes `main.py` in a container. This is the most natural fit because:
- The pipeline already loads to BigQuery, so staying within GCP reduces authentication complexity
- Cloud Run Jobs handle container lifecycle, retries, and timeout automatically
- Cost is near-zero for a daily run that takes ~10 seconds

**Alternative options:**
- **Apache Airflow (Cloud Composer):** If the team already runs Airflow, define this as a DAG with three tasks (fetch → transform → load). Overkill for a single pipeline, but makes sense if there are many pipelines to orchestrate.
- **Simple cron job:** `crontab -e` on a Linux VM. Lowest overhead, but no built-in alerting or retry logic. Suitable for small-scale internal tools where simplicity matters more than resilience.

### How would you know if it failed?

Four layers of failure detection, from immediate to background:

1. **Exit codes:** The script exits with code 1 on any failure. Cloud Scheduler / Airflow catches non-zero exits and triggers alerts (email, Slack, PagerDuty).

2. **Structured logs:** All pipeline activity is logged at INFO/ERROR level. In production, these would be shipped to Cloud Logging with a log-based alert on any `ERROR`-level message.

3. **Data freshness monitoring:** A scheduled check (or BigQuery monitoring rule) that queries `MAX(fetched_at)` from the table. If the most recent pipeline run is older than 25 hours, alert — the pipeline likely failed silently or was never triggered.

4. **Row count validation:** After each load, the pipeline compares expected rows (cities × hours) with actual rows loaded and logs a warning on significant discrepancy. In production, this would feed into an alerting system.

### What would you add or change if this pipeline needed to scale to 10× the data volume?

| Change | Why |
|---|---|
| **Concurrent fetching** | Use `asyncio` + `aiohttp` to fetch all cities in parallel instead of sequentially. At 50 cities, sequential fetching would take ~50 seconds; concurrent fetching stays under 5. |
| **Chunked loading** | For DataFrames larger than memory, chunk the load into smaller batches (e.g., 100K rows each). This enables partial retries and prevents OOM errors. |
| **Partitioned tables** | Partition the BigQuery table by `date`. This dramatically reduces query scan costs (BigQuery charges by bytes scanned) and speeds up date-filtered queries. |
| **Incremental loading** | Switch from `WRITE_TRUNCATE` to `WRITE_APPEND` with a deduplication strategy. Each run only fetches and loads new data, not the full history. Requires a watermark (e.g., `MAX(timestamp)` from the existing table). |
| **Containerisation** | Package the pipeline as a Docker container and run it as a Cloud Run Job or Kubernetes CronJob. This provides resource isolation, reproducible builds, and horizontal scaling. |
| **Monitoring dashboard** | Add a Grafana or Looker Studio dashboard tracking pipeline run times, row counts, and failure rates over time. |

---

## Decisions and Trade-offs

### WRITE_TRUNCATE over WRITE_APPEND
Each run replaces the table entirely. This means no duplicates, no complex deduplication logic, and the table always contains exactly the latest 7 days. The trade-off is that we lose historical data beyond the 7-day window. For this assessment, that is acceptable. In production, I would switch to `WRITE_APPEND` with deduplication.

### Explicit schema over autodetect
Autodetect is convenient but fragile — a single `null` column can cause type inference to change between runs. Defining the schema explicitly in code makes the pipeline deterministic and self-documenting.

### Per-city error isolation
If the API fails for one city, the pipeline continues with the others rather than aborting entirely. This is a deliberate choice: partial data is more useful than no data. The failure is logged so someone can investigate.

### No `.env` file for API credentials
Open-Meteo requires no API key. BigQuery credentials come from `gcloud auth application-default login`. This means the repo has zero secrets and anyone can clone and run it immediately.

---

## What I Would Do Differently With More Time

- **Integration tests:** Run the full pipeline against a test BigQuery dataset and assert on row counts, schema correctness, and derived field values.
- **Data validation framework:** Use a library like Great Expectations or Pandera to define and enforce data quality rules (e.g., temperature between -60°C and 60°C, humidity between 0% and 100%).
- **Historical backfill:** Use Open-Meteo's `/v1/archive` endpoint to load months of historical data, not just the last 7 days. This would make the SQL queries more interesting and demonstrate incremental loading.
- **CI/CD pipeline:** GitHub Actions workflow that runs linting, type checking, and unit tests on every push.
- **Configuration via environment variables or YAML:** Move all config out of Python into a `.yaml` file or environment variables so the pipeline can be reconfigured without code changes.
