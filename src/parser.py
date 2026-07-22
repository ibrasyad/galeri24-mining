"""HTML parsing utilities for Galeri24 scraper."""

import re
import logging
from typing import List, Optional
from bs4 import BeautifulSoup, Tag
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


def parse_currency_to_int(text: Optional[str]) -> Optional[int]:
    """Parse currency string to integer.

    Handles formats like "Rp1.234,50" -> 1234

    Args:
        text: Currency string (e.g., "Rp1.234,50")

    Returns:
        Integer value or None if parsing fails
    """
    if not text or not isinstance(text, str):
        return None

    # Extract numeric part
    match = re.search(r"([\d\.\,]+)", text)
    if not match:
        return None

    # Remove separators and convert
    num_str = match.group(1).replace(".", "").replace(",", "")
    try:
        return int(num_str)
    except ValueError:
        return None


def parse_table(container_div: Tag, brand: str, timestamp_iso: str) -> List[List]:
    """Parse price table from a brand container.

    Args:
        container_div: BeautifulSoup Tag containing the brand section
        brand: Brand name
        timestamp_iso: ISO format timestamp

    Returns:
        List of parsed rows [timestamp, brand, weight, jual, buyback]
    """
    parsed = []
    rows = container_div.select("div.grid.grid-cols-5.divide-x.lg\\:hover\\:bg-neutral-50.transition-all")

    for row in rows:
        cols = [col.get_text(strip=True) for col in row.select("div")]
        if len(cols) == 3:
            weight, jual, buyback = cols
            parsed.append([timestamp_iso, brand, weight, jual, buyback])

    return parsed
