import pandas as pd

# ── Check 1: CISO in EIA file ─────────────────────────────────────────────────
print("── EIA file BA identifiers ──────────────────────────────────────────")
eia = pd.read_csv("data/eia_demand_2018_2025.csv")
print(f"  All BAs: {sorted(eia['region'].unique().tolist())}")

ciso = eia[(eia["region"] == "CISO") & (eia["data_type"] == "D")]
if len(ciso) == 0:
    print("  CISO: NOT FOUND")
else:
    ciso["year"] = pd.to_datetime(ciso["datetime"]).dt.year
    print(f"  CISO rows: {len(ciso):,}")
    print(f"  CISO date range: {ciso['datetime'].min()} to {ciso['datetime'].max()}")
    print(f"  CISO years: {sorted(ciso['year'].unique().tolist())}")

print()

# ── Check 2: LBL cumulative 100MW+ filings by BA ──────────────────────────────
print("── LBL cumulative 100MW+ filings 2019-2025 by BA ────────────────────")

BA_MAP = {"ERCOT": "ERCO", "PJM": "PJM", "MISO": "MISO",
          "CAISO": "CISO", "ISO-NE": "ISNE", "NYISO": "NYIS", "SPP": "SWPP"}
TARGET_REGIONS = list(BA_MAP.keys())

queue = pd.read_csv("data/lbnl_queue_data.csv")
queue = queue[queue["region"].isin(TARGET_REGIONS)].copy()
queue["ba"] = queue["region"].map(BA_MAP)
queue = queue[queue["mw1"].notna() & (queue["mw1"] >= 100)].copy()

queue["q_date_parsed"] = pd.to_datetime(
    queue["q_date"], unit="D", origin="1899-12-30", errors="coerce"
)
queue = queue[queue["q_date_parsed"].notna()].copy()
queue = queue[queue["q_date_parsed"].dt.year >= 2019].copy()
queue = queue[queue["q_date_parsed"].dt.year <= 2025].copy()

summary = (
    queue.groupby("ba")["mw1"]
    .agg(n_projects="count", total_gw=lambda x: round(x.sum() / 1000, 1))
    .reset_index()
    .sort_values("total_gw", ascending=False)
)
print(summary.to_string(index=False))