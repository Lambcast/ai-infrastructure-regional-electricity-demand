import pandas as pd

df = pd.read_csv('data/ercot_zone_raw.csv')
print(f"Raw columns: {df.columns.tolist()}")

# Merge the two datetime columns into one
if 'HourEnding' in df.columns and 'Hour Ending' in df.columns:
    df['ts'] = df['HourEnding'].fillna(df['Hour Ending'])
elif 'HourEnding' in df.columns:
    df['ts'] = df['HourEnding']
else:
    df['ts'] = df['Hour Ending']

# Parse datetime
df['datetime'] = pd.to_datetime(df['ts'], dayfirst=False, errors='coerce')
null_dt = df['datetime'].isna().sum()
print(f"Unparseable datetime rows: {null_dt}")
df = df.dropna(subset=['datetime'])

# Extract year_month
df['year_month'] = df['datetime'].dt.to_period('M').astype(str)

zones = ['COAST', 'EAST', 'FWEST', 'NORTH', 'NCENT', 'SOUTH', 'SCENT', 'WEST']

# Aggregate to monthly avg and min per zone
records = []
for zone in zones:
    monthly = df.groupby('year_month')[zone].agg(
        avg_demand_mwh='mean',
        min_demand_mwh='min',
        n_hours='count'
    ).reset_index()
    monthly['zone'] = zone
    records.append(monthly)

panel = pd.concat(records, ignore_index=True)
panel = panel.sort_values(['zone', 'year_month']).reset_index(drop=True)

print(f"\nPanel shape: {panel.shape}")
print(f"Zones: {sorted(panel['zone'].unique())}")
print(f"Date range: {panel['year_month'].min()} to {panel['year_month'].max()}")
print(f"Months per zone: {panel.groupby('zone')['year_month'].count().to_string()}")

panel.to_csv('data/ercot_zone_monthly.csv', index=False)
print("\nSaved: data/ercot_zone_monthly.csv")