import pandas as pd
import glob
import os

def generate_fo_stocks_txt():
    raw_folder = "raw_fo_data"
    
    # फोल्डर की किसी भी एक डाउनलोड की हुई F&O CSV फाइल को खोजें
    csv_files = glob.glob(os.path.join(raw_folder, "*_Full_FO.csv"))
    
    if not csv_files:
        print("❌ कोई F&O CSV फाइल नहीं मिली! कृपया पहले डेटा डाउनलोड करें।")
        return

    # नवीनतम CSV फाइल चुनें
    latest_file = csv_files[0]
    print(f"📄 फाइल से स्टॉक्स की लिस्ट निकाली जा रही है: {os.path.basename(latest_file)}")

    try:
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip() # स्पेस हटाएं

        # 1. सिंबल और इंस्ट्रूमेंट टाइप वाले कॉलम की पहचान करें
        symbol_col = None
        instrument_col = None

        for col in ['TckrSymb', 'SYMBOL']:
            if col in df.columns:
                symbol_col = col
                break

        for col in ['Sgmt', 'INSTRUMENT']:
            if col in df.columns:
                instrument_col = col
                break

        if not symbol_col:
            print("❌ सिंबल कॉलम नहीं मिला!")
            return

        # 2. F&O स्टॉक्स को फिल्टर करें
        # नए UDiFF फॉर्मेट में Stock Futures/Options (STKF/STKO) होते हैं, पुराने में FUTSTK/OPTSTK
        if instrument_col:
            stock_df = df[df[instrument_col].isin(['STKF', 'STKO', 'FUTSTK', 'OPTSTK'])]
            stocks = stock_df[symbol_col].dropna().unique()
        else:
            # अगर Instrument कॉलम न मिले तो सूचकांकों (Indices) को हटाकर बाकी स्टॉक्स लें
            indices = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY']
            all_symbols = df[symbol_col].dropna().unique()
            stocks = [s for s in all_symbols if s not in indices]

        # 3. अल्फाबेटिकल क्रम में सॉर्ट करें
        stocks = sorted(stocks)

        # 4. .txt फाइल में सेव करें (हर स्टॉक नई लाइन पर)
        txt_output_path = "fo_stocks_list.txt"
        with open(txt_output_path, "w", encoding="utf-8") as f:
            for stock in stocks:
                f.write(f"{stock}\n")

        print(f"✅ कुल {len(stocks)} F&O स्टॉक्स सफलतापूर्वक सेव हो गए हैं: '{txt_output_path}'")

    except Exception as e:
        print(f"❌ लिस्ट बनाने में समस्या आई: {e}")

if __name__ == "__main__":
    generate_fo_stocks_txt()
