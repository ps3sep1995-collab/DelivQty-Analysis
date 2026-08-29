import os
import glob
import pandas as pd

def process_daily_3expiry_with_options(file_path):
    try:
        df = pd.read_csv(file_path, low_memory=False)
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return None

    df.columns = df.columns.str.strip()

    # Image ke exact NSE UDiFF Column Mapping
    symbol_col = 'TckrSymb'
    expiry_col = 'XpryDt'
    oi_col = 'OpnIntrst'
    chg_oi_col = 'ChngInOpnIntrst'
    close_col = 'ClsPrc'
    option_type_col = 'OptnTp'
    instr_type_col = 'FinInstrmTp'  # STO, IDO (Options) / STF, IDF (Futures)

    # Required columns check
    missing_cols = [col for col in [symbol_col, expiry_col, oi_col, chg_oi_col] if col not in df.columns]
    if missing_cols:
        print(f"❌ Missing columns {missing_cols} in file: {file_path}")
        return None

    # Cleaning and converting types
    df[expiry_col] = pd.to_datetime(df[expiry_col], errors='coerce')
    df[oi_col] = pd.to_numeric(df[oi_col], errors='coerce').fillna(0)
    df[chg_oi_col] = pd.to_numeric(df[chg_oi_col], errors='coerce').fillna(0)
    if close_col in df.columns:
        df[close_col] = pd.to_numeric(df[close_col], errors='coerce').fillna(0)

    # ----------------------------------------------------
    # 1. FUTURES PROCESSING ( Near, Next, Far 3 Expiries )
    # Futures me OptnTp khali hota hai ya FinInstrmTp me 'F' hota hai (STF/IDF)
    # ----------------------------------------------------
    if option_type_col in df.columns:
        # Options wo hain jaha OptnTp 'CE' ya 'PE' hai
        is_option = df[option_type_col].astype(str).str.upper().isin(['CE', 'PE'])
        fut_df = df[~is_option].copy()
    else:
        fut_df = df.copy()

    # Grouping Futures by Symbol & Expiry
    agg_dict = {oi_col: 'sum', chg_oi_col: 'sum'}
    if close_col in df.columns:
        agg_dict[close_col] = 'last'

    grouped_fut = fut_df.groupby([symbol_col, expiry_col]).agg(agg_dict).reset_index()

    # ----------------------------------------------------
    # 2. OPTIONS PROCESSING ( Combine CE & Combine PE )
    # ----------------------------------------------------
    opt_summary = {}

    if option_type_col in df.columns:
        df[option_type_col] = df[option_type_col].astype(str).str.strip().str.upper()

        # CE Aggregation
        ce_df = df[df[option_type_col] == 'CE']
        ce_agg = ce_df.groupby(symbol_col).agg({oi_col: 'sum', chg_oi_col: 'sum'}).reset_index()

        # PE Aggregation
        pe_df = df[df[option_type_col] == 'PE']
        pe_agg = pe_df.groupby(symbol_col).agg({oi_col: 'sum', chg_oi_col: 'sum'}).reset_index()

        for _, row in ce_agg.iterrows():
            sym = row[symbol_col]
            opt_summary[sym] = {
                'Combine_CE_OI': int(row[oi_col]),
                'Combine_CE_OI_Chg': int(row[chg_oi_col]),
                'Combine_PE_OI': 0,
                'Combine_PE_OI_Chg': 0
            }

        for _, row in pe_agg.iterrows():
            sym = row[symbol_col]
            if sym not in opt_summary:
                opt_summary[sym] = {'Combine_CE_OI': 0, 'Combine_CE_OI_Chg': 0}
            opt_summary[sym]['Combine_PE_OI'] = int(row[oi_col])
            opt_summary[sym]['Combine_PE_OI_Chg'] = int(row[chg_oi_col])

    # ----------------------------------------------------
    # 3. MERGING FUTURES + OPTIONS INTO FINAL STRUCTURE
    # ----------------------------------------------------
    consolidated_records = []

    for symbol, group in grouped_fut.groupby(symbol_col):
        group = group.sort_values(expiry_col)

        # Checking minimum 3 Expiration Contracts
        if len(group) >= 3:
            e1 = group.iloc[0]
            e2 = group.iloc[1]
            e3 = group.iloc[2]

            total_fut_oi = int(e1[oi_col] + e2[oi_col] + e3[oi_col])
            total_fut_oi_chg = int(e1[chg_oi_col] + e2[chg_oi_col] + e3[chg_oi_col])

            sym_opt = opt_summary.get(symbol, {
                'Combine_CE_OI': 0, 'Combine_CE_OI_Chg': 0,
                'Combine_PE_OI': 0, 'Combine_PE_OI_Chg': 0
            })

            record = {
                'Symbol': symbol,

                # 1st Expiry (Futures)
                '1st_Expiry_Date': e1[expiry_col].strftime('%Y-%m-%d'),
                '1st_Close': e1[close_col] if close_col in df.columns else 0,
                '1st_OI': int(e1[oi_col]),
                '1st_OI_Chg': int(e1[chg_oi_col]),

                # 2nd Expiry (Futures)
                '2nd_Expiry_Date': e2[expiry_col].strftime('%Y-%m-%d'),
                '2nd_Close': e2[close_col] if close_col in df.columns else 0,
                '2nd_OI': int(e2[oi_col]),
                '2nd_OI_Chg': int(e2[chg_oi_col]),

                # 3rd Expiry (Futures)
                '3rd_Expiry_Date': e3[expiry_col].strftime('%Y-%m-%d'),
                '3rd_Close': e3[close_col] if close_col in df.columns else 0,
                '3rd_OI': int(e3[oi_col]),
                '3rd_OI_Chg': int(e3[chg_oi_col]),

                # Aggregated Futures
                'Total_Futures_OI': total_fut_oi,
                'Total_Futures_OI_Chg': total_fut_oi_chg,

                # Combine Options Data
                'Combine_CE_OI': sym_opt['Combine_CE_OI'],
                'Combine_CE_OI_Chg': sym_opt['Combine_CE_OI_Chg'],
                'Combine_PE_OI': sym_opt['Combine_PE_OI'],
                'Combine_PE_OI_Chg': sym_opt['Combine_PE_OI_Chg'],

                # Put-Call Ratio
                'PCR_OI': round(sym_opt['Combine_PE_OI'] / sym_opt['Combine_CE_OI'], 2) if sym_opt['Combine_CE_OI'] > 0 else 0
            }
            consolidated_records.append(record)

    return pd.DataFrame(consolidated_records)

def build_daily_files():
    input_files = sorted(glob.glob("fo_data/*_FO.csv"))
    output_dir = "daily_3expiry_data"
    os.makedirs(output_dir, exist_ok=True)

    for csv_file in input_files:
        filename = os.path.basename(csv_file)
        date_part = filename.split('_')[0]
        out_filepath = os.path.join(output_dir, f"{date_part}_3Expiry_Data.csv")

        res_df = process_daily_3expiry_with_options(csv_file)
        if res_df is not None and not res_df.empty:
            res_df.to_csv(out_filepath, index=False)
            print(f"✅ Daily Data Created Successfully: {out_filepath}")

if __name__ == "__main__":
    build_daily_files()
