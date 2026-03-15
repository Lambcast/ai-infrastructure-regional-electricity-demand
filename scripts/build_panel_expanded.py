"""
build_panel_expanded.py
-----------------------
Extends panel_with_controls.csv (ERCO/PJM/MISO) by adding three donor
balancing authorities for the synthetic control: ISNE, NYIS, SWPP.

Output: data/panel_expanded.csv
  - 504 rows: 6 BAs x 84 months (2019-01 to 2025-12)
  - Columns: ba, year_month, year, month, quarter,
             avg_demand_mwh, n_hours, hdd, cdd, gdp
  - No queue variables for donor BAs — controls only

Sources:
  - data/eia_demand_2018_2025.csv   (EIA Form 930 hourly demand)
  - data/weather_controls.csv       (NOAA HDD/CDD — all 6 BAs already pulled)
  - BEA Regional Accounts API       (annual state GDP → monthly)

Run from project root: python scripts/build_panel_expanded.py
"""

import os
import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()
BEA_KEY = os.getenv("BEA_API_KEY")

os.makedirs("data", exist_ok=True)

# ── Config ────────────────────────────────────────────────────────────────────

DONOR_BAS    = ["ISNE", "NYIS", "SWPP"]
START_YEAR   = 2019
END_YEAR     = 2025
EIA_MWH_CAP  = 500_000

# BEA state-to-donor-BA mapping
DONOR_STATES = {
    "ISNE": ["CT", "ME", "MA", "NH", "RI", "VT"],
    "NYIS": ["NY"],
    "SWPP": ["KS", "NE", "OK", "ND", "SD"],
}

STATE_ABBREV = {
    "Connecticut": "CT", "Maine": "ME", "Massachusetts": "MA",
    "New Hampshire": "NH", "Rhode Island": "RI", "Vermont": "VT",
    "New York": "NY", "Kansas": "KS", "Nebraska": "NE",
    "Oklahoma": "OK", "North Dakota": "ND", "South Dakota": "SD",
}

# ── Step 1: Aggregate EIA demand for donor BAs ────────────────────────────────
print("Step 1: Aggregating EIA demand for donor BAs...")

eia = pd.read_csv("data/eia_demand_2018_2025.csv", parse_dates=["datetime"])
eia = eia[
    (eia["data_type"] == "D") &
    (eia["region"].isin(DONOR_BAS)) &
    (eia["mwh"] < EIA_MWH_CAP)
].copy()

eia["year_month"] = eia["datetime"].dt.to_period("M")

demand = (
    eia.groupby(["region", "year_month"])["mwh"]
    .agg(avg_demand_mwh="mean", n_hours="count")
    .reset_index()
    .rename(columns={"region": "ba"})
)

print(f"  Demand rows: {len(demand):,}")
print(f"  BAs: {demand['ba'].unique().tolist()}")
print(f"  Period: {demand['year_month'].min()} to {demand['year_month'].max()}")
print()

# ── Step 2: Build complete donor BA x month scaffold ─────────────────────────
print("Step 2: Building complete donor BA x month scaffold...")

all_months = pd.period_range(start=f"{START_YEAR}-01", end=f"{END_YEAR}-12", freq="M")
scaffold = pd.MultiIndex.from_product(
    [DONOR_BAS, all_months],
    names=["ba", "year_month"]
).to_frame(index=False)

print(f"  Scaffold rows: {len(scaffold):,} ({len(DONOR_BAS)} BAs x {len(all_months)} months)")

panel = scaffold.merge(demand, on=["ba", "year_month"], how="left")
print(f"  Missing demand after merge: {panel['avg_demand_mwh'].isna().sum()}")
print()

# ── Step 3: Merge weather controls ───────────────────────────────────────────
print("Step 3: Merging weather controls...")

weather = pd.read_csv("data/weather_controls.csv")
# Remap weather BA names to match EIA codes
weather["ba"] = weather["ba"].replace({
    "ISONE": "ISNE",
    "NYISO": "NYIS",
    "SPP":   "SWPP",
})
weather = weather[weather["ba"].isin(DONOR_BAS)].copy()

print(f"  Weather rows for donor BAs: {len(weather):,}")

panel["year_month"] = panel["year_month"].astype(str)
panel = panel.merge(weather[["ba", "year_month", "hdd", "cdd"]],
                    on=["ba", "year_month"], how="left")

print(f"  Missing HDD after merge: {panel['hdd'].isna().sum()}")
print(f"  Missing CDD after merge: {panel['cdd'].isna().sum()}")
print()

# ── Step 4: Pull BEA GDP for donor BAs ───────────────────────────────────────
print("Step 4: Pulling BEA GDP for donor BAs...")

BEA_BASE = "https://apps.bea.gov/api/data"

params = {
    "UserID":      BEA_KEY,
    "method":      "GetData",
    "datasetname": "Regional",
    "TableName":   "SAGDP9",
    "LineCode":    "1",
    "GeoFips":     "STATE",
    "Year":        ",".join(str(y) for y in range(START_YEAR, END_YEAR + 1)),
    "ResultFormat":"JSON",
}

try:
    r = requests.get(BEA_BASE, params=params, timeout=60)
    records = r.json()["BEAAPI"]["Results"]["Data"]
    bea_raw = pd.DataFrame(records)
    print(f"  BEA raw rows: {len(bea_raw):,}")
except Exception as e:
    print(f"  BEA API error: {e}")
    bea_raw = pd.DataFrame()

bea_raw["DataValue"] = pd.to_numeric(
    bea_raw["DataValue"].str.replace(",", ""), errors="coerce"
)
bea_raw = bea_raw.dropna(subset=["DataValue"])
bea_raw["state_abbrev"] = bea_raw["GeoName"].map(STATE_ABBREV)
bea_raw = bea_raw.dropna(subset=["state_abbrev"])
bea_raw["year"] = pd.to_numeric(bea_raw["TimePeriod"], errors="coerce")

# Aggregate to donor BA level
gdp_annual_rows = []
for ba, states in DONOR_STATES.items():
    ba_data = bea_raw[bea_raw["state_abbrev"].isin(states)].copy()
    if len(ba_data) == 0:
        print(f"  ⚠️  No BEA data for {ba}")
        continue
    ba_gdp = (
        ba_data.groupby("year")["DataValue"]
        .sum()
        .reset_index()
        .rename(columns={"DataValue": "gdp"})
    )
    ba_gdp["ba"] = ba
    gdp_annual_rows.append(ba_gdp)

gdp_annual = pd.concat(gdp_annual_rows, ignore_index=True)
print(f"  Annual GDP rows: {len(gdp_annual):,}")

# Interpolate annual GDP to monthly
month_df = pd.DataFrame({"year_month": [str(m) for m in all_months]})
month_df["year"] = pd.to_datetime(month_df["year_month"]).dt.year

gdp_monthly_rows = []
for ba in gdp_annual["ba"].unique():
    ba_annual = gdp_annual[gdp_annual["ba"] == ba].sort_values("year")
    ba_months = month_df.copy()
    ba_months = ba_months.merge(ba_annual[["year", "gdp"]], on="year", how="left")
    ba_months["gdp"] = ba_months["gdp"].interpolate(method="linear", limit_direction="both")
    ba_months["ba"] = ba
    gdp_monthly_rows.append(ba_months[["ba", "year_month", "gdp"]])

gdp_monthly = pd.concat(gdp_monthly_rows, ignore_index=True)
print(f"  Monthly GDP rows: {len(gdp_monthly):,}")

panel = panel.merge(gdp_monthly, on=["ba", "year_month"], how="left")
print(f"  Missing GDP after merge: {panel['gdp'].isna().sum()}")
print()

# ── Step 5: Add time variables ────────────────────────────────────────────────
print("Step 5: Adding time variables...")

panel["year_month_dt"] = pd.to_datetime(panel["year_month"])
panel["year"]    = panel["year_month_dt"].dt.year
panel["month"]   = panel["year_month_dt"].dt.month
panel["quarter"] = panel["year_month_dt"].dt.quarter
panel = panel.drop(columns=["year_month_dt"])

# ── Step 6: Stack onto panel_with_controls.csv ────────────────────────────────
print("Step 6: Stacking onto panel_with_controls.csv...")

primary = pd.read_csv("data/panel_with_controls.csv")
print(f"  Primary panel rows: {len(primary):,}")

# Align columns — donor panel has no queue variables, fill with NaN
col_order = ["ba", "year_month", "year", "month", "quarter",
             "avg_demand_mwh", "n_hours", "hdd", "cdd", "gdp"]

donor_panel = panel[col_order].copy()

# Keep only the same columns from primary for the expanded file
primary_slim = primary[col_order].copy()

expanded = pd.concat([primary_slim, donor_panel], ignore_index=True)
expanded = expanded.sort_values(["ba", "year_month"]).reset_index(drop=True)

print(f"  Expanded panel rows: {len(expanded):,}")
print()

# ── Step 7: Diagnostics and save ─────────────────────────────────────────────
print("── Expanded panel diagnostics ───────────────────────────────────────")
print(f"  BAs: {expanded['ba'].unique().tolist()}")
print(f"  Period: {expanded['year_month'].min()} to {expanded['year_month'].max()}")
print(f"  Rows per BA:")
print(expanded.groupby("ba").size().to_string())
print()
print(f"  Missing avg_demand_mwh: {expanded['avg_demand_mwh'].isna().sum()}")
print(f"  Missing hdd:            {expanded['hdd'].isna().sum()}")
print(f"  Missing cdd:            {expanded['cdd'].isna().sum()}")
print(f"  Missing gdp:            {expanded['gdp'].isna().sum()}")
print()

print("── Demand summary by BA (avg hourly MWh) ────────────────────────────")
print(
    expanded.groupby("ba")["avg_demand_mwh"]
    .agg(["mean", "min", "max"])
    .round(0)
    .to_string()
)
print()

expanded.to_csv("data/panel_expanded.csv", index=False)
print(f"✅ Saved: data/panel_expanded.csv")
print(f"   Rows: {len(expanded):,}")
print(f"   Columns: {len(expanded.columns)}")
print()
print("Done. panel_expanded.csv is ready for synthetic control.")