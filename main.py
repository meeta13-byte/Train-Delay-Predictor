"""Main pipeline: run all phases end-to-end."""

import argparse
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

from src.config import get_path, load_config
from src.data_generation.generate_data import write_raw_data
from src.ingestion.loader import load_all
from src.cleaning.cleaner import run_cleaning
from src.cleaning.cleaning_report import write_cleaned_excel
from src.database.db_loader import get_engine, create_schema, load_to_db, run_integrity_check
from src.database import queries
from src.visualization import static_charts
from src.timeseries import arima_model, decomposition, prepare, smoothing
from src.utils.logger import get_logger

logger = get_logger("main")


def run_pipeline(args):
    config = load_config()
    raw_dir = get_path(config, "raw_dir")
    processed_dir = get_path(config, "processed_dir")
    reports_dir = get_path(config, "reports_dir")
    processed_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=== Phase 1: Generate synthetic data ===")
    write_raw_data(raw_dir, regenerate=args.regenerate)

    logger.info("=== Phase 2: Ingest all formats ===")
    data = load_all(raw_dir)

    logger.info("=== Phase 3: Clean + preprocess ===")
    cleaned, report = run_cleaning(data)
    for name, df in cleaned.items():
        if df is None:
            continue
        out_path = processed_dir / f"{name}_cleaned.csv"
        df.to_csv(out_path, index=False)
        logger.info("Wrote %s", out_path)
    excel_path = get_path(config, "cleaned_excel")
    write_cleaned_excel(cleaned, report, excel_path)
    with open(reports_dir / "cleaning_report.json", "w") as f:
        import json

        json.dump(report, f, indent=2)

    logger.info("=== Phase 4: Database schema + load + integrity ===")
    engine = get_engine(args.db)
    create_schema(engine)
    load_to_db(cleaned, engine)
    integrity = run_integrity_check(engine)
    logger.info("Integrity: %s", integrity)

    logger.info("=== Phase 5: SQL queries ===")
    query_results = {
        "top_delayed_trains": queries.top_delayed_trains(engine),
        "worst_stations": queries.worst_stations(engine),
        "monthly_avg_delay": queries.monthly_avg_delay(engine),
        "avg_delay_by_train_type": queries.avg_delay_by_train_type(engine),
        "avg_delay_by_zone": queries.avg_delay_by_zone(engine),
        "avg_delay_by_season": queries.avg_delay_by_season(engine),
        "avg_delay_by_weather": queries.avg_delay_by_weather(engine),
        "ontime_performance": queries.ontime_performance(engine),
        "common_delay_reasons": queries.common_delay_reasons(engine),
    }
    for name, df in query_results.items():
        path = reports_dir / f"{name}.csv"
        df.to_csv(path, index=False)
        logger.info("Saved query %s -> %s", name, path)

    if not args.skip_charts:
        logger.info("=== Phase 6: Visualizations ===")
        delays = cleaned["delay_records"]
        routes = cleaned.get("routes")
        static_charts.plot_monthly_avg_delay(query_results["monthly_avg_delay"])
        static_charts.plot_delay_histogram(delays["delay_minutes"])
        delays_with_train = delays.merge(cleaned["trains"][["train_no", "train_type", "zone"]], on="train_no", how="left")
        if "train_type" in delays_with_train.columns:
            static_charts.plot_delay_histogram_kde_by_train_type(delays_with_train)
            static_charts.plot_delay_by_train_type(delays_with_train)
            static_charts.plot_stacked_bar_delay_categories(delays_with_train)
        static_charts.plot_delay_by_season(delays)
        static_charts.plot_top_delayed_trains(query_results["top_delayed_trains"])
        static_charts.plot_worst_stations(query_results["worst_stations"])
        zone_year = delays_with_train.groupby(["zone", "year"])["delay_minutes"].mean().reset_index(name="avg_delay")
        static_charts.plot_avg_delay_by_zone_per_year(zone_year)
        static_charts.plot_pie_delay_categories(delays)
        if not query_results["common_delay_reasons"].empty:
            static_charts.plot_donut_delay_reasons(query_results["common_delay_reasons"])
        month_year = delays.groupby(["month", "year"])["delay_minutes"].mean().reset_index(name="avg_delay")
        static_charts.plot_heatmap_month_year(month_year)
        corr = delays[["delay_minutes", "month", "year"]].copy()
        corr["stop_sequence"] = delays_with_train.get("stop_sequence", 0)
        static_charts.plot_correlation_heatmap(corr)
        if routes is not None and "distance_from_source_km" in routes.columns:
            merged = delays.merge(routes[["train_no", "station_code", "distance_from_source_km"]], on=["train_no", "station_code"], how="left")
            static_charts.plot_scatter_distance_vs_delay(merged)
        acc = queries.delay_accumulation_by_stop(engine, train_no=int(delays["train_no"].iloc[0]))
        static_charts.plot_delay_accumulation(acc)

    logger.info("=== Phase 7: Time series + ARIMA forecast ===")
    series = prepare.monthly_series_from_df(query_results["monthly_avg_delay"])
    try:
        decomposition.decompose_series(series)
    except Exception as e:
        logger.warning("Decomposition failed: %s", e)
    try:
        sma, ema = smoothing.moving_averages(series)
        logger.info("SMA computed, EMA computed")
    except Exception as e:
        logger.warning("Smoothing failed: %s", e)
    adf = arima_model.adf_test(series)
    logger.info("ADF test: %s", adf)
    metrics = arima_model.evaluate_holdout(series)
    logger.info("Holdout metrics: MAE=%s RMSE=%s", metrics["mae"], metrics["rmse"])
    fc = arima_model.forecast_next_months(series, steps=3)
    forecast_df = fc["forecast"].reset_index()
    forecast_df.columns = ["month", "forecast_delay"]
    fc_path = reports_dir / "forecast_next_3_months.csv"
    forecast_df.to_csv(fc_path, index=False)
    logger.info("Forecast saved to %s", fc_path)

    logger.info("=== FINAL SUMMARY ===")
    top = query_results["top_delayed_trains"].iloc[0] if not query_results["top_delayed_trains"].empty else None
    worst = query_results["worst_stations"].iloc[0] if not query_results["worst_stations"].empty else None
    logger.info("Worst train: %s avg=%.2f", top["train_name"] if top is not None else None, top["avg_delay"] if top is not None else 0)
    logger.info("Worst station: %s avg=%.2f", worst["station_name"] if worst is not None else None, worst["avg_delay"] if worst is not None else 0)
    logger.info("On-time %%: %.2f", query_results["ontime_performance"]["ontime_pct"].mean())
    logger.info("Fog/Winter avg: %s", query_results["avg_delay_by_season"].to_string())


def main():
    parser = argparse.ArgumentParser(description="Indian Railways Train Delay Analytics Pipeline")
    parser.add_argument("--regenerate", action="store_true", help="Regenerate synthetic data")
    parser.add_argument("--db", choices=["sqlite", "mysql", "postgresql"], default="sqlite")
    parser.add_argument("--skip-charts", action="store_true", help="Skip chart generation")
    args = parser.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
