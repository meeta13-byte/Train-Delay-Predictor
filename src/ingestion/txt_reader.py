"""Unstructured TXT reader: regex extraction of delay info from remarks."""

import re
from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)

_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_TRAIN_RE = re.compile(r"\b(\d{5})\b")
_COMPACT_RE = re.compile(r"(\d{1,2})h(\d{2})m\b")
_HR_MIN_RE = re.compile(r"(\d{1,3})\s*(?:hr|hrs|hour|hours?|h)\s*(\d{1,3})?\s*(?:min|mins|minute|minutes|minut|ut|m)?\b", re.I)
_MIN_ONLY_RE = re.compile(r"(\d{1,3})\s*(?:min|mins|minute|minutes|minut|ut|u|m)\b", re.I)
_STATION_RE = re.compile(r"\b(?:at|near|between|by)\s+([A-Za-z]{1,4})\b", re.I)
_REASON_RE = re.compile(
    r"\b(fog|signal|maintenance|crowding|weather|rain|derailment|track|congestion|power|overcast|storm|failure|breakdown)\b",
    re.I,
)


def parse_remark_line(line: str, station_codes=None) -> "dict":
    """Parse a single delay remark line into a dict. Returns None if unparseable."""
    date_m = _DATE_RE.search(line)
    train_m = _TRAIN_RE.search(line)
    compact_m = _COMPACT_RE.search(line)
    hr_min_m = _HR_MIN_RE.search(line)
    min_only_m = _MIN_ONLY_RE.search(line)

    if compact_m:
        delay_min = int(compact_m.group(1)) * 60 + int(compact_m.group(2))
    elif hr_min_m:
        delay_min = int(hr_min_m.group(1)) * 60 + (int(hr_min_m.group(2)) if hr_min_m.group(2) else 0)
    elif min_only_m:
        delay_min = int(min_only_m.group(1))
    else:
        delay_min = None

    station_code = None
    station_m = _STATION_RE.search(line)
    if station_m:
        token = station_m.group(1).upper()
        codes = [str(c).upper() for c in (station_codes or [])]
        if not codes or token in codes:
            station_code = token

    if delay_min is not None and re.search(r"\bearly\b", line, re.I):
        delay_min = -delay_min

    reason_m = _REASON_RE.search(line)
    reason = reason_m.group(1).lower() if reason_m else "unknown"

    if train_m is None or delay_min is None:
        return None
    return {
        "date": date_m.group(1) if date_m else None,
        "train_no": int(train_m.group(1)),
        "station_code": station_code,
        "delay_minutes": float(delay_min),
        "reason": reason,
    }


def read_delay_remarks(path: Path, station_codes=None) -> "tuple":
    """Read unstructured delay remarks.

    Returns (DataFrame of parsed remarks, list of unparseable lines).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Delay remarks file not found: {path}")
    lines = [ln.strip() for ln in path.read_text().splitlines() if ln.strip() and not ln.strip().startswith("#")]
    rows = []
    unparsed = []
    for line in lines:
        parsed = parse_remark_line(line, station_codes=station_codes)
        if parsed is None:
            unparsed.append(line)
            continue
        rows.append(parsed)
    df = pd.DataFrame(rows, columns=["date", "train_no", "station_code", "delay_minutes", "reason"])
    logger.info("TXT remarks source=%s total_lines=%d parsed=%d unparsed=%d", path, len(lines), len(rows), len(unparsed))
    for bad in unparsed:
        logger.warning("Unparseable remark line: %s", bad)
    return df, unparsed
