# Galeri24 Mining Tool

A professional-grade web scraper and data pipeline for collecting gold prices from Galeri24 and storing them in Google Sheets.

## Features

- ✨ **Modular Architecture**: Clean separation of concerns with dedicated modules for scraping, parsing, and storage
- 🔄 **Automatic Retries**: Built-in retry logic with exponential backoff for network resilience
- 📊 **Google Sheets Integration**: Automatic data storage with deduplication
- 📅 **Scheduled Execution**: GitHub Actions workflow for daily automated runs
- 🛡️ **Error Handling**: Comprehensive logging and error handling
- 🧪 **Production-Ready**: Type hints, logging, and configuration management

## Project Structure

```
.
├── src/
│   ├── __init__.py          # Package initialization
│   ├── config.py            # Configuration management
│   ├── scraper.py           # Web scraper implementation
│   ├── parser.py            # HTML parsing utilities
│   ├── sheets.py            # Google Sheets client
│   ├── logger.py            # Logging configuration
│   └── pipeline.py          # Main orchestration
├── main.py                  # Entry point
├── requirements.txt         # Python dependencies
├── .github/workflows/       # GitHub Actions workflows
└── README.md               # This file
```

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ibrasyad/galeri24-mining.git
   cd galeri24-mining
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   export GCP_SERVICE_ACCOUNT_JSON='your-service-account-json'
   ```

## Usage

### Local Execution

```bash
python main.py
```

### With Custom Configuration

Modify `src/config.py` or set environment variables to customize:
- Scraper URL and timeouts
- Google Sheets ID and worksheet name
- Data validation thresholds

## Configuration

The application uses a hierarchical configuration system:

1. **Environment Variables** (highest priority)
   - `GCP_SERVICE_ACCOUNT_JSON`: Service account credentials

2. **Config Dataclasses** (default values)
   - `ScraperConfig`: Web scraping settings
   - `GoogleSheetsConfig`: Sheets integration settings
   - `AppConfig`: Application-level settings

## Data Collection

The scraper collects the following data from each gold product:

- **Timestamp (UTC)**: When the data was collected
- **Timestamp (Local)**: Local timezone adjusted timestamp (UTC+7)
- **Brand**: Gold product brand (e.g., "GALERI 24", "ANTAM")
- **Weight**: Product weight
- **Harga Jual**: Selling price (Rp)
- **Harga Buyback**: Buyback price (Rp)

## GitHub Actions Workflow

The project includes an automated workflow that:
- Runs daily at 12:00 PM UTC+7 (05:00 UTC)
- Can be manually triggered via `workflow_dispatch`
- Automatically stores results in Google Sheets

**Workflow file**: `.github/workflows/scrape_galeri24.yml`

## Error Handling

The pipeline includes multiple error handling mechanisms:

1. **Network Errors**: Automatic retries with exponential backoff
2. **API Rate Limiting**: Graceful handling with smart retry strategy
3. **Data Validation**: Minimum row threshold checks
4. **Duplicate Detection**: Automatic deduplication in Google Sheets

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black src/ main.py

# Lint code
flake8 src/ main.py

# Type checking
mypy src/ main.py
```

## Troubleshooting

### "GCP_SERVICE_ACCOUNT_JSON is not set"

Ensure the environment variable is properly set with your Google Service Account JSON credentials.

### "No sections found"

The website structure may have changed. Check the page and update the `BRAND_IDS` in `src/scraper.py`.

### "Request failed: Connection Error"

Check network connectivity. The scraper includes automatic retries, but verify the target URL is accessible.

## Contributing

Contributions are welcome! Please follow the project's code style and include tests for new features.

## License

MIT License - see LICENSE file for details

## Author

[@ibrasyad](https://github.com/ibrasyad)
