"""
add_min_demand_idx.py
---------------------
Adds min_demand_idx to panel_load_shape.csv.
Construction: monthly minimum hourly demand indexed to each BA's
2019 annual average minimum demand = 100. Same method as demand_idx.

Run from project root: python scripts/add_min_demand_idx.py
"""

import pandas as pd

PANEL_PATH = "data/panel_load_shape.csv"

# ── Load panel ────────────────────────────────────────────────────────────────
print("Loading panel_load_shape.csv...")
panel = pd.read_csv(PANEL_PATH)
panel["year"] = pd.to_datetime(panel["year_month"]).dt.year
print(f"  Rows: {len(panel):,}")

# ── Compute 2019 base — mean of monthly minimums within 2019 by BA ────────────
base_2019 = (
    panel[panel["year"] == 2019]
    .groupby("ba")["demand_min"]
    .mean()
    .rename("base_min_2019")
    .reset_index()
)
print(f"  2019 base min demand by BA:")
print(base_2019.to_string(index=False))

# ── Index ─────────────────────────────────────────────────────────────────────
panel = panel.merge(base_2019, on="ba", how="left")
panel["min_demand_idx"] = (panel["demand_min"] / panel["base_min_2019"] * 100).round(4)
panel = panel.drop(columns=["base_min_2019"])

# ── Verify and save ───────────────────────────────────────────────────────────
print(f"\n  Rows: {len(panel):,} (expected 252)")
print(f"  Missing min_demand_idx: {panel['min_demand_idx'].isna().sum()} (expected 0)")

print()
print("── Sample — ERCO, first 5 rows ──────────────────────────────────────")
print(panel[panel["ba"] == "ERCO"][["ba", "year_month", "demand_min", "min_demand_idx"]].head().to_string(index=False))

panel.to_csv(PANEL_PATH, index=False)
print(f"\n✅ Saved: {PANEL_PATH}")
print("Done.")