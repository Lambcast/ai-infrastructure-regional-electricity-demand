"""
pull_controls.py
----------------
Pulls weather (HDD/CDD) and GDP controls for the AI Infrastructure &
Regional Electricity Demand project and merges them onto the analysis panel.

Sources:
  - NOAA NCEI Climate Data Online API  (daily temperature → monthly HDD/CDD)
  - BEA Regional Accounts API          (annual state GDP → monthly BA GDP)

Target BAs:
  Primary (regression):  ERCO, PJM, MISO
  Expanded (synthetic control donor pool): ISONE, NYISO, SPP

Output:
  - data/weather_controls.csv       (ba, year_month, hdd, cdd)
  - data/gdp_controls.csv           (ba, year_month, gdp)
  - data/panel_with_controls.csv    (panel_base.csv + weather + GDP)

Run from project root: python scripts/pull_controls.py

Notes:
  - HDD = sum of max(65 - avg_daily_temp, 0) across days in month
  - CDD = sum of max(avg_daily_temp - 65, 0) across days in month
  - Annual GDP is linearly interpolated to monthly frequency
  - States are weighted by their share of BA total GDP
"""

import os
import time
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

NOAA_KEY = os.getenv("NOAA_API_KEY")
BEA_KEY  = os.getenv("BEA_API_KEY")

os.makedirs("data",    exist_ok=True)
os.makedirs("outputs", exist_ok=True)

# ── Config ────────────────────────────────────────────────────────────────────

START_YEAR = 2019
END_YEAR   = 2025

# Representative NOAA stations by BA
STATIONS = {
    "ERCO":  "USW00003927",   # Dallas-Fort Worth
    "MISO":  "USW00094846",   # Chicago O'Hare
    "PJM":   "USW00013739",   # Philadelphia
    "ISONE": "USW00014739",   # Boston Logan
    "NYISO": "USW00094789",   # New York JFK
    "SPP":   "USW00013967",   # Oklahoma City
}

# BEA state-to-BA mapping
BA_STATES = {
    "ERCO":  ["TX"],
    "MISO":  ["IL", "IN", "MI", "MN", "MO", "WI"],
    "PJM":   ["DE", "IL", "IN", "MD", "MI", "NJ", "NC", "OH", "PA", "TN", "VA", "WV", "DC"],
    "ISONE": ["CT", "ME", "MA", "NH", "RI", "VT"],
    "NYISO": ["NY"],
    "SPP":   ["KS", "NE", "OK", "ND", "SD"],
}

# Full state name to FIPS abbreviation map (BEA uses full names)
STATE_ABBREV = {
    "Connecticut": "CT", "Maine": "ME", "Massachusetts": "MA",
    "New Hampshire": "NH", "Rhode Island": "RI", "Vermont": "VT",
    "New York": "NY", "Kansas": "KS", "Nebraska": "NE",
    "Oklahoma": "OK", "North Dakota": "ND", "South Dakota": "SD",
    "Texas": "TX", "Illinois": "IL", "Indiana": "IN",
    "Michigan": "MI", "Minnesota": "MN", "Missouri": "MO",
    "Wisconsin": "WI", "Delaware": "DE", "Maryland": "MD",
    "New Jersey": "NJ", "North Carolina": "NC", "Ohio": "OH",
    "Pennsylvania": "PA", "Tennessee": "TN", "Virginia": "VA",
    "West Virginia": "WV", "District of Columbia": "DC",
}

# ── Step 1: Pull NOAA daily temperature data ──────────────────────────────────
print("Step 1: Pulling NOAA weather data...")

NOAA_BASE = "https://www.ncei.noaa.gov/cdo-web/api/v2/data"

def pull_noaa_station(station_id, year):
    """Pull daily TMAX and TMIN for one station and year."""
    headers = {"token": NOAA_KEY}
    params = {
        "datasetid":  "GHCND",
        "stationid":  f"GHCND:{station_id}",
        "datatypeid": "TMAX,TMIN",
        "startdate":  f"{year}-01-01",
        "enddate":    f"{year}-12-31",
        "units":      "standard",
        "limit":      1000,
        "offset":     1,
    }
    all_records = []
    while True:
        try:
            r = requests.get(NOAA_BASE, headers=headers, params=params, timeout=60)
            if r.status_code == 429:
                print(f"    Rate limited, waiting 30s...")
                time.sleep(30)
                continue
            if r.status_code == 503:
                print(f"    503 error, waiting 60s and retrying...")
                time.sleep(60)
                continue
            if r.status_code != 200:
                print(f"    Error {r.status_code} for {station_id} {year}")
                return []
            data = r.json()
            results = data.get("results", [])
            all_records.extend(results)
            meta = data.get("metadata", {}).get("resultset", {})
            count  = meta.get("count", 0)
            offset = meta.get("offset", 1)
            limit  = meta.get("limit", 1000)
            if offset + limit - 1 >= count:
                break
            params["offset"] = offset + limit
            time.sleep(0.5)
        except Exception as e:
            print(f"    Exception: {e}, retrying in 15s...")
            time.sleep(15)
    return all_records

def compute_hdd_cdd(records):
    """
    Convert daily TMAX/TMIN records to monthly HDD and CDD.
    avg_daily_temp = (TMAX + TMIN) / 2, values are in tenths of degrees F.
    HDD = max(65 - avg_temp, 0), CDD = max(avg_temp - 65, 0)
    """
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df = df[df["datatype"].isin(["TMAX", "TMIN"])].copy()
    df["date"]  = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")  # already in °F (units=standard)

    # Pivot to get TMAX and TMIN columns
    pivot = df.pivot_table(index="date", columns="datatype", values="value").reset_index()
    pivot.columns.name = None

    if "TMAX" not in pivot.columns or "TMIN" not in pivot.columns:
        return pd.DataFrame()

    pivot = pivot.dropna(subset=["TMAX", "TMIN"])
    pivot["avg_temp"] = (pivot["TMAX"] + pivot["TMIN"]) / 2
    pivot["hdd_day"]    = (65 - pivot["avg_temp"]).clip(lower=0)
    pivot["cdd_day"]    = (pivot["avg_temp"] - 65).clip(lower=0)
    pivot["year_month"] = pivot["date"].dt.to_period("M").astype(str)

    monthly = (
        pivot.groupby("year_month")
        .agg(hdd=("hdd_day", "sum"), cdd=("cdd_day", "sum"), n_days=("avg_temp", "count"))
        .reset_index()
    )
    return monthly

all_weather = []

for ba, station_id in STATIONS.items():
    print(f"  Pulling {ba} ({station_id})...")
    ba_records = []
    for year in range(START_YEAR, END_YEAR + 1):
        records = pull_noaa_station(station_id, year)
        ba_records.extend(records)
        print(f"    {year}: {len(records)} daily records")
        time.sleep(1)

    monthly = compute_hdd_cdd(ba_records)
    if len(monthly) == 0:
        print(f"    ⚠️  No data returned for {ba}")
        continue

    monthly["ba"] = ba
    all_weather.append(monthly)
    print(f"    ✅ {len(monthly)} months computed for {ba}")

weather = pd.concat(all_weather, ignore_index=True)
weather = weather[["ba", "year_month", "hdd", "cdd"]].copy()
weather.to_csv("data/weather_controls.csv", index=False)
print(f"\n✅ Weather saved: data/weather_controls.csv ({len(weather):,} rows)")
print()

# ── Step 2: Pull BEA state GDP data ──────────────────────────────────────────
print("Step 2: Pulling BEA regional GDP data...")

BEA_BASE = "https://apps.bea.gov/api/data"

def pull_bea_gdp():
    """Pull annual real GDP by state from BEA SAGDP table."""
    params = {
        "UserID":     BEA_KEY,
        "method":     "GetData",
        "datasetname":"Regional",
        "TableName":  "SAGDP9",
        "LineCode":   "1",
        "GeoFips":    "STATE",
        "Year":       ",".join(str(y) for y in range(START_YEAR, END_YEAR + 1)),
        "ResultFormat":"JSON",
    }
    try:
        r = requests.get(BEA_BASE, params=params, timeout=60)
        data = r.json()
        records = data["BEAAPI"]["Results"]["Data"]
        df = pd.DataFrame(records)
        return df
    except Exception as e:
        print(f"  BEA API error: {e}")
        return pd.DataFrame()

bea_raw = pull_bea_gdp()
print(f"  BEA raw rows: {len(bea_raw):,}")
print(f"  Columns: {bea_raw.columns.tolist()}")

# Clean BEA data
bea_raw["DataValue"] = pd.to_numeric(
    bea_raw["DataValue"].str.replace(",", ""), errors="coerce"
)
bea_raw = bea_raw.dropna(subset=["DataValue"])
bea_raw["state_abbrev"] = bea_raw["GeoName"].map(STATE_ABBREV)
bea_raw = bea_raw.dropna(subset=["state_abbrev"])
bea_raw["year"] = pd.to_numeric(bea_raw["TimePeriod"], errors="coerce")

# Aggregate to BA level — weight states by GDP share within BA
gdp_annual_rows = []

for ba, states in BA_STATES.items():
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

# Interpolate annual GDP to monthly frequency
all_months = pd.period_range(start=f"{START_YEAR}-01", end=f"{END_YEAR}-12", freq="M")
month_df   = pd.DataFrame({"year_month": all_months.astype(str)})
month_df["year"] = pd.to_datetime(month_df["year_month"]).dt.year

gdp_monthly_rows = []

for ba in gdp_annual["ba"].unique():
    ba_annual = gdp_annual[gdp_annual["ba"] == ba].sort_values("year")
    ba_months = month_df.copy()
    ba_months = ba_months.merge(ba_annual[["year", "gdp"]], on="year", how="left")

    # Linear interpolation within each year using month position
    # Assign annual value to July (mid-year), then interpolate
    ba_months["gdp"] = ba_months["gdp"].interpolate(method="linear", limit_direction="both")
    ba_months["ba"]  = ba
    gdp_monthly_rows.append(ba_months[["ba", "year_month", "gdp"]])

gdp_monthly = pd.concat(gdp_monthly_rows, ignore_index=True)
gdp_monthly.to_csv("data/gdp_controls.csv", index=False)
print(f"✅ GDP saved: data/gdp_controls.csv ({len(gdp_monthly):,} rows)")
print()

# ── Step 3: Merge controls onto panel ────────────────────────────────────────
print("Step 3: Merging controls onto panel_base.csv...")

panel = pd.read_csv("data/panel_base.csv")
print(f"  Panel rows before merge: {len(panel):,}")

panel = panel.merge(weather, on=["ba", "year_month"], how="left")
panel = panel.merge(gdp_monthly, on=["ba", "year_month"], how="left")

print(f"  Panel rows after merge:  {len(panel):,}")
print(f"  Missing HDD:  {panel['hdd'].isna().sum()}")
print(f"  Missing CDD:  {panel['cdd'].isna().sum()}")
print(f"  Missing GDP:  {panel['gdp'].isna().sum()}")

panel.to_csv("data/panel_with_controls.csv", index=False)
print(f"✅ Saved: data/panel_with_controls.csv")
print()

# ── Step 4: Verification plots ────────────────────────────────────────────────
print("Step 4: Building verification plots...")

primary_bas = ["ERCO", "MISO", "PJM"]
colors = {"ERCO": "#e74c3c", "MISO": "#27ae60", "PJM": "#1F3864"}
panel["year_month_dt"] = pd.to_datetime(panel["year_month"])
primary = panel[panel["ba"].isin(primary_bas)].copy()

fig, axes = plt.subplots(3, 1, figsize=(12, 12))
fig.suptitle("Control Variables Verification\nPJM, ERCOT, MISO  |  2019–2025",
             fontsize=13, fontweight="bold")

for ba, grp in primary.groupby("ba"):
    axes[0].plot(grp["year_month_dt"], grp["hdd"], label=ba,
                 color=colors[ba], linewidth=1.8)
    axes[1].plot(grp["year_month_dt"], grp["cdd"], label=ba,
                 color=colors[ba], linewidth=1.8)
    axes[2].plot(grp["year_month_dt"], grp["gdp"], label=ba,
                 color=colors[ba], linewidth=1.8)

for ax, title, ylabel in zip(
    axes,
    ["Heating Degree Days (HDD)", "Cooling Degree Days (CDD)", "Real GDP (millions $)"],
    ["HDD", "CDD", "GDP"]
):
    ax.set_title(title, fontsize=11)
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

plt.tight_layout()
plt.savefig("outputs/controls_verification.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Saved: outputs/controls_verification.png")
print()
print("Done. panel_with_controls.csv is ready for Stata.")