"""Main data pipeline orchestration."""

import logging
from datetime import datetime, timezone, timedelta

import pandas as pd

from src.config import AppConfig
from src.scraper import Galeri24Scraper
from src.sheets import GoogleSheetsClient

logger = logging.getLogger(__name__)


class GoldPricePipeline:
    """Orchestrate gold price scraping and storage pipeline."""

    def __init__(self, config: AppConfig):
        """Initialize pipeline with configuration.

        Args:
            config: AppConfig instance
        """
        self.config = config
        self.scraper = Galeri24Scraper(config.scraper)
        self.sheets_client = GoogleSheetsClient(config.sheets)

    def run(self) -> dict:
        """Execute the complete pipeline.

        Returns:
            Dictionary with execution results

        Raises:
            RuntimeError: If scraped data is below minimum threshold
        """
        logger.info("Starting gold price pipeline...")

        # Scrape data
        df = self.scraper.scrape()

        if df.empty:
            logger.warning("No data scraped")
            return {"status": "warning", "rows_scraped": 0, "rows_appended": 0}

        logger.info(f"Successfully scraped {len(df)} rows")

        # Validate data volume
        if len(df) < self.config.min_rows_threshold:
            raise RuntimeError(
                f"Scraped too few rows ({len(df)}). "
                f"Expected at least {self.config.min_rows_threshold}. "
                "Possible site change or partial load."
            )

        # Enrich data
        df = self._enrich_data(df)

        # Store to Google Sheets
        rows_appended = self.sheets_client.append_data(df)

        logger.info("Pipeline completed successfully")
        return {
            "status": "success",
            "rows_scraped": len(df),
            "rows_appended": rows_appended
        }

    def _enrich_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add computed columns to the DataFrame.

        Args:
            df: Raw scraped data

        Returns:
            Enriched DataFrame with additional columns
        """
        # Convert UTC timestamp to local timezone
        df["timestamp_local"] = (
            pd.to_datetime(df["timestamp"], utc=True)
            + timedelta(hours=self.config.timezone_offset_hours)
        ).dt.strftime("%Y-%m-%d %H:%M:%S")

        # Reorder columns
        return df[[
            "timestamp",
            "timestamp_local",
            "brand",
            "weight",
            "harga_jual",
            "harga_buyback"
        ]]
