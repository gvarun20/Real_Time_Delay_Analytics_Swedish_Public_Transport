"""Diagnose static vs realtime ID compatibility."""
import sys
import tempfile
import zipfile
from pathlib import Path

from google.transit import gtfs_realtime_pb2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

rt = Path("/opt/airflow/project/data/raw/realtime/2026-07-12/15-45-01/tripupdates.pb")
feed = gtfs_realtime_pb2.FeedMessage()
feed.ParseFromString(rt.read_bytes())
rt_trips = set()
rt_routes = set()
for e in feed.entity:
    if e.HasField("trip_update"):
        t = e.trip_update.trip
        if t.trip_id:
            rt_trips.add(t.trip_id)
        if t.route_id:
            rt_routes.add(t.route_id)

print("RT unique trip_ids:", len(rt_trips))
print("RT sample trip_ids:", list(rt_trips)[:5])
print("RT sample route_ids:", list(rt_routes)[:5])

z = Path("/opt/airflow/project/data/raw/static/2026-07-12/gtfs.zip")
tmpdir = tempfile.mkdtemp()
with zipfile.ZipFile(z) as zf:
    zf.extractall(tmpdir)

static_trips = set()
with open(f"{tmpdir}/trips.txt") as f:
    f.readline()  # skip header
    for line in f:
        static_trips.add(line.split(",")[0])

print("Static trip count:", len(static_trips))
print("Static sample trip_ids:", list(static_trips)[:5])
overlap = rt_trips & static_trips
print("trip_id overlap count:", len(overlap))
print("overlap sample:", list(overlap)[:5])

with open(f"{tmpdir}/agency.txt") as f:
    for line in f:
        if "275" in line or "SL" in line or "Stockholm" in line:
            print("agency:", line.strip())
