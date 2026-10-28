"""Tests for ingestion layer."""

from pathlib import Path

import pandas as pd

from src.ingestion.csv_reader import read_delay_records_csv, read_trains_csv
from src.ingestion.json_reader import read_stations_json
from src.ingestion.loader import load_all
from src.ingestion.txt_reader import parse_remark_line, read_delay_remarks
from src.ingestion.xml_reader import read_routes_xml


def test_read_trains_csv():
    df = read_trains_csv("data/raw/trains.csv")
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


def test_read_delay_records_csv():
    df = read_delay_records_csv("data/raw/delay_records.csv")
    assert isinstance(df, pd.DataFrame)
    assert "delay_minutes" in df.columns


def test_read_stations_json():
    df = read_stations_json("data/raw/stations.json")
    assert isinstance(df, pd.DataFrame)
    assert "station_code" in df.columns


def test_read_routes_xml():
    df = read_routes_xml("data/raw/routes.xml")
    assert isinstance(df, pd.DataFrame)
    assert "stop_sequence" in df.columns


def test_read_delay_remarks():
    df, unparsed = read_delay_remarks("data/raw/delay_remarks.txt")
    assert isinstance(df, pd.DataFrame)
    assert isinstance(unparsed, list)


def test_parse_remark_line():
    parsed = parse_remark_line("2024-01-12 | 12139 | Late by 3 hr 20 min at NGP due to dense fog")
    assert parsed is not None


def test_load_all():
    data = load_all()
    assert set(["trains", "stations", "routes", "delay_records", "delay_remarks"]).issubset(data.keys())


def test_early_remark_is_negative_delay():
    parsed = parse_remark_line("12002 departed 18 mins early due to scheduling correction")
    assert parsed["delay_minutes"] == -18


def test_generator_keeps_user_data(tmp_path):
    from src.data_generation.generate_data import write_raw_data

    raw = tmp_path / "raw"
    write_raw_data(raw)  # empty folder -> generate
    assert (raw / ".generator_version").exists()
    (raw / ".generator_version").unlink()
    (raw / "trains.csv").write_text("user data")
    write_raw_data(raw)  # no marker -> user's own files, keep them
    assert (raw / "trains.csv").read_text() == "user data"
    (raw / ".generator_version").write_text("1")
    write_raw_data(raw)  # old marker -> rebuild
    assert (raw / "trains.csv").read_text() != "user data"
