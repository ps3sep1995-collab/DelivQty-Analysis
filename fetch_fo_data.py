import requests
import datetime
import os
import pandas as pd
import io
import time
import zoneinfo

def fetch_fo_data(days_to_fetch=10):
    # NSE से डेटा डाउनलोड करने के लिए HTTP Headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*'
    }
    
    output_folder = "fo_data"
    os.makedirs(output_folder, exist_ok=True)
    
    # IST Timezone
    ist_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    now_ist = datetime.datetime.now(ist_tz)

    print(f"🚀 F&O Data Fetching (Last {days_to_fetch} Days)...")

    for days_back in range(0, days_to_fetch):
        target_date = now_ist - datetime.timedelta(days=days_back)

        file_date_str = target_date.strftime("%Y-%m-%d") # Format: YYYY-MM-DD
        output_path = os.path.join(output_folder, f"{file_date_str}_FO.csv")

        # अगर फ़ाइल पहले से डाउनलोड है तो दोबारा ना करें
        if os.path.exists(output_path):
            print(f"⏩ File Already Exists: {file_date_str}")
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
                        # --------------------------------------------------
                        # 🔥 DATE VALIDATION LOGIC (NSE Redirect Check)
                        # --------------------------------------------------
                        date_col = None
                        for col in ['TradDt', 'TIMESTAMP', 'TRAD_DT']:
                            if col in df.columns:
                                date_col = col
                                break

                        if date_col:
                            # CSV की पहली रो से वास्तविक ट्रेडिंग डेट निकालना
                            file_actual_date = pd.to_datetime(df[date_col].iloc[0]).strftime("%Y-%m-%d")
                            
                            # यदि फ़ाइल की असली तारीख हमारी target_date से मैच नहीं करती (छुट्टी का दिन)
                            if file_actual_date != file_date_str:
                                print(f"⚠️ Holiday/Closed Market for {file_date_str}! NSE served last trading day data ({file_actual_date}). Skipping.")
                                break

                        # यदि असली तारीख मैच हो गई
                        df.to_csv(output_path, index=False)
                        print(f"✅ Real F&O Data Saved for Date: {file_date_str}")
                        downloaded = True
                        break

            except Exception as e:
                pass

        if not downloaded:
            print(f"⏩ Market Closed / No Real Data for: {file_date_str}")

        time.sleep(0.8)

if __name__ == "__main__":
    fetch_fo_data(10)
