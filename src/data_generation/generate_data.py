"""Synthetic Indian Railways delay data generator.

Produces realistic, reproducible sample data in CSV / JSON / XML / TXT formats
so the analytics pipeline can run fully offline. A fixed random seed keeps the
output reproducible.
"""

import csv
import json
import random
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path

STATIONS = [
    ("NGP", "Nagpur", "Maharashtra", "CR", 21.15, 79.10),
    ("NDLS", "New Delhi", "Delhi", "NR", 28.63, 77.22),
    ("CSMT", "Mumbai", "Maharashtra", "CR", 19.08, 72.88),
    ("HWH", "Howrah", "West Bengal", "ER", 22.58, 88.26),
    ("MAS", "Chennai", "Tamil Nadu", "SR", 13.04, 80.27),
    ("SBC", "Bengaluru", "Karnataka", "SBC", 12.97, 77.59),
    ("BPL", "Bhopal", "Madhya Pradesh", "NFR", 23.18, 77.41),
    ("ADM", "Port Blair", "Andaman and Nicobar Islands", "??", 11.68, 92.74),
    ("JT", "Jaisalmer", "Rajasthan", "NW", 26.83, 70.88),
    ("LKO", "Lucknow", "Uttar Pradesh", "NR", 26.95, 80.79),
    ("KOTA", "Kota", "Rajasthan", "NW", 26.20, 73.84),
    ("ET", "Prayagraj", "Uttar Pradesh", "NER", 27.19, 78.28),
    ("GSH", "Gondia", "Maharashtra", "CR", 21.26, 78.86),
    ("G", "Gandhidham", "Gujarat", "NR", 23.24, 71.57),
    ("PDU", "Patiala", "Punjab", "NR", 30.33, 75.75),
    ("LDH", "Ludhiana", "Punjab", "NR", 30.70, 75.85),
    ("JM", "Jamnagar", "Gujarat", "NW", 22.45, 69.99),
    ("UJN", "Ratnagiri", "Maharashtra", "CR", 16.70, 73.92),
    ("PPT", "Porbandar", "Gujarat", "NR", 22.41, 69.86),
    ("SA", "Surat", "Gujarat", "ST", 21.17, 72.83),
    ("BRC", "Bharatpur", "Rajasthan", "NR", 27.78, 77.97),
    ("NCU", "Nagpur", "Maharashtra", "CR", 21.15, 79.10),
]

TRAIN_DEFS = [
    (12139, "Mumbai Rajdhani", "Rajdhani", "CSMT", "NDLS"),
    (12951, "Mumbai Nagpur Express", "Superfast", "CSMT", "NGP"),
    (23019, "Delhi Bhopal Rajdhani", "Rajdhani", "NDLS", "BPL"),
    (12002, "New Delhi Bhopal Shatabdi", "Shatabdi", "NDLS", "BPL"),
    (20919, "Delhi Bhopal Vande Bharat", "Vande Bharat", "NDLS", "BPL"),
    (12408, "Mumbai Nagpur Express", "Mail/Express", "CSMT", "NGP"),
    (12621, "Malwa Express", "Mail/Express", "BPL", "SBC"),
    (12864, "Delhi Bhopal Shramik Express", "Passenger", "NDLS", "BPL"),
    (12295, "Mumbai Indore Express", "Superfast", "CSMT", "BPL"),
    (12420, "Nanded Mumbai Superfast", "Superfast", "NGP", "CSMT"),
    (12627, "Marudhar Express", "Mail/Express", "BPL", "NDLS"),
    (12309, "Vaishali Express", "Mail/Express", "NDLS", "BPL"),
]

BASE_DELAYS = {
    "Rajdhani": 6.0,
    "Shatabdi": 8.0,
    "Vande Bharat": 5.0,
    "Duronto": 10.0,
    "Superfast": 25.0,
    "Mail/Express": 45.0,
    "Passenger": 55.0,
}


def _season_multiplier(zone: str, month: int) -> float:
    if zone in ("NR", "NCR", "NER", "ECR", "NW", "NFR") and month in (12, 1, 2):
        return 1.9  # winter fog peak
    if month in (7, 8):
        return 1.5  # monsoon
    if month in (10, 11):
        return 1.3  # festive crowding
    return 1.0


def generate_stations() -> list:
    return [
        {
            "station_code": code,
            "station_name": name,
            "state": state,
            "zone": zone,
            "latitude": lat,
            "longitude": lon,
        }
        for code, name, state, zone, lat, lon in STATIONS
    ]


def generate_trains(stations: list) -> list:
    codes = [s["station_code"] for s in stations]
    zone_by_code = {s["station_code"]: s["zone"] for s in stations}
    trains = []
    for idx, (train_no, train_name, train_type, source, dest) in enumerate(TRAIN_DEFS, start=1):
        src = source if source in codes else codes[0]
        dst = dest if dest in codes else codes[-1]
        trains.append(
            {
                "train_no": train_no,
                "train_name": train_name,
                "train_type": train_type,
                "source_station_code": src,
                "destination_station_code": dst,
                "zone": zone_by_code.get(src, "NR"),
                "distance_km": 1400.0 + idx * 37.5,
            }
        )
    return trains


def generate_routes(trains: list, stations: list) -> dict:
    """Return {train_no: [stop dicts]} ordered by stop_sequence."""
    codes = [s["station_code"] for s in stations]
    routes = {}
    for train in trains:
        n_stops = 3 + (train["train_no"] % 4)
        stops = []
        step = train["distance_km"] / (n_stops - 1) if n_stops > 1 else train["distance_km"]
        for seq in range(n_stops):
            frac = seq / (n_stops - 1) if n_stops > 1 else 0.0
            code = codes[int(frac * (len(codes) - 1))]
            stops.append(
                {
                    "train_no": train["train_no"],
                    "stop_sequence": seq,
                    "station_code": code,
                    "scheduled_arrival": f"{6 + int(frac * 14):02d}:{int(frac * 60) % 60:02d}",
                    "scheduled_departure": f"{7 + int(frac * 13):02d}:{int(frac * 40) % 60:02d}",
                    "distance_from_source_km": round(step * seq, 1),
                }
            )
        routes[train["train_no"]] = stops
    return routes


def _add_minutes(ts: str, minutes: float) -> str:
    dt = datetime.fromisoformat(ts.strip())
    return (dt + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M")


def generate_delay_records(trains, routes, stations, start_year=2023, end_year=2025, seed=42):
    rng = random.Random(seed)
    records = []
    record_id = 1
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    days = (end - start).days + 1

    for train in trains:
        stops = routes.get(train["train_no"], [])
        for day_offset in range(days):
            d = start + timedelta(days=day_offset)
            season_mult = _season_multiplier(train["zone"], d.month)
            for stop in stops:
                seq = stop["stop_sequence"]
                sched_arr = f"{d.year:04d}-{d.month:02d}-{d.day:02d} {stop['scheduled_arrival']}"
                cancelled = rng.random() < 0.01
                delay = 0.0 if cancelled else BASE_DELAYS[train["train_type"]] * rng.uniform(0.4, 2.0) * season_mult * (1 + 0.05 * seq)
                if rng.random() < 0.04:
                    delay = -rng.uniform(0, 12)
                if rng.random() < 0.015:
                    delay = round(rng.uniform(3000, 8000), 1)
                actual_arr = sched_arr if cancelled else _add_minutes(sched_arr, delay)
                missing = (not cancelled) and rng.random() < 0.03
                records.append(
                    {
                        "record_id": record_id,
                        "date": d.isoformat(),
                        "train_no": train["train_no"],
                        "station_code": stop["station_code"],
                        "scheduled_arrival": sched_arr,
                        "actual_arrival": "" if missing else actual_arr,
                        "delay_minutes": None if missing else (round(delay, 1) if not cancelled else 0),
                        "weather_condition": "Unknown" if cancelled else ("Fog" if season_mult > 1.5 and rng.random() < 0.7 else "Clear"),
                        "cancelled": cancelled,
                    }
                )
                record_id += 1

    # Deliberate duplicates (~2%)
    for _ in range(int(len(records) * 0.02)):
        records.append(dict(rng.choice(records)))

    # Deliberate malformed rows
    records.append(
        {
            "record_id": 900001,
            "date": "2023-13-45",
            "train_no": 12139,
            "station_code": "NDLS",
            "scheduled_arrival": "2023-13-45 06:10",
            "actual_arrival": "",
            "delay_minutes": None,
            "weather_condition": "Unknown",
            "cancelled": False,
        }
    )
    records.append(
        {
            "record_id": 900002,
            "date": "invalid-date",
            "train_no": 12951,
            "station_code": "NGP",
            "scheduled_arrival": "invalid-date 06:10",
            "actual_arrival": "",
            "delay_minutes": None,
            "weather_condition": "Unknown",
            "cancelled": False,
        }
    )
    return records


def generate_remarks() -> list:
    return [
        "2024-01-12 | 12139 | Late by 3 hr 20 min at NGP due to dense fog",
        "Train 12951 arrived 45 mins late, signal failure near BPL",
        "12133 delayed 2h05m due to track maintenance at G",
        "12947 running 1 hr late due to crowding in coaches",
        "17221 was 30 minutes late because of heavy rain in the region",
        "17117 held up 2 hr 10 min at BPL due to derailment",
        "12438 departed 18 mins early due to scheduling correction",
        "not a valid remark line at all !!!",
    ]


def write_raw_data(raw_dir: Path, regenerate: bool = False) -> list:
    raw_dir = Path(raw_dir)
    if raw_dir.exists() and not regenerate:
        return sorted(p for p in raw_dir.glob("*") if p.is_file())

    raw_dir.mkdir(parents=True, exist_ok=True)
    stations = generate_stations()
    trains = generate_trains(stations)
    routes = generate_routes(trains, stations)
    records = generate_delay_records(trains, routes, stations)

    paths = []

    trains_path = raw_dir / "trains.csv"
    with open(trains_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["train_no", "train_name", "train_type", "source_station_code", "destination_station_code", "zone", "distance_km"])
        for t in trains:
            w.writerow([t["train_no"], t["train_name"], t["train_type"], t["source_station_code"], t["destination_station_code"], t["zone"], t["distance_km"]])
    paths.append(trains_path)

    stations_path = raw_dir / "stations.json"
    with open(stations_path, "w") as f:
        json.dump(stations, f, indent=2)
    paths.append(stations_path)

    routes_path = raw_dir / "routes.xml"
    root = ET.Element("trains")
    for train_no in sorted(routes):
        train = next((t for t in trains if t["train_no"] == train_no), None)
        tr = ET.SubElement(root, "train", {"train_no": str(train_no)})
        if train is not None:
            ET.SubElement(tr, "train_name").text = train["train_name"]
        for stop in routes[train_no]:
            st = ET.SubElement(tr, "stop", {"stop_sequence": str(stop["stop_sequence"])})
            ET.SubElement(st, "station_code").text = stop["station_code"]
            ET.SubElement(st, "scheduled_arrival").text = stop["scheduled_arrival"]
            ET.SubElement(st, "scheduled_departure").text = stop["scheduled_departure"]
            ET.SubElement(st, "distance_from_source_km").text = str(stop["distance_from_source_km"])
    ET.ElementTree(root).write(routes_path, encoding="unicode")
    paths.append(routes_path)

    records_path = raw_dir / "delay_records.csv"
    with open(records_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["record_id", "date", "train_no", "station_code", "scheduled_arrival", "actual_arrival", "delay_minutes", "weather_condition", "cancelled"])
        for r in records:
            w.writerow([
                r["record_id"], r["date"], r["train_no"], r["station_code"],
                r["scheduled_arrival"], r["actual_arrival"],
                "" if r["delay_minutes"] is None else r["delay_minutes"],
                r["weather_condition"], r["cancelled"],
            ])
    paths.append(records_path)

    remarks_path = raw_dir / "delay_remarks.txt"
    with open(remarks_path, "w") as f:
        for line in generate_remarks():
            f.write(line + "\n")
    paths.append(remarks_path)

    return paths


if __name__ == "__main__":
    from src.utils.logger import get_logger

    logger = get_logger(__name__)
    paths = write_raw_data(Path(__file__).resolve().parents[2] / "data" / "raw", regenerate=True)
    for p in paths:
        logger.info("Wrote %s", p)
