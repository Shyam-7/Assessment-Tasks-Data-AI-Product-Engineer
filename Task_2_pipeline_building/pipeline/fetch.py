"""
Step 1 — Fetch data from the Open-Meteo Forecast API.

Calls the API once per configured city and returns the raw JSON responses.
Handles errors gracefully: if one city fails, the rest still run.
Uses automatic retries with exponential backoff for transient failures.
"""

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config

logger = logging.getLogger(__name__)


def _build_session() -> requests.Session:
    """Create an HTTP session with automatic retry on transient errors."""
    session = requests.Session()
    retry_strategy = Retry(
        total=config.MAX_RETRIES,
        backoff_factor=config.RETRY_BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _build_params(city: dict[str, Any]) -> dict[str, Any]:
    """Construct API query parameters for a single city."""
    return {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": ",".join(config.HOURLY_VARIABLES),
        "past_days": config.PAST_DAYS,
        "forecast_days": config.FORECAST_DAYS,
        "timezone": config.TIMEZONE,
    }


def fetch_city(
    session: requests.Session, city: dict[str, Any]
) -> dict[str, Any] | None:
    """
    Fetch weather data for a single city.

    Returns the parsed JSON response on success, or None on failure.
    Failures are logged but do not raise — the pipeline continues with
    the remaining cities.
    """
    city_name = city["name"]
    params = _build_params(city)

    try:
        logger.info("Fetching data for %s (%.2f, %.2f) …", city_name, city["latitude"], city["longitude"])
        response = session.get(
            config.API_BASE_URL, params=params, timeout=config.REQUEST_TIMEOUT
        )
        response.raise_for_status()

    except requests.exceptions.Timeout:
        logger.error("Timeout fetching data for %s after %ds", city_name, config.REQUEST_TIMEOUT)
        return None
    except requests.exceptions.ConnectionError:
        logger.error("Connection error fetching data for %s — is the network available?", city_name)
        return None
    except requests.exceptions.HTTPError as exc:
        logger.error("HTTP %s for %s: %s", response.status_code, city_name, exc)
        return None
    except requests.exceptions.RequestException as exc:
        logger.error("Unexpected request error for %s: %s", city_name, exc)
        return None

    # --- Parse the JSON body ------------------------------------------------
    try:
        data = response.json()
    except ValueError:
        logger.error("Invalid JSON in response for %s", city_name)
        return None

    # --- Validate the response shape ----------------------------------------
    if "hourly" not in data:
        logger.error("Response for %s is missing the 'hourly' key — unexpected API format", city_name)
        return None

    record_count = len(data["hourly"].get("time", []))
    logger.info("Received %d hourly records for %s", record_count, city_name)
    return data


def fetch_all_cities() -> list[dict[str, Any]]:
    """
    Fetch weather data for every city in the config.

    Returns a list of (city_meta, raw_json) tuples for cities that
    succeeded. Cities that failed are logged and skipped.
    """
    session = _build_session()
    results: list[dict[str, Any]] = []

    logger.info("Starting data fetch for %d cities …", len(config.CITIES))

    for city in config.CITIES:
        data = fetch_city(session, city)
        if data is not None:
            # Attach the city metadata so the transform step knows
            # which city this response belongs to.
            results.append({"city": city, "response": data})

    succeeded = len(results)
    failed = len(config.CITIES) - succeeded
    logger.info(
        "Fetch complete — %d/%d cities succeeded, %d failed",
        succeeded, len(config.CITIES), failed,
    )

    if succeeded == 0:
        logger.error("All city fetches failed. Pipeline cannot continue.")

    return results
