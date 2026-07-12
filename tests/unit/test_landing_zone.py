import json
from datetime import date
from pathlib import Path

from jobs.ingest.common import write_metadata


def test_static_landing_dir_structure(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_RAW_DIR", str(tmp_path))
    from importlib import reload

    import config.settings as settings

    reload(settings)
    import jobs.ingest.common as common

    reload(common)

    path = common.static_landing_dir(date(2026, 7, 11))
    assert path == tmp_path / "static" / "2026-07-11"
    assert path.exists()


def test_realtime_landing_dir_includes_timestamp(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_RAW_DIR", str(tmp_path))
    from importlib import reload

    import config.settings as settings

    reload(settings)
    import jobs.ingest.common as common

    reload(common)

    from datetime import datetime, timezone

    ts = datetime(2026, 7, 11, 9, 30, 0, tzinfo=timezone.utc)
    path = common.realtime_landing_dir("2026-07-11", ts)
    assert path.parent.name == "2026-07-11"
    assert path.name == "09-30-00"


def test_write_metadata_creates_json(tmp_path):
    landing = tmp_path / "landing"
    landing.mkdir()
    meta_path = write_metadata(
        landing,
        operator="SL",
        feed_type="trip_updates",
        record_count=42,
        api_status=200,
    )
    payload = json.loads(Path(meta_path).read_text(encoding="utf-8"))
    assert payload["operator"] == "SL"
    assert payload["record_count"] == 42
    assert payload["api_status"] == 200
    assert "pulled_at_utc" in payload
