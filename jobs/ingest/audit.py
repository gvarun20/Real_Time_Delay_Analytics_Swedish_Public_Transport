"""Append-only audit log for ingest runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from config.settings import PROJECT_ROOT

INGEST_LOG = PROJECT_ROOT / "logs" / "ingest_runs.jsonl"


def record_ingest_run(
    *,
    feed_type: str,
    service_date: str,
    file_path: str,
    bytes_written: int,
    record_count: int | None = None,
    api_status: int = 200,
    dag_id: str | None = None,
    task_id: str | None = None,
    run_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    INGEST_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "feed_type": feed_type,
        "service_date": service_date,
        "file_path": file_path,
        "bytes": bytes_written,
        "record_count": record_count,
        "api_status": api_status,
        "dag_id": dag_id,
        "task_id": task_id,
        "run_id": run_id,
    }
    if extra:
        entry.update(extra)

    with INGEST_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
