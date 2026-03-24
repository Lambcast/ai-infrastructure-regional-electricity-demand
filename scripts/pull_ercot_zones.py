import pandas as pd
import zipfile
import os

zone_dir = 'data/ercot_zones'
all_dfs = []

for year in range(2019, 2026):
    path = os.path.join(zone_dir, f'Native_Load_{year}.zip')
    print(f"Reading {year}...")
    try:
        with zipfile.ZipFile(path) as z:
            files = z.namelist()
            print(f"  Files: {files}")
            xlsx_files = [f for f in files if f.endswith('.xlsx') or f.endswith('.xls') or f.endswith('.csv')]
            with z.open(xlsx_files[0]) as f:
                if xlsx_files[0].endswith('.csv'):
                    df = pd.read_csv(f)
                else:
                    df = pd.read_excel(f)
            print(f"  Shape: {df.shape}")
            print(f"  Columns: {df.columns.tolist()}")
            df['source_year'] = year
            all_dfs.append(df)
    except Exception as e:
        print(f"  ERROR: {e}")

if all_dfs:
    combined = pd.concat(all_dfs, ignore_index=True)
    combined.to_csv('data/ercot_zone_raw.csv', index=False)
    print(f"\nSaved: data/ercot_zone_raw.csv | Shape: {combined.shape}")