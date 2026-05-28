"""
Weather Data Pipeline — main orchestrator.

Runs the full pipeline: fetch → transform → load.

Usage:
    python main.py
"""

import logging
import sys
import time

from pipeline.fetch import fetch_all_cities
from pipeline.transform import transform
from pipeline.load import load_to_bigquery


def _configure_logging() -> None:
    """Set up structured logging to stdout."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)-25s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main() -> None:
    _configure_logging()
    logger = logging.getLogger("pipeline")
    logger.info("=" * 60)
    logger.info("Weather Data Pipeline — starting")
    logger.info("=" * 60)

    start = time.time()

    # ------------------------------------------------------------------
    # Step 1: Fetch
    # ------------------------------------------------------------------
    logger.info("STEP 1/3 — Fetching data from Open-Meteo API …")
    raw_data = fetch_all_cities()

    if not raw_data:
        logger.error("No data fetched. Aborting pipeline.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 2: Transform
    # ------------------------------------------------------------------
    logger.info("STEP 2/3 — Transforming raw data …")
    df = transform(raw_data)

    if df.empty:
        logger.error("Transform produced an empty DataFrame. Aborting pipeline.")
        sys.exit(1)

    logger.info("Preview of transformed data (first 5 rows):")
    logger.info("\n%s", df.head().to_string())

    # ------------------------------------------------------------------
    # Step 3: Load to BigQuery
    # ------------------------------------------------------------------
    logger.info("STEP 3/3 — Loading data to BigQuery …")
    success = load_to_bigquery(df)

    if not success:
        logger.error("BigQuery load failed. Pipeline finished with errors.")
        sys.exit(1)

    elapsed = time.time() - start
    logger.info("=" * 60)
    logger.info("Pipeline completed successfully in %.1f seconds", elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
