"""Database loading: SQLAlchemy engine, schema creation, to_sql, sqlite3 + Excel import, integrity check."""

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.utils.logger import get_logger

from src.database.schema import Base

logger = get_logger(__name__)

TABLE_ORDER = ["stations", "trains", "train_stops", "delay_records", "delay_remarks"]


def get_engine(db_type: str = "sqlite"):
    from src.config import load_config

    config = load_config()
    url = config.get("db", {}).get("url", "sqlite:///data/railway.db")
    if db_type not in ("sqlite", "mysql", "postgresql"):
        raise ValueError(f"Unsupported db type: {db_type}")
    if db_type == "sqlite":
        url = "sqlite:///" + str((Path(__file__).resolve().parents[2] / "data" / "railway.db").resolve())
    return create_engine(url, future=True)


def create_schema(engine) -> None:
    """(Re)create all tables from the SQLAlchemy models so each pipeline run starts clean."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    logger.info("Database schema created")


DELAY_RECORD_COLUMNS = [
    "record_id", "date", "train_no", "station_code", "scheduled_arrival", "actual_arrival",
    "delay_minutes", "weather_condition", "cancelled",
]


def load_to_db(data: dict, engine) -> dict:
    """Load cleaned DataFrames into the DB in parent->child order; returns row counts."""
    df_map = {
        "stations": data.get("stations"),
        "trains": data.get("trains"),
        "train_stops": data.get("routes"),
        "delay_records": data.get("delay_records"),
        "delay_remarks": data.get("delay_remarks"),
    }
    counts = {}
    for table in TABLE_ORDER:
        df = df_map.get(table)
        if df is None or len(df) == 0:
            counts[table] = 0
            continue
        if table == "train_stops":
            df = df.drop(columns=["train_name"], errors="ignore")
        if table == "delay_records":
            df = df[[c for c in DELAY_RECORD_COLUMNS if c in df.columns]]
        if table == "delay_remarks":
            # ensure remark_id is present
            if "remark_id" not in df.columns:
                df = df.copy()
                df["remark_id"] = range(1, len(df) + 1)
        try:
            df.to_sql(table, engine, if_exists="append", index=False)
        except Exception as e:
            logger.warning("Append to %s failed (%s); replacing table", table, str(e).splitlines()[0])
            df.to_sql(table, engine, if_exists="replace", index=False)
        counts[table] = int(len(df))
        logger.info("Loaded table=%s rows=%d", table, counts[table])
    return counts


def load_cleaned_excel(path, engine) -> int:
    """Read the cleaned Excel workbook and append its sheets into the DB."""
    path = str(path)
    xl = pd.read_excel(path, sheet_name=None)
    total = 0
    sheet_map = {
        "trains": "trains",
        "stations": "stations",
        "routes": "train_stops",
        "delay_records": "delay_records",
        "delay_remarks": "delay_remarks",
    }
    for sheet, table in sheet_map.items():
        if sheet not in xl:
            continue
        df = xl[sheet]
        df.to_sql(table, engine, if_exists="append", index=False)
        total += int(len(df))
    logger.info("Loaded %d rows from cleaned Excel workbook", total)
    return total


def run_integrity_check(engine) -> dict:
    """Check referential integrity; return orphan counts per table."""
    with engine.begin() as conn:
        orphans_delays_train = conn.execute(
            text("SELECT COUNT(*) FROM delay_records d LEFT JOIN trains t ON d.train_no = t.train_no WHERE t.train_no IS NULL")
        ).scalar()
        orphans_delays_station = conn.execute(
            text("SELECT COUNT(*) FROM delay_records d LEFT JOIN stations s ON d.station_code = s.station_code WHERE s.station_code IS NULL")
        ).scalar()
        orphans_remarks_train = conn.execute(
            text("SELECT COUNT(*) FROM delay_remarks r LEFT JOIN trains t ON r.train_no = t.train_no WHERE t.train_no IS NULL")
        ).scalar()
        orphans_remarks_station = conn.execute(
            text("SELECT COUNT(*) FROM delay_remarks r LEFT JOIN stations s ON r.station_code = s.station_code WHERE s.station_code IS NULL AND r.station_code IS NOT NULL")
        ).scalar()
        total_delays = conn.execute(text("SELECT COUNT(*) FROM delay_records")).scalar()
    return {
        "delay_records_total": int(total_delays),
        "orphan_delay_train_no": int(orphans_delays_train),
        "orphan_delay_station": int(orphans_delays_station),
        "orphan_remark_train_no": int(orphans_remarks_train),
        "orphan_remark_station": int(orphans_remarks_station),
    }
