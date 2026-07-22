"""Web scraper for Galeri24 gold prices."""

import logging
from typing import List, Tuple, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timezone, timedelta

from src.config import ScraperConfig
from src.parser import parse_table, parse_currency_to_int

logger = logging.getLogger(__name__)


class Galeri24Scraper:
    """Scraper for Galeri24 gold prices."""

    BRAND_IDS = ["GALERI 24", "ANTAM", "Dinar G24", "ANTAM NON PEGADAIAN", "UBS"]
    COLUMNS = ["timestamp", "brand", "weight", "harga_jual", "harga_buyback"]

    def __init__(self, config: ScraperConfig):
        """Initialize scraper with configuration.

        Args:
            config: ScraperConfig instance
        """
        self.config = config
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy.

        Returns:
            Configured requests.Session instance
        """
        session = requests.Session()
        session.headers.update({"User-Agent": self.config.user_agent})

        retry_strategy = Retry(
            total=self.config.retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=self.config.status_forcelist,
            allowed_methods=frozenset(["GET", "POST"])
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def fetch_page(self) -> str:
        """Fetch the target webpage.

        Returns:
            HTML content of the page

        Raises:
            requests.RequestException: If request fails
        """
        try:
            logger.info(f"Fetching {self.config.url}...")
            response = self.session.get(self.config.url, timeout=self.config.timeout)
            response.raise_for_status()
            logger.info(f"Successfully fetched page (status: {response.status_code})")
            return response.text
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def parse_page(self, html: str) -> pd.DataFrame:
        """Parse HTML content and extract gold price data.

        Args:
            html: HTML content as string

        Returns:
            DataFrame with parsed data
        """
        soup = BeautifulSoup(html, "html.parser")
        timestamp_iso = datetime.now(timezone.utc).isoformat()

        # Find all brand sections
        sections = soup.find_all(
            "div",
            id=lambda x: x and x.strip() in self.BRAND_IDS
        )

        if not sections:
            logger.warning("No sections found. Check the page structure.")
            return pd.DataFrame(columns=self.COLUMNS)

        logger.info(f"Found {len(sections)} brand sections")

        all_data = []
        for section in sections:
            brand = section.get("id", "").strip()
            try:
                section_data = parse_table(section, brand, timestamp_iso)
                all_data.extend(section_data)
                logger.debug(f"Parsed {len(section_data)} rows from {brand}")
            except Exception as e:
                logger.warning(f"Failed to parse section {brand}: {e}")

        if not all_data:
            logger.warning("No rows parsed. Check selectors/HTML structure.")
            return pd.DataFrame(columns=self.COLUMNS)

        df = pd.DataFrame(all_data, columns=self.COLUMNS)
        return df

    def scrape(self) -> pd.DataFrame:
        """Execute full scraping workflow.

        Returns:
            Cleaned DataFrame with gold price data

        Raises:
            RuntimeError: If scraped data is below minimum threshold
        """
        html = self.fetch_page()
        df = self.parse_page(html)

        if df.empty:
            return df

        # Clean and convert price columns
        df["harga_jual"] = df["harga_jual"].apply(parse_currency_to_int)
        df["harga_buyback"] = df["harga_buyback"].apply(parse_currency_to_int)

        before_cleanup = len(df)
        df = df.dropna(subset=["harga_jual", "harga_buyback"]).reset_index(drop=True)
        logger.info(
            f"Parsed {before_cleanup} rows, {before_cleanup - len(df)} "
            "dropped due to missing prices"
        )

        df["harga_jual"] = df["harga_jual"].astype(int)
        df["harga_buyback"] = df["harga_buyback"].astype(int)

        return df
