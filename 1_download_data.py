import os
import io
import time
import zipfile
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_fno_symbols():
    """fno_symbols.txt से सिंबल्स लोड करता है"""
    fno_file = "data/fno_symbols.txt"
    if os.path.exists(fno_file):
        with open(fno_file, 'r', encoding='utf-8') as f:
            symbols = {line.strip().upper() for line in f if line.strip()}
            print(f"🎯 F&O फ़िल्टर लोड हुआ: {len(symbols)} सिंबल्स", flush=True)
            return symbols
    else:
        print("⚠️ Warning: `data/fno_symbols.txt` नहीं मिली! बिना फ़िल्टर सारा डेटा सेव होगा।", flush=True)
        return set()

def get_nse_session():
    """NSE कुकीज़ और हेडर्स जनरेट करता है"""
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nseindia.com/'
    }
    session.headers.update(headers)
    
    try:
        session.get("https://www.nseindia.com", timeout=15)
        time.sleep(1)
    except Exception as e:
        print(f"⚠️ NSE Homepage Connect Warning: {e}", flush=True)
        
    return session

def extract_df_from_response(response):
    """ZIP या CSV फ़ाइल को Read करके DataFrame में बदलता है"""
    content = response.content
    if content.startswith(b'PK\x03\x04'):
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            csv_filenames = [f for f in z.namelist() if f.lower().endswith('.csv')]
            if csv_filenames:
                with z.open(csv_filenames[0]) as csv_file:
                    return pd.read_csv(csv_file)
    return pd.read_csv(io.BytesIO(content))

def download_last_2_years_fno_data():
    os.makedirs("data/raw", exist_ok=True)
    fno_symbols = get_fno_symbols()
    session = get_nse_session()

    today = datetime.now()
    start_date = today - timedelta(days=50)
    current_date = start_date

    downloaded_count = 0
    skipped_count = 0

    print(f"🚀 NSE F&O डिलीवरी डेटा डाउनलोड शुरू ({start_date.strftime('%Y-%m-%d')} से आज तक)... \n", flush=True)

    while current_date <= today:
        date_str_file = current_date.strftime('%Y-%m-%d')
        date_dmy = current_date.strftime('%d%m%Y')
        date_str_upper = current_date.strftime('%d%b%Y').upper()
        date_str_lower = current_date.strftime('%d%b%Y').lower()
        year_str = current_date.strftime('%Y')
        month_str = current_date.strftime('%b').upper()

        file_path = f"data/raw/bhav_{date_str_file}.csv"

        # Auto-Resume Support
        if os.path.exists(file_path):
            downloaded_count += 1
            current_date += timedelta(days=1)
            continue

        # 🚨 FIX 1: sec_bhavdata_full (Deliverable Volume वाली CSV) को सबसे पहली प्राथमिकता दी है
        urls_to_try = [
            f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{date_dmy}.csv",
            f"https://www.nseindia.com/api/reports?archives=%5B%7B%22name%22%3A%22Full%20Bhavcopy%20and%20Security%20Deliverable%20Data%22%2C%22type%22%3A%22daily-reports%22%2C%22category%22%3A%22capital-market%22%7D%5D&date={date_dmy}&type=equity",
            f"https://archives.nseindia.com/content/historical/EQUITIES/{year_str}/{month_str}/cm{date_str_upper}bhav.csv.zip"
        ]

        success = False
        for bhav_url in urls_to_try:
            try:
                response = session.get(bhav_url, timeout=10)

                if response.status_code == 200 and len(response.content) > 500:
                    df = extract_df_from_response(response)
                    
                    # 🚨 FIX 2: कॉलम नामों में से स्पेस और स्पेशल कैरेक्टर हटाना
                    df.columns = df.columns.astype(str).str.strip().str.upper()

                    # Series Filter (केवल Equity)
                    if 'SERIES' in df.columns:
                        df['SERIES'] = df['SERIES'].astype(str).str.strip()
                        df = df[df['SERIES'].isin(['EQ', 'BE'])].copy()

                    # STRICT F&O FILTER
                    if fno_symbols:
                        sym_col = [c for c in df.columns if 'SYMBOL' in c or 'TICKER' in c][0]
                        df['SYMBOL_CLEAN'] = df[sym_col].astype(str).str.strip().str.upper()
                        df = df[df['SYMBOL_CLEAN'].isin(fno_symbols)].drop(columns=['SYMBOL_CLEAN'])

                    # 🚨 FIX 3: Deliverable Quantity Column Standardization
                    deliv_col = [c for c in df.columns if 'DELIV_QTY' in c or 'DELIVERABLE' in c or 'DELIVQTY' in c]
                    if deliv_col:
                        # '-' वैल्यू को 0 में बदलना और नंबर बनाना
                        df['DELIV_QTY'] = pd.to_numeric(df[deliv_col[0]].astype(str).str.strip().str.replace('-', '0'), errors='coerce').fillna(0)
                    elif 'TOTTRDQTY' in df.columns:
                        df['DELIV_QTY'] = pd.to_numeric(df['TOTTRDQTY'], errors='coerce').fillna(0)

                    # Percentage Change Column
                    if not df.empty:
                        close_col = 'CLOSE_PRICE' if 'CLOSE_PRICE' in df.columns else ('LAST_PRICE' if 'LAST_PRICE' in df.columns else 'CLOSE')
                        prev_col = 'PREV_CLOSE' if 'PREV_CLOSE' in df.columns else 'PREVCLOSE'

                        if close_col in df.columns and prev_col in df.columns:
                            close_p = pd.to_numeric(df[close_col].astype(str).str.strip(), errors='coerce').fillna(0)
                            prev_p = pd.to_numeric(df[prev_col].astype(str).str.strip(), errors='coerce').fillna(0)

                            df['PCT_CHANGE'] = np.where(
                                prev_p > 0,
                                ((close_p - prev_p) / prev_p * 100).round(2),
                                0.0
                            )

                        df.to_csv(file_path, index=False)
                        print(f"✅ [{date_str_file}] Deliverable F&O Data Saved ({len(df)} rows)", flush=True)
                        downloaded_count += 1
                        success = True
                        break
                elif response.status_code == 403:
                    session = get_nse_session()
            except Exception:
                continue

        if not success:
            skipped_count += 1

        time.sleep(0.2)
        current_date += timedelta(days=1)

    print(f"\n🎉 डाउनलोड पूरा हुआ! कुल वैध फ़ाइलें: {downloaded_count}", flush=True)

if __name__ == "__main__":
    download_last_2_years_fno_data()
