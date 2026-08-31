import os
import glob
import pandas as pd

def extract_current_month_expiry():
    raw_folder = "raw_fo_data"
    
    # raw_fo_data फोल्डर की सभी CSV फाइलों को ढूंढें
    csv_files = glob.glob(os.path.join(raw_folder, "*_Full_FO.csv"))
    
    if not csv_files:
        print("❌ कोई भी CSV फाइल नहीं मिली। कृपया पहले डेटा डाउनलोड करें।")
        return

    print(f"🔄 कुल {len(csv_files)} फाइलों को प्रोसेस किया जा रहा है...")

    for file_path in csv_files:
        # फाइल नेम से ट्रेड तारीख निकालना
        file_name = os.path.basename(file_path)
        trade_date_str = file_name.split("_")[0]
        
        try:
            df = pd.read_csv(file_path)
            df.columns = df.columns.str.strip() # कॉलम के नाम से स्पेस हटाएं

            # 1. ट्रेड डेट और एक्सपायरी डेट का कॉलम पहचानें
            date_col = None
            expiry_col = None

            for col in ['TradDt', 'TIMESTAMP', 'TRAD_DT']:
                if col in df.columns:
                    date_col = col
                    break
                    
            for col in ['XpryDt', 'EXPIRY_DT', 'EXPIR_DATE']:
                if col in df.columns:
                    expiry_col = col
                    break

            if not date_col or not expiry_col:
                print(f"⚠️ आवश्यक कॉलम नहीं मिले: {file_name}")
                continue

            # 2. डेट फॉर्मेट को 'Datetime' में बदलें
            df[date_col] = pd.to_datetime(df[date_col])
            df[expiry_col] = pd.to_datetime(df[expiry_col])

            # 3. ट्रेड डेट का साल और महीना निकालें
            trade_year = df[date_col].dt.year
            trade_month = df[date_col].dt.month

            # 4. फिल्टर: सिर्फ वही डेटा रखें जिसकी एक्सपायरी डेट उसी महीने और साल की हो
            current_month_df = df[
                (df[expiry_col].dt.year == trade_year) & 
                (df[expiry_col].dt.month == trade_month)
            ]

            if not current_month_df.empty:
                # 5. डेटा में से उस महीने की अंतिम/अक्षरित एक्सपायरी डेट निकालें
                actual_expiry_date = current_month_df[expiry_col].max().strftime("%Y-%m-%d")
                
                # नया फाइल नेम फॉर्मेट: YYYY-MM-DD_expire_date_YYYY-MM-DD.csv
                output_path = os.path.join(raw_folder, f"{trade_date_str}_expire_date_{actual_expiry_date}.csv")
                
                # अगर फाइल पहले से मौजूद है तो स्किप करें
                if os.path.exists(output_path):
                    print(f"⏩ पहले से मौजूद है: {os.path.basename(output_path)}")
                    continue

                current_month_df.to_csv(output_path, index=False)
                print(f"✅ सेव की गई: {os.path.basename(output_path)}")
            else:
                print(f"⚠️ कोई मैचिंग करंट मंथ डेटा नहीं मिला: {file_name}")

        except Exception as e:
            print(f"❌ एरर फाइल {file_name} में: {e}")

if __name__ == "__main__":
    extract_current_month_expiry()
