import pandas as pd
import glob
import os

def generate_fo_stocks_txt():
    raw_folder = "raw_fo_data"
    
    # raw_fo_data फोल्डर की CSV फाइलों की लिस्ट लें
    csv_files = glob.glob(os.path.join(raw_folder, "*_Full_FO.csv"))
    
    if not csv_files:
        print("❌ कोई F&O CSV फाइल नहीं मिली!")
        return

    # सबसे नई CSV फाइल चुनें
    latest_file = sorted(csv_files)[-1]
    print(f"📄 फाइल से स्टॉक्स की लिस्ट निकाली जा रही है: {os.path.basename(latest_file)}")

    try:
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip() # स्पेस हटाएं

        # 1. सिंबल कॉलम पहचानें
        symbol_col = None
        for col in ['TckrSymb', 'SYMBOL', 'Symbol', 'TCKR_SYMB']:
            if col in df.columns:
                symbol_col = col
                break

        if not symbol_col:
            print(f"❌ सिंबल कॉलम नहीं मिला! CSV कॉलम: {list(df.columns)}")
            return

        # 2. सूचकांकों (Indices) की लिस्ट जिन्हें हटाना है
        indices = [
            'NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 
            'NIFTYNXT50', 'NIFTY IT', 'NIFTY50', 'BANKNIFTY'
        ]

        # 3. सभी यूनिक सिम्बल्स निकालें
        all_symbols = df[symbol_col].dropna().unique()

        # 4. फिल्टर: सिर्फ स्टॉक्स (अक्षरों से शुरू होने वाले और Index को छोड़कर)
        stocks = []
        for sym in all_symbols:
            sym_str = str(sym).strip()
            # सूचकांकों को छोड़ें और केवल वैलिड स्टॉक सिंबल लें
            if sym_str.upper() not in indices and len(sym_str) > 0:
                stocks.append(sym_str)

        # 5. अल्फाबेटिकल क्रम में सॉर्ट करें
        stocks = sorted(list(set(stocks)))

        # 6. .txt फाइल में सेव करें
        txt_output_path = "fo_stocks_list.txt"
        with open(txt_output_path, "w", encoding="utf-8") as f:
            for stock in stocks:
                f.write(f"{stock}\n")

        print(f"✅ कुल {len(stocks)} F&O स्टॉक्स सफलतापूर्वक सेव हो गए हैं: '{txt_output_path}'")

    except Exception as e:
        print(f"❌ लिस्ट बनाने में समस्या आई: {e}")

if __name__ == "__main__":
    generate_fo_stocks_txt()
