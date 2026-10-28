"""CSV readers for structured railway data (trains, delay records)."""

from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


def _report(source: str, df: pd.DataFrame) -> None:
    logger.info("CSV source=%s shape=%s columns=%s", source, df.shape, list(df.columns))
    logger.info("CSV head:\n%s", df.head().to_string())


def read_trains_csv(path: Path) -> pd.DataFrame:
    """Read trains.csv into a DataFrame."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Trains CSV not found: {path}")
    df = pd.read_csv(path)
    _report(str(path), df)
    return df


def read_delay_records_csv(path: Path) -> pd.DataFrame:
    """Read delay_records.csv into a DataFrame."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Delay records CSV not found: {path}")
    df = pd.read_csv(path)
    df["cancelled"] = df["cancelled"].map(lambda v: str(v).strip().lower() in ("true", "1", "yes"))
    _report(str(path), df)
    return df
