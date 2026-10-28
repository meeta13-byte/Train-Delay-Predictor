# Indian Railways Train Delay Analysis & Forecasting System

## Project Overview

This project is an academic Data Analytics & Visualization (DAV) mini-project that builds a complete Python-based analytics pipeline for Indian Railways train delay data.

**Problem statement:** Indian Railways runs thousands of passenger trains daily, and delays are frequent. Delay information is scattered and rarely stored in a central database. This pipeline reads data from multiple formats, cleans it, models relationships, loads into a SQL database, runs analytical queries, visualizes trends, and forecasts delays.

**Key features:**
- Multi-format ingestion (`.csv`, `.json`, `.xml`, `.txt`)
- Data cleaning with missing values, duplicates, outliers, and feature engineering
- Relational data model with PK/FK relationships
- SQL database (SQLite by default) via SQLAlchemy
- 15+ static (Matplotlib/Seaborn) and interactive (Plotly) visualizations
- Time-series analysis (decomposition, moving averages, exponential smoothing, ARIMA(1,1,1)) with 3-month forecast
- Excel-ready outputs

**Note:** Data is simulated for academic purposes. No live scraping of NTES/IRCTC/eRail/RailYatri.

## Objectives

1. Collect and extract structured and unstructured railway data
2. Clean and preprocess (missing values, duplicates, outliers)
3. Define relational tables with relationships and cardinality
4. Load cleaned data into SQL database using SQLAlchemy and `to_sql()`
5. Run analytical SQL queries from Python
6. Produce visualizations and Excel-ready outputs
7. Perform time-series analysis and forecast average delay for next 3 months

## Tech Stack

**Backend / analytics:** Python 3.9+, pandas, numpy, matplotlib, seaborn, statsmodels, SQLAlchemy + SQLite,
openpyxl, xml.etree.ElementTree, scikit-learn, PyYAML, pytest.

**Web app:** Node.js 20.11+, Express (API), React + Vite (UI), Plotly.js (charts and map), Mermaid (ER diagram).

## Folder Structure

```
Train-Delay-Predictor/
├── README.md
├── package.json            # npm scripts: setup, dev, start, test, screenshots
├── requirements.txt
├── config.yaml
├── main.py                 # runs the whole analytics pipeline
├── data/                   # generated: raw/, processed/, railway.db
├── outputs/                # generated: charts/, reports/, excel/ (+ ui_screenshots/, kept in git)
├── src/
│   ├── config.py
│   ├── api.py              # functions used by the UI (JSON-ready)
│   ├── bridge.py           # long-running worker the Express server talks to
│   ├── planner.py          # journey planner: delay prediction + better-train suggestions
│   ├── data_generation/generate_data.py
│   ├── ingestion/          # csv_reader, json_reader, xml_reader, txt_reader, loader
│   ├── cleaning/           # cleaner, cleaning_report
│   ├── database/           # schema, db_loader, queries
│   ├── visualization/      # static_charts, interactive_charts
│   ├── timeseries/         # prepare, decomposition, smoothing, arima_model
│   └── utils/logger.py
├── server/                 # Express API (app.js, python.js bridge client, pipeline.js)
├── client/                 # React + Vite UI (pages/, components/, theme.js, styles.css, assets/)
├── tools/
│   ├── make_svgs.py        # draws the isometric illustrations and icons
│   └── screenshots.mjs     # screenshots every page with Playwright
└── tests/                  # pytest (backend + API helpers); server/test for the API routes
```

## Setup and Run

You need **Python 3.9+** and **Node.js 20.11+**.

```bash
# one-time setup: npm packages, Python packages, and the first pipeline run (~1 min)
npm run setup

# start the web app (API on :8000, UI on :5173) and open http://localhost:5173
npm run dev
```

`npm run setup` is the same as:

```bash
npm install                        # also installs server/ and client/
python3 -m pip install -r requirements.txt
python3 main.py --regenerate       # generate → clean → load DB → charts → forecast
```

Other commands:

```bash
npm start                 # production: builds the UI and serves everything on http://localhost:8000
npm test                  # pytest + Express route tests
npm run pipeline          # re-run python main.py (also possible from the Data Pipeline page)
python3 main.py --regenerate   # rebuild the synthetic raw data too
python3 main.py --skip-charts  # skip the Matplotlib charts
```

The server finds Python automatically (`$PYTHON`, then `.venv/` or `venv/`, then `python3` / `python`).
If you use a virtual environment, create it as `.venv` in the project folder, or start with
`PYTHON=/path/to/python npm run dev`. On Windows, use `python` instead of `python3` in the commands above.

## Web App

Pages (the top navigation):

| Page | What it shows |
|---|---|
| **Home** | Hero, key insights (most delayed train, winter fog impact, on-time %), how the pipeline works |
| **Plan journey** | Enter a train number or category, From / To, date and an optional "leave after" time. Predicts the delay and suggests better trains on the same route |
| **Dashboard** | Filters (date range, zone, train type, season) shared by the analysis pages; KPI tiles, monthly trend, delay by type, category share, month × year heatmap |
| **Delays** | Histogram, box plots by season and type, weather, distance vs delay, category share per type, delay reasons from text, and a train explorer (delay along the route) |
| **Stations** | Map of stations sized and coloured by delay (works offline without the street map), worst 10, full table |
| **Forecast** | ARIMA(1,1,1) 3-month forecast with 95% band for all trains / a zone / a train type / one train; MAE and RMSE on a 6-month holdout; decomposition, moving averages, exponential smoothing, ADF + ACF/PACF; CSV download |
| **Data Pipeline** | For the viva: raw file previews, cleaning counts, ER diagram + cardinality + orphan check, database tables, SQL playground (preset queries or your own read-only `SELECT`), downloads, and a "Re-run pipeline" button with progress |
| **Lab Outputs** | Gallery of the saved Matplotlib / Seaborn charts, labelled by lab; click to enlarge |
| **About** | Problem statement, objectives, tech stack, lab-to-module mapping, future scope |

Screenshots of every page are in [`outputs/ui_screenshots/`](outputs/ui_screenshots/) (regenerate with
`npm run screenshots` while `npm run dev` is running; needs `npm i -D playwright && npx playwright install chromium`).

![Home](outputs/ui_screenshots/home-1440.png)

## Journey Planner

The **Plan journey** page (logic in `src/planner.py`):

- predicts the train's delay at your destination from its history at that station for the same month,
  adjusted for the day of the week, with the likely range, on-time chance and cancellation rate;
- ranks every train that serves the same From → To on **expected arrival** (timetable + predicted delay);
- suggests better options in plain language: *"leave later, arrive earlier"*, *"same arrival, more time at
  home"*, *"usually runs late but still gets there first"*, or *"arrives earlier"* (only trains leaving at most
  2 hours before yours).

Example: 12951 Mumbai Nagpur Express (Mail/Express, 18:40) to Nagpur → 12105 Vidarbha Express leaves 25 min
later but is expected about 2 hours earlier.

![Journey planner](outputs/ui_screenshots/plan-1440.png)

## How to Switch to MySQL/PostgreSQL

1. Install a driver: `pip install pymysql` (MySQL) or `pip install psycopg2-binary` (PostgreSQL).
2. Put the connection URL in `config.yaml`:
```yaml
db:
  url: "mysql+pymysql://user:password@host:port/dbname"
  # or: "postgresql+psycopg2://user:password@host:port/dbname"
```
3. Run `python3 main.py --db mysql` (or `--db postgresql`).

The web app reads the SQLite database (`data/railway.db`), so keep running the default pipeline as well.

## How to Plug in Real Data

Put your files in `data/raw/` with these names and columns (see `src/ingestion/` for the exact format):

- `trains.csv`: train_no, train_name, train_type, source_station_code, destination_station_code, zone, distance_km
- `stations.json`: list of {station_code, station_name, state, zone, latitude, longitude}
- `routes.xml`: `<train train_no>` with `<stop stop_sequence>` children (station_code, scheduled_arrival,
  scheduled_departure, day, distance_from_source_km)
- `delay_records.csv`: record_id, date, train_no, station_code, scheduled_arrival, actual_arrival, delay_minutes,
  weather_condition, cancelled
- `delay_remarks.txt`: free-text remarks, one per line

Delete the synthetic files and the `.generator_version` marker in `data/raw/` first, then copy yours in and run
`python3 main.py` (not `--regenerate`, which would overwrite them). Files without the marker are never overwritten.

## Lab Mapping

| Lab topic | Module(s) |
|---|---|
| Data collection from .csv/.txt/.json/.xml, structured & unstructured | `ingestion/` |
| Collect related datasets (customer/order equivalent: trains & delay records) | `data_generation/`, `ingestion/` |
| Data cleaning (missing, duplicates, outliers), relationships & cardinality, Excel | `cleaning/`, `database/schema.py`, Excel export |
| Python + MySQL/SQLite/PostgreSQL, SQLAlchemy, sqlite3, `to_sql()`, Excel import | `database/` |
| Visualization toolkit: temporal trends & relationships (Matplotlib, Seaborn, Excel) | `visualization/static_charts.py` |
| Histograms, box plots, bar/pie/donut, Plotly | `visualization/` |
| Time series: decomposition, trend, moving averages, smoothing, ARIMA | `timeseries/` |

## Sample Outputs

- `data/railway.db` - SQLite database
- `data/processed/*_cleaned.csv` - Cleaned tables
- `outputs/excel/railway_cleaned_data.xlsx` - Cleaned Excel workbook with Cleaning_Report
- `outputs/charts/*.png` - All visualizations
- `outputs/reports/*.csv` - SQL query results, forecast
- `outputs/reports/forecast_next_3_months.csv` - 3-month ARIMA forecast

## Running Tests

```bash
npm test          # or separately:
python3 -m pytest -q
npm --prefix server test
```

## Future Scope

- Real-time NTES data integration (with official permission)
- Weather API integration (IMD/OpenWeather)
- Machine-learning delay prediction models
- Journeys with a change of train

## Data Note

The data used in this project is **synthetic/simulated** for academic purposes and does not represent actual Indian Railways operations.
