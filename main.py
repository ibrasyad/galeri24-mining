import os
import json
import re
import logging
from datetime import datetime, timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import pandas as pd
import gspread

# ---------- Configuration ----------
URL = "https://www.ecorp.galeri24.co.id/harga-emas"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
SHEET_ID = "1wBU6Tqyv-FI2Vp3unGo_jObz9RMabgSJu1X7ztzauO4"
WORKSHEET_NAME = "Galeri24"
# ENV: GCP_SERVICE_ACCOUNT_JSON contains the raw JSON string (not a path)
# ---------- End config ----------

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def create_session(retries=3, backoff=0.3, status_forcelist=(500,502,503,504)):
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
    """Extract digits like 'Rp 1.234.567' -> 1234567, else return None"""
    if not text or not isinstance(text, str):
        return None
    m = re.search(r"([\d\.\,]+)", text)
    if not m:
        return None
    num = m.group(1)
    # normalize: remove thousands separators, replace comma decimal with dot (if any)
    num = num.replace(".", "").replace(",", "")
    try:
        return int(num)
    except ValueError:
        return None

def parse_table(container_div, brand, timestamp_iso):
    """Extract rows for a brand. This one tries to be more defensive."""
    parsed = []
    # Try to locate rows by a reliable child structure; adjust selectors if site differs.
    # Using immediate children helps avoid picking nested UI containers.
    for row in container_div.find_all("div", recursive=False):
        cols = [c.get_text(strip=True) for c in row.find_all("div", recursive=False)]
        # if the page uses inner wrapper divs this may not match; adapt based on actual HTML.
        if len(cols) >= 3:
            weight = cols[0]
            jual = cols[1]
            buyback = cols[2]
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

    # Use a single timestamp for the whole run (UTC)
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    # Find the relevant sections: this depends on the site's HTML structure.
    # Original script used id in ["GALERI 24", "ANTAM"]; real site might use headings or specific classes.
    # Try a few strategies defensively:
    target_ids = {"GALERI 24", "ANTAM"}
    sections = []

    # 1) find by id if available
    for tid in target_ids:
        el = soup.find(id=tid)
        if el:
            sections.append((tid, el))

    # 2) fallback: find by visible headings/text
    if not sections:
        for heading in soup.find_all(["h2", "h3", "h4"]):
            txt = heading.get_text(strip=True).upper()
            if txt in target_ids:
                # assume the sibling or parent container holds the table
                container = heading.find_next_sibling("div") or heading.parent
                sections.append((txt, container))

    all_data = []
    for brand, sec in sections:
        try:
            all_data.extend(parse_table(sec, brand, timestamp_iso))
        except Exception as e:
            logging.warning("Failed to parse section %s: %s", brand, e)

    if not all_data:
        logging.warning("No rows parsed. Check selectors/HTML structure.")
        return pd.DataFrame(columns=["timestamp", "brand", "weight", "harga_jual", "harga_buyback"])

    df = pd.DataFrame(all_data, columns=["timestamp", "brand", "weight", "harga_jual", "harga_buyback"])

    # convert currency columns robustly
    df["harga_jual"] = df["harga_jual"].apply(parse_currency_to_int)
    df["harga_buyback"] = df["harga_buyback"].apply(parse_currency_to_int)

    # drop rows with missing numeric prices (or decide how to handle them)
    before = len(df)
    df = df.dropna(subset=["harga_jual", "harga_buyback"]).reset_index(drop=True)
    logging.info("Parsed %d rows, %d dropped due to missing price", before, before - len(df))

    # convert to int dtype
    df["harga_jual"] = df["harga_jual"].astype(int)
    df["harga_buyback"] = df["harga_buyback"].astype(int)

    return df

def auth_gspread_from_env():
    json_str = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    if not json_str:
        raise RuntimeError("GCP_SERVICE_ACCOUNT_JSON is not set in environment")
    creds = json.loads(json_str)
    # Use in-memory credentials (no disk writes)
    return gspread.service_account_from_dict(creds)

def append_to_sheet(df):
    gc = auth_gspread_from_env()
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.worksheet(WORKSHEET_NAME)

    if df.empty:
        logging.info("No data to append.")
        return 0

    # prepare values (list of lists)
    values = df.values.tolist()
    # Append rows atomically via Sheets API (value_input_option can be RAW or USER_ENTERED)
    try:
        ws.append_rows(values, value_input_option="USER_ENTERED")
        logging.info("Appended %d rows", len(values))
    except Exception as e:
        logging.error("Failed to append rows: %s", e)
        raise
    return len(values)

if __name__ == "__main__":
    df = scrape()
    appended = append_to_sheet(df)
    logging.info("Done. Appended %d rows.", appended)
