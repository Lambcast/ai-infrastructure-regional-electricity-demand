import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import root_mean_squared_error
import logging
logging.getLogger('prophet').setLevel(logging.WARNING)

train = pd.read_csv('data/panel_train.csv')
holdout = pd.read_csv('data/panel_holdout.csv')

results = []

for ba in ['ERCO', 'MISO', 'PJM']:
    print(f"Fitting Prophet for {ba}...")

    train_ba = train[train['ba'] == ba].sort_values('year_month').copy()
    train_ba['queue_mw_large_lag18'] = train_ba['queue_mw_large_lag18'].fillna(0)
    holdout_ba = holdout[holdout['ba'] == ba].sort_values('year_month').copy()
    holdout_ba['queue_mw_large_lag18'] = holdout_ba['queue_mw_large_lag18'].fillna(0)

    train_ba['ds'] = pd.to_datetime(train_ba['year_month'])
    holdout_ba['ds'] = pd.to_datetime(holdout_ba['year_month'])
    train_ba['y'] = train_ba['avg_demand_mwh']

    model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    model.add_regressor('queue_mw_large_lag18')
    model.fit(train_ba[['ds', 'y', 'queue_mw_large_lag18']])

    future = holdout_ba[['ds', 'queue_mw_large_lag18']].copy()
    forecast = model.predict(future)

    y_actual = holdout_ba['avg_demand_mwh'].values
    y_pred = forecast['yhat'].values

    rmse = root_mean_squared_error(y_actual, y_pred)
    print(f"{ba} RMSE: {rmse:,.0f} MWh")

    for i, ym in enumerate(holdout_ba['year_month'].values):
        results.append({
            'ba': ba,
            'year_month': ym,
            'actual': y_actual[i],
            'prophet_forecast': y_pred[i],
            'model': 'Prophet'
        })

pd.DataFrame(results).to_csv('data/forecasts_prophet.csv', index=False)
print("Saved: data/forecasts_prophet.csv")