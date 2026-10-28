"""Data cleaning: missing values, duplicates, outliers, standardisation, features."""

import re

import pandas as pd

from src.config import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

TRAIN_NAME_ALIASES = {
    "mumbai - nagpur express": "Mumbai Nagpur Express",
    "mumbai nagpur express": "Mumbai Nagpur Express",
    "new delhi bhopal shatabdi": "New Delhi Bhopal Shatabdi",
}

SEASONS = ["Winter", "Summer", "Monsoon", "Post-Monsoon"]


def normalize_station_code(series: pd.Series) -> pd.Series:
    """Uppercase + trim station codes."""
    return series.astype(str).str.strip().str.upper()


def normalize_train_name(name) -> str:
    """Collapse whitespace and unify known train-name spellings."""
    if pd.isna(name):
        return name
    key = re.sub(r"\s+", " ", str(name).strip()).lower()
    return TRAIN_NAME_ALIASES.get(key, re.sub(r"\s+", " ", str(name).strip()).title())


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar / season / delay-category features to a delay DataFrame."""
    out = df.copy()
    dates = pd.to_datetime(out.get("date"), errors="coerce")
    out["year"] = dates.dt.year
    out["month"] = dates.dt.month
    out["month_name"] = dates.dt.month_name()
    out["day_of_week"] = dates.dt.day_name()
    out["is_weekend"] = dates.dt.dayofweek.isin([5, 6])

    season_by_month = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Summer", 4: "Summer", 5: "Summer", 6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Post-Monsoon", 10: "Post-Monsoon", 11: "Post-Monsoon"}
    out["season"] = dates.dt.month.map(season_by_month)
    out["is_fog_season"] = out["season"] == "Winter"

    def category(delay):
        if pd.isna(delay):
            return "Unknown"
        if delay <= 15:
            return "On-time"
        if delay <= 60:
            return "Minor"
        if delay <= 180:
            return "Major"
        return "Severe"

    out["delay_category"] = out["delay_minutes"].map(category)
    return out


def clean_trains(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise trains table."""
    out = df.copy()
    out["train_no"] = pd.to_numeric(out["train_no"], errors="coerce").astype("Int64")
    out["train_name"] = out["train_name"].astype(str).map(normalize_train_name)
    out["train_type"] = out["train_type"].astype(str).str.strip()
    out["source_station_code"] = normalize_station_code(out["source_station_code"])
    out["destination_station_code"] = normalize_station_code(out["destination_station_code"])
    out["zone"] = out["zone"].astype(str).str.strip()
    out["distance_km"] = pd.to_numeric(out["distance_km"], errors="coerce")
    return out


def clean_stations(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise stations table."""
    out = df.copy()
    out["station_code"] = normalize_station_code(out["station_code"])
    out["station_name"] = out["station_name"].astype(str).str.strip()
    out["state"] = out["state"].astype(str).str.strip()
    out["zone"] = out["zone"].astype(str).str.strip()
    out["latitude"] = pd.to_numeric(out["latitude"], errors="coerce")
    out["longitude"] = pd.to_numeric(out["longitude"], errors="coerce")
    return out


def clean_routes(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise train_stops table."""
    out = df.copy()
    out["train_no"] = pd.to_numeric(out["train_no"], errors="coerce").astype("Int64")
    out["stop_sequence"] = pd.to_numeric(out["stop_sequence"], errors="coerce").astype("Int64")
    out["station_code"] = normalize_station_code(out["station_code"])
    out["scheduled_arrival"] = out["scheduled_arrival"].astype(str).str.strip()
    out["scheduled_departure"] = out["scheduled_departure"].astype(str).str.strip()
    out["day"] = pd.to_numeric(out.get("day", 1), errors="coerce").fillna(1).astype(int)
    out["distance_from_source_km"] = pd.to_numeric(out["distance_from_source_km"], errors="coerce")
    return out


def clean_delay_records(df: pd.DataFrame, cap_minutes: float = 3000.0) -> pd.DataFrame:
    """Clean delay records: dtypes, missing values, duplicates, outliers, features."""
    config = load_config()
    cap = float(config.get("cleaning", {}).get("delay_cap_minutes", cap_minutes))
    out = df.copy()
    before = len(out)

    out["train_no"] = pd.to_numeric(out["train_no"], errors="coerce").astype("Int64")
    out["station_code"] = normalize_station_code(out["station_code"])
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["scheduled_arrival"] = pd.to_datetime(out["scheduled_arrival"], errors="coerce")
    out["actual_arrival"] = pd.to_datetime(out["actual_arrival"], errors="coerce")
    out["delay_minutes"] = pd.to_numeric(out["delay_minutes"], errors="coerce")
    out["cancelled"] = out["cancelled"].fillna(False).astype(bool)
    out["weather_condition"] = out["weather_condition"].fillna("Unknown").astype(str).str.strip().str.title()

    valid = out["date"].notna() & out["train_no"].notna() & out["station_code"].notna()
    n_invalid = int((~valid).sum())
    out = out[valid].copy()

    both = out["actual_arrival"].notna() & out["scheduled_arrival"].notna()
    computed = (out["actual_arrival"] - out["scheduled_arrival"]).dt.total_seconds() / 60
    out.loc[both, "delay_minutes"] = computed[both]

    missing = out["delay_minutes"].isna()
    imputed = int(missing.sum())
    train_medians = out.groupby("train_no")["delay_minutes"].transform("median")
    out["delay_minutes"] = out["delay_minutes"].fillna(train_medians).fillna(0.0).astype(float)

    dup_cols = ["date", "train_no", "station_code", "scheduled_arrival", "actual_arrival", "delay_minutes"]
    dups = out.duplicated(subset=dup_cols, keep="first")
    n_dups = int(dups.sum())
    out = out[~dups].copy()

    impossible = out["delay_minutes"] > cap
    n_impossible = int(impossible.sum())
    out = out[~impossible].copy()

    out = add_features(out)
    after = len(out)
    logger.info("Cleaning delay_records: before=%d after=%d invalid_dropped=%d imputed=%d duplicates_removed=%d impossible_dropped=%d",
                before, after, n_invalid, imputed, n_dups, n_impossible)
    return out


def clean_remarks(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise the cleaned delay_remarks table (assign remark_id)."""
    out = df.copy()
    out["train_no"] = pd.to_numeric(out["train_no"], errors="coerce").astype("Int64")
    out["station_code"] = normalize_station_code(out["station_code"].fillna(""))
    out["station_code"] = out["station_code"].replace({"": None, "NONE": None, "NAN": None})
    out["delay_minutes"] = pd.to_numeric(out["delay_minutes"], errors="coerce")
    out["reason"] = out["reason"].astype(str).str.strip().str.lower()
    out = out.dropna(subset=["train_no"]).copy()
    out["remark_id"] = range(1, len(out) + 1)
    return out.reset_index(drop=True)


def run_cleaning(data: dict):
    """Run cleaning over all raw tables.

    Returns (cleaned_data, cleaning_report).
    """
    before_counts = {k: len(v) for k, v in data.items() if isinstance(v, pd.DataFrame)}
    cleaned = {
        "trains": clean_trains(data.get("trains")),
        "stations": clean_stations(data.get("stations")),
        "routes": clean_routes(data.get("routes")),
        "delay_records": clean_delay_records(data.get("delay_records")),
        "delay_remarks": clean_remarks(data.get("delay_remarks")),
    }
    after_counts = {k: len(v) for k, v in cleaned.items()}
    from src.cleaning.cleaning_report import build_cleaning_report

    report = build_cleaning_report(before_counts, after_counts)
    remarks = cleaned.get("delay_remarks")
    if remarks is not None and len(remarks) > 0:
        train_nos = set(cleaned.get("trains", pd.DataFrame())["train_no"].dropna().astype(int).tolist())
        remarks = remarks[remarks["train_no"].isin(list(train_nos))].reset_index(drop=True)
        cleaned["delay_remarks"] = remarks
    return cleaned, report
