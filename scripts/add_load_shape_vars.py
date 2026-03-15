"""
add_load_shape_vars.py
----------------------
Adds load shape variables to panel_with_controls.csv from hourly EIA data.

New variables:
  demand_min        — monthly minimum hourly demand by BA
  load_factor       — monthly average / monthly peak (0-1 ratio)
  demand_overnight  — average hourly demand midnight to 6am (hours 0-5)
  demand_daytime    — average hourly demand 9am to 9pm (hours 9-21)

Output: data/panel_load_shape.csv (252 rows)

Run from project root: python scripts/add_load_shape_vars.py
"""

import os
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────
EIA_PATH    = "data/eia_demand_2018_2025.csv"
PANEL_PATH  = "data/panel_with_controls.csv"
OUTPUT_PATH = "data/panel_load_shape.csv"

TARGET_BAS  = ["ERCO", "PJM", "MISO"]
EIA_MWH_CAP = 500_000

# ── Step 1: Load and clean EIA hourly data ────────────────────────────────────
print("Step 1: Loading EIA hourly demand data...")

eia = pd.read_csv(EIA_PATH, parse_dates=["datetime"])
eia = eia[
    (eia["data_type"] == "D") &
    (eia["region"].isin(TARGET_BAS)) &
    (eia["mwh"] < EIA_MWH_CAP)
].copy()

eia = eia.rename(columns={"region": "ba"})
eia["year_month"] = eia["datetime"].dt.to_period("M").astype(str)
eia["hour"]       = eia["datetime"].dt.hour

print(f"  Rows loaded: {len(eia):,}")
print(f"  BAs: {eia['ba'].unique().tolist()}")
print(f"  Date range: {eia['datetime'].min()} → {eia['datetime'].max()}")
print()

# ── Step 2: Compute monthly minimum and peak ──────────────────────────────────
print("Step 2: Computing monthly min, peak, and load factor...")

monthly_stats = (
    eia.groupby(["ba", "year_month"])["mwh"]
    .agg(
        demand_min="min",
        demand_peak="max",
        demand_avg="mean",
    )
    .reset_index()
)

monthly_stats["load_factor"] = (
    monthly_stats["demand_avg"] / monthly_stats["demand_peak"]
).round(4)

print(f"  Monthly stats rows: {len(monthly_stats):,}")
print()

# ── Step 3: Compute overnight average (midnight to 6am, hours 0-5) ────────────
print("Step 3: Computing overnight average demand (hours 0-5)...")

overnight = (
    eia[eia["hour"].between(0, 5)]
    .groupby(["ba", "year_month"])["mwh"]
    .mean()
    .reset_index()
    .rename(columns={"mwh": "demand_overnight"})
)

print(f"  Overnight rows: {len(overnight):,}")
print()

# ── Step 4: Compute daytime average (9am to 9pm, hours 9-21) ─────────────────
print("Step 4: Computing daytime average demand (hours 9-21)...")

daytime = (
    eia[eia["hour"].between(9, 21)]
    .groupby(["ba", "year_month"])["mwh"]
    .mean()
    .reset_index()
    .rename(columns={"mwh": "demand_daytime"})
)

print(f"  Daytime rows: {len(daytime):,}")
print()

# ── Step 5: Merge all load shape variables together ───────────────────────────
print("Step 5: Merging load shape variables...")

load_shape = monthly_stats[["ba", "year_month", "demand_min", "load_factor"]].copy()
load_shape = load_shape.merge(overnight, on=["ba", "year_month"], how="left")
load_shape = load_shape.merge(daytime,   on=["ba", "year_month"], how="left")

print(f"  Load shape rows: {len(load_shape):,}")
print(f"  Missing demand_min:       {load_shape['demand_min'].isna().sum()}")
print(f"  Missing load_factor:      {load_shape['load_factor'].isna().sum()}")
print(f"  Missing demand_overnight: {load_shape['demand_overnight'].isna().sum()}")
print(f"  Missing demand_daytime:   {load_shape['demand_daytime'].isna().sum()}")
print()

# ── Step 6: Merge onto panel_with_controls.csv ────────────────────────────────
print("Step 6: Merging onto panel_with_controls.csv...")

panel = pd.read_csv(PANEL_PATH)
print(f"  Panel rows before merge: {len(panel):,}")

panel = panel.merge(load_shape, on=["ba", "year_month"], how="left")
print(f"  Panel rows after merge:  {len(panel):,}")
print()

# ── Step 7: Verify and save ───────────────────────────────────────────────────
print("Step 7: Verifying...")

print(f"  Rows: {len(panel):,} (expected 252)")
for col in ["demand_min", "load_factor", "demand_overnight", "demand_daytime"]:
    print(f"  Missing {col}: {panel[col].isna().sum()} (expected 0)")

print()
print("── Sample — ERCO, first 5 rows ──────────────────────────────────────")
sample_cols = ["ba", "year_month", "avg_demand_mwh",
               "demand_min", "load_factor",
               "demand_overnight", "demand_daytime"]
print(panel[panel["ba"] == "ERCO"][sample_cols].head().to_string(index=False))
print()

panel.to_csv(OUTPUT_PATH, index=False)
print(f"✅ Saved: {OUTPUT_PATH}")
print(f"   Rows: {len(panel):,}")
print(f"   Columns added: demand_min, load_factor, demand_overnight, demand_daytime")
print()
print("Done. panel_load_shape.csv ready for Stata.")