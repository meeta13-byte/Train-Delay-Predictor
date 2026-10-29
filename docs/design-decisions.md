# Design decisions

Why this project is built the way it is: each choice, the alternative that was rejected, and the
trade-off that came with it. Written for the viva — read this before the demo.

> Honesty rule: the data is simulated (seeded generator, `seed: 42`). Every number in this project
> demonstrates a *method* on structured data; none of it forecasts real trains.

---

## 1. Shape of the project

Two halves, one data store.

| Half | Code | Job |
|---|---|---|
| Analytics pipeline | `main.py`, `src/` | Generate → ingest 4 formats → clean → load SQLite → SQL queries → charts → ARIMA forecast → Excel/CSV/report artifacts |
| Web app | `server/`, `client/` | Read that same database: KPIs, filters, SQL playground, forecast, journey planner |

`data/railway.db` is the contract between them. The pipeline writes it, the web app only reads it.

```
generate_data.py  →  data/raw/{trains.csv, stations.json, routes.xml,
                                 delay_records.csv, delay_remarks.txt, manual_delay_log.csv}
        ↓  ingestion/   (4 readers → one dict of DataFrames)
   cleaning/cleaner.py (normalise, drop dupes, impute, cap, feature engineering)
        ↓  data/processed/*_cleaned.csv  +  outputs/excel/*.xlsx
   database/schema.py + db_loader.py  →  data/railway.db (5 tables, PK/FK)
        ↓
   database/queries.py (9 SQL queries) → outputs/reports/*.csv
   visualization/*                     → outputs/charts/*.png|html
   timeseries/*                        → ADF → ARIMA(1,1,1) → 3-month forecast + MAE/RMSE
        ↓
   src/api.py  →  src/bridge.py (JSON-lines over stdin/stdout)
        ↓
   server/app.js (Express) → client/ (React + Vite)
```

**Schema — 5 tables, star-ish:**

| Table | Key | Notes |
|---|---|---|
| `stations` | `station_code` | name, state, zone, latitude, longitude |
| `trains` | `train_no` | type, source/destination → FK `stations`, zone, distance |
| `train_stops` | `(train_no, stop_sequence)` | composite PK; timetable, day, distance from source |
| `delay_records` | `record_id` | fact table: FKs to train + station, scheduled vs actual arrival, delay minutes, weather, cancelled |
| `delay_remarks` | `remark_id` | free text parsed into reasons ("signal failure", "fog"), FKs to train/station |

`delay_records` is the fact table; the other four are dimensions. That is the whole model.

---

## 2. Stack choices

### Python + pandas — ingestion and cleaning

**Why.** `read_csv` / `read_json` / `read_xml` / fixed-width parsing cover all four required formats
with one resulting type (a DataFrame) flowing through cleaning, querying and charting. Every downstream
library we need (statsmodels, matplotlib, scikit-learn) lives in the same runtime.

**Rejected.** Excel macros or pure `LOAD DATA` SQL: both fail once you need "clean, derive 6 columns,
chart, then model" in one pass. R would work equally well — pandas wins only on ecosystem breadth and
course familiarity.

**Trade-off / honest limit.** This is not big data. 40 trains × 60 stations × 3 years fits in RAM
comfortably. Spark or Dask would be costume. If asked about scale: *"cleaning would move into SQL or
Parquet at ~10^8 rows; pandas stays for feature engineering only."*

### SQLAlchemy + SQLite

Three separate reasons:

1. **Declarative models** (`src/database/schema.py`) express PK/FK relationships *as Python*, which is
   exactly the "define relational tables with relationships and cardinality" objective — and the
   Mermaid ER diagram on the Data Pipeline page is generated from the same definitions.
2. **Dialect independence.** `python3 main.py --db mysql|postgresql` switches target with no code
   change. That flag exists to prove the abstraction, not because MySQL is needed.
3. **SQLite** because the deliverable is a folder that runs on a laptop. No daemon, no credentials,
   no "did you start the database?" on demo day. One file to back up, share, or open in DB Browser.

**Rejected.** Raw `sqlite3`: hand-written DDL, no ORM, no ER diagram. MySQL/Postgres: correct for
production, pointless for a single-user local demo, and adds setup steps that only create failure
modes. CSV-only: fails the "load into a SQL database with relationships" objective outright.

### matplotlib + seaborn (static) and Plotly (interactive)

Two consumers, not duplication. Static PNGs are what a report or PDF submission needs and what the
Lab Outputs gallery shows; Plotly is what a *screen* needs — hover values, zoom, the station map.
It also lets the Python layer and the browser share one chart vocabulary.

**Rejected.** All-Plotly (nothing printable without a browser), all-matplotlib (dead charts in a UI),
Chart.js (would mean re-implementing each chart in JS instead of reusing the pandas aggregation).

### statsmodels ARIMA(1,1,1)

**Why this order.** The monthly series has ~36 points. `d=1` is justified by the **ADF test** the
pipeline runs. `p=1, q=1` is the smallest order capturing one autoregressive step plus one
moving-average shock. It is evaluated on a **6-month holdout with MAE and RMSE**, then refit on the full
series to forecast 3 months **with confidence intervals**.

**Rejected and why:**

| Alternative | Why not here |
|---|---|
| Prophet | Black box in a project graded on understanding the method; heavy dependency for a trend + seasonality series. |
| LSTM / any net | 36 samples. It would memorise the series ("parameter-to-sample ratio"). |
| Linear regression on month dummies | No memory of shocks, no principled interval. |
| SARIMA | Arguably better — monthly seasonality is real — but there are only 3 seasonal cycles, so estimating seasonal terms is not defensible. |

Saying *"I considered SARIMA and rejected it for sample size"* is a strong answer.

### React 19 + Vite (replacing Streamlit)

The git history shows the migration off Streamlit. The reasons are concrete: Streamlit re-runs the
whole script on every widget change, cannot do real routing, and every Streamlit app looks like
Streamlit. React gives URL-addressable pages (`react-router`), per-page fetching with a small in-memory
cache (`client/src/api.js`), and full control of layout.

**Cost admitted.** ~200 lines of Streamlit were traded for a build step, two `node_modules`, and a
JS↔Python boundary that did not exist before. That is the single biggest complexity call in the repo.

**Rejected.** Next.js (SSR for a localhost app is needless), Vue/Svelte (fine, no reason to prefer),
HTMX + Jinja (genuinely the lazier correct answer for a form-and-chart app — React was a deliberate
learning goal).

### Plotly.js and Mermaid on the client

Plotly.js keeps one chart vocabulary across Python and browser. Mermaid renders the ER diagram **from
text**, so it regenerates from the schema instead of being a PNG that rots.

**Rejected.** Recharts/ECharts (rewrite chart logic in JS); a hand-drawn ER diagram (breaks silently
when the schema changes).

### Express 5 + a long-lived Python bridge

`server/python.js` spawns **one** `python -m src.bridge` process and speaks **JSON-lines over
stdin/stdout**: one request per line, one reply per line, whitelisted methods in `bridge.METHODS`,
120 s timeout, logs on stderr so stdout stays clean.

- **Why not spawn Python per request:** importing pandas + matplotlib costs ~1–2 s. Per-request
  spawning would make every page load feel broken; one worker amortises startup and keeps the engine
  and cache warm.
- **Why not FastAPI instead of Express:** FastAPI would be the cleaner design — one language, real
  async, no IPC layer. The counter is that the bridge is ~80 lines, the Python side stays a plain
  *library* (`import src.api`) rather than being entangled with a web framework, and Node serves the
  React build cleanly. The seam is the cost of keeping the analytics importable.

**Rejected.** Flask/FastAPI (see above — the refactor to name as future work), Celery/RabbitMQ (job
queues for a single-user tool), gRPC (schema overhead for 13 methods), an HTTP microservice on port
8000 (second server, CORS, two health checks).

### Supporting choices

| Choice | Why it beats the alternative |
|---|---|
| Cache keyed on the DB file's `mtime` (`src/api.py`) | Re-reading and filtering in pandas per request is slow; a `stat()` check invalidates automatically after a pipeline re-run. Simpler and more correct than a TTL or Redis. |
| Filters in POST bodies (`/api/dashboard`, `/api/delays`) | Zone/station/date lists are too long for a query string. |
| Read-only SQL runner (`run_select_query`) | Regex-gates to `SELECT`/`WITH`, rejects `;` and forbidden keywords, **and** opens SQLite with `mode=ro`. Two independent guards — defence in depth. |
| `pytest` + `node:test`, no Jest/Vitest | Zero config, zero extra dependencies for a handful of tests. |
| Seeded generator (`seed: 42`) | Reproducible outputs — a demo that produces different numbers each run cannot be graded. |
| `concurrently` in `npm run dev` | One command, one terminal, `-k` so ctrl-C kills both processes. |
| Cancelled runs dropped from delay stats | Cancellations store a placeholder 0 delay; averaging them in would make cancellations look punctual. They are counted separately as `cancel_pct`. |
| Delay cap of 3000 min (`config.yaml`) | Log/sensor artefacts otherwise produce impossible multi-day delays. Configurable. |

---

## 3. Limits to state out loud

1. **All data is simulated.** No scraping of NTES / IRCTC / eRail / RailYatri. The ARIMA forecast and
   the planner's estimates are not predictions about real trains.
2. **The planner is a heuristic, not a model.** `_predict_from_history` takes the median delay for that
   train in the same month, scales it by a day-of-week ratio clamped to 0.7–1.5, and reports p20/p80/p95,
   on-time % and cancellation %. Call it a "statistical estimate from history".
3. **36 monthly points, 6-month holdout → 30 training observations.** ARIMA confidence intervals will
   be wide. Naming that is better than being caught by it.
4. **`scikit-learn` is used only for `mean_absolute_error` / `mean_squared_error`.** Do not claim a
   machine-learning model where there is a metric helper.
5. **Single-user, no auth, no rate limiting.** `/api/sql` is read-only but unauthenticated — fine on
   localhost, unacceptable if hosted.
6. **The bridge is the fragile seam.** One Python process, serialised requests, 120 s timeout. A slow
   request blocks the queue behind it.

---

## 4. Quickfire viva answers

- **"Why SQL when you have pandas?"** — Relational integrity (FKs catch orphans; `run_integrity_check`
  proves it), query reuse, and the objective requires a database. Analysts read SQL; a notebook is not
  a shared interface.
- **"Why is `train_stops` keyed on two columns?"** — A stop only exists as (train, sequence); neither
  column is unique alone.
- **"Why drop cancelled runs?"** — They store a placeholder 0 delay; including them would make
  cancellations look punctual.
- **"What is your accuracy?"** — Give MAE/RMSE from `outputs/reports/`, then add: "on synthetic data
  with a known generating process, so it measures fit, not skill."
- **"What next?"** — Real data via an API/scrape; SARIMA or a gradient-boosted model once there are ≥5
  years; move the bridge to FastAPI; add auth and a request queue.
