"""Streamlit dashboard: Swedish transit delay analytics.

Local:
    streamlit run dashboard/app.py

Public (Streamlit Community Cloud):
    Main file = dashboard/app.py
    Requirements file = dashboard/requirements.txt
    Uses sample CSV when Postgres is not reachable (no secrets needed).
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard import energy_queries, queries  # noqa: E402
from dashboard.filters import Filters  # noqa: E402

st.set_page_config(
    page_title="Swedish Transit Delays",
    page_icon="🚋",
    layout="wide",
)


@st.cache_data(ttl=300)
def cached_date_range():
    return queries.get_available_date_range()


@st.cache_data(ttl=300)
def cached_routes():
    return queries.get_available_routes()


@st.cache_data(ttl=300)
def cached_vehicle_types():
    return queries.get_available_vehicle_types()


@st.cache_data(ttl=300)
def cached_kpis(start_date, end_date, route_ids, vehicle_types):
    filters = Filters(start_date, end_date, list(route_ids), list(vehicle_types))
    return queries.get_kpis(filters)


@st.cache_data(ttl=300)
def cached_avg_delay_by_route(start_date, end_date, route_ids, vehicle_types):
    filters = Filters(start_date, end_date, list(route_ids), list(vehicle_types))
    return queries.get_avg_delay_by_route(filters)


@st.cache_data(ttl=300)
def cached_heatmap(start_date, end_date, route_ids, vehicle_types):
    filters = Filters(start_date, end_date, list(route_ids), list(vehicle_types))
    return queries.get_delay_heatmap(filters)


@st.cache_data(ttl=300)
def cached_worst_stops(start_date, end_date, route_ids, vehicle_types):
    filters = Filters(start_date, end_date, list(route_ids), list(vehicle_types))
    return queries.get_worst_stops(filters)


@st.cache_data(ttl=300)
def cached_map_data(start_date, end_date, route_ids, vehicle_types):
    filters = Filters(start_date, end_date, list(route_ids), list(vehicle_types))
    return queries.get_stops_map_data(filters)


@st.cache_data(ttl=300)
def cached_delay_distribution(start_date, end_date, route_ids, vehicle_types):
    filters = Filters(start_date, end_date, list(route_ids), list(vehicle_types))
    return queries.get_delay_distribution(filters)


@st.cache_data(ttl=300)
def cached_energy_scores(start_date, end_date, region_id):
    return energy_queries.get_energy_scores(start_date, end_date, region_id)


def fmt_minutes(seconds: float | None) -> str:
    if seconds is None or pd.isna(seconds):
        return "N/A"
    minutes = seconds / 60
    sign = "+" if minutes >= 0 else ""
    return f"{sign}{minutes:.1f} min"


def render_empty_state(message: str = "No data for the selected filters.") -> None:
    st.info(f"ℹ️ {message} Try widening the date range or clearing filters.")


def main() -> None:
    st.title("Swedish Transit Delays")
    st.caption("SL (Stockholm) · GTFS + GTFS-RT · delay analytics")

    if queries.using_sample_data():
        st.info(
            "Public demo mode: showing a **sample export** of delay facts "
            "(same charts as the local Postgres dashboard). "
            "The full Airflow + PySpark pipeline still runs in Docker on the developer machine."
        )
    else:
        st.caption("Live mode: reading from local PostgreSQL star schema.")

    min_date, max_date = cached_date_range()
    if min_date is None:
        st.warning(
            "No data found. Locally: run the `gtfs_transform` DAG, then "
            "`py scripts/export_dashboard_sample.py`. "
            "For Streamlit Cloud: commit `dashboard/sample_data/delay_facts.csv.gz`."
        )
        return

    st.sidebar.header("Filters")
    default_start = max(min_date, max_date - timedelta(days=6))
    date_range = st.sidebar.date_input(
        "Date range",
        value=(default_start, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    # While the user has only picked one endpoint, Streamlit returns a
    # 1-tuple instead of a pair — fall back to the defaults until both are set.
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = default_start, max_date

    routes_df = cached_routes()
    route_options = dict(zip(routes_df["route_short_name"], routes_df["route_id"], strict=False))
    selected_route_names = st.sidebar.multiselect("Route", options=list(route_options.keys()))
    selected_route_ids = tuple(route_options[name] for name in selected_route_names)

    vehicle_types_df = cached_vehicle_types()
    selected_vehicle_types = tuple(
        st.sidebar.multiselect(
            "Vehicle type", options=vehicle_types_df["type_name"].tolist()
        )
    )

    filter_args = (start_date, end_date, selected_route_ids, selected_vehicle_types)

    delay_tab, energy_tab = st.tabs(["Delays", "Energy scores"])

    with delay_tab:
        render_delay_tab(filter_args)

    with energy_tab:
        render_energy_tab(start_date, end_date)


def render_delay_tab(filter_args: tuple) -> None:
    kpis = cached_kpis(*filter_args)
    if kpis["total_facts"] == 0:
        render_empty_state()
        return

    st.subheader("Key metrics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Median delay", fmt_minutes(kpis["median_delay_sec"]))
    on_time_pct = (
        f"{kpis['on_time_rate'] * 100:.1f}%" if kpis["on_time_rate"] is not None else "N/A"
    )
    col2.metric("% on-time (≤0 delay)", on_time_pct)
    col3.metric("Trips observed", f"{kpis['trips_observed']:,}")
    col4.metric("Worst route (avg delay)", kpis["worst_route"])

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Average delay by route (top 20)")
        route_df = cached_avg_delay_by_route(*filter_args)
        if route_df.empty:
            render_empty_state()
        else:
            route_df["avg_delay_min"] = route_df["avg_delay_sec"] / 60
            fig = px.bar(
                route_df.sort_values("avg_delay_min"),
                x="avg_delay_min",
                y="route_short_name",
                orientation="h",
                labels={"avg_delay_min": "Avg delay (min)", "route_short_name": "Route"},
                color="avg_delay_min",
                color_continuous_scale="RdYlGn_r",
            )
            fig.update_layout(height=500, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Delay heatmap — hour of day × day of week")
        heatmap_df = cached_heatmap(*filter_args)
        if heatmap_df.empty:
            render_empty_state()
        else:
            pivot = heatmap_df.pivot(
                index="day_name", columns="hour_of_day", values="avg_delay_sec"
            )
            # dim_date.day_name is abbreviated (TO_CHAR(d, 'Dy') in sql/seed_dim_date.sql).
            day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            pivot = pivot.reindex([d for d in day_order if d in pivot.index])
            fig = px.imshow(
                pivot,
                labels={"x": "Hour of day", "y": "Day", "color": "Avg delay (s)"},
                color_continuous_scale="RdYlGn_r",
                aspect="auto",
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    left2, right2 = st.columns(2)

    with left2:
        st.subheader("Stops colored by average delay")
        map_df = cached_map_data(*filter_args)
        if map_df.empty:
            render_empty_state("No stop coordinates for the selected filters.")
        else:
            map_df["avg_delay_min"] = map_df["avg_delay_sec"] / 60
            fig = px.scatter_map(
                map_df,
                lat="stop_lat",
                lon="stop_lon",
                color="avg_delay_min",
                size="n_observations",
                hover_name="stop_name",
                hover_data={"avg_delay_min": ":.1f", "n_observations": True},
                color_continuous_scale="RdYlGn_r",
                map_style="open-street-map",
                zoom=9,
                height=500,
            )
            fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
            st.plotly_chart(fig, use_container_width=True)

    with right2:
        st.subheader("Top 10 worst stops (avg delay)")
        stops_df = cached_worst_stops(*filter_args)
        if stops_df.empty:
            render_empty_state()
        else:
            stops_df["avg_delay_min"] = (stops_df["avg_delay_sec"] / 60).round(1)
            st.dataframe(
                stops_df[["stop_name", "avg_delay_min", "n_observations"]].rename(
                    columns={
                        "stop_name": "Stop",
                        "avg_delay_min": "Avg delay (min)",
                        "n_observations": "Observations",
                    }
                ),
                use_container_width=True,
                height=460,
                hide_index=True,
            )

    st.divider()

    st.subheader("Delay distribution")
    dist_df = cached_delay_distribution(*filter_args)
    if dist_df.empty:
        render_empty_state()
    else:
        dist_df["delay_min"] = dist_df["delay_seconds"] / 60
        fig = px.histogram(dist_df, x="delay_min", nbins=60, labels={"delay_min": "Delay (min)"})
        fig.add_vline(x=0, line_dash="dash", line_color="gray")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)


def render_energy_tab(start_date, end_date) -> None:
    st.subheader("Relative bus energy score")
    st.markdown(
        """
This page ranks **bus routes** by a simple proxy we call an **energy score**.

**Important:** the score is **not** real electricity or fuel (no kWh, no litres).
We do not have meters on the buses. Instead we combine things we *can* measure from GTFS
schedules and realtime delays — how far a trip goes, how long it takes, how many stops it
makes, and how much delay piles up — into one comparable number from **0 to 100**.

Think of it like a **workload index**: a higher score means that route looks “heavier”
to operate relative to the other bus routes on the same day (more distance, more time,
more stops, and/or more delay). A low score means a lighter route in that peer group.
"""
    )

    with st.expander("How the score is built (for developers)", expanded=False):
        st.markdown(
            """
1. For each **bus trip**, estimate distance from stop coordinates (haversine along the stop
   sequence), duration from first→last arrival, stop count, and total positive delay.
2. Combine those four inputs with fixed weights (distance 35%, duration 35%, stops 20%,
   delay 10%) into a raw number.
3. **Average per route**, then **min–max scale** across routes so the lightest route ≈ 0
   and the heaviest ≈ 100 **for this region and date range only**. Scores are relative —
   you cannot compare a “40” from one day to another day as an absolute energy value.
4. A route is **flagged** only when it is both near the top of the score list
   (**≥ 90th percentile**) *and* has long trips (**p90 duration ≥ 75th percentile**).
   That avoids flagging a short hop that somehow got a noisy high score.
"""
        )

    if queries.using_sample_data():
        st.info(
            "Energy scores need local Postgres (`fact_route_energy_score`). "
            "Public sample mode only ships delay facts — run the compute job locally."
        )
        return

    regions = energy_queries.list_regions()
    region_labels = {name: rid for rid, name in regions}
    selected_region_name = st.selectbox("Region", options=list(region_labels.keys()), index=0)
    region_id = region_labels[selected_region_name]
    st.caption(
        "Region limits which trips count: a trip is included if enough of its stops fall "
        "inside the chosen map box (or all trips when “All stops” is selected)."
    )

    raw = cached_energy_scores(start_date, end_date, region_id)
    if raw.empty:
        st.warning(
            "No energy scores for this range. After delay facts exist, run:\n\n"
            "`py jobs/compute_route_energy_scores.py --service-date YYYY-MM-DD --region "
            f"{region_id}`"
        )
        return

    view = energy_queries.aggregate_energy_for_view(raw)
    flagged = view[view["is_flagged"] == True]  # noqa: E712
    top_score = view.nlargest(15, "energy_score")
    top_duration = view.nlargest(15, "p90_hours")
    mean_score = float(view["energy_score"].mean())
    n_routes = len(view)
    n_flagged = len(flagged)

    st.markdown("### At a glance")
    st.markdown(
        f"""
These three numbers summarize the whole peer group for **{selected_region_name}**
in the selected date range:

- **Routes scored ({n_routes}):** how many distinct bus routes had enough usable stop
  coordinates and trip times to compute a score. If this is small, the ranking is less
  stable — fewer peers to compare against.
- **Flagged ({n_flagged}):** routes that look both **high-workload** (top scores) and
  **long-running** (long p90 trip time). Red in the charts = flagged. Zero flagged does
  not mean “everything is fine”; it means nobody crossed *both* thresholds together.
- **Mean energy score ({mean_score:.1f}):** the average of the 0–100 scores. Because scores
  are min–max scaled inside this group, the mean often sits well below 50 when one route
  is a clear outlier (it pulls the top of the scale up, and everyone else compresses lower).
"""
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Routes scored", f"{n_routes:,}")
    c2.metric("Flagged (high score ∩ long trips)", f"{n_flagged:,}")
    c3.metric("Mean energy score", f"{mean_score:.1f}")

    left, right = st.columns(2)
    with left:
        st.markdown("### Highest energy score")
        st.markdown(
            """
**What you are looking at:** the 15 bus routes with the **largest** relative energy
scores. Longer bars = heavier estimated workload vs peers.

**How to read it:**
- **Blue** = high score but *not* flagged (either not long enough on duration, or not
  quite in the top score tier for flagging).
- **Red** = flagged — worth opening the table below and reading the reason tags.
- Hover a bar to see average km, p90 hours, and reason tags.

**Why this chart exists:** operators and analysts need a shortlist — “which routes look
most demanding today?” — without opening raw GTFS tables. A single red bar standing far
to the right usually means one route is dominating the peer group (much more distance /
time / stops / delay than the rest).
"""
        )
        fig = px.bar(
            top_score.sort_values("energy_score"),
            x="energy_score",
            y="route_short_name",
            orientation="h",
            color="is_flagged",
            color_discrete_map={True: "#c0392b", False: "#2980b9"},
            labels={
                "energy_score": "Energy score (0–100)",
                "route_short_name": "Route",
                "is_flagged": "Flagged",
            },
            hover_data={"avg_km": ":.1f", "p90_hours": ":.2f", "flag_reasons": True},
        )
        fig.update_layout(height=480, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("### Longest trip duration (p90 hours)")
        st.markdown(
            """
**What you are looking at:** the 15 routes whose trips take the longest when we look at
the **90th percentile** of trip duration (p90).

**What “p90 hours” means in plain language:** sort that route’s trip lengths from shortest
to longest; pick the value where **90% of trips are shorter**. So p90 = 0.8 hours means
most trips finish in under ~48 minutes, but the longer ones reach about 48 minutes. We use
p90 instead of the average so a few weird outliers do not hide a pattern of long runs.

**Why this chart exists next to the score chart:** energy score mixes several signals.
Duration alone answers a different question: “which routes keep the bus on the road the
longest?” A route can score high mainly from many short delayed hops, or mainly from long
runs. Comparing both charts tells you *which* ingredient is driving the result.
"""
        )
        fig = px.bar(
            top_duration.sort_values("p90_hours"),
            x="p90_hours",
            y="route_short_name",
            orientation="h",
            labels={"p90_hours": "P90 trip hours", "route_short_name": "Route"},
            hover_data={"energy_score": ":.1f", "avg_km": ":.1f"},
        )
        fig.update_layout(height=480)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Score vs duration")
    st.markdown(
        """
**What you are looking at:** each **dot is one bus route**.

| Axis / encoding | Meaning |
|---|---|
| **X (p90 hours)** | How long the longer trips on that route tend to run |
| **Y (energy score)** | Relative workload index (0–100) among peers |
| **Dot size** | How many trips we observed (bigger = more evidence) |
| **Colour** | Red = flagged; grey = not flagged |

**How to reason about the shape:**
- Dots that climb **up and to the right** support the idea that longer trips tend to get
  higher scores (duration is a large part of the formula).
- A **cluster bottom-left** means most routes are short and light — normal for a city bus
  network on a quiet slice of data.
- A **lonely red dot top-right** is the main call-out: that route is both long-running and
  high-scoring, so it cleared the flag rules. Hover it to see km and reason tags.
- A high score with **small** duration (up-left) would mean distance, stops, or delay —
  not trip length — is pushing the score. That is useful when diagnosing “why is this red?”
"""
    )
    scatter = view.copy()
    scatter["flag_label"] = scatter["is_flagged"].map({True: "Flagged", False: "Other"})
    fig = px.scatter(
        scatter,
        x="p90_hours",
        y="energy_score",
        color="flag_label",
        size="trip_count",
        hover_name="route_short_name",
        hover_data={"avg_km": ":.1f", "flag_reasons": True, "trip_count": True},
        labels={
            "p90_hours": "P90 trip hours",
            "energy_score": "Energy score",
            "flag_label": "",
        },
        color_discrete_map={"Flagged": "#c0392b", "Other": "#7f8c8d"},
    )
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Flagged routes & reason tags")
    st.markdown(
        """
**What you are looking at:** only the routes that met the flag rule (high score **and**
long p90 duration). The **Reasons** column explains *which inputs* were high relative to
other routes that day — tags are labels, not separate measurements of fuel.

| Tag | Plain meaning |
|---|---|
| `LONG_DISTANCE` | Average trip path is among the longer ones (more km) |
| `LONG_DURATION` | p90 trip time is among the longer ones |
| `HIGH_STOP_DENSITY` | Many stops per km (stop-and-go style work) |
| `CONGESTION` | Delay is large compared with trip duration |
| `HIGH_FREQUENCY` | Many trips observed (busy route in this window) |
| `SLOW_SPEED` | Hours per km is high (slow progress along the route) |

**Example reading:** a row with score ~38, p90 ~0.8 h, avg ~9 km, and tags
`LONG_DISTANCE, LONG_DURATION, CONGESTION, HIGH_FREQUENCY` means: among peers, this route
runs farther and longer, shows a lot of delay relative to runtime, and appears often in
the data — so the model treats it as a high relative workload candidate to investigate,
not as a proven kWh number.
"""
    )
    if flagged.empty:
        st.info(
            "No routes flagged for this selection. That only means nobody was *both* in the "
            "top score band (≥ p90) and in the long-duration band (p90 hours ≥ p75). "
            "You can still use the charts above to compare relative scores."
        )
    else:
        show = flagged[
            [
                "route_short_name",
                "route_long_name",
                "energy_score",
                "p90_hours",
                "avg_km",
                "trip_count",
                "flag_reasons",
            ]
        ].copy()
        show["energy_score"] = show["energy_score"].round(1)
        show["p90_hours"] = show["p90_hours"].round(2)
        show["avg_km"] = show["avg_km"].round(1)
        st.dataframe(
            show.rename(
                columns={
                    "route_short_name": "Route",
                    "route_long_name": "Name",
                    "energy_score": "Score",
                    "p90_hours": "P90 hours",
                    "avg_km": "Avg km",
                    "trip_count": "Trips",
                    "flag_reasons": "Reasons",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


if __name__ == "__main__":
    main()
