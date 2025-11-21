# Daily Gold Price Scraper (Python + Google Sheets)

A simple automated scraper that collects **daily gold prices** from [Galeri24](https://www.ecorp.galeri24.co.id/harga-emas) and stores them in **Google Sheets**.  
Each record includes both UTC and local (UTC+7) timestamps, brand, weight, and buy/sell prices. It's perfect for tracking gold price trends over time.

---

## Features

- Automatically logs gold prices daily  
- Dual timestamps UTC and UTC+7 (Jakarta time)  
- Saves data directly to Google Sheets (BigQuery support may come later)  
- Clean, ready-to-analyze data format  

---

## Background

This project was built to help my family track gold price movements for investment purposes.  
As a Data Analyst, I wanted to provide reliable, structured data so they can make informed decisions. On a side note, it's also to demonstrate automation, API usage, and data handling in Python.

---

## Special Thanks

Thanks to **Galeri24** for making their pricing data publicly available.  
Based on their `robots.txt`, this scraping activity is permitted.  
However, if this project causes any issues or violates any policy, please contact me and I’ll take it down immediately.

---

## License

MIT License — feel free to use, modify, or learn from this project.
