"""Tests for database layer."""

from src.database import queries
from src.database.db_loader import create_schema, get_engine, load_to_db, run_integrity_check
from src.ingestion.loader import load_all
from src.cleaning.cleaner import run_cleaning


def test_db_load_row_counts():
    import os

    cleaned, _ = run_cleaning(load_all())
    engine = get_engine("sqlite")
    create_schema(engine)
    counts = load_to_db(cleaned, engine)
    assert counts["stations"] == len(cleaned["stations"])
    assert counts["trains"] == len(cleaned["trains"])


def test_fk_integrity():
    import os

    cleaned, _ = run_cleaning(load_all())
    engine = get_engine("sqlite")
    create_schema(engine)
    load_to_db(cleaned, engine)
    integrity = run_integrity_check(engine)
    assert integrity["orphan_delay_train_no"] == 0
    assert integrity["orphan_delay_station"] == 0


def test_sql_queries_return_dataframes():
    import pandas as pd

    cleaned, _ = run_cleaning(load_all())
    engine = get_engine("sqlite")
    create_schema(engine)
    load_to_db(cleaned, engine)
    df = queries.top_delayed_trains(engine)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
