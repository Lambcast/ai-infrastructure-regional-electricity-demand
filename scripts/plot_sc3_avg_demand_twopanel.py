"""
plot_sc3_avg_demand_twopanel.py
Produces a two-panel figure for the SC-3 average demand synthetic control result.
Matches the style of sc3_mindemand_gap_overlay.png exactly.

Top panel:  Actual vs synthetic ERCOT average demand (indexed, 2019=100)
Bottom panel: In-space placebo distribution — gray donor gaps, black ERCOT gap

Reads:
    results/sc3_idx_results.csv     -- ERCOT treated + synthetic
    results/sc3_placebo_isne.csv    -- ISNE placebo
    results/sc3_placebo_nyis.csv    -- NYIS placebo
    results/sc3_placebo_swpp.csv    -- SWPP placebo

Saves:
    outputs/sc3_avg_demand_twopanel.png

Run from project root:
    python scripts/plot_sc3_avg_demand_twopanel.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# ─── Step 1: Load data ────────────────────────────────────────────────────────
print("Step 1: Loading SC-3 average demand results")

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

main     = load_sc("results/sc3_idx_results.csv")
p_isne   = load_sc("results/sc3_placebo_isne.csv")
p_nyis   = load_sc("results/sc3_placebo_nyis.csv")
p_swpp   = load_sc("results/sc3_placebo_swpp.csv")
placebos = [("ISNE", p_isne), ("NYIS", p_nyis), ("SWPP", p_swpp)]

treatment_tm   = 760   # 2023m5
treatment_date = stata_tm_to_date(treatment_tm)

post_gap = main[main["_time"] >= treatment_tm]["gap"].mean()
pre_rmspe = (
    (main[main["_time"] < treatment_tm]["gap"] ** 2).mean() ** 0.5
)

print(f"  Main series rows: {len(main)}")
print(f"  Treatment date: {treatment_date.strftime('%Y-%m')}")
print(f"  Post-treatment mean gap: {post_gap:.1f} index points")
print(f"  Pre-treatment RMSPE: {pre_rmspe:.2f}")

# ─── Step 2: Build figure ────────────────────────────────────────────────────
print("\nStep 2: Building figure")

fig, axes = plt.subplots(
    2, 1, figsize=(10, 8),
    gridspec_kw={"height_ratios": [2, 1], "hspace": 0.08}
)

treat_color = "#CC0000"
line_color  = "black"
date_min    = main["date"].min()
date_max    = main["date"].max()

# ── Top panel: actual vs synthetic ───────────────────────────────────────────
ax1 = axes[0]

ax1.plot(main["date"], main["_Y_treated"],
         color=line_color, linewidth=1.8, label="ERCOT (actual)", zorder=3)
ax1.plot(main["date"], main["_Y_synthetic"],
         color=line_color, linewidth=1.4, linestyle="--",
         label="Synthetic ERCOT", zorder=3)
ax1.axvline(treatment_date, color=treat_color, linewidth=1.2,
            linestyle="dotted", zorder=2,
            label="Treatment date (2023m5)")
ax1.axvspan(treatment_date, date_max,
            alpha=0.04, color="gray", zorder=1)

ax1.set_ylabel("Avg. Demand Index (2019 = 100)", fontsize=10)
ax1.set_xlim(date_min, date_max)
ax1.set_ylim(70, 145)
ax1.xaxis.set_major_locator(mdates.YearLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax1.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[7]))
ax1.tick_params(axis="x", labelbottom=False)
ax1.tick_params(axis="both", labelsize=9)
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)
ax1.legend(loc="upper left", fontsize=8.5, frameon=False)

# ── Bottom panel: placebo distribution ───────────────────────────────────────
ax2 = axes[1]

# Donor placebo gaps in gray
for name, pdf in placebos:
    ax2.plot(pdf["date"], pdf["gap"],
             color="gray", linewidth=1.0, alpha=0.6, zorder=2)

# ERCOT gap in black on top
ax2.plot(main["date"], main["gap"],
         color=line_color, linewidth=1.8, zorder=3, label="ERCOT gap")

ax2.axhline(0, color="gray", linewidth=0.8, linestyle="--", zorder=1)
ax2.axvline(treatment_date, color=treat_color, linewidth=1.2,
            linestyle="dotted", zorder=2)
ax2.axvspan(treatment_date, date_max,
            alpha=0.04, color="gray", zorder=1)

# Post-treatment mean annotation — bottom right, clear of lines
ax2.text(
    0.97, 0.08,
    f"Post-treatment mean: +{post_gap:.1f} index pts",
    transform=ax2.transAxes,
    fontsize=7.5, color="#555555",
    ha="right", va="bottom", style="italic",
)

ax2.set_ylabel("Gap (index points)", fontsize=10)
ax2.set_xlim(date_min, date_max)
ax2.xaxis.set_major_locator(mdates.YearLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax2.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[7]))
ax2.tick_params(axis="both", labelsize=9)
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)

# Gray line label for placebos
ax2.plot([], [], color="gray", linewidth=1.0, alpha=0.6,
         label="Donor placebo gaps (ISNE, NYIS, SWPP)")
ax2.legend(loc="upper left", fontsize=8.5, frameon=False)

# ── Figure title ──────────────────────────────────────────────────────────────
fig.suptitle(
    "Figure 5. Synthetic Control Gap \u2014 ERCOT Average Hourly Demand\n"
    "SC-3 Specification: ISNE, NYIS, SWPP Donor Pool",
    fontsize=11, fontweight="bold", x=0.5, y=0.98, ha="center"
)

# ── Notes ─────────────────────────────────────────────────────────────────────
note_text = (
    "Notes: Outcome variable is average hourly demand indexed to 2019 average\u202f=\u202f100. "
    "Dashed black line is the synthetic counterfactual (SC-3 donor pool: ISNE, NYIS, SWPP). "
    "Dotted red vertical line marks the Bai-Perron structural break date (2023m5, "
    "UDmax\u202f=\u202f35.39). "
    "Gray lines in the bottom panel show in-space placebo gaps for each donor unit "
    "treated as if it were the treated unit. "
    f"Pre-treatment RMSPE: {pre_rmspe:.2f}. "
    f"Post-treatment mean gap: +{post_gap:.1f} index points. "
    "Zero of three placebos exceed ERCOT\u2019s post-treatment gap (p\u202f=\u202f0.25)."
)
fig.text(0.5, -0.03, note_text, ha="center", fontsize=7.5,
         style="italic", wrap=True)

plt.tight_layout(rect=[0, 0.0, 1, 0.97])

# ─── Step 3: Save ────────────────────────────────────────────────────────────
print("\nStep 3: Saving")
os.makedirs("outputs", exist_ok=True)
out_path = "outputs/sc3_avg_demand_twopanel.png"
plt.savefig(out_path, dpi=300, bbox_inches="tight",
            facecolor="white", edgecolor="none")
plt.close()
print(f"  Saved to {out_path}")
print("\nDone.")