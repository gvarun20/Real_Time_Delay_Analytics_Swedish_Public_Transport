from config.settings import REALTIME_FEED, static_gtfs_url, trip_updates_url


def test_static_gtfs_url_sweden_3():
    url = static_gtfs_url("sl", "test-static-key")
    assert "gtfs-sweden/sweden.zip" in url
    assert "key=test-static-key" in url


def test_static_gtfs_url_regional(monkeypatch):
    monkeypatch.setenv("STATIC_FEED", "gtfs_regional")
    from importlib import reload

    import config.settings as settings

    reload(settings)
    url = settings.static_gtfs_url("sl", "test-key")
    assert "gtfs/sl/sl.zip" in url


def test_trip_updates_url_regional_default():
    url = trip_updates_url("sl", "test-rt-key")
    assert REALTIME_FEED == "gtfs_regional"
    assert "gtfs-rt/sl/TripUpdates.pb" in url
    assert "key=test-rt-key" in url


def test_trip_updates_url_sweden(monkeypatch):
    monkeypatch.setenv("REALTIME_FEED", "gtfs_sweden")
    from importlib import reload

    import config.settings as settings

    reload(settings)
    url = settings.trip_updates_url("sl", "test-rt-key")
    assert "gtfs-rt-sweden/sl/TripUpdatesSweden.pb" in url
