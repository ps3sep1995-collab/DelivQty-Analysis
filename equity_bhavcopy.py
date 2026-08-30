import os
import requests
import datetime
import pytz

def download_raw_equity_bhavcopy(target_trade_days=100):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    os.makedirs("raw_equity_data", exist_ok=True)
    ist_tz = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.datetime.now(ist_tz)

    print(f"🚀 Equity Raw Data Download Started: Target = {target_trade_days} Active Trading Days")

    saved_count = 0
    days_back = 0

    while saved_count < target_trade_days and days_back < 160:
        target_date = now_ist - datetime.timedelta(days=days_back)
        file_date_str = target_date.strftime("%Y-%m-%d")
        date_formatted = target_date.strftime("%d%m%Y")
        
        out_file = f"raw_equity_data/{file_date_str}_Full_Equity.csv"

        if os.path.exists(out_file):
            print(f"⏩ [{saved_count + 1}/{target_trade_days}] Already Exists: {file_date_str}")
            saved_count += 1
            days_back += 1
            continue

        url = f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{date_formatted}.csv"

        try:
            res = requests.get(url, headers=headers, timeout=12)
            
            if res.status_code == 200 and len(res.text) > 1000:
                lines = res.text.splitlines()
                if len(lines) > 5:
                    first_row = lines[1].split(',')
                    actual_date_in_file = first_row[2].strip() if len(first_row) > 2 else ""

                    expected_date_fmt = target_date.strftime("%d-%b-%Y")
                    
                    if actual_date_in_file and actual_date_in_file.upper() != expected_date_fmt.upper():
                        print(f"⚠️ Market Closed on {file_date_str} (NSE redirected). Skipping.")
                    else:
                        with open(out_file, "wb") as f:
                            f.write(res.content)
                        saved_count += 1
                        print(f"✅ [{saved_count}/{target_trade_days}] Raw Equity Saved: {file_date_str}")
            else:
                print(f"⏩ Market Closed on: {file_date_str}")

        except Exception as e:
            print(f"❌ Error downloading Equity {file_date_str}: {e}")

        days_back += 1

if __name__ == "__main__":
    download_raw_equity_bhavcopy(100)
