"""Tests for time-series layer."""

import pandas as pd

from src.timeseries import arima_model, prepare
from src.database import queries
from src.database.db_loader import get_engine


def _series():
    return prepare.monthly_series_from_df(queries.monthly_avg_delay(get_engine("sqlite")))


def test_monthly_series_has_no_gaps():
    engine = get_engine("sqlite")
    monthly = queries.monthly_avg_delay(engine)
    series = prepare.monthly_series_from_df(monthly)
    # should have 36 months
    assert len(series) == 36


def test_forecast_has_three_rows():
    engine = get_engine("sqlite")
    monthly = queries.monthly_avg_delay(engine)
    series = prepare.monthly_series_from_df(monthly)
    fc = arima_model.forecast_next_months(series, steps=3)
    assert len(fc["forecast"]) == 3


def test_adf_test():
    engine = get_engine("sqlite")
    monthly = queries.monthly_avg_delay(engine)
    series = prepare.monthly_series_from_df(monthly)
    result = arima_model.adf_test(series)
    assert "stationary" in result
    assert "p_value" in result


def test_smoothing_models_fit():
    from src.timeseries import smoothing

    series = _series()
    assert len(smoothing.simple_exp_smooth(series).fittedvalues) == len(series)
    assert len(smoothing.holt_winters(series).forecast(3)) == 3
