"""
plot_inspace_placebos_mindemand.py
Produces the in-space placebo distribution figure for the SC-3 minimum
demand specification. Legend placed below the figure, outside the axes.

Reads:
    results/sc3_mindemand_results.csv      -- ERCOT gap
    results/mindemand_placebo_isne.csv     -- ISNE placebo
    results/mindemand_placebo_nyis.csv     -- NYIS placebo
    results/mindemand_placebo_swpp.csv     -- SWPP placebo

Saves:
    outputs/inspace_placebos_mindemand_sc3.png

Run from project root:
    python scripts/plot_inspace_placebos_mindemand.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# ─── Step 1: Load data ────────────────────────────────────────────────────────
print("Step 1: Loading data")

def stata_tm_to_date(tm):
    year  = 1960 + int(tm) // 12
    month = int(tm) % 12 + 1
    return pd.Timestamp(year=year, month=month, day=1)

def load_sc(path):
    df = pd.read_csv(path)
    df = df[df["_Y_treated"].notna() & df["_time"].notna()].copy()
    df = df.sort_values("_time").reset_index(drop=True)
    df["date"] = df["_time"].apply(stata_tm_to_date)
    df["gap"]  = df["_Y_treated"] - df["_Y_synthetic"]
    return df

ercot = load_sc("results/sc3_mindemand_results.csv")
p_isne = load_sc("results/mindemand_placebo_isne.csv")
p_nyis = load_sc("results/mindemand_placebo_nyis.csv")
p_swpp = load_sc("results/mindemand_placebo_swpp.csv")

treatment_tm   = 760
treatment_date = stata_tm_to_date(treatment_tm)

print(f"  ERCOT rows: {len(ercot)}")
print(f"  Treatment date: {treatment_date.strftime('%Y-%m')}")

# ─── Step 2: Build figure ────────────────────────────────────────────────────
print("\nStep 2: Building figure")

fig, ax = plt.subplots(figsize=(10, 5.5))

# Placebo gaps — gray, behind ERCOT
placebo_data = [
    ("ISNE placebo", p_isne),
    ("NYIS placebo", p_nyis),
    ("SWPP placebo", p_swpp),
]
for label, pdf in placebo_data:
    ax.plot(pdf["date"], pdf["gap"],
            color="gray", linewidth=1.1, alpha=0.6,
            label=label, zorder=2)

# ERCOT gap — black, on top
ax.plot(ercot["date"], ercot["gap"],
        color="black", linewidth=2.0,
        label="ERCOT (treated)", zorder=3)

# Reference lines
ax.axhline(0, color="#999999", linewidth=0.9, linestyle="--", zorder=1)
ax.axvline(treatment_date, color="#CC0000", linewidth=1.1,
           linestyle="dotted", zorder=2)

# Light grid
ax.yaxis.grid(True, color="#DDDDDD", linewidth=0.6, zorder=0)
ax.set_axisbelow(True)

# Axes
date_min = ercot["date"].min()
date_max = ercot["date"].max()
ax.set_xlim(date_min, date_max)
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("Jan %Y"))
ax.tick_params(axis="both", labelsize=9.5)
ax.set_ylabel("Gap (index points, 2019=100)", fontsize=10.5)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Title
ax.set_title(
    "In-Space Placebo Tests: SC-3 Specification\n"
    "Minimum Hourly Demand",
    fontsize=12, fontweight="bold", pad=8
)

# Legend — below the plot, outside axes, ERCOT first
handles, labels = ax.get_legend_handles_labels()
# Reorder so ERCOT is first
order = [labels.index("ERCOT (treated)")] + \
        [i for i, l in enumerate(labels) if l != "ERCOT (treated)"]
ax.legend(
    [handles[i] for i in order],
    [labels[i] for i in order],
    loc="upper center",
    bbox_to_anchor=(0.5, -0.14),
    ncol=4,
    fontsize=9.5,
    frameon=True,
    framealpha=1.0,
    edgecolor="#CCCCCC",
)

# Notes
fig.text(
    0.12, -0.08,
    "Black = ERCOT. Gray = donor BAs treated as placebo units. "
    "Vertical line = treatment date (2023m5).\n"
    "Placebos with pre-treatment RMSPE > 2\u00d7 ERCOT excluded from p-value calculation.",
    fontsize=8.5, color="#444444", va="top"
)

plt.tight_layout(rect=[0, 0.08, 1, 1])

# ─── Step 3: Save ────────────────────────────────────────────────────────────
print("\nStep 3: Saving")
os.makedirs("outputs", exist_ok=True)
out_path = "outputs/inspace_placebos_mindemand_sc3.png"
plt.savefig(out_path, dpi=300, bbox_inches="tight",
            facecolor="white", edgecolor="none")
plt.close()
print(f"  Saved to {out_path}")
print("\nDone.")