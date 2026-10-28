"""Seasonal decomposition and trend plotting."""

import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import seasonal_decompose

from src.config import get_path, load_config


def decompose_series(series, period: int = 12):
    """Decompose series with seasonal_decompose (additive)."""
    result = seasonal_decompose(series, model="additive", period=period)
    config = load_config()
    path = get_path(config, "charts_dir") / "ts_decomposition.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = result.plot()
    fig.savefig(path)
    plt.close(fig)
    return result, path
