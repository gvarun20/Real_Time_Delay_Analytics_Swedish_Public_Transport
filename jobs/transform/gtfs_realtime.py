"""Parse GTFS-RT TripUpdates protobuf into flat records."""

from __future__ import annotations

from pathlib import Path

from google.transit import gtfs_realtime_pb2

from jobs.transform.time_utils import gtfs_rt_start_to_epoch


def parse_trip_updates(pb_path: Path) -> list[dict]:
    """Extract stop-level delay updates from a TripUpdates feed."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(pb_path.read_bytes())

    rows: list[dict] = []
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        trip_update = entity.trip_update
        trip_id = trip_update.trip.trip_id if trip_update.trip.trip_id else None
        route_id = trip_update.trip.route_id if trip_update.trip.route_id else None
        trip_start_epoch = gtfs_rt_start_to_epoch(
            trip_update.trip.start_date or None,
            trip_update.trip.start_time or None,
        )
        start_date = trip_update.trip.start_date if trip_update.trip.start_date else None

        for stu in trip_update.stop_time_update:
            stop_id = stu.stop_id if stu.stop_id else None
            if not stop_id:
                continue

            delay_seconds = None
            actual_epoch = None
            if stu.HasField("arrival"):
                if stu.arrival.delay:
                    delay_seconds = int(stu.arrival.delay)
                if stu.arrival.time:
                    actual_epoch = int(stu.arrival.time)
            elif stu.HasField("departure"):
                if stu.departure.delay:
                    delay_seconds = int(stu.departure.delay)
                if stu.departure.time:
                    actual_epoch = int(stu.departure.time)

            rows.append(
                {
                    "trip_id": trip_id,
                    "route_id": route_id,
                    "trip_start_epoch": trip_start_epoch,
                    "start_date": start_date,
                    "stop_id": stop_id,
                    "stop_sequence": int(stu.stop_sequence) if stu.stop_sequence else None,
                    "delay_seconds": delay_seconds,
                    "actual_epoch": actual_epoch,
                }
            )
    return rows
