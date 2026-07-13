"""Airflow DAG: PySpark transform raw GTFS into Postgres star schema."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.filesystem import FileSensor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dags.common import DEFAULT_ARGS  # noqa: E402
from jobs.transform.paths import latest_realtime_pb  # noqa: E402
from jobs.transform_gtfs import run_transform  # noqa: E402


def transform_task(**context) -> int:
    service_date = context["ds"]
    rows = run_transform(
        service_date=service_date,
        dag_run_id=context.get("run_id"),
    )
    return rows


def check_realtime_available(**context) -> None:
    latest_realtime_pb(context["ds"])


with DAG(
    dag_id="gtfs_transform",
    default_args=DEFAULT_ARGS,
    description="PySpark transform: raw GTFS -> Postgres star schema",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["gtfs", "transform", "pyspark"],
    doc_md="""
    ## gtfs_transform

    Reads landed raw files for the execution date, filters SL (Stockholm) data,
    joins static stop_times with realtime TripUpdates, computes delays,
    and loads `fact_trip_delay` + dimensions in Postgres.

    **Requires:** static + realtime data for the service date in `data/raw/`.
    """,
) as dag:
    wait_for_static = FileSensor(
        task_id="wait_for_static_gtfs",
        filepath="/opt/airflow/project/data/raw/static/{{ ds }}/gtfs.zip",
        poke_interval=60,
        timeout=60 * 60,
        mode="reschedule",
    )

    check_realtime = PythonOperator(
        task_id="check_realtime_snapshot",
        python_callable=check_realtime_available,
    )

    transform_with_pyspark = PythonOperator(
        task_id="transform_with_pyspark",
        python_callable=transform_task,
        execution_timeout=timedelta(hours=2),
    )

    [wait_for_static, check_realtime] >> transform_with_pyspark
