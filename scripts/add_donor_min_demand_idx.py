"""
add_donor_min_demand_idx.py
---------------------------
Computes min_demand_idx for donor BAs (ISNE, NYIS, SWPP) from hourly
EIA data using the same method as primary BAs in add_min_demand_idx.py.
Fills in the 252 missing values in panel_expanded.csv.

Run from project root: python scripts/add_donor_min_demand_idx.py
"""

import pandas as pd

EIA_PATH   = "data/eia_demand_2018_2025.csv"
PANEL_PATH = "data/panel_expanded.csv"

DONOR_BAS  = ["ISNE", "NYIS", "SWPP"]
EIA_MWH_CAP = 500_000

# ── Step 1: Load EIA hourly data for donor BAs ────────────────────────────────
print("Step 1: Loading EIA hourly demand for donor BAs...")

eia = pd.read_csv(EIA_PATH, parse_dates=["datetime"])
eia = eia[
    (eia["data_type"] == "D") &
    (eia["region"].isin(DONOR_BAS)) &
    (eia["mwh"] < EIA_MWH_CAP)
].copy()

eia = eia.rename(columns={"region": "ba"})
eia["year_month"] = eia["datetime"].dt.to_period("M").astype(str)
eia["year"]       = eia["datetime"].dt.year

print(f"  Rows loaded: {len(eia):,}")
print(f"  BAs: {eia['ba'].unique().tolist()}")
print()

# ── Step 2: Compute monthly minimum demand ────────────────────────────────────
print("Step 2: Computing monthly minimum demand...")

monthly_min = (
    eia.groupby(["ba", "year_month"])["mwh"]
    .min()
    .reset_index()
    .rename(columns={"mwh": "demand_min"})
)
monthly_min["year"] = pd.to_datetime(monthly_min["year_month"]).dt.year

print(f"  Monthly min rows: {len(monthly_min):,}")
print()

# ── Step 3: Index to 2019 average = 100 ──────────────────────────────────────
print("Step 3: Indexing to 2019 average = 100...")

base_2019 = (
    monthly_min[monthly_min["year"] == 2019]
    .groupby("ba")["demand_min"]
    .mean()
    .rename("base_min_2019")
    .reset_index()
)
print(f"  2019 base min demand by donor BA:")
print(base_2019.to_string(index=False))

monthly_min = monthly_min.merge(base_2019, on="ba", how="left")
monthly_min["min_demand_idx"] = (
    monthly_min["demand_min"] / monthly_min["base_min_2019"] * 100
).round(4)
monthly_min = monthly_min[["ba", "year_month", "min_demand_idx"]]
print()

# ── Step 4: Fill into panel_expanded.csv ─────────────────────────────────────
print("Step 4: Filling into panel_expanded.csv...")

panel = pd.read_csv(PANEL_PATH)
print(f"  Panel rows: {len(panel):,}")
print(f"  Missing min_demand_idx before: {panel['min_demand_idx'].isna().sum()}")

# Update only donor BA rows — primary BA values already correct
for _, row in monthly_min.iterrows():
    mask = (panel["ba"] == row["ba"]) & (panel["year_month"] == row["year_month"])
    panel.loc[mask, "min_demand_idx"] = row["min_demand_idx"]

print(f"  Missing min_demand_idx after:  {panel['min_demand_idx'].isna().sum()} (expected 0)")
print()

# ── Step 5: Verify and save ───────────────────────────────────────────────────
print("Step 5: Verifying and saving...")

print(f"  Rows: {len(panel):,} (expected 504)")
print(f"  Missing min_demand_idx: {panel['min_demand_idx'].isna().sum()} (expected 0)")

print()
print("── Sample — all BAs, January 2019 ───────────────────────────────────")
sample = panel[panel["year_month"] == "2019-01"][["ba", "year_month", "min_demand_idx"]]
print(sample.to_string(index=False))

panel.to_csv(PANEL_PATH, index=False)
print(f"\n✅ Saved: {PANEL_PATH}")
print("Done.")