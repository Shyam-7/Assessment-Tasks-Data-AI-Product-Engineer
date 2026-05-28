"""
Pipeline configuration.

All parameterised values live here — nothing is hardcoded in the pipeline modules.
To override the BigQuery project ID, set the GOOGLE_CLOUD_PROJECT environment variable.
"""

import os

# ---------------------------------------------------------------------------
# API Configuration
# ---------------------------------------------------------------------------
API_BASE_URL = "https://api.open-meteo.com/v1/forecast"
PAST_DAYS = 7
FORECAST_DAYS = 0
TIMEZONE = "auto"

HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "wind_speed_10m",
    "wind_gusts_10m",
    "pressure_msl",
    "cloud_cover",
    "weather_code",
]

CITIES = [
    {"name": "London", "latitude": 51.51, "longitude": -0.13},
    {"name": "New York", "latitude": 40.71, "longitude": -74.01},
    {"name": "Tokyo", "latitude": 35.68, "longitude": 139.69},
    {"name": "Sydney", "latitude": -33.87, "longitude": 151.21},
    {"name": "Mumbai", "latitude": 19.08, "longitude": 72.88},
]

# ---------------------------------------------------------------------------
# BigQuery Configuration
# ---------------------------------------------------------------------------
BQ_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "cosmic-kite-427209-j4")
BQ_DATASET_ID = "weather_pipeline"
BQ_TABLE_ID = "hourly_weather"

# ---------------------------------------------------------------------------
# Retry / Resilience
# ---------------------------------------------------------------------------
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 0.5
REQUEST_TIMEOUT = 30  # seconds
