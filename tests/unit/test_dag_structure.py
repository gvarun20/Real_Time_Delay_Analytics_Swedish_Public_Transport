"""DAG file structure tests (no Airflow runtime required)."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DAG_DIR = PROJECT_ROOT / "dags"

EXPECTED_DAGS = {
    "dag_ingest_gtfs.py": "gtfs_static_ingest",
    "dag_realtime_gtfs.py": "gtfs_realtime_ingest",
    "dag_gtfs_transform.py": "gtfs_transform",
}


def test_all_expected_dag_files_exist():
    for filename in EXPECTED_DAGS:
        assert (DAG_DIR / filename).exists(), f"Missing {filename}"


def test_dag_files_define_expected_dag_ids():
    for filename, dag_id in EXPECTED_DAGS.items():
        content = (DAG_DIR / filename).read_text(encoding="utf-8")
        assert f'dag_id="{dag_id}"' in content


def test_dag_files_use_default_args_retries():
    for filename in EXPECTED_DAGS:
        content = (DAG_DIR / filename).read_text(encoding="utf-8")
        assert "DEFAULT_ARGS" in content
        assert "PythonOperator" in content


def test_common_module_has_failure_callback():
    content = (DAG_DIR / "common.py").read_text(encoding="utf-8")
    assert "on_failure_callback" in content
    assert "retries" in content
