"""Moving averages and exponential smoothing."""

import matplotlib.pyplot as plt
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def moving_averages(series):
    """Compute 3-month SMA and EMA."""
    return series.rolling(window=3).mean(), series.ewm(span=3).mean()


def simple_exp_smooth(series, alpha: float = 0.2):
    from statsmodels.tsa.api import SimpleExpSmoothing

    model = SimpleExpSmoothing(series).fit(smoothing_level=alpha, optimized=False)
    return model


def holt_winters(series, period: int = 12):
    """Holt-Winters additive trend + seasonality."""
    model = ExponentialSmoothing(series, trend="add", seasonal="add", seasonal_periods=period).fit()
    return model
