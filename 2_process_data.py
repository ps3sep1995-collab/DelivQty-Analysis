import os
import glob
import json
import pandas as pd

def run_breakout_processor():
    raw_dir = "data/raw"
    output_dir = "data/processed"
    output_csv = os.path.join(output_dir, "volume_breakout_scan.csv")
    output_json = os.path.join(output_dir, "full_history_data.json")

    files = sorted(glob.glob(os.path.join(raw_dir, "*.csv")))
    if not files:
        print("❌ `data/raw` में कोई CSV फ़ाइल नहीं मिली!")
        return

    print(f"📖 {len(files)} फ़ाइलों की प्रोसेसिंग शुरू...")
    all_dfs = []

    for f in files:
        try:
            df = pd.read_csv(f)
            df.columns = df.columns.str.strip().str.upper()

            sym_col = [c for c in df.columns if 'SYMBOL' in c or 'TICKER' in c][0]
            df['SYMBOL'] = df[sym_col].astype(str).str.strip().str.upper()

            # 🚨 यहाँ बदलाव किया गया है (Deliverable Qty फिक्स)
            deliv_cols = [c for c in df.columns if 'DELIV_QTY' in c or 'DELIVERABLE' in c or 'DELIVQTY' in c or 'DELIV_QTY' in c]
            if deliv_cols:
                df['DELIV_QTY'] = pd.to_numeric(df[deliv_cols[0]], errors='coerce').fillna(0)
            else:
                vol_col = [c for c in df.columns if 'TOTTRDQTY' in c or 'VOLUME' in c][0]
                df['DELIV_QTY'] = pd.to_numeric(df[vol_col], errors='coerce').fillna(0)
            
            close_col = 'CLOSE_PRICE' if 'CLOSE_PRICE' in df.columns else 'CLOSE'
            prev_col = 'PREV_CLOSE' if 'PREV_CLOSE' in df.columns else 'PREVCLOSE'
            
            df['CLOSE'] = pd.to_numeric(df.get(close_col, 0), errors='coerce').fillna(0)
            df['PREVCLOSE'] = pd.to_numeric(df.get(prev_col, 0), errors='coerce').fillna(0)

            date_str = os.path.basename(f).replace('bhav_', '').replace('.csv', '')
            df['DATE'] = date_str

            all_dfs.append(df[['SYMBOL', 'DATE', 'CLOSE', 'PREVCLOSE', 'DELIV_QTY', 'PCT_CHANGE']])
        except Exception:
            continue

    if not all_dfs:
        print("❌ कोई वैध डेटा नहीं मिला!")
        return

    bhav_df = pd.concat(all_dfs, ignore_index=True)
    bhav_df = bhav_df.sort_values(['SYMBOL', 'DATE']).reset_index(drop=True)

    # 1. Popup के लिए पूरे इतिहास का JSON बनाएं
    history_dict = {}
    for symbol, group in bhav_df.groupby('SYMBOL'):
        history_dict[symbol] = group.sort_values('DATE', ascending=False).to_dict(orient='records')

    os.makedirs(output_dir, exist_ok=True)
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(history_dict, f)

    # 2. Moving Averages (2D, 5D, 7D, 10D)
    bhav_df['AVG_2D'] = bhav_df.groupby('SYMBOL')['DELIV_QTY'].transform(lambda x: x.shift(1).rolling(2).mean())
    bhav_df['AVG_5D'] = bhav_df.groupby('SYMBOL')['DELIV_QTY'].transform(lambda x: x.shift(1).rolling(5).mean())
    bhav_df['AVG_7D'] = bhav_df.groupby('SYMBOL')['DELIV_QTY'].transform(lambda x: x.shift(1).rolling(7).mean())
    bhav_df['AVG_10D'] = bhav_df.groupby('SYMBOL')['DELIV_QTY'].transform(lambda x: x.shift(1).rolling(10).mean())

    def check_breakout(r):
        signals = []
        d = r['DELIV_QTY']
        if r['AVG_2D'] > 0 and d >= 2 * r['AVG_2D']: signals.append("2D")
        if r['AVG_5D'] > 0 and d >= 2 * r['AVG_5D']: signals.append("5D")
        if r['AVG_7D'] > 0 and d >= 2 * r['AVG_7D']: signals.append("7D")
        if r['AVG_10D'] > 0 and d >= 2 * r['AVG_10D']: signals.append("10D")
        return ", ".join(signals) if signals else "NO"

    bhav_df['BREAKOUT_TYPE'] = bhav_df.apply(check_breakout, axis=1)

    scan_df = bhav_df[bhav_df['BREAKOUT_TYPE'] != "NO"].copy()
    scan_df.to_csv(output_csv, index=False)
    print(f"🎉 Breakout CSV और Full History JSON सफलता से बन गए हैं!")

if __name__ == "__main__":
    run_breakout_processor()
