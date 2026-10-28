"""XML reader for train route / stop schedule data."""

from pathlib import Path

import pandas as pd
import xml.etree.ElementTree as ET

from src.utils.logger import get_logger

logger = get_logger(__name__)

COLUMNS = [
    "train_no",
    "stop_sequence",
    "station_code",
    "scheduled_arrival",
    "scheduled_departure",
    "distance_from_source_km",
]


def read_routes_xml(path: Path) -> pd.DataFrame:
    """Parse nested <train>/<stop> XML into a flat DataFrame."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Routes XML not found: {path}")
    root = ET.parse(path).getroot()
    rows = []
    for train in root.iter("train"):
        train_no = int(train.get("train_no", 0))
        train_name = train.findtext("train_name") or ""
        for stop in train.findall("stop"):
            rows.append(
                {
                    "train_no": train_no,
                    "train_name": train_name,
                    "stop_sequence": int(stop.get("stop_sequence", 0)),
                    "station_code": stop.findtext("station_code", "").strip(),
                    "scheduled_arrival": stop.findtext("scheduled_arrival", "").strip(),
                    "scheduled_departure": stop.findtext("scheduled_departure", "").strip(),
                    "distance_from_source_km": float(stop.findtext("distance_from_source_km") or 0),
                }
            )
    df = pd.DataFrame(rows, columns=COLUMNS + ["train_name"])
    logger.info("XML source=%s shape=%s columns=%s", path, df.shape, list(df.columns))
    logger.info("XML head:\n%s", df.head().to_string())
    return df
