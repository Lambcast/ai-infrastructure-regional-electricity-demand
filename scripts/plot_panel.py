import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

os.makedirs("outputs", exist_ok=True)

# ── Config ────────────────────────────────────────────────────────────────────
PANEL_PATH = "data/panel_base.csv"

BA_LABELS = {
    "ERCO": "ERCOT (Texas)",
    "MISO": "MISO (Southeast / Midwest)",
    "PJM":  "PJM (Mid-Atlantic / Midwest)",
}

DEMAND_COLOR = "#1F3864"
QUEUE_COLOR  = "#e74c3c"

# ── Load panel ────────────────────────────────────────────────────────────────
print("Loading panel data...")
panel = pd.read_csv(PANEL_PATH)
panel["year_month"] = pd.to_datetime(panel["year_month"].astype(str))

print(f"  Rows: {len(panel):,}")
print(f"  BAs: {panel['ba'].unique().tolist()}")
print(f"  Period: {panel['year_month'].min().strftime('%Y-%m')} to {panel['year_month'].max().strftime('%Y-%m')}")
print()

# ── Helper: single BA co-movement chart ──────────────────────────────────────
def plot_ba(ax, data, ba, show_xlabel=True):
    """
    Plot demand (left axis) and queue filings (right axis) for one BA.
    Returns the twin axis so the caller can adjust it if needed.
    """
    label = BA_LABELS.get(ba, ba)

    ax2 = ax.twinx()

    # Queue filings — bar chart on right axis (background)
    ax2.bar(
        data["year_month"],
        data["queue_mw_filed"],
        width=20,
        color=QUEUE_COLOR,
        alpha=0.35,
        label="Queue MW Filed (right)",
        zorder=1,
    )

    # Demand line — on left axis (foreground)
    ax.plot(
        data["year_month"],
        data["avg_demand_mwh"],
        color=DEMAND_COLOR,
        linewidth=2.0,
        label="Avg Hourly Demand (left)",
        zorder=2,
    )

    # Titles and labels
    ax.set_title(label, fontsize=12, fontweight="bold", pad=8)
    ax.set_ylabel("Avg Hourly Demand (MWh)", color=DEMAND_COLOR, fontsize=10)
    ax2.set_ylabel("Queue MW Filed", color=QUEUE_COLOR, fontsize=10)

    ax.tick_params(axis="y", labelcolor=DEMAND_COLOR)
    ax2.tick_params(axis="y", labelcolor=QUEUE_COLOR)

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    if show_xlabel:
        ax.set_xlabel("Month", fontsize=10)

    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)

    # Combined legend
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper left")

    return ax2


# ── Chart 1: Individual BA charts ────────────────────────────────────────────
print("Building individual BA charts...")

for ba in ["ERCO", "MISO", "PJM"]:
    data = panel[panel["ba"] == ba].copy()

    fig, ax = plt.subplots(figsize=(12, 5))
    plot_ba(ax, data, ba)

    fig.suptitle(
        f"Electricity Demand vs Queue Filings — {BA_LABELS[ba]}\n2019–2025",
        fontsize=13, fontweight="bold", y=1.01
    )
    plt.tight_layout()

    outpath = f"outputs/comovement_{ba.lower()}.png"
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✅ Saved: {outpath}")

print()

# ── Chart 2: Combined 3-panel figure ─────────────────────────────────────────
print("Building combined 3-panel figure...")

fig, axes = plt.subplots(3, 1, figsize=(13, 14), sharex=False)

for i, ba in enumerate(["ERCO", "MISO", "PJM"]):
    data = panel[panel["ba"] == ba].copy()
    show_xlabel = (i == 2)
    plot_ba(axes[i], data, ba, show_xlabel=show_xlabel)

fig.suptitle(
    "Electricity Demand vs Interconnection Queue Filings\nPJM, ERCOT, MISO  |  2019–2025",
    fontsize=14, fontweight="bold"
)
plt.tight_layout()

outpath = "outputs/comovement_combined.png"
plt.savefig(outpath, dpi=150, bbox_inches="tight")
plt.close()
print(f"  ✅ Saved: {outpath}")

print()
print("Done. All co-movement charts saved to outputs/")