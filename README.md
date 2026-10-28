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

- Python 3.9+
- pandas, numpy
- matplotlib, seaborn, plotly
- statsmodels
- SQLAlchemy, sqlite3
- openpyxl
- lxml/xml.etree.ElementTree
- scikit-learn
- pytest
- PyYAML

## Folder Structure

```
railway-delay-analytics/
├── README.md
├── requirements.txt
├── config.yaml
├── main.py
├── data/
│   ├── raw/
│   ├── processed/
│   └── railway.db
├── outputs/
│   ├── charts/
│   ├── reports/
│   └── excel/
├── notebooks/
│   └── railway_delay_analysis.ipynb
├── src/
│   ├── config.py
│   ├── api.py
│   ├── data_generation/generate_data.py
│   ├── ingestion/ (csv_reader, json_reader, xml_reader, txt_reader, loader)
│   ├── cleaning/ (cleaner, cleaning_report)
│   ├── database/ (schema, db_loader, queries)
│   ├── visualization/ (static_charts, interactive_charts)
│   ├── timeseries/ (prepare, decomposition, smoothing, arima_model)
│   └── utils/logger.py
├── tests/
└── app/ (UI to be added later)
```

## Setup and Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run full pipeline
python main.py

# Regenerate synthetic data
python main.py --regenerate

# Skip chart generation
python main.py --skip-charts

# Use different DB type (configure URL in config.yaml)
python main.py --db mysql  # or postgresql
```

## How to Switch to MySQL/PostgreSQL

1. Install driver: `pip install pymysql` (MySQL) or `psycopg2-binary` (PostgreSQL)
2. Update `config.yaml`:
```yaml
db:
  type: mysql  # or postgresql
  url: "mysql+pymysql://user:password@host:port/dbname"
```
Or:
```yaml
db:
  type: postgresql
  url: "postgresql+psycopg2://user:password@host:port/dbname"
```

## How to Plug in Real Data

- Place files in `data/raw/` with the expected names from `config.yaml`:
  - `trains.csv`, `stations.json`, `routes.xml`, `delay_records.csv`, `delay_remarks.txt`
- For manual logs: add `data/raw/manual_delay_log.csv` with columns `date, train_no, station_code, delay_minutes`
- The loaders are flexible and will read your files if they exist
- Update column mappings in `config.yaml` if needed

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
pytest -v
```

## Future Scope

- Real-time NTES data integration (with official permission)
- Weather API integration (IMD/OpenWeather)
- Machine-learning delay prediction models
- UI dashboard (Streamlit) - see `app/README.md`

## Data Note

The data used in this project is **synthetic/simulated** for academic purposes and does not represent actual Indian Railways operations.
