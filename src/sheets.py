"""Google Sheets integration for data storage."""

import logging
import tempfile
import time
import random
from typing import Optional

import gspread
from gspread.exceptions import APIError
from gspread_dataframe import set_with_dataframe
import pandas as pd

from src.config import GoogleSheetsConfig

logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    """Client for Google Sheets operations."""

    def __init__(self, config: GoogleSheetsConfig):
        """Initialize Google Sheets client.

        Args:
            config: GoogleSheetsConfig instance

        Raises:
            RuntimeError: If service account JSON is not configured
        """
        if not config.service_account_json:
            raise RuntimeError("GCP_SERVICE_ACCOUNT_JSON is not set in environment")

        self.config = config
        self.gc = self._authenticate(config.service_account_json)

    @staticmethod
    def _authenticate(service_account_json: str) -> gspread.Client:
        """Authenticate with Google Sheets API.

        Args:
            service_account_json: Service account JSON content as string

        Returns:
            Authenticated gspread client
        """
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            f.write(service_account_json)
            temp_path = f.name

        return gspread.service_account(filename=temp_path)

    def append_data(self, df: pd.DataFrame) -> int:
        """Append data to worksheet, avoiding duplicates.

        Args:
            df: DataFrame with columns [timestamp, timestamp_local, brand, weight, harga_jual, harga_buyback]

        Returns:
            Number of rows appended
        """
        if df.empty:
            logger.info("No data to append.")
            return 0

        try:
            spreadsheet = self.gc.open_by_key(self.config.sheet_id)
            worksheet = spreadsheet.worksheet(self.config.worksheet_name)
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error(f"Spreadsheet {self.config.sheet_id} not found")
            raise

        # Get existing data
        existing_values = self._get_with_retry(worksheet.get_all_values)
        row_count = len(existing_values)
        start_row = row_count + 1

        # Deduplicate based on timestamp
        df_to_append = self._deduplicate(df, existing_values)

        if df_to_append.empty:
            logger.info("All rows already exist, skipping append.")
            return 0

        # Append new data
        self._set_with_retry(
            lambda: set_with_dataframe(
                worksheet,
                df_to_append,
                row=start_row,
                include_column_header=False
            )
        )

        logger.info(
            f"Appended {len(df_to_append)} rows. Total rows now: {row_count + len(df_to_append)}"
        )
        return len(df_to_append)

    @staticmethod
    def _deduplicate(df: pd.DataFrame, existing_values: list) -> pd.DataFrame:
        """Remove rows that already exist in the worksheet.

        Args:
            df: New data to append
            existing_values: Existing worksheet data

        Returns:
            Deduplicated DataFrame
        """
        if not existing_values or len(existing_values) < 2:
            return df

        header = existing_values[0]
        if "timestamp" not in header:
            return df

        ts_idx = header.index("timestamp")
        existing_timestamps = {
            row[ts_idx]
            for row in existing_values[1:]
            if len(row) > ts_idx
        }

        before = len(df)
        df_filtered = df[~df["timestamp"].isin(existing_timestamps)]
        dropped = before - len(df_filtered)

        if dropped > 0:
            logger.info(f"Dropped {dropped} duplicate rows")

        return df_filtered.reset_index(drop=True)

    @staticmethod
    def _get_with_retry(func, max_attempts: int = 5, base_sleep: int = 5):
        """Retry wrapper for Google Sheets API calls.

        Args:
            func: Callable to execute
            max_attempts: Maximum number of retry attempts
            base_sleep: Base sleep duration between retries

        Returns:
            Result of func() call

        Raises:
            APIError: If all retries are exhausted
        """
        for attempt in range(1, max_attempts + 1):
            try:
                return func()
            except APIError as e:
                status = getattr(e.response, "status_code", None)

                # Don't retry non-rate-limit errors
                if status not in (429, 500, 503):
                    raise

                if attempt == max_attempts:
                    raise

                sleep_duration = base_sleep * attempt + random.uniform(0, 2)
                logger.warning(
                    f"Google Sheets API error {status}. "
                    f"Retrying in {sleep_duration:.1f}s (attempt {attempt}/{max_attempts})"
                )
                time.sleep(sleep_duration)

    def _set_with_retry(self, func, max_attempts: int = 5, base_sleep: int = 5):
        """Retry wrapper for set operations.

        Args:
            func: Callable to execute
            max_attempts: Maximum number of retry attempts
            base_sleep: Base sleep duration between retries
        """
        self._get_with_retry(func, max_attempts, base_sleep)
