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
def cached_route_lateness(start_date, end_date, route_ids, vehicle_types, min_observations):
    filters = Filters(start_date, end_date, list(route_ids), list(vehicle_types))
    return queries.get_route_lateness(filters, min_observations=min_observations)


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


def _punctuality_summary(delay_min: pd.Series) -> dict:
    """Build simple punctuality stats from delay minutes (non-null)."""
    n = int(len(delay_min))
    if n == 0:
        return {"n": 0}

    early = delay_min < -1
    on_time = delay_min.between(-1, 1, inclusive="both")
    late = delay_min > 1

    def pct(mask: pd.Series) -> float:
        return 100.0 * float(mask.sum()) / n

    return {
        "n": n,
        "early_pct": pct(early),
        "on_time_pct": pct(on_time),
        "late_pct": pct(late),
        "within_1_pct": pct(delay_min.abs() <= 1),
        "within_3_pct": pct(delay_min.abs() <= 3),
        "within_5_pct": pct(delay_min.abs() <= 5),
        "within_10_pct": pct(delay_min.abs() <= 10),
        "median_min": float(delay_min.median()),
        "p90_min": float(delay_min.quantile(0.90)),
    }


def _punctuality_story(stats: dict) -> str:
    """One short paragraph a non-expert can understand."""
    if not stats.get("n"):
        return "No delay measurements available for these filters."

    dominant = max(
        ("early", stats["early_pct"]),
        ("about on time", stats["on_time_pct"]),
        ("late", stats["late_pct"]),
        key=lambda x: x[1],
    )[0]

    return (
        f"Out of **{stats['n']:,}** stop arrivals with a live update, "
        f"**{stats['on_time_pct']:.0f}%** were about on time (+/-1 min), "
        f"**{stats['early_pct']:.0f}%** were early, and "
        f"**{stats['late_pct']:.0f}%** were late. "
        f"Most arrivals in this filter fall in the **{dominant}** group. "
        f"Half of arrivals were within about **{stats['median_min']:+.1f} min** of the plan "
        f"(median), and 9 out of 10 were at or below **{stats['p90_min']:+.1f} min** (p90)."
    )


def _robust_color_range(values: pd.Series, pad: float = 0.5) -> tuple[float, float]:
    """Colour limits that ignore extreme outliers (p5..p95), in minutes."""
    clean = values.dropna()
    if clean.empty:
        return -5.0, 15.0
    lo = float(clean.quantile(0.05))
    hi = float(clean.quantile(0.95))
    if hi - lo < 1.0:
        mid = float(clean.median())
        lo, hi = mid - 5.0, mid + 5.0
    return lo - pad, hi + pad


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
    st.sidebar.caption(
        "These filters apply to **both** tabs. Leave Route / Vehicle type empty to see everything."
    )
    default_start = max(min_date, max_date - timedelta(days=6))
    date_range = st.sidebar.date_input(
        "Date range",
        value=(default_start, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Only days that already have data in the warehouse.",
    )
    # While the user has only picked one endpoint, Streamlit returns a
    # 1-tuple instead of a pair — fall back to the defaults until both are set.
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = default_start, max_date

    routes_df = cached_routes()
    route_options = dict(zip(routes_df["route_short_name"], routes_df["route_id"], strict=False))
    selected_route_names = st.sidebar.multiselect(
        "Route",
        options=list(route_options.keys()),
        help="Pick one or more line names. Empty = all routes.",
    )
    selected_route_ids = tuple(route_options[name] for name in selected_route_names)

    vehicle_types_df = cached_vehicle_types()
    selected_vehicle_types = tuple(
        st.sidebar.multiselect(
            "Vehicle type",
            options=vehicle_types_df["type_name"].tolist(),
            help="Bus, Metro, Rail, etc. Empty = all types.",
        )
    )

    filter_args = (start_date, end_date, selected_route_ids, selected_vehicle_types)

    delay_tab, energy_tab = st.tabs(["Delays", "Energy scores"])

    with delay_tab:
        render_delay_tab(filter_args)

    with energy_tab:
        render_energy_tab(start_date, end_date)


def render_delay_tab(filter_args: tuple) -> None:
    st.subheader("How late are the buses and trains?")
    st.markdown(
        """
This tab answers one simple question: **are vehicles on time, early, or late?**

We compare the **planned** arrival time (from the schedule) with the **actual** arrival
time (from live updates). The difference is the delay:

| Delay | Meaning |
|---|---|
| **Positive** (e.g. +5 min) | Late |
| **Zero** | On time |
| **Negative** (e.g. −2 min) | Early |
| **Missing** | No live update matched that stop (unknown) |

Use the **sidebar filters** (date, route, vehicle type) to focus. Empty filters = show all.
"""
    )

    kpis = cached_kpis(*filter_args)
    if kpis["total_facts"] == 0:
        render_empty_state()
        return

    st.markdown("### 1) Numbers at a glance")
    st.markdown(
        """
These five cards summarize the filtered data. Read them **before** the charts.

| Card | What it tells you |
|---|---|
| **Median delay** | Middle delay (half better, half worse). More stable than average. |
| **% on-time** | Share on time or early (delay ≤ 0). Higher is better. |
| **Trips observed** | Distinct trips seen. Low count → less trustworthy charts. |
| **Realtime match %** | Share with a live update. Low % → many unknown delays. |
| **Worst route** | Highest average delay in your filter — start investigating here. |
"""
    )
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Median delay", fmt_minutes(kpis["median_delay_sec"]))
    on_time_pct = (
        f"{kpis['on_time_rate'] * 100:.1f}%" if kpis["on_time_rate"] is not None else "N/A"
    )
    col2.metric("% on-time (≤0 delay)", on_time_pct)
    col3.metric("Trips observed", f"{kpis['trips_observed']:,}")
    match_pct = (
        f"{kpis['realtime_match_rate'] * 100:.1f}%"
        if kpis.get("realtime_match_rate") is not None
        else "N/A"
    )
    col4.metric("Realtime match %", match_pct)
    col5.metric("Worst route (avg delay)", kpis["worst_route"])

    st.divider()

    st.markdown("### 2) Which routes are late?")
    st.markdown(
        """
**Question:** *Which lines should I look at first?*

We rank routes by how often they are late — not only by average delay
(averages can be skewed by a few extreme trips).

| Term | Meaning here |
|---|---|
| **% late** | Share of arrivals more than **1 minute** after the plan |
| **% very late** | Share more than **5 minutes** late |
| **Avg / median delay** | Typical lateness in minutes (median is more robust) |
| **Samples** | How many arrivals we measured — ignore tiny samples |
"""
    )
    ctrl1, ctrl2 = st.columns(2)
    with ctrl1:
        sort_by = st.radio(
            "Rank routes by",
            options=["% late (recommended)", "Average delay (minutes)"],
            horizontal=True,
            help=(
                "% late = how often is this line late? "
                "Average = how late is it typically?"
            ),
        )
    with ctrl2:
        min_obs = st.slider(
            "Minimum samples per route",
            min_value=5,
            max_value=100,
            value=20,
            step=5,
            help="Hide routes with too little data so outliers cannot dominate.",
        )

    route_df = cached_route_lateness(*filter_args, min_obs)
    if route_df.empty:
        render_empty_state(
            "No routes meet the minimum sample size. Lower the slider or widen filters."
        )
    else:
        view = route_df.copy()
        view["avg_delay_min"] = view["avg_delay_sec"] / 60.0
        view["median_delay_min"] = view["median_delay_sec"] / 60.0
        view["pct_late_display"] = (view["pct_late"] * 100).round(1)
        view["pct_very_late_display"] = (view["pct_very_late"] * 100).round(1)

        if sort_by.startswith("% late"):
            view = view.sort_values(["pct_late", "avg_delay_min"], ascending=False)
            bar_x = "pct_late_display"
            bar_label = "% of arrivals late (>1 min)"
        else:
            view = view.sort_values(["avg_delay_min", "pct_late"], ascending=False)
            bar_x = "avg_delay_min"
            bar_label = "Average delay (minutes)"

        view = view.reset_index(drop=True)
        top = view.head(3)
        st.markdown("#### Top 3 problem routes (with enough data)")
        cards = st.columns(3)
        for i, (_, row) in enumerate(top.iterrows()):
            with cards[i]:
                st.metric(
                    label=f"#{i + 1}  Route {row['route_short_name']}",
                    value=f"{row['pct_late_display']:.0f}% late",
                    delta=(
                        f"avg {row['avg_delay_min']:+.1f} min · "
                        f"{int(row['n_observations']):,} samples"
                    ),
                    delta_color="off",
                )

        chart_col, table_col = st.columns([1.1, 1])
        with chart_col:
            st.markdown("#### Chart — top 15")
            st.caption(
                "Longer bar = worse on the ranking you chose. "
                "Hover for route name and value."
            )
            top15 = view.head(15).sort_values(bar_x)
            fig = px.bar(
                top15,
                x=bar_x,
                y="route_short_name",
                orientation="h",
                labels={bar_x: bar_label, "route_short_name": "Route"},
                color=bar_x,
                color_continuous_scale="RdYlGn_r",
                hover_data={
                    "pct_late_display": True,
                    "avg_delay_min": ":.1f",
                    "median_delay_min": ":.1f",
                    "n_observations": True,
                },
            )
            fig.update_layout(height=520, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

        with table_col:
            st.markdown("#### Table — same ranking")
            st.caption("Use this when you want exact numbers, not just the picture.")
            table = view.head(15)[
                [
                    "route_short_name",
                    "pct_late_display",
                    "pct_very_late_display",
                    "avg_delay_min",
                    "median_delay_min",
                    "n_observations",
                ]
            ].copy()
            table["avg_delay_min"] = table["avg_delay_min"].round(1)
            table["median_delay_min"] = table["median_delay_min"].round(1)
            st.dataframe(
                table.rename(
                    columns={
                        "route_short_name": "Route",
                        "pct_late_display": "% late (>1 min)",
                        "pct_very_late_display": "% very late (>5 min)",
                        "avg_delay_min": "Avg delay (min)",
                        "median_delay_min": "Median delay (min)",
                        "n_observations": "Samples",
                    }
                ),
                use_container_width=True,
                height=520,
                hide_index=True,
            )

        st.markdown(
            """
**How to use this**
- Prefer **% late** when asking “which lines fail often?”
- Prefer **average delay** when asking “which lines are late by a lot when they miss?”
- Always glance at **Samples** — a route with 8 samples is less trustworthy than one with 800.
"""
        )

    st.divider()

    st.markdown("### 3) When is delay worst? (by day + hour)")
    st.markdown(
        """
**Simple idea:** each cell is one **weekday + hour** combo.
Colour = average delay in **minutes** for that slot.

| Colour | Meaning |
|---|---|
| Greener | Closer to on time / early |
| Redder | More late on average |

**Tip:** if you only see one weekday, widen the **Date range** in the sidebar —
the grid can only show days that have data.
"""
    )
    heatmap_df = cached_heatmap(*filter_args)
    if heatmap_df.empty:
        render_empty_state()
    else:
        heatmap_df = heatmap_df.copy()
        heatmap_df["avg_delay_min"] = heatmap_df["avg_delay_sec"] / 60
        days_present = sorted(heatmap_df["day_name"].dropna().unique().tolist())
        st.caption(
            f"Days with data in this filter: **{', '.join(days_present)}** "
            f"({len(heatmap_df)} hour-slots). "
            "Colour scale ignores extreme outliers so normal hours stay readable."
        )
        pivot = heatmap_df.pivot(
            index="day_name", columns="hour_of_day", values="avg_delay_min"
        )
        # dim_date.day_name is abbreviated (TO_CHAR(d, 'Dy') in sql/seed_dim_date.sql).
        day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        pivot = pivot.reindex([d for d in day_order if d in pivot.index])
        zmin, zmax = _robust_color_range(heatmap_df["avg_delay_min"])
        fig = px.imshow(
            pivot,
            labels={
                "x": "Hour of day (0-23)",
                "y": "Day of week",
                "color": "Avg delay (min)",
            },
            color_continuous_scale="RdYlGn_r",
            aspect="auto",
            zmin=zmin,
            zmax=zmax,
        )
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

        # Easy companion: busiest late hours as a small table
        late_hours = (
            heatmap_df.sort_values("avg_delay_min", ascending=False)
            .head(8)[["day_name", "hour_of_day", "avg_delay_min"]]
            .copy()
        )
        late_hours["avg_delay_min"] = late_hours["avg_delay_min"].round(1)
        st.markdown("**Worst time slots in this filter** (same data as the grid):")
        st.dataframe(
            late_hours.rename(
                columns={
                    "day_name": "Day",
                    "hour_of_day": "Hour",
                    "avg_delay_min": "Avg delay (min)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    left2, right2 = st.columns(2)

    with left2:
        st.markdown("### 4) Where on the map are stops late?")
        st.markdown(
            """
**Simple idea:** each **dot = one stop**.

| Signal | Meaning |
|---|---|
| **Colour** | Average delay (minutes). Redder = later |
| **Size** | How many samples. Bigger = more trustworthy |
| **Hover** | Stop name + exact delay |

Colour is scaled with a **robust range** (ignores a few crazy outliers), so the map
stays readable. Extreme stops still appear in the Top 10 list on the right.
"""
        )
        map_df = cached_map_data(*filter_args)
        if map_df.empty:
            render_empty_state("No stop coordinates for the selected filters.")
        else:
            map_df = map_df.copy()
            map_df["avg_delay_min"] = map_df["avg_delay_sec"] / 60
            # Prefer stops with a little evidence on the map
            map_plot = map_df[map_df["n_observations"] >= 3].copy()
            if map_plot.empty:
                map_plot = map_df
            cmin, cmax = _robust_color_range(map_plot["avg_delay_min"])
            st.caption(
                f"Showing **{len(map_plot):,}** stops "
                f"(colour roughly {cmin:.0f} to {cmax:.0f} min for readability)."
            )
            fig = px.scatter_map(
                map_plot,
                lat="stop_lat",
                lon="stop_lon",
                color="avg_delay_min",
                size="n_observations",
                hover_name="stop_name",
                hover_data={"avg_delay_min": ":.1f", "n_observations": True},
                color_continuous_scale="RdYlGn_r",
                range_color=(cmin, cmax),
                map_style="open-street-map",
                zoom=9,
                height=500,
                labels={"avg_delay_min": "Avg delay (min)"},
            )
            fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
            st.plotly_chart(fig, use_container_width=True)

    with right2:
        st.markdown("### 5) Top 10 worst stops (list)")
        st.markdown(
            """
**Same story as the map**, as a ranked list.

- **Avg delay (min)** — higher = worse
- **Observations** — prefer larger numbers (more evidence)

A stop with huge delay but only 3 observations can be noise — check the sample count.
"""
        )
        stops_df = cached_worst_stops(*filter_args)
        if stops_df.empty:
            render_empty_state()
        else:
            stops_df["avg_delay_min"] = (stops_df["avg_delay_sec"] / 60).round(1)
            st.dataframe(
                stops_df[["stop_name", "avg_delay_min", "n_observations"]].rename(
                    columns={
                        "stop_name": "Stop name",
                        "avg_delay_min": "Avg delay (min)",
                        "n_observations": "Observations",
                    }
                ),
                use_container_width=True,
                height=420,
                hide_index=True,
            )

    st.divider()

    st.markdown("### 6) Punctuality — easy view")
    st.markdown(
        """
**Forget “distribution”.** This section answers only:

> *Of all arrivals that got a live update, how punctual were they?*

We do **not** plot every weird outlier on a stretched axis. Instead we show:
1. a **short written summary**,
2. three big groups (**early / on time / late**),
3. a **punctuality ladder** — what % stayed within 1, 3, 5, or 10 minutes of the plan.
"""
    )
    dist_df = cached_delay_distribution(*filter_args)
    if dist_df.empty:
        render_empty_state()
    else:
        delay_min = dist_df["delay_seconds"] / 60.0
        stats = _punctuality_summary(delay_min)

        st.info(_punctuality_story(stats))

        st.markdown("#### Step A — Three groups only")
        st.caption(
            "Early = more than 1 minute early · On time = within ±1 minute · "
            "Late = more than 1 minute late."
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Early", f"{stats['early_pct']:.0f}%")
        c2.metric("About on time", f"{stats['on_time_pct']:.0f}%")
        c3.metric("Late", f"{stats['late_pct']:.0f}%")

        pie_df = pd.DataFrame(
            {
                "group": ["Early", "About on time", "Late"],
                "percent": [stats["early_pct"], stats["on_time_pct"], stats["late_pct"]],
            }
        )
        fig_pie = px.pie(
            pie_df,
            names="group",
            values="percent",
            color="group",
            color_discrete_map={
                "Early": "#3498db",
                "About on time": "#27ae60",
                "Late": "#e74c3c",
            },
            hole=0.45,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(height=320, showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("#### Step B — Punctuality ladder (most useful view)")
        st.markdown(
            """
Ask: **“What share of arrivals stayed close enough to the timetable?”**

Each bar is independent (not stacked). Higher % on the tighter rows = better service.
Example: **within 5 minutes = 90%** means 9 of 10 arrivals were at most 5 minutes
early or late.
"""
        )
        ladder = pd.DataFrame(
            {
                "rule": [
                    "Within ±1 minute",
                    "Within ±3 minutes",
                    "Within ±5 minutes",
                    "Within ±10 minutes",
                ],
                "percent": [
                    stats["within_1_pct"],
                    stats["within_3_pct"],
                    stats["within_5_pct"],
                    stats["within_10_pct"],
                ],
            }
        )
        fig_ladder = px.bar(
            ladder,
            x="percent",
            y="rule",
            orientation="h",
            text="percent",
            labels={"percent": "Share of arrivals (%)", "rule": ""},
            color="percent",
            color_continuous_scale="Greens",
            range_x=[0, 100],
        )
        fig_ladder.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
        fig_ladder.update_layout(
            height=280,
            coloraxis_showscale=False,
            margin=dict(l=10, r=40, t=10, b=10),
        )
        st.plotly_chart(fig_ladder, use_container_width=True)

        st.markdown(
            f"""
**How to judge this quickly**

| If you see… | It usually means… |
|---|---|
| High **About on time** + high **within ±5 min** | Service is mostly reliable |
| High **Late** but still high **within ±10 min** | Small delays are common; huge delays are rare |
| Low **within ±10 min** | Many arrivals are far from the plan — dig into routes/stops above |
| Median around **{stats['median_min']:+.1f} min** | Typical arrival in this filter |

This replaces the old “delay distribution” histogram, which was hard to read when a few
extreme values stretched the scale.
"""
        )

    with st.expander("If something looks empty or weird", expanded=False):
        st.markdown(
            """
- **No data** → widen the date range or clear route filters.
- **Very high delays** → can be real congestion, or a bad join / sparse realtime match.
  Check **Realtime match %** above.
- **Public demo** uses a sample CSV export; local mode reads your Postgres warehouse.
"""
        )


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
            "Public demo mode: energy scores come from the shipped sample CSV "
            "(`dashboard/sample_data/energy_scores.csv.gz`), not your home Postgres."
        )

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
        if queries.using_sample_data():
            st.warning(
                "No energy sample for this date/region. "
                "Widen the date range, try region **All stops**, or re-export with "
                "`py scripts/export_dashboard_sample.py`."
            )
        else:
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
