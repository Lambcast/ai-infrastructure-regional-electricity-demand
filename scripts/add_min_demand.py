"""
add_min_demand.py
=================
Adds min_demand_mwh to panel_load_shape.csv by aggregating from
the hourly EIA Form 930 demand data.

Run from the project root:
    python scripts/add_min_demand.py

Input:   data/eia_demand_2018_2025.csv   (hourly, 184k rows)
         data/panel_load_shape.csv       (monthly panel, 252 rows)
Output:  data/panel_load_shape.csv       (overwritten in place — backup made first)

Author:  Alan Lamb — March 2026
"""

import pandas as pd
import os
import shutil

# ── Paths ─────────────────────────────────────────────────────────────────────
HOURLY_FILE = "data/eia_demand_2018_2025.csv"
PANEL_FILE  = "data/panel_load_shape.csv"
BACKUP_FILE = "data/panel_load_shape_backup.csv"

# ── Safety backup ──────────────────────────────────────────────────────────────
shutil.copy(PANEL_FILE, BACKUP_FILE)
print(f"Backup saved: {BACKUP_FILE}")

# ── Load hourly data ──────────────────────────────────────────────────────────
print(f"Loading hourly data from {HOURLY_FILE}...")
hourly = pd.read_csv(HOURLY_FILE, low_memory=False)
print(f"  Loaded {len(hourly):,} rows, columns: {list(hourly.columns)}")

# ── Standardise column names ──────────────────────────────────────────────────
# The EIA pull script typically produces: respondent, datetime, demand_mwh
# (or similar). Adjust these if your column names differ.
hourly.columns = hourly.columns.str.strip().str.lower()

# Find the BA identifier column
ba_col_candidates = ['region', 'respondent', 'ba', 'balancing_authority', 'ba_id', 'respondent_code']
ba_col = next((c for c in ba_col_candidates if c in hourly.columns), None)
if ba_col is None:
    print(f"ERROR: Cannot find BA column. Available columns: {list(hourly.columns)}")
    raise SystemExit(1)

# Filter to demand-type rows only (file contains multiple data_type values)
if 'data_type' in hourly.columns:
    before_filter = len(hourly)
    hourly = hourly[hourly['data_type'].str.upper() == 'D'].copy()
    print(f'  Filtered to demand rows (data_type=D): {len(hourly):,} of {before_filter:,} rows kept')
    if len(hourly) == 0:
        print('  WARNING: No rows with data_type=D. Checking unique values...')
        print('  Unique data_type values:', hourly_raw['data_type'].unique())
        raise SystemExit(1)

# Find the demand column
demand_col_candidates = ['mwh', 'demand_mwh', 'demand', 'value', 'demand_mw']
demand_col = next((c for c in demand_col_candidates if c in hourly.columns), None)
if demand_col is None:
    print(f"ERROR: Cannot find demand column. Available columns: {list(hourly.columns)}")
    raise SystemExit(1)

# Find the datetime column
dt_col_candidates = ['datetime', 'utc_time', 'time', 'date', 'period', 'timestamp']
dt_col = next((c for c in dt_col_candidates if c in hourly.columns), None)
if dt_col is None:
    print(f"ERROR: Cannot find datetime column. Available columns: {list(hourly.columns)}")
    raise SystemExit(1)

print(f"  Using: BA='{ba_col}', demand='{demand_col}', datetime='{dt_col}'")

# ── Filter to our three BAs ───────────────────────────────────────────────────
target_bas = {'ERCO', 'PJM', 'MISO'}
hourly = hourly[hourly[ba_col].isin(target_bas)].copy()
print(f"  After filtering to ERCO/PJM/MISO: {len(hourly):,} rows")

# ── Parse datetime and extract year-month ─────────────────────────────────────
hourly[dt_col] = pd.to_datetime(hourly[dt_col], utc=True, errors='coerce')
hourly = hourly.dropna(subset=[dt_col])

hourly['year']       = hourly[dt_col].dt.year
hourly['month']      = hourly[dt_col].dt.month
hourly['year_month'] = hourly['year'].astype(str) + 'm' + hourly['month'].astype(str).str.zfill(2)

# ── Drop corrupt rows (the billion-MWh outliers from Oct 2021) ────────────────
before = len(hourly)
hourly = hourly[hourly[demand_col] < 500_000]
print(f"  Dropped {before - len(hourly)} corrupt rows (demand > 500,000 MWh)")

# ── Aggregate: min demand per BA-month ────────────────────────────────────────
print("Aggregating minimum hourly demand by BA-month...")
min_demand = (
    hourly
    .groupby([ba_col, 'year', 'month', 'year_month'])[demand_col]
    .min()
    .reset_index()
    .rename(columns={ba_col: 'ba', demand_col: 'min_demand_mwh'})
)
print(f"  Aggregated to {len(min_demand):,} BA-month rows")

# Quick sanity check
print("\nSanity check — min demand by BA (overall mean across sample):")
print(min_demand.groupby('ba')['min_demand_mwh'].mean().round(0))

# ── Load existing panel ───────────────────────────────────────────────────────
print(f"\nLoading panel: {PANEL_FILE}")
panel = pd.read_csv(PANEL_FILE)
panel.columns = panel.columns.str.strip()
print(f"  Loaded {len(panel):,} rows, columns: {list(panel.columns)}")

# Standardise BA column name in panel
panel_ba_col = next((c for c in ['ba', 'ba_id', 'respondent'] if c in panel.columns), None)
if panel_ba_col is None:
    print(f"ERROR: Cannot find BA column in panel. Columns: {list(panel.columns)}")
    raise SystemExit(1)

# Standardise year_month in panel
# Panel likely has year_month as "2019m01" or "2019m1" format — normalise
panel_ym_col = next((c for c in ['year_month', 'ym', 'period'] if c in panel.columns), None)
if panel_ym_col is None:
    # Try to construct it from year + month columns
    if 'year' in panel.columns and 'month' in panel.columns:
        panel['year_month'] = panel['year'].astype(str) + 'm' + panel['month'].astype(str).str.zfill(2)
        panel_ym_col = 'year_month'
    else:
        print(f"ERROR: Cannot find year_month in panel. Columns: {list(panel.columns)}")
        raise SystemExit(1)

# ── Merge min demand into panel ───────────────────────────────────────────────
# Align year_month formats before merge
# Panel format might be "2019m01", min_demand format is "2019m01" — both zfill(2)
min_demand['year_month_norm'] = (
    min_demand['year'].astype(str) + 'm' +
    min_demand['month'].astype(str).str.zfill(2)
)
panel['year_month_norm'] = (
    panel[panel_ym_col]
    .astype(str)
    .str.replace(r'm(\d)$', lambda m: 'm0' + m.group(1), regex=True)
)

# If panel BA column is named differently from 'ba', add alignment
min_demand_merge = min_demand[['ba', 'year_month_norm', 'min_demand_mwh']].copy()
min_demand_merge = min_demand_merge.rename(columns={'ba': panel_ba_col})

before_cols = list(panel.columns)
panel = panel.merge(
    min_demand_merge,
    on=[panel_ba_col, 'year_month_norm'],
    how='left'
)

# Drop helper column
panel = panel.drop(columns=['year_month_norm'])

matched = panel['min_demand_mwh'].notna().sum()
print(f"\nMerge result: {matched}/{len(panel)} rows matched ({len(panel)-matched} unmatched)")

if matched < len(panel) * 0.9:
    print("WARNING: More than 10% unmatched — check BA name and year_month format alignment")
    print("Panel BA values:      ", panel[panel_ba_col].unique())
    print("Min demand BA values: ", min_demand_merge[panel_ba_col].unique())

# ── Write output ──────────────────────────────────────────────────────────────
panel.to_csv(PANEL_FILE, index=False)
print(f"\nSaved updated panel to: {PANEL_FILE}")
print(f"New columns: {[c for c in panel.columns if c not in before_cols]}")
print("\nSample output (ERCO, first 3 rows):")
sample = panel[panel[panel_ba_col] == 'ERCO'][['year', 'month', 'avg_demand_mwh', 'min_demand_mwh']].head(3)
print(sample.to_string(index=False))
print("\nDone. You can now re-run make_fig2_fig4.do for Figure 4.")