"""
plot_sc3_energizations.py
--------------------------
Plots SC3 synthetic control gap with known ERCOT data center
energization event markers overlaid.

Reads: results/sc3_mindemand_results.dta
Output: outputs/sc3_mindemand_with_energizations.png

Stata monthly date conversion:
  _time is months since January 1960
  _time=708 → January 2019
  _time=760 → May 2023 (treatment date)

Run from project root: python scripts/plot_sc3_energizations.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pyreadstat
import os

os.makedirs("outputs", exist_ok=True)

# ── Load SC3 results ──────────────────────────────────────────────────────────
print("Loading SC3 results...")
df, meta = pyreadstat.read_dta("results/sc3_mindemand_results.dta")
print(f"  Columns: {df.columns.tolist()}")
print(f"  Rows: {len(df)}")
print(df.head())

# ── Convert Stata monthly date to calendar date ───────────────────────────────
# _time = months since January 1960
df["date"] = pd.to_datetime("1960-01-01") + pd.to_timedelta(
    df["_time"] * 30.4375, unit="D"
)
df["date"] = df["date"].dt.to_period("M").dt.to_timestamp()

# ── Compute gap ───────────────────────────────────────────────────────────────
df["gap"] = df["_Y_treated"] - df["_Y_synthetic"]

# ── Plot ──────────────────────────────────────────────────────────────────────
print("Building plot...")

fig, ax = plt.subplots(figsize=(13, 6))

ax.plot(df["date"], df["gap"], color="#1F3864", linewidth=2.0,
        label="ERCOT gap (actual − synthetic)")
ax.axhline(0, color="black", linestyle="--", linewidth=1, alpha=0.5)

# ── Treatment date — May 2023 ─────────────────────────────────────────────────
treatment_date = pd.Timestamp("2023-05-01")
ax.axvline(treatment_date, color="black", linestyle="--", linewidth=1.5,
           label="Treatment date (May 2023)")

# ── Energization events — staggered vertical label positions ─────────────────
energizations = [
    ("QTS Irving",             "2023-04-01"),
    ("Microsoft\nSan Antonio", "2023-06-01"),
    ("Google\nMidlothian",     "2023-10-01"),
    ("Meta\nFort Worth",       "2024-01-01"),
    ("Switch\nSan Antonio",    "2024-06-01"),
]

colors_e   = ["#8e44ad", "#e67e22", "#e74c3c", "#27ae60", "#2980b9"]
y_positions = [62, 55, 62, 55, 62]

for (label, date), color, ypos in zip(energizations, colors_e, y_positions):
    dt = pd.Timestamp(date)
    ax.axvline(dt, color=color, linestyle="--", linewidth=1.2, alpha=0.8)
    ax.text(dt + pd.Timedelta(days=10), ypos,
            label, fontsize=7.5, color=color, ha="left", va="top",
            rotation=90, alpha=0.95)

# ── Labels and formatting ─────────────────────────────────────────────────────
ax.set_title(
    "SC3 Synthetic Control Gap — ERCOT Min Demand\nWith Known Data Center Energization Events",
    fontsize=13, fontweight="bold"
)
ax.set_xlabel("Month", fontsize=11)
ax.set_ylabel("Gap: Actual − Synthetic Min Demand (MWh)", fontsize=10)
ax.legend(fontsize=9)
ax.grid(axis="y", linestyle="--", alpha=0.4)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

plt.tight_layout()
plt.savefig("outputs/sc3_mindemand_with_energizations.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Saved: outputs/sc3_mindemand_with_energizations.png")
print("Done.")