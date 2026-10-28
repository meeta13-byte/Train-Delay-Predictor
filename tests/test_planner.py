from datetime import date, time

import pytest

from src.database.db_loader import get_engine
from src.data_generation.generate_data import generate_routes, generate_stations, generate_trains
from src.planner import PlannerError, plan_journey, route_options

ENGINE = get_engine("sqlite")
TRAVEL = date(2026, 12, 18)


def test_routes_follow_real_corridors():
    stations = generate_stations()
    routes = generate_routes(generate_trains(stations), stations)
    for stops in routes.values():
        km = [s["distance_from_source_km"] for s in stops]
        assert km == sorted(km) and km[0] == 0
        # arrival clock + day counter never goes backwards
        t = [(s["day"], s["scheduled_arrival"]) for s in stops]
        assert t == sorted(t)


def test_route_options_only_forward_trains():
    opts = route_options(ENGINE, "CSMT", "NGP")
    assert len(opts) >= 3
    assert (opts["run_minutes"] > 0).all()
    assert 12140 not in set(opts["train_no"])  # runs NGP -> CSMT


def test_plan_journey_predicts_and_ranks():
    r = plan_journey(ENGINE, to_code="NGP", travel_date=TRAVEL, train_no=12951)
    assert r["from_code"] == "CSMT"
    assert r["your_train"]["train_no"] == 12951
    opts = r["options"]
    assert list(opts["expected_arr"]) == sorted(opts["expected_arr"])
    assert r["suggestions"], "slower Mail/Express should get faster alternatives"
    assert all(s["gain_minutes"] >= 10 or s["kind"] == "leave_later_same_arrival" for s in r["suggestions"])


def test_plan_by_category_only():
    r = plan_journey(ENGINE, to_code="R", from_code="NGP", travel_date=TRAVEL, train_type="Passenger")
    assert r["your_train"]["train_type"] == "Passenger"


def test_leave_after_filters_trains():
    r = plan_journey(ENGINE, to_code="BPL", from_code="NDLS", travel_date=TRAVEL, leave_after=time(18, 0))
    assert (r["options"]["sched_dep"].dt.hour >= 18).all()


def test_wrong_direction_is_rejected():
    with pytest.raises(PlannerError):
        plan_journey(ENGINE, to_code="CSMT", from_code="NGP", travel_date=TRAVEL, train_no=12951)
