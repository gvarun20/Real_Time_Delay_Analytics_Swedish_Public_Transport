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

from dashboard import queries  # noqa: E402
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


if __name__ == "__main__":
    main()
