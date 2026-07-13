"""Download and land a GTFS-RT TripUpdates snapshot from Trafiklab."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timezone

import requests

from config.settings import (
    OPERATOR,
    OPERATOR_NAME,
    REALTIME_FEED,
    TRAFIKLAB_REALTIME_API_KEY,
    trip_updates_url,
)
from jobs.ingest.audit import record_ingest_run
from jobs.ingest.common import (
    REALTIME_HEADERS,
    count_trip_update_entities,
    realtime_landing_dir,
    write_metadata,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_fetch_realtime(
    service_date: str | date | None = None,
    operator: str | None = None,
    api_key: str | None = None,
    pulled_at: datetime | None = None,
    *,
    dag_id: str | None = None,
    task_id: str | None = None,
    run_id: str | None = None,
) -> tuple[str, int]:
    service_date = service_date or date.today().isoformat()
    operator = (operator or OPERATOR).lower()
    api_key = api_key or TRAFIKLAB_REALTIME_API_KEY
    pulled_at = pulled_at or datetime.now(timezone.utc)

    if not api_key or api_key in ("your_api_key_here", "your_realtime_key_here"):
        raise ValueError(
            "TRAFIKLAB_REALTIME_API_KEY is not set. Edit .env in VS Code:\n"
            "  TRAFIKLAB_REALTIME_API_KEY=<key matching REALTIME_FEED's product, "
            "e.g. 'GTFS Sweden 3 Realtime' for REALTIME_FEED=gtfs_sweden>\n"
            "Then run: docker compose up -d --force-recreate airflow-scheduler airflow-webserver"
        )

    landing_dir = realtime_landing_dir(service_date, pulled_at)
    output_path = landing_dir / "tripupdates.pb"
    url = trip_updates_url(operator, api_key)

    logger.info("Fetching TripUpdates for %s from Trafiklab", operator)
    response = requests.get(url, headers=REALTIME_HEADERS, timeout=60)
    if response.status_code == 403:
        detail = ""
        try:
            detail = response.json().get("errorMessage", "")
        except Exception:
            pass
        raise ValueError(
            "Trafiklab returned 403 Forbidden"
            + (f": {detail}" if detail else "")
            + ". Use a key whose project has the product matching REALTIME_FEED "
            + f"(currently '{REALTIME_FEED}') at https://developer.trafiklab.se"
        )
    response.raise_for_status()

    output_path.write_bytes(response.content)
    record_count = count_trip_update_entities(response.content)

    write_metadata(
        landing_dir,
        operator=OPERATOR_NAME,
        feed_type="trip_updates",
        record_count=record_count,
        api_status=response.status_code,
        extra={"operator_code": operator, "service_date": str(service_date)},
    )
    logger.info(
        "Saved TripUpdates to %s (%d entities, %d bytes)",
        output_path,
        record_count,
        output_path.stat().st_size,
    )
    record_ingest_run(
        feed_type="trip_updates",
        service_date=str(service_date),
        file_path=str(output_path),
        bytes_written=output_path.stat().st_size,
        record_count=record_count,
        api_status=response.status_code,
        dag_id=dag_id,
        task_id=task_id,
        run_id=run_id,
        extra={"operator_code": operator},
    )
    return str(output_path), record_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch GTFS-RT TripUpdates from Trafiklab")
    parser.add_argument("--service-date", default=date.today().isoformat())
    parser.add_argument("--operator", default=OPERATOR)
    args = parser.parse_args()

    try:
        run_fetch_realtime(service_date=args.service_date, operator=args.operator)
    except Exception:
        logger.exception("Realtime GTFS fetch failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
