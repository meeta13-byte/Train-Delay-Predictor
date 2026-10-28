"""Tests for the JSON helpers used by the web UI (src/api.py + src/bridge.py)."""

import json

import pytest

from src import api, bridge


def _json_ok(obj):
    json.dumps(api.to_jsonable(obj), allow_nan=False)


def test_meta_and_home():
    meta = api.ui_meta()
    assert meta["train_types"] and meta["zones"] and meta["stations"]
    home = api.ui_home()
    assert home["total_records"] > 0 and 0 <= home["ontime_pct"] <= 100
    _json_ok(meta), _json_ok(home)


def test_dashboard_filters_and_empty_state():
    full = api.ui_dashboard({})
    winter = api.ui_dashboard({"season": "Winter", "train_types": ["Passenger"]})
    assert winter["kpis"]["total_records"] < full["kpis"]["total_records"]
    assert len(full["heatmap"]["months"]) == 12
    assert api.ui_dashboard({"start": "1990-01-01", "end": "1990-02-01"}) == {"empty": True}


def test_delay_analysis_and_explorer():
    d = api.ui_delay_analysis({})
    assert sum(d["histogram"]["counts"]) > 0
    assert {b["label"] for b in d["by_season"]} == set(api.SEASON_ORDER)
    for i in range(len(d["category_share"]["types"])):
        assert abs(sum(s["values"][i] for s in d["category_share"]["series"]) - 100) < 0.5
    t = api.ui_train_explorer(12616)
    assert t["accumulation"][0]["stop_sequence"] == 0 and t["accumulation"][-1]["station_code"] == "NGP"
    _json_ok(d), _json_ok(t)


@pytest.mark.parametrize("scope", [{"kind": "all"}, {"kind": "train_type", "value": "Passenger"}, {"kind": "train", "value": 12002}])
def test_forecast_scopes(scope):
    f = api.ui_forecast(scope)
    assert len(f["forecast"]["values"]) == 3
    assert all(lo <= v <= hi for lo, v, hi in zip(f["forecast"]["lower"], f["forecast"]["values"], f["forecast"]["upper"]))
    assert len(f["smoothing"]["hw_forecast"]) == 3
    _json_ok(f)


def test_select_only_sql():
    assert api.run_select_query("SELECT COUNT(*) AS n FROM trains")["rows"][0]["n"] > 0
    for bad in ["DELETE FROM trains", "select 1; drop table trains", "PRAGMA table_info(trains)",
                "WITH x AS (SELECT 1) DELETE FROM trains"]:
        with pytest.raises(ValueError):
            api.run_select_query(bad)


def test_predefined_queries_expose_sql():
    qs = api.list_predefined_queries()
    assert all(q["sql"].upper().startswith("SELECT") for q in qs)
    assert api.run_predefined_query("worst_stations")["rows"]


def test_pipeline_overview():
    p = api.ui_pipeline()
    formats = {f["format"] for f in p["files"]}
    assert formats == {"CSV", "JSON", "XML", "TXT"}
    assert p["er_diagram"].startswith("erDiagram")
    assert p["integrity"]["orphan_delay_train_no"] == 0
    _json_ok(p)


def test_plan_journey_json():
    r = api.ui_plan_journey(train_no="12951", to_code="NGP", travel_date="2026-12-18", leave_after="")
    assert r["your_train"]["train_no"] == 12951 and r["options"]
    assert "error" in api.ui_plan_journey(train_no="12951", to_code="HWH", travel_date="2026-12-18")
    _json_ok(r)


def test_bridge_dispatch():
    assert bridge.handle({"id": 1, "method": "db_status"})["ok"]
    assert not bridge.handle({"id": 2, "method": "__import__"})["ok"]
    bad = bridge.handle({"id": 3, "method": "run_select", "params": {"sql": "drop table trains"}})
    assert bad == {"id": 3, "ok": False, "error": "Only SELECT queries are allowed."}
