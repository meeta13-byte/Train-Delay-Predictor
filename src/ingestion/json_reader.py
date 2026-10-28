"""JSON reader for station reference data."""

from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


def read_stations_json(path: Path) -> pd.DataFrame:
    """Read stations JSON into a DataFrame."""
    import json

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Stations JSON not found: {path}")
    with open(path, "r") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("stations", data.get("data", []))
    df = pd.DataFrame(data)
    logger.info("JSON source=%s shape=%s columns=%s", path, df.shape, list(df.columns))
    logger.info("JSON head:\n%s", df.head().to_string())
    return df
