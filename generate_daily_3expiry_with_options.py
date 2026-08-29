import os
import glob
import pandas as pd

def process_daily_3expiry_with_options(file_path):
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()

    # Dynamic Column Standardisation (All NSE Formats Supported)
    symbol_col = None
    for col in ['TckrSymb', 'SYMBOL', 'Symbol']:
        if col in df.columns:
            symbol_col = col
            break

    expiry_col = None
    for col in ['XpryDt', 'EXPIRY_DT', 'Expiry_Dt']:
        if col in df.columns:
            expiry_col = col
            break

    oi_col = None
    for col in ['OpnIntrst', 'OPEN_INT', 'Open_Int']:
        if col in df.columns:
            oi_col = col
            break

    chg_oi_col = None
    for col in ['ChngInOpnIntrst', 'CHG_IN_OI', 'Chg_In_OI']:
        if col in df.columns:
            chg_oi_col = col
            break

    close_col = None
    for col in ['ClsPrc', 'CLOSE', 'Close', 'CmpltdTprs', 'LTP', 'LAST_PRICE']:
        if col in df.columns:
            close_col = col
            break

    instrument_col = None
    for col in ['SctySrs', 'INSTRUMENT', 'Instrument']:
        if col in df.columns:
            instrument_col = col
            break

    option_type_col = None
    for col in ['OptnTp', 'OPTION_TYP', 'Option_Type']:
        if col in df.columns:
            option_type_col = col
            break

    # Required columns check
    if not all([symbol_col, expiry_col, oi_col, chg_oi_col]):
        print(f"❌ Standard columns missing in file: {file_path}")
        return None

    df[expiry_col] = pd.to_datetime(df[expiry_col])

    # Dynamic Aggregation Dictionary Setup
    agg_dict = {
        oi_col: 'sum',
        chg_oi_col: 'sum'
    }
    if close_col:
        agg_dict[close_col] = 'last'

    # 1. FUTURES PROCESSING ( Near, Next, Far 3 Expiry )
    if instrument_col:
        fut_df = df[df[instrument_col].astype(str).str.contains('FUT|FF', case=False, na=False)]
    else:
        fut_df = df.copy()

    grouped_fut = fut_df.groupby([symbol_col, expiry_col]).agg(agg_dict).reset_index()

    # 2. OPTIONS PROCESSING ( Combine CE & Combine PE )
    opt_summary = {}
    
    if option_type_col and option_type_col in df.columns:
        ce_df = df[df[option_type_col].astype(str).str.upper() == 'CE']
        ce_agg = ce_df.groupby(symbol_col).agg({
            oi_col: 'sum',
            chg_oi_col: 'sum'
        }).reset_index()

        pe_df = df[df[option_type_col].astype(str).str.upper() == 'PE']
        pe_agg = pe_df.groupby(symbol_col).agg({
            oi_col: 'sum',
            chg_oi_col: 'sum'
        }).reset_index()

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

    # 3. MERGING FUTURES + OPTIONS
    consolidated_records = []

    for symbol, group in grouped_fut.groupby(symbol_col):
        group = group.sort_values(expiry_col)
        
        if len(group) >= 3:
            e1 = group.iloc[0]
            e2 = group.iloc[1]
            e3 = group.iloc[2]

            total_fut_oi = e1[oi_col] + e2[oi_col] + e3[oi_col]
            total_fut_oi_chg = e1[chg_oi_col] + e2[chg_oi_col] + e3[chg_oi_col]

            sym_opt = opt_summary.get(symbol, {
                'Combine_CE_OI': 0, 'Combine_CE_OI_Chg': 0,
                'Combine_PE_OI': 0, 'Combine_PE_OI_Chg': 0
            })

            record = {
                'Symbol': symbol,
                
                '1st_Expiry_Date': e1[expiry_col].strftime('%Y-%m-%d'),
                '1st_Close': e1[close_col] if close_col else 0,
                '1st_OI': e1[oi_col],
                '1st_OI_Chg': e1[chg_oi_col],
                
                '2nd_Expiry_Date': e2[expiry_col].strftime('%Y-%m-%d'),
                '2nd_Close': e2[close_col] if close_col else 0,
                '2nd_OI': e2[oi_col],
                '2nd_OI_Chg': e2[chg_oi_col],
                
                '3rd_Expiry_Date': e3[expiry_col].strftime('%Y-%m-%d'),
                '3rd_Close': e3[close_col] if close_col else 0,
                '3rd_OI': e3[oi_col],
                '3rd_OI_Chg': e3[chg_oi_col],
                
                'Total_Futures_OI': total_fut_oi,
                'Total_Futures_OI_Chg': total_fut_oi_chg,

                'Combine_CE_OI': sym_opt['Combine_CE_OI'],
                'Combine_CE_OI_Chg': sym_opt['Combine_CE_OI_Chg'],
                'Combine_PE_OI': sym_opt['Combine_PE_OI'],
                'Combine_PE_OI_Chg': sym_opt['Combine_PE_OI_Chg'],
                
                'PCR_OI': round(sym_opt['Combine_PE_OI'] / sym_opt['Combine_CE_OI'], 2) if sym_opt['Combine_CE_OI'] > 0 else 0
            }
            consolidated_records.append(record)

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
