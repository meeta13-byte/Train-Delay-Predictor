"""Tests for cleaning layer."""

import pandas as pd

from src.cleaning.cleaner import clean_delay_records, clean_routes, clean_stations, clean_trains, run_cleaning
from src.ingestion.loader import load_all


def test_clean_trains_dtypes():
    data = load_all()
    cleaned = clean_trains(data["trains"])
    assert cleaned is not None


def test_duplicates_removed():
    data = load_all()
    cleaned, report = run_cleaning(data)
    dr = cleaned["delay_records"]
    # check no exact duplicates in key columns
    dup_cols = ["date", "train_no", "station_code", "scheduled_arrival"]
    assert dr.duplicated(subset=dup_cols).sum() == 0


def test_no_impossible_values():
    data = load_all()
    cleaned, report = run_cleaning(data)
    dr = cleaned["delay_records"]
    assert dr["delay_minutes"].max() <= 5000


def test_features_added():
    data = load_all()
    cleaned, report = run_cleaning(data)
    dr = cleaned["delay_records"]
    for col in ["year", "month", "season", "delay_category", "is_weekend"]:
        assert col in dr.columns


def test_cleaned_excel_has_headers(tmp_path):
    import pandas as pd
    from src.cleaning.cleaning_report import write_cleaned_excel

    data, report = run_cleaning(load_all())
    small = {k: (v.head(50) if hasattr(v, "head") else v) for k, v in data.items()}
    path = tmp_path / "cleaned.xlsx"
    write_cleaned_excel(small, report, path)
    sheets = pd.read_excel(path, sheet_name=None)
    assert list(sheets["trains"].columns) == list(data["trains"].columns)
    assert pd.api.types.is_numeric_dtype(sheets["delay_records"]["delay_minutes"])
    assert "Cleaning_Report" in sheets
