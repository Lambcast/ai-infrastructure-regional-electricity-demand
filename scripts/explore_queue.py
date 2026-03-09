"""
explore_queue.py
----------------
Exploratory analysis of LBNL interconnection queue data (thru 2024).
Produces charts for Website Post 1 and paper descriptive section.

Pairs with explore_eia.py — demand side vs. queue (investment) side.

Run from project root: python scripts/explore_queue.py
Output saved to: outputs/
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

os.makedirs("outputs", exist_ok=True)

# ── Load & clean ──────────────────────────────────────────────────────────────
print("Loading LBNL queue data...")
df = pd.read_csv("data/lbnl_queue_data.csv")

# Filter to target regions only
REGIONS = ["PJM", "MISO", "ERCOT"]
df = df[df["region"].isin(REGIONS)].copy()

# q_year is our primary time variable
df = df[df["q_year"].notna()].copy()
df["q_year"] = df["q_year"].astype(int)

# mw1 is the primary MW field — drop rows with no MW value
df = df[df["mw1"].notna() & (df["mw1"] > 0)].copy()

print(f"  Loaded {len(df):,} queue records across {df['region'].nunique()} regions.")
print(f"  Year range: {df['q_year'].min()} to {df['q_year'].max()}")
print(f"  Regions: {df['region'].value_counts().to_dict()}")
print(f"  Status breakdown:\n{df['q_status'].value_counts().to_string()}")
print()

COLORS = {
    "PJM":   "#1F3864",
    "ERCO":  "#2E75B6",   # kept for cross-script compatibility
    "ERCOT": "#2E75B6",
    "MISO":  "#70AD47",
}

LABELS = {
    "PJM":   "PJM (Mid-Atlantic / Midwest)",
    "ERCO":  "ERCOT (Texas)",              # kept for cross-script compatibility
    "ERCOT": "ERCOT (Texas)",
    "MISO":  "MISO (Southeast / Midwest)",
}

# Focus on 2005 onward for clarity — queue data exists before but
# is sparse and less relevant to the data center story
df_plot = df[df["q_year"] >= 2005].copy()

# ── Chart 1: Annual GW filed by region ───────────────────────────────────────
# Total MW of new interconnection requests filed each year
print("Building Chart 1: Annual GW filed by region...")

annual_mw = (
    df_plot.groupby(["q_year", "region"])["mw1"]
    .sum()
    .reset_index()
    .rename(columns={"mw1": "total_mw"})
)
annual_mw["total_gw"] = annual_mw["total_mw"] / 1000

fig, ax = plt.subplots(figsize=(10, 6))

for region, grp in annual_mw.groupby("region"):
    ax.plot(
        grp["q_year"], grp["total_gw"],
        marker="o", linewidth=2.5, markersize=6,
        color=COLORS.get(region, "gray"),
        label=LABELS.get(region, region),
    )

ax.set_title(
    "Annual Interconnection Queue Filings by Region\nPJM, ERCOT, MISO  |  Total GW Filed per Year  |  2005–2024",
    fontsize=13, pad=12
)
ax.set_xlabel("Year", fontsize=11)
ax.set_ylabel("Total Capacity Filed (GW)", fontsize=11)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.legend(fontsize=10)
ax.grid(axis="y", linestyle="--", alpha=0.5)
ax.set_xticks(range(2005, 2025, 2))
plt.xticks(rotation=45)
ax.annotate(
    "MISO queue reform\n(backlog processed)",
    xy=(2022, 185), xytext=(2019.5, 160),
    fontsize=8.5, color="#555555",
    arrowprops=dict(arrowstyle="->", color="#555555", lw=1.2),
    ha="center"
)
plt.tight_layout()

plt.savefig("outputs/queue_annual_gw_filed.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Chart 1 saved: outputs/queue_annual_gw_filed.png")

# ── Chart 2: Cumulative queue GW by region ────────────────────────────────────
# Shows the total weight of investment building up over time.
# Note: this is cumulative of all filings, not just active projects —
# treat as a measure of total investment pressure, not current queue size.
print("Building Chart 2: Cumulative queue GW by region...")

cumulative = (
    df_plot.groupby(["region", "q_year"])["mw1"]
    .sum()
    .groupby(level=0)
    .cumsum()
    .reset_index()
    .rename(columns={"mw1": "cumulative_mw"})
)
cumulative["cumulative_gw"] = cumulative["cumulative_mw"] / 1000

fig, ax = plt.subplots(figsize=(10, 6))

for region, grp in cumulative.groupby("region"):
    ax.plot(
        grp["q_year"], grp["cumulative_gw"],
        marker="o", linewidth=2.5, markersize=6,
        color=COLORS.get(region, "gray"),
        label=LABELS.get(region, region),
    )

ax.set_title(
    "Cumulative Interconnection Queue Capacity by Region\nPJM, ERCOT, MISO  |  Total GW Ever Filed  |  2005–2024",
    fontsize=13, pad=12
)
ax.set_xlabel("Year", fontsize=11)
ax.set_ylabel("Cumulative Capacity Filed (GW)", fontsize=11)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.legend(fontsize=10)
ax.grid(axis="y", linestyle="--", alpha=0.5)
ax.set_xticks(range(2005, 2025, 2))
plt.xticks(rotation=45)
plt.tight_layout()

plt.savefig("outputs/queue_cumulative_gw.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Chart 2 saved: outputs/queue_cumulative_gw.png")

# ── Chart 3: Annual GW filed by generation type (ERCOT focus) ────────────────
# Shows the composition of what's being built in ERCOT — the star of our story.
# Solar and battery dominance is the grid's response to the demand surge.
print("Building Chart 3: ERCOT queue filings by generation type...")

ercot = df_plot[df_plot["region"] == "ERCOT"].copy()

top_types = ercot["type_clean"].value_counts().head(6).index.tolist()
ercot["type_grouped"] = ercot["type_clean"].apply(
    lambda x: x if x in top_types else "Other"
)

type_annual = (
    ercot.groupby(["q_year", "type_grouped"])["mw1"]
    .sum()
    .reset_index()
    .rename(columns={"mw1": "total_mw"})
)
type_annual["total_gw"] = type_annual["total_mw"] / 1000

type_pivot = type_annual.pivot(
    index="q_year", columns="type_grouped", values="total_gw"
).fillna(0)

TYPE_COLORS = {
    "Solar":               "#F4A261",
    "Wind":                "#4CC9F0",
    "Battery":             "#7209B7",
    "Solar+Battery":       "#E76F51",
    "Gas":                 "#6C757D",
    "Solar+Wind+Battery":  "#2EC4B6",
    "Offshore Wind":       "#0077B6",
    "Other":               "#ADB5BD",
}

fig, ax = plt.subplots(figsize=(12, 6))
type_pivot.plot(
    kind="bar", stacked=True, ax=ax,
    color=[TYPE_COLORS.get(c, "#ADB5BD") for c in type_pivot.columns],
    width=0.75, edgecolor="none"
)

ax.set_title(
    "ERCOT Interconnection Queue Filings by Generation Type\nTotal GW Filed per Year  |  2005–2024",
    fontsize=13, pad=12
)
ax.set_xlabel("Year", fontsize=11)
ax.set_ylabel("Total Capacity Filed (GW)", fontsize=11)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.legend(fontsize=9, bbox_to_anchor=(1.01, 1), loc="upper left")
ax.grid(axis="y", linestyle="--", alpha=0.4)
plt.xticks(rotation=45)
plt.tight_layout()

plt.savefig("outputs/queue_ercot_by_type.png", dpi=150, bbox_inches="tight")
plt.close()
print("✅ Chart 3 saved: outputs/queue_ercot_by_type.png")

# ── Summary stats ─────────────────────────────────────────────────────────────
print("\n── Summary: Total GW filed 2019–2024 by region ──────────────────────")
recent = df_plot[df_plot["q_year"] >= 2019]
summary = (
    recent.groupby("region")["mw1"]
    .sum()
    .reset_index()
    .rename(columns={"mw1": "total_mw"})
)
summary["total_gw"] = summary["total_mw"] / 1000
for _, row in summary.iterrows():
    if row["region"] in REGIONS:
        print(f"  {LABELS[row['region']]}: {row['total_gw']:,.0f} GW")

print("\n── Top 5 years by ERCOT GW filed ────────────────────────────────────")
ercot_annual = annual_mw[annual_mw["region"] == "ERCOT"].nlargest(5, "total_gw")
for _, row in ercot_annual.iterrows():
    print(f"  {int(row['q_year'])}: {row['total_gw']:,.0f} GW")

print("\nDone. All outputs saved to outputs/")
