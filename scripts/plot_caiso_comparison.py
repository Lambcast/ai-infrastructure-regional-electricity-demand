"""
plot_caiso_comparison.py
------------------------
Produces contrast case figure: demand_idx and min_demand_idx for
CAISO, ERCO, PJM, and MISO indexed to 2019=100.

Output: outputs/caiso_vs_ercot_comparison.png
Run from project root: python scripts/plot_caiso_comparison.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import os

os.makedirs("outputs", exist_ok=True)

COLORS = {
    "ERCO": "#e74c3c",
    "MISO": "#27ae60",
    "PJM":  "#1F3864",
    "CISO": "#8e44ad",
}
LABELS = {
    "ERCO": "ERCOT (Texas)",
    "MISO": "MISO (Southeast / Midwest)",
    "PJM":  "PJM (Mid-Atlantic / Midwest)",
    "CISO": "CAISO (California)",
}

# Load panels
caiso  = pd.read_csv("data/panel_caiso_comparison.csv")
panel  = pd.read_csv("data/panel_load_shape.csv")

# Compute demand_idx for primary BAs if not present
if "demand_idx" not in panel.columns:
    base = panel[panel["year"] == 2019].groupby("ba")["avg_demand_mwh"].mean()
    panel["demand_idx"] = panel.apply(
        lambda r: r["avg_demand_mwh"] / base[r["ba"]] * 100, axis=1
    )

# Stack
caiso_slim = caiso[["ba", "year_month", "demand_idx", "min_demand_idx"]].copy()
panel_slim = panel[["ba", "year_month", "demand_idx", "min_demand_idx"]].copy()
combined   = pd.concat([panel_slim, caiso_slim], ignore_index=True)
combined["year_month_dt"] = pd.to_datetime(combined["year_month"])

# Plot
fig, axes = plt.subplots(2, 1, figsize=(13, 10), sharex=True)
fig.suptitle(
    "CAISO vs ERCOT, PJM, MISO — Demand Indices (2019 = 100)",
    fontsize=14, fontweight="bold"
)

for ba in ["ERCO", "MISO", "PJM", "CISO"]:
    data = combined[combined["ba"] == ba].sort_values("year_month_dt")
    ls   = "--" if ba == "CISO" else "-"
    axes[0].plot(data["year_month_dt"], data["demand_idx"],
                 color=COLORS[ba], linewidth=2.0, linestyle=ls, label=LABELS[ba])
    axes[1].plot(data["year_month_dt"], data["min_demand_idx"],
                 color=COLORS[ba], linewidth=2.0, linestyle=ls, label=LABELS[ba])

for ax, title, ylabel in zip(
    axes,
    ["Average Hourly Demand Index (2019 = 100)",
     "Minimum Hourly Demand Index (2019 = 100)"],
    ["Demand Index", "Min Demand Index"]
):
    ax.axhline(100, color="black", linestyle="--", linewidth=1, alpha=0.4)
    ax.set_title(title, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

# COVID annotation on CAISO early 2020
axes[1].annotate(
    "COVID-19\nlockdowns",
    xy=(pd.Timestamp("2020-03-01"), 2),
    xytext=(pd.Timestamp("2020-08-01"), 20),
    arrowprops=dict(arrowstyle="->", color="#8e44ad", lw=1.2),
    fontsize=8, color="#8e44ad", ha="left"
)

# Winter Storm Uri annotation on ERCOT early 2021
axes[1].annotate(
    "Winter Storm Uri",
    xy=(pd.Timestamp("2021-02-01"), 88),
    xytext=(pd.Timestamp("2021-05-01"), 72),
    arrowprops=dict(arrowstyle="->", color="#e74c3c", lw=1.2),
    fontsize=8, color="#e74c3c", ha="left"
)

axes[1].set_xlabel("Month", fontsize=10)
plt.tight_layout()
plt.savefig("outputs/caiso_vs_ercot_comparison.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Saved: outputs/caiso_vs_ercot_comparison.png")