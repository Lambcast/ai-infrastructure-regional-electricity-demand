"""
plot_caiso_sc_gaps.py
Produces three CAISO synthetic control gap figures for the appendix.

  Figure B7: CAISO SC-1 — PJM + MISO donors (avg demand)
  Figure B8: CAISO SC-2 — ISNE/NYIS/SWPP donors (avg demand)
  Figure B9: CAISO SC — Minimum demand

Reads:
    results/caiso_sc1_results.csv
    results/caiso_sc2_results.csv
    results/caiso_sc_mindemand_results.csv

Saves:
    outputs/caiso_sc1_gap_plot.png
    outputs/caiso_sc2_gap_plot.png
    outputs/caiso_sc_mindemand_gap_plot.png

Run from project root:
    python scripts/plot_caiso_sc_gaps.py
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

sc1 = load_sc("results/caiso_sc1_results.csv")
sc2 = load_sc("results/caiso_sc2_results.csv")
scm = load_sc("results/caiso_sc_mindemand_results.csv")

treatment_date = stata_tm_to_date(760)  # 2023m5
treatment_tm   = 760

for name, df in [("SC-1", sc1), ("SC-2", sc2), ("Min demand", scm)]:
    post = df[df["_time"] >= treatment_tm]["gap"].mean()
    print(f"  {name} post-treatment mean gap: {post:+.1f} index points")

# ─── Step 2: Plot function ────────────────────────────────────────────────────

def make_gap_plot(df, title, note_text, out_path):
    fig, ax = plt.subplots(figsize=(9, 4.5))

    ax.plot(df["date"], df["gap"],
            color="black", linewidth=1.6, zorder=3)
    ax.axhline(0, color="#999999", linewidth=0.9,
               linestyle="--", zorder=1)
    ax.axvline(treatment_date, color="#CC0000", linewidth=1.1,
               linestyle="dotted", zorder=2)
    ax.axvspan(treatment_date, df["date"].max(),
               alpha=0.04, color="gray", zorder=1)

    # Light grid

    # Axes
    ax.set_xlim(df["date"].min(), df["date"].max())
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("Jan %Y"))
    ax.tick_params(axis="x", labelsize=9, rotation=45)
    ax.tick_params(axis="y", labelsize=9)
    ax.set_ylabel("Gap (index points, 2019=100)", fontsize=10)
    ax.set_xlabel("")   # no x-axis label

    ax.yaxis.grid(True, color="#CCCCCC", linewidth=0.5, linestyle=(0, (6, 4)), zorder=0)
    ax.xaxis.grid(True, color="#CCCCCC", linewidth=0.5, linestyle=(0, (6, 4)), zorder=0)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.set_title(title, fontsize=16, fontweight="normal", pad=8)

    # Notes below figure
    fig.text(0.12, -0.04, note_text, fontsize=8,
             color="#444444", va="top", style="italic")

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close()
    print(f"  Saved: {out_path}")

# ─── Step 3: Produce three figures ───────────────────────────────────────────
print("\nStep 2: Producing figures")
os.makedirs("outputs", exist_ok=True)

make_gap_plot(
    sc1,
    title="CAISO SC-1: Avg Demand Gap vs Synthetic",
    note_text=(
        "Donor pool: PJM + MISO (contaminated lower bound). "
        "Treatment date: 2023m5 (same as ERCOT)."
    ),
    out_path="outputs/caiso_sc1_gap_plot.png"
)

make_gap_plot(
    sc2,
    title="CAISO SC-2: Avg Demand Gap vs Synthetic",
    note_text=(
        "Donor pool: ISNE, NYIS, SWPP (low-exposure). "
        "Treatment date: 2023m5."
    ),
    out_path="outputs/caiso_sc2_gap_plot.png"
)

make_gap_plot(
    scm,
    title="CAISO SC: Min Demand Gap vs Synthetic",
    note_text=(
        "Donor pool: ISNE, NYIS, SWPP. Treatment date: 2023m5. "
        "Pre-treatment RMSPE = 23.4 \u2014 poor fit; results for reference only."
    ),
    out_path="outputs/caiso_sc_mindemand_gap_plot.png"
)

print("\nDone.")