"""
plot_ercot_caiso_comparison.py
Task 4: Side-by-side comparison of ERCOT and CAISO synthetic control gaps.

Reads:
    results/sc3_mindemand_results.csv
    results/caiso_sc2_results.csv
    results/caiso_sc_mindemand_results.csv

Saves:
    outputs/ercot_caiso_comparison.png

Run from project root:
    python scripts/plot_ercot_caiso_comparison.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# ─── Step 1: Load data ────────────────────────────────────────────────────────
print("Step 1: Loading SC results")

def load_sc(path):
    df = pd.read_csv(path)
    df = df[df["_Y_treated"].notna() & df["_time"].notna()].copy()
    df = df.sort_values("_time").reset_index(drop=True)
    df["gap"] = df["_Y_treated"] - df["_Y_synthetic"]
    return df

def stata_tm_to_date(tm):
    year  = 1960 + int(tm) // 12
    month = int(tm) % 12 + 1
    return pd.Timestamp(year=year, month=month, day=1)

ercot_min = load_sc("results/sc3_mindemand_results.csv")
caiso_avg = load_sc("results/caiso_sc2_results.csv")
caiso_min = load_sc("results/caiso_sc_mindemand_results.csv")

for df in [ercot_min, caiso_avg, caiso_min]:
    df["date"] = df["_time"].apply(stata_tm_to_date)

treatment_date = stata_tm_to_date(760)
treatment_tm   = 760

ercot_post_mean = ercot_min[ercot_min["_time"] >= treatment_tm]["gap"].mean()
caiso_avg_post  = caiso_avg[caiso_avg["_time"] >= treatment_tm]["gap"].mean()

print(f"  ERCOT min demand post-treatment mean gap: {ercot_post_mean:+.1f}")
print(f"  CAISO avg demand post-treatment mean gap: {caiso_avg_post:+.1f}")

# ─── Step 2: Build figure ────────────────────────────────────────────────────
print("\nStep 2: Building figure")

fig, axes = plt.subplots(
    2, 2, figsize=(12, 7.5),
    gridspec_kw={"height_ratios": [2, 1], "hspace": 0.08, "wspace": 0.12}
)

treat_color = "#CC0000"
line_color  = "black"
date_min    = ercot_min["date"].min()
date_max    = ercot_min["date"].max()

def format_ax(ax, show_xlabel=False):
    ax.axvline(treatment_date, color=treat_color, linewidth=1.1,
               linestyle="dotted", zorder=2)
    ax.axvspan(treatment_date, date_max, alpha=0.04, color="gray", zorder=1)
    ax.set_xlim(date_min, date_max)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=8.5)
    if not show_xlabel:
        ax.tick_params(axis="x", labelbottom=False)

# ── Top-left: ERCOT actual vs synthetic ──────────────────────────────────────
ax = axes[0, 0]
ax.plot(ercot_min["date"], ercot_min["_Y_treated"],
        color=line_color, linewidth=1.8, label="ERCOT (actual)", zorder=3)
ax.plot(ercot_min["date"], ercot_min["_Y_synthetic"],
        color=line_color, linewidth=1.3, linestyle="--",
        label="Synthetic ERCOT", zorder=3)
format_ax(ax)
ax.set_ylabel("Min. Demand Index (2019 = 100)", fontsize=9)
ax.set_ylim(65, 175)
ax.set_title("ERCOT (Texas \u2014 Deregulated)", fontsize=10, fontweight="bold", pad=6)
ax.legend(loc="upper left", fontsize=8, frameon=False)

# ── Top-right: CAISO actual vs synthetic ─────────────────────────────────────
ax = axes[0, 1]
ax.plot(caiso_avg["date"], caiso_avg["_Y_treated"],
        color=line_color, linewidth=1.8, label="CAISO (actual)", zorder=3)
ax.plot(caiso_avg["date"], caiso_avg["_Y_synthetic"],
        color=line_color, linewidth=1.3, linestyle="--",
        label="Synthetic CAISO", zorder=3)
format_ax(ax)
ax.set_ylabel("Avg. Demand Index (2019 = 100)", fontsize=9)
ax.set_ylim(65, 175)
ax.set_title("CAISO (California \u2014 Regulated)", fontsize=10, fontweight="bold", pad=6)
ax.legend(loc="upper left", fontsize=8, frameon=False)

# ── Bottom-left: ERCOT gap ────────────────────────────────────────────────────
ax = axes[1, 0]
ax.plot(ercot_min["date"], ercot_min["gap"],
        color=line_color, linewidth=1.6, zorder=3)
ax.axhline(0, color="gray", linewidth=0.8, linestyle="--", zorder=1)

# Post-treatment mean reference line — only in post-treatment window
ax.axhline(ercot_post_mean,
           xmin=(treatment_date - date_min).days / (date_max - date_min).days,
           color="#888888", linewidth=0.9, linestyle=(0, (5, 3)),
           zorder=2, alpha=0.9)

# Annotation in bottom-right corner of the panel — clear of data
ax.text(
    0.97, 0.08,
    f"Post-treatment mean: +{ercot_post_mean:.1f} pts",
    transform=ax.transAxes,
    fontsize=7.5, color="#555555",
    ha="right", va="bottom",
    style="italic",
)

format_ax(ax, show_xlabel=True)
ax.set_ylabel("Gap (index points)", fontsize=9)
ax.set_ylim(-35, 80)

# ── Bottom-right: CAISO gap ───────────────────────────────────────────────────
ax = axes[1, 1]

# Avg demand gap — solid, primary
ax.plot(caiso_avg["date"], caiso_avg["gap"],
        color=line_color, linewidth=1.6,
        label="Avg. demand gap", zorder=3)

# Min demand gap — muted, reference only (RMSPE = 23.4, poor fit)
ax.plot(caiso_min["date"], caiso_min["gap"],
        color="gray", linewidth=0.9, linestyle=(0, (4, 2)),
        alpha=0.45, label="Min. demand gap\u2020",
        zorder=2)

ax.axhline(0, color="gray", linewidth=0.8, linestyle="--", zorder=1)

# Annotation in bottom-right corner — same position as ERCOT panel
ax.text(
    0.97, 0.08,
    f"Post-treatment mean: {caiso_avg_post:+.1f} pts",
    transform=ax.transAxes,
    fontsize=7.5, color="#555555",
    ha="right", va="bottom",
    style="italic",
)

format_ax(ax, show_xlabel=True)
ax.set_ylabel("Gap (index points)", fontsize=9)
ax.set_ylim(-35, 80)
ax.legend(loc="upper left", fontsize=7.5, frameon=False)

# ── Figure title ──────────────────────────────────────────────────────────────
fig.suptitle(
    "Figure 8. Synthetic Control Gap \u2014 ERCOT vs. CAISO\n"
    "Deregulated vs. Regulated Market Response to Data Center Investment",
    fontsize=11, fontweight="bold", y=1.01
)

# ── Notes ─────────────────────────────────────────────────────────────────────
note_text = (
    "Notes: ERCOT outcome is minimum hourly demand; CAISO primary outcome is average demand, "
    "both indexed to 2019 average\u202f=\u202f100. "
    "Donor pool for both: ISNE, NYIS, SWPP (low data center exposure by LBNL queue filings). "
    "Dotted red vertical line marks treatment date (2023m5); Bai-Perron UDmax\u202f=\u202f35.39 for ERCOT. "
    "CAISO Bai-Perron UDmax\u202f=\u202f4.00 \u2014 fails to reject null of no structural break. "
    "ERCOT post-treatment min. demand gap: +34.8 index points (mean). "
    "CAISO post-treatment avg. demand gap: \u22124.0 index points (mean). "
    "\u2020CAISO min. demand RMSPE\u202f=\u202f23.4; poor pre-treatment fit, shown for reference only."
)
fig.text(0.5, -0.07, note_text, ha="center", fontsize=7.5, style="italic", wrap=True)

plt.tight_layout()

# ─── Step 3: Save ────────────────────────────────────────────────────────────
print("\nStep 3: Saving")
os.makedirs("outputs", exist_ok=True)
out_path = "outputs/ercot_caiso_comparison.png"
plt.savefig(out_path, dpi=300, bbox_inches="tight",
            facecolor="white", edgecolor="none")
plt.close()
print(f"  Saved to {out_path}")
print("\nDone.")