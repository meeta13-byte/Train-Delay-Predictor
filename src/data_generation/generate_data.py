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
    # code, name, state, zone, lat, lon
    ("NDLS", "New Delhi", "Delhi", "NR", 28.64, 77.22),
    ("MTJ", "Mathura Jn", "Uttar Pradesh", "NCR", 27.48, 77.68),
    ("AGC", "Agra Cantt", "Uttar Pradesh", "NCR", 27.16, 77.99),
    ("GWL", "Gwalior", "Madhya Pradesh", "NCR", 26.22, 78.18),
    ("VGLJ", "Jhansi", "Uttar Pradesh", "NCR", 25.45, 78.58),
    ("BPL", "Bhopal", "Madhya Pradesh", "WCR", 23.27, 77.41),
    ("ET", "Itarsi Jn", "Madhya Pradesh", "WCR", 22.61, 77.76),
    ("NGP", "Nagpur", "Maharashtra", "CR", 21.15, 79.09),
    ("CSMT", "Mumbai CSMT", "Maharashtra", "CR", 18.94, 72.84),
    ("KYN", "Kalyan Jn", "Maharashtra", "CR", 19.24, 73.13),
    ("NK", "Nashik Road", "Maharashtra", "CR", 19.95, 73.84),
    ("BSL", "Bhusaval Jn", "Maharashtra", "CR", 21.05, 75.78),
    ("AK", "Akola Jn", "Maharashtra", "CR", 20.71, 77.00),
    ("BD", "Badnera Jn", "Maharashtra", "CR", 20.86, 77.73),
    ("WR", "Wardha Jn", "Maharashtra", "CR", 20.74, 78.60),
    ("KNW", "Khandwa Jn", "Madhya Pradesh", "CR", 21.82, 76.35),
    ("G", "Gondia Jn", "Maharashtra", "SECR", 21.46, 80.20),
    ("R", "Raipur Jn", "Chhattisgarh", "SECR", 21.25, 81.63),
    ("BSP", "Bilaspur Jn", "Chhattisgarh", "SECR", 22.08, 82.15),
    ("TATA", "Tatanagar Jn", "Jharkhand", "SER", 22.77, 86.20),
    ("HWH", "Howrah Jn", "West Bengal", "ER", 22.58, 88.34),
]

# Corridors: ordered (station_code, km from corridor start). Trains run along a
# corridor in either direction, stopping at a subset of its stations.
CORRIDORS = {
    "delhi_bhopal_nagpur": [
        ("NDLS", 0), ("MTJ", 141), ("AGC", 195), ("GWL", 313), ("VGLJ", 410),
        ("BPL", 701), ("ET", 793), ("NGP", 1091),
    ],
    "mumbai_nagpur": [
        ("CSMT", 0), ("KYN", 54), ("NK", 187), ("BSL", 443), ("AK", 581),
        ("BD", 663), ("WR", 760), ("NGP", 837),
    ],
    "mumbai_bhopal": [
        ("CSMT", 0), ("KYN", 54), ("NK", 187), ("BSL", 443), ("KNW", 567),
        ("ET", 750), ("BPL", 842),
    ],
    "nagpur_howrah": [
        ("NGP", 0), ("G", 130), ("R", 299), ("BSP", 410), ("TATA", 925), ("HWH", 1130),
    ],
}

# train_no, name, type, corridor, from, to, departure (HH:MM), stops (None = every station)
TRAIN_DEFS = [
    # Delhi - Bhopal - Nagpur
    (12002, "New Delhi Bhopal Shatabdi", "Shatabdi", "delhi_bhopal_nagpur", "NDLS", "BPL", "06:00", ["NDLS", "MTJ", "AGC", "GWL", "VGLJ", "BPL"]),
    (20172, "Delhi Bhopal Vande Bharat", "Vande Bharat", "delhi_bhopal_nagpur", "NDLS", "BPL", "15:00", ["NDLS", "AGC", "GWL", "VGLJ", "BPL"]),
    (12616, "Grand Trunk Express", "Mail/Express", "delhi_bhopal_nagpur", "NDLS", "NGP", "16:10", None),
    (12622, "Tamil Nadu Express", "Superfast", "delhi_bhopal_nagpur", "NDLS", "NGP", "21:05", ["NDLS", "AGC", "GWL", "VGLJ", "BPL", "ET", "NGP"]),
    (12430, "Delhi Nagpur Rajdhani", "Rajdhani", "delhi_bhopal_nagpur", "NDLS", "NGP", "20:50", ["NDLS", "AGC", "VGLJ", "BPL", "NGP"]),
    (51832, "Delhi Jhansi Passenger", "Passenger", "delhi_bhopal_nagpur", "NDLS", "VGLJ", "17:45", None),
    (12156, "Bhopal Express", "Superfast", "delhi_bhopal_nagpur", "NDLS", "BPL", "20:40", ["NDLS", "MTJ", "AGC", "GWL", "VGLJ", "BPL"]),
    (12001, "Bhopal New Delhi Shatabdi", "Shatabdi", "delhi_bhopal_nagpur", "BPL", "NDLS", "14:40", ["BPL", "VGLJ", "GWL", "AGC", "MTJ", "NDLS"]),
    (12155, "Bhopal Delhi Express", "Superfast", "delhi_bhopal_nagpur", "BPL", "NDLS", "20:35", ["BPL", "VGLJ", "GWL", "AGC", "MTJ", "NDLS"]),
    (12615, "Grand Trunk Express (Up)", "Mail/Express", "delhi_bhopal_nagpur", "NGP", "NDLS", "15:20", None),
    # Mumbai - Nagpur
    (12139, "Sewagram Express", "Superfast", "mumbai_nagpur", "CSMT", "NGP", "21:30", ["CSMT", "KYN", "NK", "BSL", "AK", "BD", "WR", "NGP"]),
    (12105, "Vidarbha Express", "Superfast", "mumbai_nagpur", "CSMT", "NGP", "19:05", ["CSMT", "KYN", "NK", "BSL", "AK", "BD", "WR", "NGP"]),
    (12289, "Mumbai Nagpur Duronto", "Duronto", "mumbai_nagpur", "CSMT", "NGP", "20:15", ["CSMT", "NGP"]),
    (12951, "Mumbai Nagpur Express", "Mail/Express", "mumbai_nagpur", "CSMT", "NGP", "18:40", None),
    (51153, "Mumbai Bhusaval Passenger", "Passenger", "mumbai_nagpur", "CSMT", "BSL", "07:10", ["CSMT", "KYN", "NK", "BSL"]),
    (12140, "Sewagram Express (Up)", "Superfast", "mumbai_nagpur", "NGP", "CSMT", "21:15", ["NGP", "WR", "BD", "AK", "BSL", "NK", "KYN", "CSMT"]),
    # Mumbai - Bhopal
    (12137, "Punjab Mail", "Mail/Express", "mumbai_bhopal", "CSMT", "BPL", "19:35", None),
    (11071, "Kamayani Express", "Mail/Express", "mumbai_bhopal", "CSMT", "BPL", "11:05", None),
    (12321, "Mumbai Bhopal Superfast", "Superfast", "mumbai_bhopal", "CSMT", "BPL", "21:50", ["CSMT", "KYN", "NK", "BSL", "KNW", "ET", "BPL"]),
    # Nagpur - Howrah
    (12860, "Gitanjali Express", "Superfast", "nagpur_howrah", "NGP", "HWH", "08:15", ["NGP", "G", "R", "BSP", "TATA", "HWH"]),
    (12130, "Azad Hind Express", "Mail/Express", "nagpur_howrah", "NGP", "HWH", "18:20", None),
    (58111, "Nagpur Raipur Passenger", "Passenger", "nagpur_howrah", "NGP", "R", "06:30", ["NGP", "G", "R"]),
    (22512, "Nagpur Howrah Duronto", "Duronto", "nagpur_howrah", "NGP", "HWH", "17:55", ["NGP", "R", "TATA", "HWH"]),
]

# Average running speed incl. halts (km/h) and halt length (min) by category.
SPEED_KMPH = {
    "Vande Bharat": 82, "Shatabdi": 84, "Rajdhani": 78, "Duronto": 76,
    "Superfast": 60, "Mail/Express": 52, "Passenger": 38,
}
HALT_MIN = {
    "Vande Bharat": 2, "Shatabdi": 2, "Rajdhani": 5, "Duronto": 5,
    "Superfast": 5, "Mail/Express": 5, "Passenger": 3,
}

BASE_DELAYS = {
    "Rajdhani": 12.0,
    "Shatabdi": 8.0,
    "Vande Bharat": 6.0,
    "Duronto": 15.0,
    "Superfast": 30.0,
    "Mail/Express": 50.0,
    "Passenger": 70.0,
}


def _season_multiplier(zone: str, month: int) -> float:
    if zone in ("NR", "NCR", "NER", "ECR", "NW", "WCR") and month in (12, 1, 2):
        return 1.9  # winter fog peak
    if month in (7, 8):
        return 1.5  # monsoon
    if month in (10, 11):
        return 1.3  # festive crowding
    return 1.0


def _weekday_multiplier(weekday: int) -> float:
    # Friday / Sunday rush
    return {4: 1.15, 6: 1.2}.get(weekday, 1.0)


def _train_reliability(train_no: int) -> float:
    """Stable per-train factor so some trains are chronically later than others."""
    return random.Random(train_no).uniform(0.7, 1.4)


def _fmt_hhmm(total_minutes: int) -> tuple:
    """Return ('HH:MM', day) where day 1 = the train's starting day."""
    day = total_minutes // 1440 + 1
    m = total_minutes % 1440
    return f"{m // 60:02d}:{m % 60:02d}", day


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


def _train_path(corridor: str, src: str, dst: str, stops) -> list:
    """Ordered [(station_code, km_from_source)] for a train running src -> dst."""
    line = CORRIDORS[corridor]
    codes = [c for c, _ in line]
    i, j = codes.index(src), codes.index(dst)
    seg = line[i:j + 1] if i < j else list(reversed(line[j:i + 1]))
    origin_km = seg[0][1]
    path = [(c, abs(km - origin_km)) for c, km in seg]
    if stops is not None:
        path = [p for p in path if p[0] in stops]
    return path


def generate_trains(stations: list) -> list:
    zone_by_code = {s["station_code"]: s["zone"] for s in stations}
    trains = []
    for train_no, train_name, train_type, corridor, src, dst, _dep, stops in TRAIN_DEFS:
        path = _train_path(corridor, src, dst, stops)
        trains.append(
            {
                "train_no": train_no,
                "train_name": train_name,
                "train_type": train_type,
                "source_station_code": src,
                "destination_station_code": dst,
                "zone": zone_by_code.get(src, "NR"),
                "distance_km": float(path[-1][1]),
            }
        )
    return trains


def generate_routes(trains: list, stations: list) -> dict:
    """Return {train_no: [stop dicts]} ordered by stop_sequence.

    Times are 'HH:MM' with a `day` counter (1 = day the train starts), the way
    Indian Railways timetables are printed.
    """
    defs = {d[0]: d for d in TRAIN_DEFS}
    routes = {}
    for train in trains:
        _, _, train_type, corridor, src, dst, dep, stops = defs[train["train_no"]]
        path = _train_path(corridor, src, dst, stops)
        speed, halt = SPEED_KMPH[train_type], HALT_MIN[train_type]
        h, m = map(int, dep.split(":"))
        start = h * 60 + m
        out = []
        for seq, (code, km) in enumerate(path):
            run = int(round(km / speed * 60 / 5.0) * 5)  # timetables use 5-min slots
            arr = start + run
            first, last = seq == 0, seq == len(path) - 1
            dep_t = arr if last else arr + (0 if first else halt)
            arr_s, arr_day = _fmt_hhmm(arr)
            dep_s, _ = _fmt_hhmm(dep_t)
            out.append(
                {
                    "train_no": train["train_no"],
                    "stop_sequence": seq,
                    "station_code": code,
                    "scheduled_arrival": arr_s,
                    "scheduled_departure": dep_s,
                    "day": arr_day,
                    "distance_from_source_km": float(km),
                }
            )
        routes[train["train_no"]] = out
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
        reliability = _train_reliability(train["train_no"])
        total_km = max(train["distance_km"], 1.0)
        for day_offset in range(days):
            d = start + timedelta(days=day_offset)
            mult = _season_multiplier(train["zone"], d.month) * _weekday_multiplier(d.weekday()) * reliability
            journey_factor = rng.uniform(0.3, 2.0)  # a bad day stays bad all the way
            cancelled = rng.random() < 0.01
            for stop in stops:
                seq = stop["stop_sequence"]
                progress = stop["distance_from_source_km"] / total_km
                run_date = d + timedelta(days=stop["day"] - 1)
                sched_arr = f"{run_date.isoformat()} {stop['scheduled_arrival']}"
                if cancelled:
                    delay = 0.0
                elif seq == 0:
                    delay = max(0.0, rng.gauss(3, 4))  # late start from origin
                else:
                    delay = BASE_DELAYS[train["train_type"]] * mult * journey_factor * (0.3 + 0.9 * progress) * rng.uniform(0.85, 1.15)
                if not cancelled and seq > 0 and rng.random() < 0.04:
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
                        "weather_condition": "Unknown" if cancelled else ("Fog" if _season_multiplier(train["zone"], d.month) > 1.5 and rng.random() < 0.7 else "Clear"),
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
        "Train 12951 arrived 45 mins late, signal failure near BSL",
        "12105 delayed 2h05m due to track maintenance at BSL",
        "12616 running 1 hr late due to crowding in coaches",
        "12860 was 30 minutes late because of heavy rain in the region",
        "12137 held up 2 hr 10 min at ET due to derailment",
        "12002 departed 18 mins early due to scheduling correction",
        "not a valid remark line at all !!!",
    ]


# Bump when the shape of generated data changes so stale raw files get rebuilt.
GENERATOR_VERSION = "2"


def write_raw_data(raw_dir: Path, regenerate: bool = False) -> list:
    raw_dir = Path(raw_dir)
    version_file = raw_dir / ".generator_version"
    up_to_date = version_file.exists() and version_file.read_text().strip() == GENERATOR_VERSION
    if raw_dir.exists() and up_to_date and not regenerate:
        return sorted(p for p in raw_dir.glob("*") if p.is_file() and not p.name.startswith("."))

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
            ET.SubElement(st, "day").text = str(stop["day"])
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

    version_file.write_text(GENERATOR_VERSION)
    return paths


if __name__ == "__main__":
    from src.utils.logger import get_logger

    logger = get_logger(__name__)
    paths = write_raw_data(Path(__file__).resolve().parents[2] / "data" / "raw", regenerate=True)
    for p in paths:
        logger.info("Wrote %s", p)
