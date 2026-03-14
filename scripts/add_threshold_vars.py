"""
add_threshold_vars.py
---------------------
Adds MW threshold sensitivity variables to panel_with_controls.csv
for Panel B robustness checks in the panel regression.

New variables added:
  queue_mw_filed_50        — monthly MW of 50MW+ projects filed (flow)
  queue_mw_filed_200       — monthly MW of 200MW+ projects filed (flow)
  queue_mw_large_lag18_50  — 18-month lag of queue_mw_filed_50
  queue_mw_large_lag18_200 — 18-month lag of queue_mw_filed_200

Same aggregation method as queue_mw_filed_large in build_panel.py.
Same outlier cap at 99th percentile per BA applied to both new variables.

Run from project root: python scripts/add_threshold_vars.py
"""

import os
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────
QUEUE_PATH  = "data/lbnl_queue_data.csv"
PANEL_PATH  = "data/panel_with_controls.csv"
OUTPUT_PATH = "data/panel_with_controls.csv"

BA_MAP = {
    "ERCOT": "ERCO",
    "PJM":   "PJM",
    "MISO":  "MISO",
}
TARGET_REGIONS = ["ERCOT", "PJM", "MISO"]

THRESHOLDS = [50, 200]
LAG        = 18

# ── Step 1: Load and clean LBNL queue data ────────────────────────────────────
print("Step 1: Loading LBNL queue data...")

queue = pd.read_csv(QUEUE_PATH)
queue = queue[queue["region"].isin(TARGET_REGIONS)].copy()
queue["ba"] = queue["region"].map(BA_MAP)
queue = queue[queue["mw1"].notna() & (queue["mw1"] > 0)].copy()

# Convert q_date Excel serials — same method as build_panel.py
queue = queue[queue["q_date"].notna()].copy()
queue["q_date_parsed"] = pd.to_datetime(
    queue["q_date"], unit="D", origin="1899-12-30", errors="coerce"
)
queue = queue[queue["q_date_parsed"].notna()].copy()
queue = queue[queue["q_date_parsed"].dt.year >= 1990].copy()
queue["year_month"] = queue["q_date_parsed"].dt.to_period("M")

print(f"  Queue rows after filter: {len(queue):,}")
print()

# ── Step 2: Build flow variables at each threshold ────────────────────────────
print("Step 2: Building threshold flow variables...")

flow_dfs = {}
for threshold in THRESHOLDS:
    col_name = f"queue_mw_filed_{threshold}"
    flow = (
        queue[queue["mw1"] >= threshold]
        .groupby(["ba", "year_month"])["mw1"]
        .sum()
        .reset_index()
        .rename(columns={"mw1": col_name})
    )
    flow_dfs[threshold] = flow
    print(f"  {threshold}MW+ flow rows: {len(flow):,}")

print()

# ── Step 3: Load panel and merge new variables ────────────────────────────────
print("Step 3: Loading panel and merging threshold variables...")

panel = pd.read_csv(PANEL_PATH)
panel["year_month_period"] = pd.to_datetime(panel["year_month"]).dt.to_period("M")

print(f"  Panel rows before merge: {len(panel):,}")

for threshold in THRESHOLDS:
    col_name = f"queue_mw_filed_{threshold}"
    flow = flow_dfs[threshold].copy()

    # Apply same 99th percentile cap as build_panel.py
    p99 = flow.groupby("ba")[col_name].quantile(0.99)
    before = flow[col_name].max()
    flow[col_name] = flow.apply(
        lambda row: min(row[col_name], p99[row["ba"]]), axis=1
    )
    after = flow[col_name].max()
    print(f"  {threshold}MW cap: {before:,.0f} → {after:,.0f} MW")

    # Merge onto panel
    flow["year_month_period"] = flow["year_month"].astype(str).apply(
        lambda x: pd.Period(x, freq="M")
    )
    panel = panel.merge(
        flow[["ba", "year_month_period", col_name]],
        on=["ba", "year_month_period"],
        how="left"
    )
    # Months with no filings → 0
    panel[col_name] = panel[col_name].fillna(0)

print()

# ── Step 4: Build 18-month lag variables ──────────────────────────────────────
print("Step 4: Building 18-month lag variables...")

panel = panel.sort_values(["ba", "year_month"]).reset_index(drop=True)

for threshold in THRESHOLDS:
    col_name     = f"queue_mw_filed_{threshold}"
    lag_col_name = f"queue_mw_large_lag18_{threshold}"
    panel[lag_col_name] = panel.groupby("ba")[col_name].shift(LAG)
    missing = panel[lag_col_name].isna().sum()
    print(f"  {lag_col_name}: {missing} missing (expected 54 = 3 BAs x 18 months)")

print()

# ── Step 5: Drop helper column and verify ─────────────────────────────────────
print("Step 5: Verifying and saving...")

panel = panel.drop(columns=["year_month_period"])

print(f"  Rows: {len(panel):,} (expected 252)")
for threshold in THRESHOLDS:
    col      = f"queue_mw_filed_{threshold}"
    lag_col  = f"queue_mw_large_lag18_{threshold}"
    print(f"  Missing {col}: {panel[col].isna().sum()} (expected 0)")
    print(f"  Missing {lag_col}: {panel[lag_col].isna().sum()} (expected 54)")

print()
print("── Sample — ERCO, first 5 rows ──────────────────────────────────────")
sample_cols = ["ba", "year_month", "queue_mw_filed_large",
               "queue_mw_filed_50", "queue_mw_filed_200"]
print(panel[panel["ba"] == "ERCO"][sample_cols].head().to_string(index=False))
print()

panel.to_csv(OUTPUT_PATH, index=False)
print(f"✅ Saved: {OUTPUT_PATH}")
print(f"   Rows: {len(panel):,}")
print(f"   New columns: queue_mw_filed_50, queue_mw_filed_200, "
      f"queue_mw_large_lag18_50, queue_mw_large_lag18_200")
print()
print("Done. panel_with_controls.csv ready for Panel B robustness checks.")