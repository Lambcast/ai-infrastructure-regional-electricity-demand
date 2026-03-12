"""
histogram_mw.py
---------------
Plots the distribution of project MW sizes from the LBNL queue data.
Used to determine the empirical threshold for 'large' projects before
any regression runs. The threshold must be set before results can
influence the choice.

Looking for: natural breaks, gaps, or bimodal distribution in the
MW size distribution across PJM, MISO, and ERCOT projects.

Run from project root: python scripts/histogram_mw.py
Output saved to: outputs/histogram_project_mw.png

Notes:
  - Filters to PJM, MISO, ERCOT only (same as build_panel.py)
  - Drops null and zero MW values
  - Converts q_date Excel serials using same method as build_panel.py
  - Drops epoch dates (year < 1990)
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

os.makedirs("outputs", exist_ok=True)

# ── Config ────────────────────────────────────────────────────────────────────
QUEUE_PATH  = "data/lbnl_queue_data.csv"
TARGET_REGIONS = ["ERCOT", "PJM", "MISO"]

# ── Load and clean queue data ─────────────────────────────────────────────────
print("Loading LBNL queue data...")

queue = pd.read_csv(QUEUE_PATH)
queue = queue[queue["region"].isin(TARGET_REGIONS)].copy()
queue = queue[queue["mw1"].notna() & (queue["mw1"] > 0)].copy()

# Convert q_date Excel serials — same method as build_panel.py
queue = queue[queue["q_date"].notna()].copy()
queue["q_date_parsed"] = pd.to_datetime(
    queue["q_date"], unit="D", origin="1899-12-30", errors="coerce"
)
queue = queue[queue["q_date_parsed"].notna()].copy()
queue = queue[queue["q_date_parsed"].dt.year >= 1990].copy()

print(f"  Projects after filter: {len(queue):,}")
print(f"  MW range: {queue['mw1'].min():,.0f} to {queue['mw1'].max():,.0f}")
print(f"  Median MW: {queue['mw1'].median():,.0f}")
print(f"  Mean MW: {queue['mw1'].mean():,.0f}")
print()

# ── Summary statistics at candidate thresholds ───────────────────────────────
print("── Projects above candidate thresholds ──────────────────────────────")
for threshold in [50, 100, 200, 500]:
    n_above = (queue["mw1"] >= threshold).sum()
    pct = n_above / len(queue) * 100
    mw_above = queue[queue["mw1"] >= threshold]["mw1"].sum()
    print(f"  >={threshold:>4} MW: {n_above:>5,} projects ({pct:.1f}%)  |  {mw_above/1000:,.0f} GW total")
print()

# ── Plot 1: Full distribution (log scale x-axis) ──────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle(
    "Distribution of Project MW Sizes — LBNL Queue Data\nPJM, ERCOT, MISO",
    fontsize=14, fontweight="bold"
)

# Panel A: Full distribution, linear scale
ax = axes[0, 0]
ax.hist(queue["mw1"], bins=100, color="#2E75B6", alpha=0.75, edgecolor="white", linewidth=0.3)
ax.set_title("Full Distribution (linear scale)", fontsize=11)
ax.set_xlabel("Project Size (MW)")
ax.set_ylabel("Number of Projects")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.axvline(100, color="#e74c3c", linestyle="--", linewidth=1.5, label="100 MW")
ax.axvline(200, color="#e67e22", linestyle="--", linewidth=1.5, label="200 MW")
ax.legend(fontsize=9)
ax.grid(axis="y", linestyle="--", alpha=0.4)

# Panel B: Log scale x-axis — reveals distribution shape better
ax = axes[0, 1]
log_bins = np.logspace(np.log10(queue["mw1"].min()), np.log10(queue["mw1"].max()), 80)
ax.hist(queue["mw1"], bins=log_bins, color="#2E75B6", alpha=0.75, edgecolor="white", linewidth=0.3)
ax.set_xscale("log")
ax.set_title("Full Distribution (log scale)", fontsize=11)
ax.set_xlabel("Project Size (MW, log scale)")
ax.set_ylabel("Number of Projects")
ax.axvline(100, color="#e74c3c", linestyle="--", linewidth=1.5, label="100 MW")
ax.axvline(200, color="#e67e22", linestyle="--", linewidth=1.5, label="200 MW")
ax.legend(fontsize=9)
ax.grid(axis="y", linestyle="--", alpha=0.4)

# Panel C: Zoomed in on 0-500 MW — where the threshold decision lives
ax = axes[1, 0]
zoom = queue[queue["mw1"] <= 500]
ax.hist(zoom["mw1"], bins=100, color="#1F3864", alpha=0.75, edgecolor="white", linewidth=0.3)
ax.set_title("Zoomed: 0–500 MW (threshold region)", fontsize=11)
ax.set_xlabel("Project Size (MW)")
ax.set_ylabel("Number of Projects")
ax.axvline(100, color="#e74c3c", linestyle="--", linewidth=1.5, label="100 MW")
ax.axvline(200, color="#e67e22", linestyle="--", linewidth=1.5, label="200 MW")
ax.legend(fontsize=9)
ax.grid(axis="y", linestyle="--", alpha=0.4)

# Panel D: By region
ax = axes[1, 1]
colors = {"ERCOT": "#e74c3c", "PJM": "#1F3864", "MISO": "#27ae60"}
for region in TARGET_REGIONS:
    data = queue[queue["region"] == region]["mw1"]
    log_bins_r = np.logspace(np.log10(max(data.min(), 1)), np.log10(data.max()), 60)
    ax.hist(data, bins=log_bins_r, alpha=0.5, color=colors[region],
            label=region, edgecolor="white", linewidth=0.2)
ax.set_xscale("log")
ax.set_title("By Region (log scale)", fontsize=11)
ax.set_xlabel("Project Size (MW, log scale)")
ax.set_ylabel("Number of Projects")
ax.axvline(100, color="black", linestyle="--", linewidth=1.2, label="100 MW")
ax.legend(fontsize=9)
ax.grid(axis="y", linestyle="--", alpha=0.4)

plt.tight_layout()
plt.savefig("outputs/histogram_project_mw.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Saved: outputs/histogram_project_mw.png")
print()
print("Done. Examine the histogram before setting the MW threshold.")
print("The threshold must be recorded before any regression runs.")