import os
import requests
import io
import zipfile
import datetime
import pytz

def download_raw_fo_bhavcopy(target_trade_days=100):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*'
    }

    os.makedirs("raw_fo_data", exist_ok=True)
    ist_tz = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.datetime.now(ist_tz)

    print(f"🚀 F&O Raw Data Download Started: Target = {target_trade_days} Active Trading Days")

    saved_count = 0
    days_back = 0

    while saved_count < target_trade_days and days_back < 160:
        target_date = now_ist - datetime.timedelta(days=days_back)
        file_date_str = target_date.strftime("%Y-%m-%d")
        
        out_file = f"raw_fo_data/{file_date_str}_Full_FO.csv"

        if os.path.exists(out_file):
            print(f"⏩ [{saved_count + 1}/{target_trade_days}] Already Exists: {file_date_str}")
            saved_count += 1
            days_back += 1
            continue

        date_ddmmyyyy = target_date.strftime("%d%m%Y")
        date_ddmmmyyyy = target_date.strftime("%d%b%Y").upper()
        year_str = target_date.strftime("%Y")
        month_str = target_date.strftime("%b").upper()

        # NSE Derivative URLs (New UDiFF Format & Historical Old Format)
        urls = [
            # 1. New NSE UDiFF Format
            f"https://archives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{date_ddmmyyyy}_F_0000.csv.zip",
            # 2. Historical Format
            f"https://archives.nseindia.com/content/historical/DERIVATIVES/{year_str}/{month_str}/fo{date_ddmmmyyyy}bhav.csv.zip"
        ]

        downloaded = False
        for url in urls:
            try:
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code == 200 and len(res.content) > 1000:
                    z = zipfile.ZipFile(io.BytesIO(res.content))
                    csv_filename = z.namelist()[0]
                    
                    with open(out_file, "wb") as f:
                        f.write(z.read(csv_filename))
                        
                    saved_count += 1
                    print(f"✅ [{saved_count}/{target_trade_days}] Raw F&O Saved: {file_date_str}")
                    downloaded = True
                    break
            except Exception:
                continue

        if not downloaded:
            print(f"⏩ Market Closed / No F&O File on: {file_date_str}")

        days_back += 1

if __name__ == "__main__":
    download_raw_fo_bhavcopy(100)
