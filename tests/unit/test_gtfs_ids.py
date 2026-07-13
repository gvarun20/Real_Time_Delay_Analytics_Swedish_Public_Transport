from jobs.transform.ids import normalize_rt_stop_id


def test_normalize_rt_stop_id_mixed_feeds():
    assert (
        normalize_rt_stop_id(
            "9022001000101001",
            static_feed="gtfs_sweden_3",
            realtime_feed="gtfs_regional",
        )
        == "9011001000101001"
    )


def test_normalize_rt_stop_id_same_family():
    assert (
        normalize_rt_stop_id(
            "9022001000101001",
            static_feed="gtfs_regional",
            realtime_feed="gtfs_regional",
        )
        == "9022001000101001"
    )
