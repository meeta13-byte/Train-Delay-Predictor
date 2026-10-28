"""Load all raw data sources into a dict of DataFrames."""

from pathlib import Path

from src.config import load_config
from src.ingestion.csv_reader import read_delay_records_csv, read_trains_csv
from src.ingestion.json_reader import read_stations_json
from src.ingestion.xml_reader import read_routes_xml
from src.ingestion.txt_reader import read_delay_remarks

EXPECTED_FILES = [
    ("trains", "trains.csv"),
    ("stations", "stations.json"),
    ("routes", "routes.xml"),
    ("delay_records", "delay_records.csv"),
    ("delay_remarks", "delay_remarks.txt"),
]


def load_all(raw_dir=None) -> dict:
    """Load every raw data source into a keyed dict of DataFrames.

    Keys: trains, stations, routes, delay_records, delay_remarks.
    """
    config = load_config()
    raw_dir = Path(raw_dir or config["paths"]["raw_dir"])
    raw_dir = raw_dir if raw_dir.is_absolute() else raw_dir.resolve()

    missing = [str(raw_dir / fname) for _, fname in EXPECTED_FILES if not (raw_dir / fname).exists()]
    if missing:
        raise FileNotFoundError(
            "Missing raw data file(s): " + ", ".join(missing) + ". Run `python src/data_generation/generate_data.py` first."
        )

    data = {
        "trains": read_trains_csv(raw_dir / "trains.csv"),
        "stations": read_stations_json(raw_dir / "stations.json"),
        "routes": read_routes_xml(raw_dir / "routes.xml"),
        "delay_records": read_delay_records_csv(raw_dir / "delay_records.csv"),
    }
    remarks_df, remarks_unparsed = read_delay_remarks(raw_dir / "delay_remarks.txt")
    data["delay_remarks"] = remarks_df
    data["delay_remarks_unparsed"] = remarks_unparsed
    return data
