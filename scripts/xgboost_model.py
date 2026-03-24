import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import root_mean_squared_error

train = pd.read_csv('data/panel_train.csv')
holdout = pd.read_csv('data/panel_holdout.csv')

features = [
    'queue_mw_filed', 'queue_mw_filed_large', 'queue_projects_filed',
    'queue_mw_active', 'queue_mw_lag12', 'queue_mw_large_lag12',
    'queue_mw_lag18', 'queue_mw_large_lag18', 'queue_mw_lag24',
    'queue_mw_large_lag24', 'queue_mw_filed_50', 'queue_mw_filed_200',
    'queue_mw_large_lag18_50', 'queue_mw_large_lag18_200',
    'hdd', 'cdd', 'gdp', 'year', 'month', 'quarter'
]

results = []
importance_all = {}

for ba in ['ERCO', 'MISO', 'PJM']:
    train_ba = train[train['ba'] == ba].sort_values('year_month').copy()
    holdout_ba = holdout[holdout['ba'] == ba].sort_values('year_month').copy()

    for col in features:
        train_ba[col] = train_ba[col].fillna(0)
        holdout_ba[col] = holdout_ba[col].fillna(0)

    X_train = train_ba[features]
    y_train = train_ba['avg_demand_mwh']
    X_holdout = holdout_ba[features]
    y_holdout = holdout_ba['avg_demand_mwh']

    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_holdout)
    rmse = root_mean_squared_error(y_holdout, y_pred)
    print(f"{ba} RMSE: {rmse:,.0f} MWh")

    importance_all[ba] = pd.Series(
        model.feature_importances_,
        index=features
    ).sort_values(ascending=False)

    for i, ym in enumerate(holdout_ba['year_month'].values):
        results.append({
            'ba': ba,
            'year_month': ym,
            'actual': y_holdout.values[i],
            'xgboost_forecast': y_pred[i],
            'model': 'XGBoost'
        })

print("\nTop 5 features per BA:")
for ba in ['ERCO', 'MISO', 'PJM']:
    print(f"\n{ba}:")
    print(importance_all[ba].head(5).to_string())

pd.DataFrame(results).to_csv('data/forecasts_xgboost.csv', index=False)
print("\nSaved: data/forecasts_xgboost.csv")
