import requests
import datetime
import os
import pandas as pd
import io
import time
import zoneinfo

def fetch_fo_data(days_to_fetch=160):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*'
    }
    
    # फोल्डर का नाम बदलकर raw_fo_data कर दिया गया है
    output_folder = "raw_fo_data"
    os.makedirs(output_folder, exist_ok=True)
    
    ist_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    now_ist = datetime.datetime.now(ist_tz)

    print(f"🚀 F&O Raw Data Fetching Started (Fetching Active Trading Days)...")

    saved_count = 0

    for days_back in range(0, days_to_fetch):
        target_date = now_ist - datetime.timedelta(days=days_back)

        file_date_str = target_date.strftime("%Y-%m-%d") # Format: YYYY-MM-DD
        output_path = os.path.join(output_folder, f"{file_date_str}_Full_FO.csv")

        # अगर फ़ाइल पहले से डाउनलोड है
        if os.path.exists(output_path):
            print(f"⏩ File Already Exists: {file_date_str}")
            saved_count += 1
            continue

        date_str = target_date.strftime("%Y%m%d")             
        date_str_upper = target_date.strftime("%d%b%Y").upper() 
        month_str_upper = target_date.strftime("%b").upper()     
        year_str = target_date.strftime("%Y")                    
        
        # NSE F&O UDiFF + Legacy URLs
        urls = [
            f"https://archives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{date_str}_F_0000.csv.zip",
            f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{date_str}_F_0000.csv.zip",
            f"https://archives.nseindia.com/content/historical/DERIVATIVES/{year_str}/{month_str_upper}/fo{date_str_upper}bhav.csv.zip"
        ]

        downloaded = False
        for url in urls:
            try:
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200 and len(response.content) > 1000:
                    df = pd.read_csv(io.BytesIO(response.content), compression='zip')
                    df.columns = df.columns.str.strip()

                    if len(df) > 100:
                        # Date Validation Logic
                        date_col = None
                        for col in ['TradDt', 'TIMESTAMP', 'TRAD_DT']:
                            if col in df.columns:
                                date_col = col
                                break

                        if date_col:
                            file_actual_date = pd.to_datetime(df[date_col].iloc[0]).strftime("%Y-%m-%d")
                            
                            # छुट्टी के दिन NSE द्वारा पिछला डेटा रिडायरेक्ट करने पर स्किप करें
                            if file_actual_date != file_date_str:
                                print(f"⚠️ Holiday/Closed Market for {file_date_str}! Skipping.")
                                break

                        df.to_csv(output_path, index=False)
                        saved_count += 1
                        print(f"✅ [{saved_count}] Real F&O Data Saved: {file_date_str}")
                        downloaded = True
                        break

            except Exception:
                pass

        if not downloaded:
            print(f"⏩ Market Closed / No Data for: {file_date_str}")

        time.sleep(0.4)

if __name__ == "__main__":
    fetch_fo_data(160)
