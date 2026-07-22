"""Tests for parsing utilities."""

import pytest
from src.parser import parse_currency_to_int


class TestParseCurrency:
    """Test currency parsing function."""

    def test_parse_valid_currency(self):
        """Test parsing valid currency strings."""
        assert parse_currency_to_int("Rp1.234,50") == 1234
        assert parse_currency_to_int("1000") == 1000
        assert parse_currency_to_int("1.000.000") == 1000000

    def test_parse_invalid_currency(self):
        """Test parsing invalid currency strings."""
        assert parse_currency_to_int("") is None
        assert parse_currency_to_int(None) is None
        assert parse_currency_to_int("abc") is None
        assert parse_currency_to_int(123) is None  # Not a string
