import pandas as pd

df = pd.read_csv('data/panel_with_controls.csv')

train = df[df['year_month'] <= '2023-12'].copy()
holdout = df[df['year_month'] >= '2024-01'].copy()

train.to_csv('data/panel_train.csv', index=False)
holdout.to_csv('data/panel_holdout.csv', index=False)

print(f"Train:   {train.shape[0]} rows | {train['year_month'].min()} to {train['year_month'].max()}")
print(f"Holdout: {holdout.shape[0]} rows | {holdout['year_month'].min()} to {holdout['year_month'].max()}")
print(f"BAs in train:   {sorted(train['ba'].unique())}")
print(f"BAs in holdout: {sorted(holdout['ba'].unique())}")