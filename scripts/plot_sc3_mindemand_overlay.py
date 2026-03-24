"""
plot_sc3_mindemand_overlay.py
Produces the narrative validation overlay figure:
SC-3 minimum demand gap plot with numbered vertical markers at known
ERCOT data center energization dates.

Reads:  results/sc3_mindemand_results.csv
Saves:  outputs/sc3_mindemand_gap_overlay.png

Run from project root:
    python scripts/plot_sc3_mindemand_overlay.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import os

# ─── Step 1: Load SC-3 minimum demand results ────────────────────────────────
print("Step 1: Loading SC-3 minimum demand results")
df = pd.read_csv("results/sc3_mindemand_results.csv")
print(f"  Raw rows: {len(df)}, columns: {df.columns.tolist()}")

df = df[df["_Y_treated"].notna() & df["_time"].notna()].copy()
df = df.sort_values("_time").reset_index(drop=True)
print(f"  Time series rows after filter: {len(df)}")

# ─── Step 2: Convert Stata monthly time to dates ─────────────────────────────
print("\nStep 2: Converting time variable")
def stata_tm_to_date(tm):
    year  = 1960 + int(tm) // 12
    month = int(tm) % 12 + 1
    return pd.Timestamp(year=year, month=month, day=1)

df["date"] = df["_time"].apply(stata_tm_to_date)
df["gap"]  = df["_Y_treated"] - df["_Y_synthetic"]

treatment_tm   = 760
treatment_date = stata_tm_to_date(treatment_tm)
print(f"  Treatment date: {treatment_date.strftime('%Y-%m')}")

post = df[df["_time"] >= treatment_tm]["gap"]
print(f"  Post-treatment mean gap: {post.mean():.1f} index points")
print(f"  Post-treatment max gap:  {post.max():.1f} index points")

# ─── Step 3: Define energization events ──────────────────────────────────────
print("\nStep 3: Defining energization events")
energizations = [
    {"n": 1, "label": "QTS Irving",            "date": pd.Timestamp("2022-12-01")},
    {"n": 2, "label": "Switch San Antonio",    "date": pd.Timestamp("2023-03-01")},
    {"n": 3, "label": "Meta Fort Worth",       "date": pd.Timestamp("2023-04-01")},
    {"n": 4, "label": "Microsoft San Antonio", "date": pd.Timestamp("2023-06-01")},
    {"n": 5, "label": "Google Midlothian",     "date": pd.Timestamp("2023-08-01")},
]
for e in energizations:
    print(f"  ({e['n']}) {e['label']}: {e['date'].strftime('%Y-%m')}")

# ─── Step 4: Build figure ────────────────────────────────────────────────────
print("\nStep 4: Building figure")

fig, axes = plt.subplots(2, 1, figsize=(10, 7.5),
                         gridspec_kw={"height_ratios": [2, 1], "hspace": 0.1})

marker_color  = "#1a6bb5"
treat_color   = "#CC0000"
line_color    = "black"

# ── Top panel ─────────────────────────────────────────────────────────────────
ax1 = axes[0]

ax1.plot(df["date"], df["_Y_treated"],
         color=line_color, linewidth=1.8, label="ERCOT (actual)", zorder=3)
ax1.plot(df["date"], df["_Y_synthetic"],
         color=line_color, linewidth=1.4, linestyle="--",
         label="Synthetic ERCOT", zorder=3)
ax1.axvline(treatment_date, color=treat_color, linewidth=1.2,
            linestyle="dotted", zorder=2, label="Treatment date (2023m5)")
ax1.axvspan(treatment_date, df["date"].max(),
            alpha=0.04, color="gray", zorder=1)

# Energization lines + numbered circle at top
y_top = ax1.get_ylim()[1] if ax1.get_ylim()[1] > 100 else 162
for e in energizations:
    ax1.axvline(e["date"], color=marker_color, linewidth=1.0,
                linestyle=(0, (4, 2)), alpha=0.75, zorder=2)
    ax1.annotate(
        str(e["n"]),
        xy=(e["date"], 158),
        xytext=(0, 0),
        textcoords="offset points",
        fontsize=7.5,
        color=marker_color,
        fontweight="bold",
        ha="center", va="center",
        bbox=dict(boxstyle="circle,pad=0.15", facecolor="white",
                  edgecolor=marker_color, linewidth=0.9),
        zorder=4,
    )

ax1.set_ylabel("Min. Demand Index (2019 = 100)", fontsize=10)
ax1.set_xlim(df["date"].min(), df["date"].max())
ax1.set_ylim(68, 164)
ax1.xaxis.set_major_locator(mdates.YearLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax1.tick_params(axis="x", labelbottom=False)
ax1.tick_params(axis="both", labelsize=9)
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)
ax1.legend(loc="upper left", fontsize=8.5, frameon=False)

# ── Bottom panel: gap ─────────────────────────────────────────────────────────
ax2 = axes[1]

ax2.plot(df["date"], df["gap"],
         color=line_color, linewidth=1.6, zorder=3)
ax2.axhline(0, color="gray", linewidth=0.8, linestyle="--", zorder=1)
ax2.axvline(treatment_date, color=treat_color, linewidth=1.2,
            linestyle="dotted", zorder=2)
ax2.axvspan(treatment_date, df["date"].max(),
            alpha=0.04, color="gray", zorder=1)

# Same energization lines in gap panel, numbers at top
gap_top = df["gap"].max() * 1.05 if df["gap"].max() > 0 else 50
for e in energizations:
    ax2.axvline(e["date"], color=marker_color, linewidth=1.0,
                linestyle=(0, (4, 2)), alpha=0.75, zorder=2)

ax2.set_ylabel("Gap (index points)", fontsize=10)
ax2.set_xlim(df["date"].min(), df["date"].max())
ax2.xaxis.set_major_locator(mdates.YearLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax2.tick_params(axis="both", labelsize=9)
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)

# ── Energization legend below bottom panel ────────────────────────────────────
legend_lines = []
for e in energizations:
    legend_lines.append(f"({e['n']}) {e['label']}")

legend_text = "    ".join(legend_lines)
fig.text(
    0.5, -0.02,
    legend_text,
    ha="center", fontsize=8,
    color=marker_color,
    fontstyle="italic",
)

# ── Figure title ──────────────────────────────────────────────────────────────
fig.suptitle(
    "Figure 6. Synthetic Control Gap — ERCOT Minimum Hourly Demand\n"
    "SC-3 Specification: ISNE, NYIS, SWPP Donor Pool",
    fontsize=11, fontweight="bold", x=0.5, y=1.01, ha="center"
)

# ── Notes ─────────────────────────────────────────────────────────────────────
note_text = (
    "Notes: Outcome variable is minimum hourly demand indexed to 2019 average\u202f=\u202f100. "
    "Dashed black line is the synthetic counterfactual (SC-3: ISNE, NYIS, SWPP). "
    "Dotted red vertical line marks the Bai-Perron structural break date (2023m5, UDmax\u202f=\u202f35.39). "
    "Numbered blue dashed lines mark known ERCOT data center energization dates (approximate; publicly announced). "
    "Post-treatment gap at end of sample:\u202f34.8 index points. "
    "Zero of three placebos exceed ERCOT gap (p\u202f=\u202f0.25)."
)
fig.text(0.5, -0.09, note_text, ha="center", fontsize=7.5,
         style="italic", wrap=True)

plt.tight_layout()

# ─── Step 5: Save ────────────────────────────────────────────────────────────
print("\nStep 5: Saving")
os.makedirs("outputs", exist_ok=True)
out_path = "outputs/sc3_mindemand_gap_overlay.png"
plt.savefig(out_path, dpi=300, bbox_inches="tight",
            facecolor="white", edgecolor="none")
plt.close()
print(f"  Saved to {out_path}")
print("\nDone.")