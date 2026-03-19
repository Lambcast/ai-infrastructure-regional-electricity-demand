"""
plot_did_parallel_trends.py
Reproduces the DiD parallel trends figure.
ERCOT (treated) vs average of low-exposure controls (ISNE, NYIS, SWPP).
Both indexed to 2019 annual average = 100.
X-axis starts at January 2019 to match all other paper figures.

Reads:  data/panel_expanded.csv
Saves:  outputs/did_parallel_trends.png

Run from project root:
    python scripts/plot_did_parallel_trends.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# ─── Step 1: Load data ────────────────────────────────────────────────────────
print("Step 1: Loading panel_expanded.csv")
df = pd.read_csv("data/panel_expanded.csv")
df["date"] = pd.to_datetime(df["year_month"])
print(f"  Rows: {len(df)}, BAs: {df['ba'].unique().tolist()}")

# ─── Step 2: Index demand to 2019 annual average = 100 per BA ────────────────
print("Step 2: Indexing demand")
base = (df[df["year"] == 2019]
        .groupby("ba")["avg_demand_mwh"]
        .mean()
        .rename("base_2019"))
df = df.merge(base, on="ba")
df["demand_idx"] = df["avg_demand_mwh"] / df["base_2019"] * 100

# ─── Step 3: Build ERCOT and control series ───────────────────────────────────
print("Step 3: Building series")
ercot = df[df["ba"] == "ERCO"].sort_values("date").copy()

# Low-exposure controls — average across ISNE, NYIS, SWPP
controls = (df[df["ba"].isin(["ISNE", "NYIS", "SWPP"])]
            .groupby("date")["demand_idx"]
            .mean()
            .reset_index()
            .sort_values("date"))

print(f"  ERCOT rows: {len(ercot)}")
print(f"  Control avg rows: {len(controls)}")

treatment_date = pd.Timestamp("2023-05-01")

# ─── Step 4: Build figure ────────────────────────────────────────────────────
print("Step 4: Building figure")

fig, ax = plt.subplots(figsize=(11, 6))

# ERCOT — red solid
ax.plot(ercot["date"], ercot["demand_idx"],
        color="#B41A1A", linewidth=2.0, linestyle="-",
        label="ERCOT (treated)", zorder=3)

# Low-exposure controls — dark blue dashed
ax.plot(controls["date"], controls["demand_idx"],
        color="#1F3D6B", linewidth=1.8, linestyle="--",
        label="Low-exposure controls (ISNE, NYIS, SWPP)", zorder=3)

# Treatment date vertical line — red dotted
ax.axvline(treatment_date, color="#CC0000", linewidth=1.2,
           linestyle="dotted", zorder=2)

# Horizontal grid lines (light blue, matching original)
ax.yaxis.grid(True, color="#C5DCF0", linewidth=0.7, zorder=1)
ax.set_axisbelow(True)

# Axes
ax.set_xlim(pd.Timestamp("2019-01-01"), pd.Timestamp("2026-01-01"))
ax.set_ylim(78, 162)
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("Jan %Y"))
ax.tick_params(axis="x", labelsize=9.5, rotation=0)
ax.tick_params(axis="y", labelsize=9.5)
ax.set_ylabel("Average Demand Index (2019 = 100)", fontsize=10.5)

# Spines — keep left and bottom only
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Title — two lines, no separate text call
ax.set_title(
    "DiD Parallel Trends \u2014 ERCOT vs Low-Exposure Controls\n"
    "Treatment date: May 2023 (Bai-Perron break)",
    fontsize=12, fontweight="bold", pad=10,
    linespacing=1.6
)

# Legend — below the plot, matching original style
ax.legend(
    loc="upper center",
    bbox_to_anchor=(0.5, -0.10),
    ncol=2,
    fontsize=10,
    frameon=True,
    framealpha=1.0,
    edgecolor="#CCCCCC",
)

# Notes
fig.text(
    0.12, -0.04,
    "Low-exposure BAs classified by cumulative 100MW+ LBNL queue filings.\n"
    "Red dotted line: Bai-Perron structural break 2023m5 (UDmax\u202f=\u202f35.39).",
    fontsize=8.5, color="#444444", va="top"
)

plt.tight_layout(rect=[0, 0.05, 1, 1])

# ─── Step 5: Save ────────────────────────────────────────────────────────────
print("\nStep 5: Saving")
os.makedirs("outputs", exist_ok=True)
out_path = "outputs/did_parallel_trends.png"
plt.savefig(out_path, dpi=300, bbox_inches="tight",
            facecolor="white", edgecolor="none")
plt.close()
print(f"  Saved to {out_path}")
print("\nDone.")