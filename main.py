import os
import json
import re
import logging
import tempfile
from datetime import datetime, timezone, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import time
import random
from gspread.exceptions import APIError

URL = "https://www.ecorp.galeri24.co.id/harga-emas"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
SHEET_ID = "1BCR_IbhFWSIR1faz9UJXItLHSOicaSWofymvDCSuq_E"
WORKSHEET_NAME = "Galeri24"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def retry_gspread(func, max_attempts=5, base_sleep=5):
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except APIError as e:
            status = getattr(e.response, "status_code", None)

            if status not in (429, 500, 503):
                raise  # real error → fail fast

            if attempt == max_attempts:
                raise

            sleep = base_sleep * attempt + random.uniform(0, 2)
            logging.warning(
                "Google Sheets API error %s. Retrying in %.1fs (attempt %d/%d)",
                status, sleep, attempt, max_attempts
            )
            time.sleep(sleep)

def create_session(retries=3, backoff=0.3, status_forcelist=(500, 502, 503, 504)):
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset(["GET", "POST"])
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s

def parse_currency_to_int(text):
    if not text or not isinstance(text, str):
        return None
    m = re.search(r"([\d\.\,]+)", text)
    if not m:
        return None
    num = m.group(1).replace(".", "").replace(",", "")
    try:
        return int(num)
    except ValueError:
        return None

def parse_table(container_div, brand, timestamp_iso):
    parsed = []
    rows = container_div.select("div.grid.grid-cols-5.divide-x.lg\\:hover\\:bg-neutral-50.transition-all")
    for row in rows:
        cols = [col.get_text(strip=True) for col in row.select("div")]
        if len(cols) == 3:
            weight, jual, buyback = cols
            parsed.append([timestamp_iso, brand, weight, jual, buyback])
    return parsed

def scrape():
    s = create_session()
    try:
        resp = s.get(URL, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error("Request failed: %s", e)
        raise

    soup = BeautifulSoup(resp.text, "html.parser")
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    sections = soup.find_all("div", id=lambda x: x and x.strip() in ["GALERI 24", "ANTAM", "Dinar G24", "ANTAM NON PEGADAIAN", "UBS"]) # Insert more gold brand here, check DIV id on the website
    if not sections:
        logging.warning("No sections found. Check the page structure.")
        return pd.DataFrame(columns=["timestamp", "brand", "weight", "harga_jual", "harga_buyback"])

    all_data = []
    for sec in sections:
        brand = sec.get("id").strip()
        try:
            all_data.extend(parse_table(sec, brand, timestamp_iso))
        except Exception as e:
            logging.warning("Failed to parse section %s: %s", brand, e)

    if not all_data:
        logging.warning("No rows parsed. Check selectors/HTML structure.")
        return pd.DataFrame(columns=["timestamp", "brand", "weight", "harga_jual", "harga_buyback"])

    df = pd.DataFrame(all_data, columns=["timestamp", "brand", "weight", "harga_jual", "harga_buyback"])

    df["harga_jual"] = df["harga_jual"].apply(parse_currency_to_int)
    df["harga_buyback"] = df["harga_buyback"].apply(parse_currency_to_int)
    before = len(df)
    df = df.dropna(subset=["harga_jual", "harga_buyback"]).reset_index(drop=True)
    logging.info("Parsed %d rows, %d dropped due to missing price", before, before - len(df))
    df["harga_jual"] = df["harga_jual"].astype(int)
    df["harga_buyback"] = df["harga_buyback"].astype(int)

    df["timestamp_local"] = (pd.to_datetime(df["timestamp"], utc=True) + timedelta(hours=7)).dt.strftime("%Y-%m-%d %H:%M:%S")

    df = df[["timestamp", "timestamp_local", "brand", "weight", "harga_jual", "harga_buyback"]]
    
    if len(df) < 3:
        raise RuntimeError(
            f"Scraped too few rows ({len(df)}). Possible site change or partial load."
        )
    
    return df

def auth_gspread_from_env():
    json_str = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    if not json_str:
        raise RuntimeError("GCP_SERVICE_ACCOUNT_JSON is not set in environment")

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
        f.write(json_str)
        SERVICE_ACCOUNT_PATH = f.name

    gc = gspread.service_account(filename=SERVICE_ACCOUNT_PATH)
    return gc


def append_to_sheet(df):
    if df.empty:
        logging.info("No data to append.")
        return 0
    
    gc = auth_gspread_from_env()
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.worksheet(WORKSHEET_NAME)

    existing = ws.get_all_values()
    row_count = len(existing)
    start_row = row_count + 1
    if existing:
        header = existing[0]
        if "timestamp" in header:
            ts_idx = header.index("timestamp")
            existing_ts = {
                row[ts_idx]
                for row in existing[1:]
                if len(row) > ts_idx
            }
            before = len(df)
            df = df[~df["timestamp"].isin(existing_ts)]
            if before != len(df):
                logging.info("Dropped %d duplicate rows", before - len(df))
    
    if df.empty:
        logging.info("All rows already exist, skipping append.")
        return 0
    
    set_with_dataframe(ws, df, row=start_row, include_column_header=False)
    logging.info("Appended %d rows. Total rows now: %d", len(df), row_count + len(df))
    return len(df)

if __name__ == "__main__":
    df = scrape()
    appended = retry_gspread(lambda: append_to_sheet(df))
    logging.info("Done. Appended %d rows.", appended)
