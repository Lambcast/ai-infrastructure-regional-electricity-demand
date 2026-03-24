import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
import warnings
warnings.filterwarnings('ignore')

# ── PARAMETERS ────────────────────────────────────────────────────────────────
BASE_DEMAND_MWH = 43758.7        # 2019 ERCOT avg hourly demand
SC_GAP_INDEX    = 34.8           # SC minimum demand gap (index points)
COMPLETED_MW    = 78566.6        # Total operational ERCOT MW in LBNL
COMPLETION_RATE = 0.339          # Historical ERCOT completion rate

# SC-implied demand intensity: MWh of avg hourly demand per completed MW
SC_DEMAND_INCREMENT = (SC_GAP_INDEX / 100) * BASE_DEMAND_MWH
INTENSITY_RATIO = SC_DEMAND_INCREMENT / COMPLETED_MW

print("── Scaling Parameters ───────────────────────────────────────")
print(f"SC-implied demand increment: {SC_DEMAND_INCREMENT:,.1f} MWh")
print(f"Completed ERCOT MW:          {COMPLETED_MW:,.1f} MW")
print(f"Intensity ratio:             {INTENSITY_RATIO:.4f} MWh per completed MW")
print(f"Completion rate (ERCOT):     {COMPLETION_RATE:.1%}")

# ── ARIMA BASELINE ────────────────────────────────────────────────────────────
zones = pd.read_csv('data/ercot_zone_monthly.csv')
ercot_total = zones.groupby('year_month').agg(
    avg_demand_mwh=('avg_demand_mwh', 'sum')
).reset_index().sort_values('year_month')

train = ercot_total[ercot_total['year_month'] <= '2024-12']['avg_demand_mwh'].values
model = ARIMA(train, order=(1,1,1), seasonal_order=(1,1,1,12))
fit = model.fit()

forecast_months = pd.period_range(start='2025-01', periods=36, freq='M').astype(str)
baseline = fit.forecast(steps=36)
baseline_df = pd.DataFrame({
    'year_month': forecast_months,
    'arima_baseline': baseline
})
print(f"\nARIMA baseline fitted on {len(train)} months (2019-2024)")

# ── QUEUE FILING SCENARIOS ────────────────────────────────────────────────────
panel = pd.read_csv('data/panel_with_controls.csv')
erco = panel[(panel['ba'] == 'ERCO') & (panel['year'] <= 2024)]
annual_filed = erco.groupby('year')['queue_mw_filed_large'].sum()
annual_filed = annual_filed[annual_filed > 0]

# Linear trend through 2019-2024
years = annual_filed.index.values
mw_vals = annual_filed.values
slope, intercept = np.polyfit(years, mw_vals, 1)

proj_years = [2025, 2026, 2027]
scenarios = {
    'conservative': {y: annual_filed[2024] for y in proj_years},
    'trend':        {y: max(slope * y + intercept, 0) for y in proj_years}
}

print("\n── Queue Filing Scenarios ───────────────────────────────────")
for name, vals in scenarios.items():
    print(f"\n{name.capitalize()}:")
    for y, v in vals.items():
        completed = v * COMPLETION_RATE
        demand_inc = completed * INTENSITY_RATIO
        print(f"  {y}: filed={v:,.0f} MW | completed={completed:,.0f} MW | demand_inc={demand_inc:,.1f} MWh")

# ── BUILD PROJECTIONS ─────────────────────────────────────────────────────────
# Convert annual completed MW to monthly demand increment
# 18-month lag: filings in year Y affect demand starting Y+1 mid-year
def get_monthly_increment(scenario_dict, year_month):
    period = pd.Period(year_month, freq='M')
    filing_period = period - 18
    filing_year = filing_period.year
    if filing_year in scenario_dict:
        annual_filed_mw = scenario_dict[filing_year]
    else:
        annual_filed_mw = list(scenario_dict.values())[-1]
    monthly_completed = (annual_filed_mw * COMPLETION_RATE) / 12
    return monthly_completed * INTENSITY_RATIO

results = []
for ym in forecast_months:
    base = baseline_df[baseline_df['year_month'] == ym]['arima_baseline'].values[0]
    inc_cons  = get_monthly_increment(scenarios['conservative'], ym)
    inc_trend = get_monthly_increment(scenarios['trend'], ym)

    results.append({
        'year_month':             ym,
        'arima_baseline':         base,
        'proj_conservative':      base + inc_cons,
        'proj_trend':             base + inc_trend,
        'increment_conservative': inc_cons,
        'increment_trend':        inc_trend,
    })

proj = pd.DataFrame(results)

# Attach actuals for 2025 comparison
actuals = ercot_total[['year_month', 'avg_demand_mwh']].rename(
    columns={'avg_demand_mwh': 'actual_demand'})
proj = proj.merge(actuals, on='year_month', how='left')

proj.to_csv('data/structural_projection.csv', index=False)

print("\n── 2026 Sample Output ───────────────────────────────────────")
cols = ['year_month', 'arima_baseline', 'proj_conservative',
        'proj_trend', 'increment_conservative', 'increment_trend']
print(proj[proj['year_month'].str.startswith('2026')][cols].to_string(index=False))
print("\nSaved: data/structural_projection.csv")