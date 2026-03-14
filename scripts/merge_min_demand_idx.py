import pandas as pd
load = pd.read_csv('data/panel_load_shape.csv')[['ba','year_month','min_demand_idx']]
exp = pd.read_csv('data/panel_expanded.csv')
exp = exp.merge(load, on=['ba','year_month'], how='left')
print(f'Rows: {len(exp)} (expected 504)')
print(f'Missing min_demand_idx: {exp["min_demand_idx"].isna().sum()} (expected 252)')
exp.to_csv('data/panel_expanded.csv', index=False)
print('Saved.')