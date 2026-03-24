import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import root_mean_squared_error

train = pd.read_csv('data/panel_train.csv')
holdout = pd.read_csv('data/panel_holdout.csv')

results = []

for ba in ['ERCO', 'MISO', 'PJM']:
    train_ba = train[train['ba'] == ba].sort_values('year_month')
    holdout_ba = holdout[holdout['ba'] == ba].sort_values('year_month')

    y_train = train_ba['avg_demand_mwh'].values
    y_actual = holdout_ba['avg_demand_mwh'].values

    model = ARIMA(y_train, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
    fit = model.fit()

    forecast = fit.forecast(steps=len(y_actual))

    rmse = root_mean_squared_error(y_actual, forecast)
    print(f"{ba} RMSE: {rmse:,.0f} MWh")

    for i, ym in enumerate(holdout_ba['year_month'].values):
        results.append({
            'ba': ba,
            'year_month': ym,
            'actual': y_actual[i],
            'arima_forecast': forecast[i],
            'model': 'ARIMA'
        })

pd.DataFrame(results).to_csv('data/forecasts_arima.csv', index=False)
print("Saved: data/forecasts_arima.csv")