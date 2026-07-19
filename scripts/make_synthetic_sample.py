"""Create a small synthetic sample CSV if Postgres export is unavailable.

Replace with real data later via: py scripts/export_dashboard_sample.py
"""

from __future__ import annotations

import gzip
import random
from datetime import date, datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "dashboard" / "sample_data" / "delay_facts.csv.gz"


def main() -> None:
    random.seed(42)
    stops = [
        ("9001", "T-Centralen", 59.3308, 18.0589),
        ("9002", "Slussen", 59.3195, 18.0722),
        ("9003", "Fridhemsplan", 59.3323, 18.0289),
        ("9004", "Odenplan", 59.3429, 18.0493),
        ("9005", "Gullmarsplan", 59.2987, 18.0806),
        ("9006", "Liljeholmen", 59.3101, 18.0224),
    ]
    routes = [
        ("R17", "17", "Tunnelbana 17", "Metro"),
        ("R14", "14", "Tunnelbana 14", "Metro"),
        ("R4", "4", "Bus 4", "Bus"),
        ("R1", "1", "Tunnelbana 1", "Metro"),
    ]
    days = [date(2026, 7, 12), date(2026, 7, 13)]
    day_names = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}

    header = (
        "date_key,full_date,day_name,day_of_week,trip_id,stop_sequence,"
        "scheduled_arrival,actual_arrival,delay_seconds,data_source,"
        "route_id,route_short_name,route_long_name,stop_id,stop_name,"
        "stop_lat,stop_lon,type_name,hour_of_day\n"
    )
    rows: list[str] = []
    for d in days:
        for trip_i in range(40):
            rid, rshort, rlong, vtype = routes[trip_i % len(routes)]
            for seq, stop in enumerate(stops, start=1):
                hour = 7 + (trip_i % 12)
                sched = datetime(d.year, d.month, d.day, hour, (seq * 3) % 60, 0)
                delay = int(max(-600, min(3600, random.gauss(120, 180))))
                actual = sched + timedelta(seconds=delay)
                sid, sname, lat, lon = stop
                trip_id = f"T{d.strftime('%m%d')}_{trip_i:03d}"
                rows.append(
                    ",".join(
                        [
                            d.strftime("%Y%m%d"),
                            str(d),
                            day_names[d.isoweekday()],
                            str(d.isoweekday()),
                            trip_id,
                            str(seq),
                            sched.isoformat(sep=" "),
                            actual.isoformat(sep=" "),
                            str(delay),
                            "gtfs_rt",
                            rid,
                            rshort,
                            rlong,
                            sid,
                            sname,
                            str(lat),
                            str(lon),
                            vtype,
                            str(hour),
                        ]
                    )
                )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(rows))
    kb = OUT.stat().st_size / 1024
    print(f"Wrote {len(rows)} synthetic demo rows to {OUT} ({kb:.1f} KB)")
    print("For real pipeline data later: start Docker Postgres, then run")
    print("  py scripts/export_dashboard_sample.py")


if __name__ == "__main__":
    main()
