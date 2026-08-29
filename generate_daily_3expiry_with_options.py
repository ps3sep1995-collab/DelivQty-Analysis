import os
import glob
import pandas as pd

def process_daily_3expiry_with_options(file_path):
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()

    # Column Standardisation (NSE UDiFF & Legacy Both Compatible)
    symbol_col = 'TckrSymb' if 'TckrSymb' in df.columns else ('SYMBOL' if 'SYMBOL' in df.columns else None)
    expiry_col = 'XpryDt' if 'XpryDt' in df.columns else ('EXPIRY_DT' if 'EXPIRY_DT' in df.columns else None)
    oi_col = 'OpnIntrst' if 'OpnIntrst' in df.columns else ('OPEN_INT' if 'OPEN_INT' in df.columns else None)
    chg_oi_col = 'ChngInOpnIntrst' if 'ChngInOpnIntrst' in df.columns else ('CHG_IN_OI' if 'CHG_IN_OI' in df.columns else None)
    close_col = 'ClsPrc' if 'ClsPrc' in df.columns else ('CLOSE' if 'CLOSE' in df.columns else None)
    instrument_col = 'SctySrs' if 'SctySrs' in df.columns else ('INSTRUMENT' if 'INSTRUMENT' in df.columns else None)
    option_type_col = 'OptnTp' if 'OptnTp' in df.columns else ('OPTION_TYP' if 'OPTION_TYP' in df.columns else None)

    if not all([symbol_col, expiry_col, oi_col, chg_oi_col]):
        print(f"❌ Standard columns missing in file: {file_path}")
        return None

    df[expiry_col] = pd.to_datetime(df[expiry_col])

    # ----------------------------------------------------
    # 1. FUTURES PROCESSING ( Near, Next, Far 3 Expiry )
    # ----------------------------------------------------
    if instrument_col:
        fut_df = df[df[instrument_col].astype(str).str.contains('FUT|FF', case=False, na=False)]
    else:
        fut_df = df.copy()

    grouped_fut = fut_df.groupby([symbol_col, expiry_col]).agg({
        oi_col: 'sum',
        chg_oi_col: 'sum',
        close_col: 'last'
    }).reset_index()

    # ----------------------------------------------------
    # 2. OPTIONS PROCESSING ( Combine CE & Combine PE )
    # ----------------------------------------------------
    opt_summary = {}
    
    if option_type_col and option_type_col in df.columns:
        # CE Filter & Aggregation
        ce_df = df[df[option_type_col].astype(str).str.upper() == 'CE']
        ce_agg = ce_df.groupby(symbol_col).agg({
            oi_col: 'sum',
            chg_oi_col: 'sum'
        }).reset_index()

        # PE Filter & Aggregation
        pe_df = df[df[option_type_col].astype(str).str.upper() == 'PE']
        pe_agg = pe_df.groupby(symbol_col).agg({
            oi_col: 'sum',
            chg_oi_col: 'sum'
        }).reset_index()

        # Merge Options Aggregates into Dictionary for fast lookup
        for _, row in ce_agg.iterrows():
            sym = row[symbol_col]
            opt_summary[sym] = {
                'Combine_CE_OI': row[oi_col],
                'Combine_CE_OI_Chg': row[chg_oi_col],
                'Combine_PE_OI': 0,
                'Combine_PE_OI_Chg': 0
            }

        for _, row in pe_agg.iterrows():
            sym = row[symbol_col]
            if sym not in opt_summary:
                opt_summary[sym] = {'Combine_CE_OI': 0, 'Combine_CE_OI_Chg': 0}
            opt_summary[sym]['Combine_PE_OI'] = row[oi_col]
            opt_summary[sym]['Combine_PE_OI_Chg'] = row[chg_oi_col]

    # ----------------------------------------------------
    # 3. MERGING FUTURES + OPTIONS INTO SINGLE RECORD
    # ----------------------------------------------------
    consolidated_records = []

    for symbol, group in grouped_fut.groupby(symbol_col):
        group = group.sort_values(expiry_col)
        
        if len(group) >= 3:
            e1 = group.iloc[0]  # 1st Expiry
            e2 = group.iloc[1]  # 2nd Expiry
            e3 = group.iloc[2]  # 3rd Expiry

            total_fut_oi = e1[oi_col] + e2[oi_col] + e3[oi_col]
            total_fut_oi_chg = e1[chg_oi_col] + e2[chg_oi_col] + e3[chg_oi_col]

            # Extract Option Data for Symbol
            sym_opt = opt_summary.get(symbol, {
                'Combine_CE_OI': 0, 'Combine_CE_OI_Chg': 0,
                'Combine_PE_OI': 0, 'Combine_PE_OI_Chg': 0
            })

            consolidated_records.append({
                'Symbol': symbol,
                
                # 1st Expiry (Futures)
                '1st_Expiry_Date': e1[expiry_col].strftime('%Y-%m-%d'),
                '1st_Close': e1[close_col],
                '1st_OI': e1[oi_col],
                '1st_OI_Chg': e1[chg_oi_col],
                
                # 2nd Expiry (Futures)
                '2nd_Expiry_Date': e2[expiry_col].strftime('%Y-%m-%d'),
                '2nd_Close': e2[close_col],
                '2nd_OI': e2[oi_col],
                '2nd_OI_Chg': e2[chg_oi_col],
                
                # 3rd Expiry (Futures)
                '3rd_Expiry_Date': e3[expiry_col].strftime('%Y-%m-%d'),
                '3rd_Close': e3[close_col],
                '3rd_OI': e3[oi_col],
                '3rd_OI_Chg': e3[chg_oi_col],
                
                # Aggregate Futures Data
                'Total_Futures_OI': total_fut_oi,
                'Total_Futures_OI_Chg': total_fut_oi_chg,

                # ---------------------------------------
                # 🔥 NEW COLUMNS: COMBINE OPTIONS DATA
                # ---------------------------------------
                'Combine_CE_OI': sym_opt['Combine_CE_OI'],
                'Combine_CE_OI_Chg': sym_opt['Combine_CE_OI_Chg'],
                'Combine_PE_OI': sym_opt['Combine_PE_OI'],
                'Combine_PE_OI_Chg': sym_opt['Combine_PE_OI_Chg'],
                
                # Put Call Ratio (PCR Calculation)
                'PCR_OI': round(sym_opt['Combine_PE_OI'] / sym_opt['Combine_CE_OI'], 2) if sym_opt['Combine_CE_OI'] > 0 else 0
            })

    return pd.DataFrame(consolidated_records)

def build_daily_files():
    input_files = glob.glob("fo_data/*_FO.csv")
    output_dir = "daily_3expiry_data"
    os.makedirs(output_dir, exist_ok=True)

    for csv_file in input_files:
        filename = os.path.basename(csv_file)
        date_part = filename.split('_')[0]
        out_filepath = os.path.join(output_dir, f"{date_part}_3Expiry_Data.csv")

        res_df = process_daily_3expiry_with_options(csv_file)
        if res_df is not None and not res_df.empty:
            res_df.to_csv(out_filepath, index=False)
            print(f"✅ Daily Data Created with CE & PE: {out_filepath}")

if __name__ == "__main__":
    build_daily_files()
