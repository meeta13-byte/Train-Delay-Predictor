"""JSON-lines bridge between the Express server (server/) and src/api.py.

The server starts one long-lived `python -m src.bridge` process and writes one
request per line to its stdin:

    {"id": 1, "method": "ui_dashboard", "params": {"filters": {...}}}

and reads one reply per line from stdout:

    {"id": 1, "ok": true, "result": {...}}      or
    {"id": 1, "ok": false, "error": "message"}

Only the functions listed in METHODS can be called. Logs go to stderr so
stdout stays clean JSON.
"""

import contextlib
import json
import logging
import sys
import traceback

import matplotlib

matplotlib.use("Agg")

from src import api  # noqa: E402

METHODS = {
    "db_status": api.db_status,
    "reset_cache": api.reset_cache,
    "meta": api.ui_meta,
    "home": api.ui_home,
    "dashboard": api.ui_dashboard,
    "delay_analysis": api.ui_delay_analysis,
    "train_explorer": api.ui_train_explorer,
    "stations": api.ui_stations,
    "forecast": api.ui_forecast,
    "pipeline": api.ui_pipeline,
    "run_query": api.run_predefined_query,
    "run_select": api.run_select_query,
    "lab_charts": api.list_lab_charts,
    "plan_journey": api.ui_plan_journey,
}


def handle(request: dict) -> dict:
    rid = request.get("id")
    method = request.get("method")
    fn = METHODS.get(method)
    if fn is None:
        return {"id": rid, "ok": False, "error": f"Unknown method: {method}"}
    try:
        # keep stray prints from libraries out of the JSON channel
        with contextlib.redirect_stdout(sys.stderr):
            result = fn(**(request.get("params") or {}))
        return {"id": rid, "ok": True, "result": api.to_jsonable(result)}
    except ValueError as e:
        return {"id": rid, "ok": False, "error": str(e)}
    except Exception as e:  # report, keep serving
        traceback.print_exc(file=sys.stderr)
        return {"id": rid, "ok": False, "error": f"{type(e).__name__}: {e}"}


def main() -> None:
    # The readers log DataFrame previews at INFO level; keep the server terminal quiet.
    logging.disable(logging.INFO)
    out = sys.stdout
    out.write(json.dumps({"ready": True}) + "\n")
    out.flush()
    # Warm the shared delay table now so the first page view is fast (requests queue meanwhile).
    with contextlib.suppress(Exception), contextlib.redirect_stdout(sys.stderr):
        if api.db_status().get("ready"):
            api.ui_meta()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            reply = {"id": None, "ok": False, "error": "Bad JSON request"}
        else:
            reply = handle(request)
        out.write(json.dumps(reply, allow_nan=False) + "\n")
        out.flush()


if __name__ == "__main__":
    main()
