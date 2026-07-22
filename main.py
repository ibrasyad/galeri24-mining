#!/usr/bin/env python3
"""Main entry point for the Galeri24 Mining Tool."""

import sys
import logging

from src.logger import setup_logging
from src.config import AppConfig
from src.pipeline import GoldPricePipeline

logger = logging.getLogger(__name__)


def main() -> int:
    """Execute the main pipeline.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    setup_logging(logging.INFO)

    try:
        logger.info("="*60)
        logger.info("Galeri24 Gold Price Scraper and Storage Pipeline")
        logger.info("="*60)

        # Load configuration
        config = AppConfig.from_env()
        logger.debug(f"Configuration loaded: {config}")

        # Execute pipeline
        pipeline = GoldPricePipeline(config)
        result = pipeline.run()

        logger.info("="*60)
        logger.info(f"Pipeline Result: {result}")
        logger.info("="*60)

        return 0

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        logger.info("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
