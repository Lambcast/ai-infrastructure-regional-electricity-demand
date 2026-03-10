"""
build_panel.py
--------------
Constructs the core analysis panel for the AI Infrastructure &
Regional Electricity Demand project.

Panel structure:
  - Unit of observation: balancing authority (BA) x calendar month
  - Three BAs: ERCO (ERCOT), PJM, MISO
  - Time range: 2019-01 through 2025-12 (~252 rows)

Sources used in this script:
  - data/eia_demand_2018_2025.csv   (EIA Form 930 hourly demand)
  - data/lbnl_queue_data.csv        (LBNL interconnection queue)

Sources added later (Phase 2):
  - NOAA weather (HDD/CDD) — not yet pulled
  - BEA regional GDP — not yet pulled

Output:
  - data/panel_base.csv             (BA x month panel, queue + demand)

Run from project root: python scripts/build_panel.py

Notes on data cleaning:
  - LBNL q_date is stored as Excel serial numbers (days since 1899-12-30)
    and must be converted before parsing to year_month periods.
  - EIA data contains three corrupt PJM rows from 2021-10-19 with values
    in the billions of MWh. These are filtered out with a 500,000 MWh cap,
    consistent with explore_eia.py.
"""

import os
import pandas as pd
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────────
EIA_PATH        = "data/eia_demand_2018_2025.csv"
QUEUE_PATH      = "data/lbnl_queue_data.csv"
OUTPUT_PATH     = "data/panel_base.csv"

# BA codes: EIA uses ERCO, LBNL uses ERCOT — standardize to EIA codes
BA_MAP = {
    "ERCOT": "ERCO",
    "PJM":   "PJM",
    "MISO":  "MISO",
}
TARGET_BAS = ["ERCO", "PJM", "MISO"]

# Outlier cap for EIA demand — three corrupt PJM rows on 2021-10-19
# reach billions of MWh; normal max is ~130,000 MWh
EIA_MWH_CAP = 500_000

# Large project threshold (MW)
LARGE_MW_THRESHOLD = 100

# Lag periods (months)
LAG_PERIODS = [12, 18, 24]

# ── Step 1: EIA demand → BA-month ─────────────────────────────────────────────
print("Step 1: Aggregating EIA demand to BA-month...")

eia = pd.read_csv(EIA_PATH, parse_dates=["datetime"])

# Keep demand only, target BAs only, filter corrupt outliers
eia = eia[
    (eia["data_type"] == "D") &
    (eia["region"].isin(TARGET_BAS)) &
    (eia["mwh"] < EIA_MWH_CAP)
].copy()

eia["year_month"] = eia["datetime"].dt.to_period("M")

demand = (
    eia.groupby(["region", "year_month"])["mwh"]
    .agg(
        avg_demand_mwh="mean",
        n_hours="count",
    )
    .reset_index()
    .rename(columns={"region": "ba"})
)

print(f"  Demand rows: {len(demand):,}")
print(f"  BAs: {demand['ba'].unique().tolist()}")
print(f"  Period: {demand['year_month'].min()} to {demand['year_month'].max()}")
print()

# ── Step 2: LBNL queue → BA-month ────────────────────────────────────────────
print("Step 2: Aggregating LBNL queue data to BA-month...")

queue = pd.read_csv(QUEUE_PATH)

# Filter to target regions and standardize BA codes
queue = queue[queue["region"].isin(BA_MAP.keys())].copy()
queue["ba"] = queue["region"].map(BA_MAP)

# Drop rows with no MW value
queue = queue[queue["mw1"].notna() & (queue["mw1"] > 0)].copy()

# q_date is stored as Excel serial number (days since 1899-12-30)
# Convert to datetime, then to year_month period
queue = queue[queue["q_date"].notna()].copy()
queue["q_date_parsed"] = pd.to_datetime(
    queue["q_date"], unit="D", origin="1899-12-30", errors="coerce"
)
queue = queue[queue["q_date_parsed"].notna()].copy()
queue = queue[queue["q_date_parsed"].dt.year >= 1990].copy()
queue["year_month"] = queue["q_date_parsed"].dt.to_period("M")

# Flag large projects
queue["is_large"] = queue["mw1"] >= LARGE_MW_THRESHOLD

print(f"  Queue rows after filter: {len(queue):,}")
print(f"  Date range: {queue['year_month'].min()} to {queue['year_month'].max()}")
print(f"  Large projects (>={LARGE_MW_THRESHOLD}MW): {queue['is_large'].sum():,}")
print()

# ── Step 3: Build queue flow variables (MW filed per BA-month) ────────────────
print("Step 3: Building queue flow variables...")

# All projects — total MW filed
flow_all = (
    queue.groupby(["ba", "year_month"])["mw1"]
    .sum()
    .reset_index()
    .rename(columns={"mw1": "queue_mw_filed"})
)

# Large projects only
flow_large = (
    queue[queue["is_large"]]
    .groupby(["ba", "year_month"])["mw1"]
    .sum()
    .reset_index()
    .rename(columns={"mw1": "queue_mw_filed_large"})
)

# Project count filed
count_filed = (
    queue.groupby(["ba", "year_month"])["mw1"]
    .count()
    .reset_index()
    .rename(columns={"mw1": "queue_projects_filed"})
)

# Merge flow variables
flow = flow_all.merge(flow_large, on=["ba", "year_month"], how="left")
flow = flow.merge(count_filed, on=["ba", "year_month"], how="left")
flow["queue_mw_filed_large"] = flow["queue_mw_filed_large"].fillna(0)

print(f"  Flow rows: {len(flow):,}")
print()

# ── Step 4: Build complete BA x month scaffold (2019-01 to 2025-12) ──────────
print("Step 4: Building complete BA x month scaffold...")

all_months = pd.period_range(start="2019-01", end="2025-12", freq="M")
scaffold = pd.MultiIndex.from_product(
    [TARGET_BAS, all_months],
    names=["ba", "year_month"]
).to_frame(index=False)

print(f"  Scaffold rows: {len(scaffold):,} ({len(TARGET_BAS)} BAs x {len(all_months)} months)")

# ── Step 5: Merge demand and queue onto scaffold ──────────────────────────────
print("Step 5: Merging demand and queue onto scaffold...")

panel = scaffold.merge(demand, on=["ba", "year_month"], how="left")
panel = panel.merge(flow, on=["ba", "year_month"], how="left")

# Months with no filings → 0 (not missing — there were genuinely no filings)
for col in ["queue_mw_filed", "queue_mw_filed_large", "queue_projects_filed"]:
    panel[col] = panel[col].fillna(0)

# ── Step 6: Build cumulative active queue stock variable ──────────────────────
print("Step 6: Building cumulative queue stock variable...")

panel = panel.sort_values(["ba", "year_month"])
panel["queue_mw_active"] = (
    panel.groupby("ba")["queue_mw_filed"]
    .cumsum()
)

# ── Step 7: Build lag variables ───────────────────────────────────────────────
print("Step 7: Building lag variables...")

for lag in LAG_PERIODS:
    panel[f"queue_mw_lag{lag}"] = (
        panel.groupby("ba")["queue_mw_filed"].shift(lag)
    )
    panel[f"queue_mw_large_lag{lag}"] = (
        panel.groupby("ba")["queue_mw_filed_large"].shift(lag)
    )
    print(f"  Created queue_mw_lag{lag} and queue_mw_large_lag{lag}")

# ── Step 8: Add time variables ────────────────────────────────────────────────
print("Step 8: Adding time variables...")

panel["year"]    = panel["year_month"].dt.year
panel["month"]   = panel["year_month"].dt.month
panel["quarter"] = panel["year_month"].dt.quarter

# ── Step 9: Final column order and save ──────────────────────────────────────
print("Step 9: Saving panel...")

col_order = [
    "ba", "year_month", "year", "month", "quarter",
    "avg_demand_mwh", "n_hours",
    "queue_mw_filed", "queue_mw_filed_large", "queue_projects_filed",
    "queue_mw_active",
    "queue_mw_lag12", "queue_mw_large_lag12",
    "queue_mw_lag18", "queue_mw_large_lag18",
    "queue_mw_lag24", "queue_mw_large_lag24",
]
panel = panel[col_order]
panel = panel.sort_values(["ba", "year_month"]).reset_index(drop=True)

os.makedirs("data", exist_ok=True)
panel.to_csv(OUTPUT_PATH, index=False)
print(f"✅ Panel saved: {OUTPUT_PATH}")
print(f"   Rows: {len(panel):,}")
print(f"   Columns: {len(panel.columns)}")

# ── Step 10: Diagnostics ─────────────────────────────────────────────────────
print()
print("── Panel diagnostics ────────────────────────────────────────────────")
print(f"  BAs: {panel['ba'].unique().tolist()}")
print(f"  Period: {panel['year_month'].min()} to {panel['year_month'].max()}")
print(f"  Missing demand rows: {panel['avg_demand_mwh'].isna().sum()}")
print(f"  Months with no queue filings: {(panel['queue_mw_filed'] == 0).sum()}")
print()

print("── Demand summary by BA (avg hourly MWh) ────────────────────────────")
print(
    panel.groupby("ba")["avg_demand_mwh"]
    .agg(["mean", "min", "max"])
    .round(0)
    .to_string()
)
print()

print("── Queue filing summary by BA (total GW filed 2019–2025) ────────────")
recent = panel[panel["year"] >= 2019]
summary = (
    recent.groupby("ba")["queue_mw_filed"]
    .sum()
    .reset_index()
    .rename(columns={"queue_mw_filed": "total_mw"})
)
summary["total_gw"] = (summary["total_mw"] / 1000).round(1)
print(summary.to_string(index=False))
print()

print("── Sample rows (ERCO, mid-panel) ────────────────────────────────────")
sample = panel[panel["ba"] == "ERCO"].iloc[30:35][
    ["ba", "year_month", "avg_demand_mwh", "queue_mw_filed", "queue_mw_active", "queue_mw_lag12"]
]
print(sample.to_string(index=False))
print()
print("Done. Panel ready for Phase 2 regression and forecasting.")
