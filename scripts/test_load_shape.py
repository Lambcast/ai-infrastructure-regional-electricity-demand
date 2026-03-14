"""
test_load_shape.py
------------------
Diagnostic script — not part of the main pipeline.
Indexes load factor and minimum demand to 2019=100 by BA and plots trends.

Output:
  results/test_load_factor.png
  results/test_min_demand.png

Run from project root: python scripts/test_load_shape.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os

os.makedirs("results", exist_ok=True)

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv("data/panel_load_shape.csv")
df["year_month_dt"] = pd.to_datetime(df["year_month"])
df["year"] = df["year_month_dt"].dt.year

COLORS = {"ERCO": "#e74c3c", "MISO": "#27ae60", "PJM": "#1F3864"}
LABELS = {"ERCO": "ERCOT (Texas)", "MISO": "MISO (Southeast / Midwest)", "PJM": "PJM (Mid-Atlantic / Midwest)"}

# ── Index to 2019 = 100 ───────────────────────────────────────────────────────
base = (
    df[df["year"] == 2019]
    .groupby("ba")[["load_factor", "demand_min"]]
    .mean()
)

df = df.merge(base.rename(columns={
    "load_factor": "base_load_factor",
    "demand_min":  "base_demand_min"
}), on="ba", how="left")

df["load_factor_idx"] = df["load_factor"] / df["base_load_factor"] * 100
df["demand_min_idx"]  = df["demand_min"]  / df["base_demand_min"]  * 100

# ── Plot 1: Load factor indexed ───────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 6))

for ba in ["ERCO", "PJM", "MISO"]:
    data = df[df["ba"] == ba].sort_values("year_month_dt")
    ax.plot(data["year_month_dt"], data["load_factor_idx"],
            color=COLORS[ba], linewidth=1.8, label=LABELS[ba])

ax.axhline(100, color="black", linestyle="--", linewidth=1, alpha=0.4, label="Baseline (2019 = 100)")
ax.set_title("Load Factor Indexed to 2019 = 100\nPJM, ERCOT, MISO  |  2019–2025", fontsize=13, fontweight="bold")
ax.set_xlabel("Month", fontsize=11)
ax.set_ylabel("Load Factor Index (2019 = 100)", fontsize=11)
ax.legend(fontsize=10)
ax.grid(axis="y", linestyle="--", alpha=0.4)

plt.tight_layout()
plt.savefig("results/test_load_factor.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Saved: results/test_load_factor.png")

# ── Plot 2: Minimum demand indexed ────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 6))

for ba in ["ERCO", "PJM", "MISO"]:
    data = df[df["ba"] == ba].sort_values("year_month_dt")
    ax.plot(data["year_month_dt"], data["demand_min_idx"],
            color=COLORS[ba], linewidth=1.8, label=LABELS[ba])

ax.axhline(100, color="black", linestyle="--", linewidth=1, alpha=0.4, label="Baseline (2019 = 100)")
ax.set_title("Minimum Hourly Demand Indexed to 2019 = 100\nPJM, ERCOT, MISO  |  2019–2025", fontsize=13, fontweight="bold")
ax.set_xlabel("Month", fontsize=11)
ax.set_ylabel("Min Demand Index (2019 = 100)", fontsize=11)
ax.legend(fontsize=10)
ax.grid(axis="y", linestyle="--", alpha=0.4)

plt.tight_layout()
plt.savefig("results/test_min_demand.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Saved: results/test_min_demand.png")

print()
print("Done. Diagnostic plots saved to results/")