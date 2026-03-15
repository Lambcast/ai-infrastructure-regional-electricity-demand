"""
caiso_diagnostic.py
-------------------
Pulls CAISO (CISO) monthly average hourly demand from EIA API
and plots indexed demand alongside ERCO, PJM, and MISO.
Diagnostic only — not part of main pipeline.

Output: outputs/caiso_demand_diagnostic.png
Run from project root: python scripts/caiso_diagnostic.py
"""

import os
import requests
import time
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()
API_KEY  = os.getenv("EIA_API_KEY")
BASE_URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
os.makedirs("outputs", exist_ok=True)

# ── Step 1: Pull CISO demand from EIA ────────────────────────────────────────
print("Pulling CAISO (CISO) demand from EIA...")

all_records = []
for year in range(2019, 2026):
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

ciso = pd.DataFrame(all_records)
ciso = ciso.rename(columns={"period": "datetime", "value": "mwh"})
ciso["datetime"]   = pd.to_datetime(ciso["datetime"])
ciso["mwh"] = pd.to_numeric(ciso["mwh"], errors="coerce")
ciso["year_month"] = ciso["datetime"].dt.to_period("M")
ciso["region"]     = "CISO"
print(f"  Total CISO rows: {len(ciso):,}")
print()

# ── Step 2: Aggregate to monthly ──────────────────────────────────────────────
print("Aggregating to monthly...")

ciso_monthly = (
    ciso.groupby("year_month")["mwh"]
    .mean()
    .reset_index()
    .rename(columns={"mwh": "avg_demand_mwh"})
)
ciso_monthly["ba"]   = "CISO"
ciso_monthly["year"] = ciso_monthly["year_month"].dt.year

# ── Step 3: Load existing panel for ERCO, PJM, MISO ──────────────────────────
print("Loading existing panel...")

panel = pd.read_csv("data/panel_with_controls.csv")
panel["year_month"] = pd.to_datetime(panel["year_month"]).dt.to_period("M")

# ── Step 4: Index all four BAs to 2019 average = 100 ─────────────────────────
print("Indexing to 2019 = 100...")

def index_to_2019(df, ba_col, ym_col, val_col):
    df["year"] = df[ym_col].dt.year
    base = df[df["year"] == 2019].groupby(ba_col)[val_col].mean()
    df["idx"] = df.apply(lambda r: r[val_col] / base[r[ba_col]] * 100, axis=1)
    return df

panel = index_to_2019(panel, "ba", "year_month", "avg_demand_mwh")
ciso_monthly = index_to_2019(ciso_monthly, "ba", "year_month", "avg_demand_mwh")

# ── Step 5: Plot ──────────────────────────────────────────────────────────────
print("Building plot...")

COLORS = {
    "ERCO": "#e74c3c",
    "MISO": "#27ae60",
    "PJM":  "#1F3864",
    "CISO": "#8e44ad",
}
LABELS = {
    "ERCO": "ERCOT (Texas)",
    "MISO": "MISO (Southeast / Midwest)",
    "PJM":  "PJM (Mid-Atlantic / Midwest)",
    "CISO": "CAISO (California)",
}

fig, ax = plt.subplots(figsize=(13, 6))

for ba in ["ERCO", "MISO", "PJM"]:
    data = panel[panel["ba"] == ba].sort_values("year_month")
    ax.plot(data["year_month"].dt.to_timestamp(), data["idx"],
            color=COLORS[ba], linewidth=2.0, label=LABELS[ba])

ciso_plot = ciso_monthly.sort_values("year_month")
ax.plot(ciso_plot["year_month"].dt.to_timestamp(), ciso_plot["idx"],
        color=COLORS["CISO"], linewidth=2.0, linestyle="--", label=LABELS["CISO"])

ax.axhline(100, color="black", linestyle="--", linewidth=1, alpha=0.4,
           label="Baseline (2019 = 100)")
ax.set_title("Indexed Electricity Demand Growth — CAISO vs ERCO, PJM, MISO\n2019 = 100",
             fontsize=13, fontweight="bold")
ax.set_xlabel("Month", fontsize=11)
ax.set_ylabel("Demand Index (2019 = 100)", fontsize=11)
ax.legend(fontsize=10)
ax.grid(axis="y", linestyle="--", alpha=0.4)

plt.tight_layout()
plt.savefig("outputs/caiso_demand_diagnostic.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Saved: outputs/caiso_demand_diagnostic.png")
print()
print("Done.")
