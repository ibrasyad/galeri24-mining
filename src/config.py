"""Configuration management for the Galeri24 scraper."""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class ScraperConfig:
    """Configuration for web scraping."""
    url: str = "https://galeri24.co.id/harga-emas"
    timeout: int = 10
    retries: int = 3
    backoff_factor: float = 0.3
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
    status_forcelist: tuple = (500, 502, 503, 504)


@dataclass
class GoogleSheetsConfig:
    """Configuration for Google Sheets integration."""
    sheet_id: str = "1BCR_IbhFWSIR1faz9UJXItLHSOicaSWofymvDCSuq_E"
    worksheet_name: str = "Galeri24"
    service_account_json: Optional[str] = None

    def __post_init__(self):
        if self.service_account_json is None:
            self.service_account_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON")


@dataclass
class AppConfig:
    """Main application configuration."""
    scraper: ScraperConfig
    sheets: GoogleSheetsConfig
    min_rows_threshold: int = 3
    timezone_offset_hours: int = 7

    @staticmethod
    def from_env() -> "AppConfig":
        """Create configuration from environment variables."""
        return AppConfig(
            scraper=ScraperConfig(),
            sheets=GoogleSheetsConfig(),
            min_rows_threshold=3,
            timezone_offset_hours=7
        )
