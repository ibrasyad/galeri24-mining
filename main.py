import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import os
import tempfile
from datetime import datetime

# --- 1. Scrape Galeri24 ---
URL = " "
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}
resp = requests.get(URL, headers=headers)
print(resp.status_code)
soup = BeautifulSoup(resp.text, "html.parser")

def parse_table(container_div, brand):
    """Extract rows of weight, jual, buyback for a given brand"""
    rows = container_div.select("div.grid.grid-cols-5.divide-x.lg\\:hover\\:bg-neutral-50.transition-all")
    parsed = []
    for row in rows:
        cols = [col.get_text(strip=True) for col in row.select("div")]
        if len(cols) == 3:  # [weight, jual, buyback]
            weight, jual, buyback = cols
            parsed.append([datetime.now().isoformat(), brand, weight, jual, buyback])
    return parsed

# --- 2. Locate both GALERI 24 and ANTAM sections ---
sections = soup.find_all("div", id=lambda x: x and x.strip() in ["GALERI 24", "ANTAM"])
all_data = []
for sec in sections:
    brand = sec.get("id").strip()
    all_data.extend(parse_table(sec, brand))

# --- 3. Convert to DataFrame ---
df = pd.DataFrame(all_data, columns=["timestamp", "brand", "weight", "harga_jual", "harga_buyback"])
df["harga_jual"] = df["harga_jual"].str.replace("Rp", "").str.replace(".", "").astype(int)
df["harga_buyback"] = df["harga_buyback"].str.replace("Rp", "").str.replace(".", "").astype(int)

# --- 4. Auth with Google Sheets using temp JSON ---
json_str = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
if not json_str:
    raise Exception("GCP_SERVICE_ACCOUNT_JSON is not set")

with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
    f.write(json_str)
    SERVICE_ACCOUNT_PATH = f.name

gc = gspread.service_account(filename=SERVICE_ACCOUNT_PATH)

# --- 5. Open Google Sheet ---
SHEET_ID = "1wBU6Tqyv-FI2Vp3unGo_jObz9RMabgSJu1X7ztzauO4"
sheet = gc.open_by_key(SHEET_ID).worksheet("Galeri24")

# --- 6. Append new rows only ---
# Get current row count to know where to start
row_count = len(sheet.get_all_values())
start_row = row_count + 1  # next empty row

# Write DataFrame starting at the next empty row
set_with_dataframe(sheet, df, row=start_row, include_column_header=False)

print(f"✅ Appended {len(df)} rows. Total rows now: {row_count + len(df)}")
