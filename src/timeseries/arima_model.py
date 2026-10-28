"""ARIMA(1,1,1), stationarity test, evaluation, forecast."""

import csv
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller


def adf_test(series):
    """Run ADF test; return dict with interpretation."""
    result = adfuller(series.dropna())
    stat, pvalue, lags, nobs, crit, _ = result
    return {
        "test_statistic": stat,
        "p_value": pvalue,
        "lags": lags,
        "n_obs": nobs,
        "critical_values": crit,
        "stationary": pvalue < 0.05,
    }


def fit_arima(series, order=(1, 1, 1)):
    model = ARIMA(series, order=order).fit()
    return model


def evaluate_holdout(series, holdout_months: int = 6):
    """Fit on train, forecast last holdout_months, return metrics."""
    train = series.iloc[:-holdout_months]
    test = series.iloc[-holdout_months:]
    model = ARIMA(train, order=(1, 1, 1)).fit()
    pred = model.forecast(steps=len(test))
    mae = mean_absolute_error(test, pred)
    rmse = np.sqrt(mean_squared_error(test, pred))
    return {"mae": mae, "rmse": rmse, "pred": pred, "test": test, "train": train}


def forecast_next_months(series, steps: int = 3):
    """Refit on full series and forecast next `steps` months with confidence intervals."""
    model = ARIMA(series, order=(1, 1, 1)).fit()
    forecast_res = model.get_forecast(steps=steps)
    pred = forecast_res.predicted_mean
    conf = forecast_res.conf_int()
    return {"model": model, "forecast": pred, "conf_int": conf}
