"""
build_panel_caiso.py
--------------------
Builds a standalone CAISO comparison panel for descriptive analysis.
CAISO is NOT added to panel_expanded.csv — this is for comparison only.

Output: data/panel_caiso_comparison.csv (84 rows, 1 BA x 84 months)

Sources:
  - EIA API (CISO demand — already pulled in caiso_diagnostic.py)
  - NOAA NCEI API (HDD/CDD — Los Angeles station USW00023174)
  - BEA Regional Accounts API (California GDP)

Run from project root: python scripts/build_panel_caiso.py
"""

import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
API_KEY    = os.getenv("EIA_API_KEY")
NOAA_KEY   = os.getenv("NOAA_API_KEY")
BEA_KEY    = os.getenv("BEA_API_KEY")
BASE_URL   = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
NOAA_BASE  = "https://www.ncei.noaa.gov/cdo-web/api/v2/data"
BEA_BASE   = "https://apps.bea.gov/api/data"

START_YEAR = 2019
END_YEAR   = 2025
EIA_MWH_CAP = 500_000

all_months = pd.period_range(start="2019-01", end="2025-12", freq="M")
month_df   = pd.DataFrame({"year_month": [str(m) for m in all_months]})
month_df["year"] = pd.to_datetime(month_df["year_month"]).dt.year

# ── Step 1: Pull CISO demand from EIA ────────────────────────────────────────
print("Step 1: Pulling CAISO (CISO) demand from EIA...")

all_records = []
for year in range(START_YEAR, END_YEAR + 1):
    offset = 0
    while True:
        params = {
            "api_key":              API_KEY,
            "frequency":            "hourly",
            "data[0]":              "value",
            "facets[respondent][]": "CISO",
            "facets[type][]":       "D",
            "start":                f"{year}-01-01T00",
            "end":                  f"{year}-12-31T23",
            "length":               5000,
            "offset":               offset,
        }
        try:
            r = requests.get(BASE_URL, params=params, timeout=60)
            data = r.json()
            records = data["response"]["data"]
            total   = int(data["response"]["total"])
            all_records.extend(records)
            offset += len(records)
            print(f"  {year}: pulled {offset}/{total}")
            if offset >= total or len(records) == 0:
                break
            time.sleep(0.5)
        except Exception as e:
            print(f"  Error: {e}, retrying...")
            time.sleep(15)
    time.sleep(1)

eia = pd.DataFrame(all_records)
eia = eia.rename(columns={"period": "datetime", "value": "mwh"})
eia["datetime"] = pd.to_datetime(eia["datetime"])
eia["mwh"]      = pd.to_numeric(eia["mwh"], errors="coerce")
eia             = eia[eia["mwh"] < EIA_MWH_CAP].copy()
eia["year_month"] = eia["datetime"].dt.to_period("M").astype(str)

demand = (
    eia.groupby("year_month")["mwh"]
    .agg(avg_demand_mwh="mean", n_hours="count")
    .reset_index()
)
demand["ba"] = "CISO"
print(f"  Monthly demand rows: {len(demand):,}")
print()

# ── Step 2: Pull NOAA weather for Los Angeles ─────────────────────────────────
print("Step 2: Pulling NOAA weather for Los Angeles (USW00023174)...")

def pull_noaa_station(station_id, year):
    headers = {"token": NOAA_KEY}
    params  = {
        "datasetid":  "GHCND",
        "stationid":  f"GHCND:{station_id}",
        "datatypeid": "TMAX,TMIN",
        "startdate":  f"{year}-01-01",
        "enddate":    f"{year}-12-31",
        "units":      "standard",
        "limit":      1000,
        "offset":     1,
    }
    all_recs = []
    while True:
        try:
            r = requests.get(NOAA_BASE, headers=headers, params=params, timeout=60)
            if r.status_code == 503:
                print(f"    503, waiting 60s...")
                time.sleep(60)
                continue
            if r.status_code != 200:
                print(f"    Error {r.status_code}")
                return []
            data    = r.json()
            results = data.get("results", [])
            all_recs.extend(results)
            meta   = data.get("metadata", {}).get("resultset", {})
            count  = meta.get("count", 0)
            offset = meta.get("offset", 1)
            limit  = meta.get("limit", 1000)
            if offset + limit - 1 >= count:
                break
            params["offset"] = offset + limit
            time.sleep(0.5)
        except Exception as e:
            print(f"    Exception: {e}, retrying...")
            time.sleep(15)
    return all_recs

def compute_hdd_cdd(records):
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df = df[df["datatype"].isin(["TMAX", "TMIN"])].copy()
    df["date"]  = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    pivot = df.pivot_table(index="date", columns="datatype", values="value").reset_index()
    pivot.columns.name = None
    if "TMAX" not in pivot.columns or "TMIN" not in pivot.columns:
        return pd.DataFrame()
    pivot       = pivot.dropna(subset=["TMAX", "TMIN"])
    pivot["avg_temp"]   = (pivot["TMAX"] + pivot["TMIN"]) / 2
    pivot["hdd_day"]    = (65 - pivot["avg_temp"]).clip(lower=0)
    pivot["cdd_day"]    = (pivot["avg_temp"] - 65).clip(lower=0)
    pivot["year_month"] = pivot["date"].dt.to_period("M").astype(str)
    return (
        pivot.groupby("year_month")
        .agg(hdd=("hdd_day", "sum"), cdd=("cdd_day", "sum"))
        .reset_index()
    )

la_records = []
for year in range(START_YEAR, END_YEAR + 1):
    recs = pull_noaa_station("USW00023174", year)
    la_records.extend(recs)
    print(f"  {year}: {len(recs)} daily records")
    time.sleep(1)

weather = compute_hdd_cdd(la_records)
weather["ba"] = "CISO"
print(f"  Weather months: {len(weather):,}")
print()

# ── Step 3: Pull BEA GDP for California ──────────────────────────────────────
print("Step 3: Pulling BEA GDP for California...")

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
r       = requests.get(BEA_BASE, params=params, timeout=60)
records = r.json()["BEAAPI"]["Results"]["Data"]
bea_raw = pd.DataFrame(records)
bea_raw["DataValue"] = pd.to_numeric(
    bea_raw["DataValue"].str.replace(",", ""), errors="coerce"
)
ca_gdp = bea_raw[bea_raw["GeoName"] == "California"].copy()
ca_gdp["year"] = pd.to_numeric(ca_gdp["TimePeriod"], errors="coerce")
ca_gdp = ca_gdp.dropna(subset=["DataValue"])

gdp_annual = ca_gdp[["year", "DataValue"]].rename(columns={"DataValue": "gdp"})
print(f"  California GDP rows: {len(gdp_annual):,}")

# Interpolate to monthly
ca_months = month_df.copy()
ca_months = ca_months.merge(gdp_annual, on="year", how="left")
ca_months["gdp"] = ca_months["gdp"].interpolate(method="linear", limit_direction="both")
ca_months["ba"]  = "CISO"
print()

# ── Step 4: Build scaffold and merge ─────────────────────────────────────────
print("Step 4: Building panel...")

scaffold = pd.DataFrame({
    "ba":         "CISO",
    "year_month": [str(m) for m in all_months]
})

panel = scaffold.merge(demand[["year_month", "avg_demand_mwh", "n_hours"]],
                       on="year_month", how="left")
panel = panel.merge(weather[["year_month", "hdd", "cdd"]],
                    on="year_month", how="left")
panel = panel.merge(ca_months[["year_month", "gdp"]],
                    on="year_month", how="left")

panel["year"]    = pd.to_datetime(panel["year_month"]).dt.year
panel["month"]   = pd.to_datetime(panel["year_month"]).dt.month
panel["quarter"] = pd.to_datetime(panel["year_month"]).dt.quarter

# ── Step 5: Compute demand_idx and min_demand_idx ────────────────────────────
print("Step 5: Computing demand indices...")

# demand_idx — indexed to 2019 average = 100
base_demand = panel[panel["year"] == 2019]["avg_demand_mwh"].mean()
panel["demand_idx"] = (panel["avg_demand_mwh"] / base_demand * 100).round(4)

# min_demand_idx — pull from hourly EIA data
eia["year_month_str"] = eia["year_month"]
monthly_min = (
    eia.groupby("year_month_str")["mwh"]
    .min()
    .reset_index()
    .rename(columns={"year_month_str": "year_month", "mwh": "demand_min"})
)
monthly_min["year"] = pd.to_datetime(monthly_min["year_month"]).dt.year
base_min = monthly_min[monthly_min["year"] == 2019]["demand_min"].mean()
monthly_min["min_demand_idx"] = (monthly_min["demand_min"] / base_min * 100).round(4)

panel = panel.merge(monthly_min[["year_month", "demand_min", "min_demand_idx"]],
                    on="year_month", how="left")

# ── Step 6: Final column order, verify, save ─────────────────────────────────
print("Step 6: Verifying and saving...")

col_order = ["ba", "year_month", "year", "month", "quarter",
             "avg_demand_mwh", "n_hours", "hdd", "cdd", "gdp",
             "demand_idx", "demand_min", "min_demand_idx"]
panel = panel[col_order]

print(f"  Rows: {len(panel):,} (expected 84)")
for col in ["avg_demand_mwh", "hdd", "cdd", "gdp", "demand_idx", "min_demand_idx"]:
    print(f"  Missing {col}: {panel[col].isna().sum()} (expected 0)")

print()
print("── First 5 rows ─────────────────────────────────────────────────────")
print(panel.head().to_string(index=False))
print()
print("── Last 5 rows ──────────────────────────────────────────────────────")
print(panel.tail().to_string(index=False))

panel.to_csv("data/panel_caiso_comparison.csv", index=False)
print(f"\n✅ Saved: data/panel_caiso_comparison.csv")
print("Done.")