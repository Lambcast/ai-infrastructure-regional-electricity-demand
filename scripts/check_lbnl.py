import pandas as pd
df = pd.read_csv('data/lbnl_queue_data.csv')
erco_ops = df[(df['region']=='ERCOT') & (df['q_status']=='operational')]
print(f'Operational projects: {len(erco_ops)}')
print(f'Total MW (mw1): {erco_ops["mw1"].sum():,.1f}')
print(f'MW column check: {erco_ops[["mw1","mw2","mw3"]].describe().to_string()}')