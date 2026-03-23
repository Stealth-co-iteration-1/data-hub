"""Streamlit dashboard for data-hub Sales Intelligence.

Displays insights from dbt marts:
- Pipeline health and forecasting
- Sales velocity and bottlenecks
- Rep performance and coaching insights
- Activity coverage analysis
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from sqlalchemy import Engine, create_engine

# Page config
st.set_page_config(
    page_title="Sales Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
)


@st.cache_resource
def get_db_connection() -> Engine:
    """Create database connection from environment variables."""
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://datahub:datahub@localhost:5432/datahub",
    )
    return create_engine(db_url)


def query_df(sql: str) -> pd.DataFrame:
    """Execute SQL and return DataFrame."""
    engine = get_db_connection()
    try:
        return pd.read_sql(sql, engine)
    except Exception:
        return pd.DataFrame()


def table_exists(table: str, schema: str = "public") -> bool:
    """Check if a table exists."""
    sql = f"""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = '{schema}' AND table_name = '{table}'
        ) as exists
    """
    result = query_df(sql)
    return bool(result["exists"].iloc[0]) if not result.empty else False


# =========================================================================
# HEADER
# =========================================================================

st.title("📊 Sales Intelligence Dashboard")

# Check if marts exist
marts_exist = table_exists("fct_opportunities", "marts")
staging_exist = table_exists("stg_salesforce__opportunities", "staging")

if not marts_exist:
    st.warning(
        "**dbt marts not found.** Run `dbt run` to build the analytics tables.\n\n"
        "```bash\ncd dbt_project && dbt run --profiles-dir .\n```"
    )
    if staging_exist:
        st.info("Staging tables exist. Only marts need to be built.")
    st.stop()


# =========================================================================
# OVERVIEW SECTION
# =========================================================================

st.header("🏠 Overview")

# Load key metrics from marts
overview_metrics = query_df("""
    SELECT
        count(*) as total_opportunities,
        count(*) filter (where opportunity_status = 'Open') as open_opportunities,
        count(*) filter (where opportunity_status = 'Won') as won_opportunities,
        count(*) filter (where opportunity_status = 'Lost') as lost_opportunities,
        sum(amount) filter (where opportunity_status = 'Open') as open_pipeline,
        sum(amount) filter (where opportunity_status = 'Won') as won_revenue,
        avg(amount) as avg_deal_size,
        avg(days_to_close) filter (where opportunity_status != 'Open') as avg_days_to_close
    FROM marts.fct_opportunities
""")

activity_metrics = query_df("""
    SELECT
        count(*) as total_activities,
        count(*) filter (where activity_type = 'event') as total_events,
        count(*) filter (where activity_type = 'task') as total_tasks,
        count(*) filter (where is_completed) as completed_tasks
    FROM marts.fct_activities
""")

if not overview_metrics.empty:
    m = overview_metrics.iloc[0]

    # Row 1: Pipeline metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        pipeline = m["open_pipeline"] or 0
        st.metric("Open Pipeline", f"${pipeline:,.0f}")

    with col2:
        won = m["won_revenue"] or 0
        st.metric("Won Revenue", f"${won:,.0f}")

    with col3:
        avg_size = m["avg_deal_size"] or 0
        st.metric("Avg Deal Size", f"${avg_size:,.0f}")

    with col4:
        won_count = m["won_opportunities"] or 0
        lost_count = m["lost_opportunities"] or 0
        total_closed = won_count + lost_count
        win_rate = (won_count / total_closed * 100) if total_closed > 0 else 0
        st.metric("Win Rate", f"{win_rate:.1f}%")

    # Row 2: Counts
    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.metric("Open Opportunities", f"{m['open_opportunities'] or 0:,}")

    with col6:
        st.metric("Won Deals", f"{m['won_opportunities'] or 0:,}")

    with col7:
        if not activity_metrics.empty:
            a = activity_metrics.iloc[0]
            st.metric("Total Activities", f"{a['total_activities'] or 0:,}")

    with col8:
        avg_days = m["avg_days_to_close"]
        st.metric("Avg Days to Close", f"{avg_days:.0f}" if pd.notna(avg_days) else "N/A")

# Last refresh
refresh_df = query_df("SELECT max(refreshed_at) as last_refresh FROM marts.fct_opportunities")
if not refresh_df.empty and refresh_df["last_refresh"].iloc[0]:
    st.caption(f"Data refreshed: {refresh_df['last_refresh'].iloc[0]}")

st.divider()


# =========================================================================
# PIPELINE SNAPSHOT
# =========================================================================

st.header("📈 Pipeline Snapshot")

pipeline_df = query_df("""
    SELECT * FROM reports.rpt_pipeline_snapshot
    ORDER BY report_section, dimension
""")

if not pipeline_df.empty:
    # Split by section
    by_stage = pipeline_df[pipeline_df["report_section"] == "by_stage"]
    by_time = pipeline_df[pipeline_df["report_section"] == "by_close_date"]
    totals = pipeline_df[pipeline_df["report_section"] == "total"]

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("By Stage")
        if not by_stage.empty:
            chart_data = by_stage[["dimension", "total_amount"]].copy()
            chart_data.columns = ["Stage", "Amount"]
            st.bar_chart(chart_data.set_index("Stage"))

            st.dataframe(
                by_stage[["dimension", "opportunity_count", "total_amount", "weighted_amount"]].rename(
                    columns={
                        "dimension": "Stage",
                        "opportunity_count": "Count",
                        "total_amount": "Total",
                        "weighted_amount": "Weighted",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    with col_right:
        st.subheader("By Close Date")
        if not by_time.empty:
            # Order time buckets properly
            time_order = ["Overdue", "This Week", "This Month", "This Quarter", "Future"]
            by_time["sort_order"] = by_time["dimension"].map(
                {v: i for i, v in enumerate(time_order)}
            )
            by_time = by_time.sort_values("sort_order")

            chart_data = by_time[["dimension", "total_amount"]].copy()
            chart_data.columns = ["Time Horizon", "Amount"]
            st.bar_chart(chart_data.set_index("Time Horizon"))

            st.dataframe(
                by_time[["dimension", "opportunity_count", "total_amount", "weighted_amount"]].rename(
                    columns={
                        "dimension": "Time Horizon",
                        "opportunity_count": "Count",
                        "total_amount": "Total",
                        "weighted_amount": "Weighted",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
else:
    st.info("No pipeline data available.")

st.divider()


# =========================================================================
# SALES VELOCITY
# =========================================================================

st.header("⏱️ Sales Velocity")
st.caption("Where do deals get stuck?")

velocity_df = query_df("""
    SELECT * FROM reports.rpt_sales_velocity
    ORDER BY avg_days_in_stage DESC
""")

if not velocity_df.empty:
    col_left, col_right = st.columns([2, 1])

    with col_left:
        # Bar chart of avg days per stage
        chart_data = velocity_df[["stage_name", "avg_days_in_stage"]].copy()
        chart_data.columns = ["Stage", "Avg Days"]
        st.bar_chart(chart_data.set_index("Stage"))

    with col_right:
        # Bottleneck callout
        bottlenecks = velocity_df[velocity_df["is_bottleneck"] == True]  # noqa: E712
        if not bottlenecks.empty:
            st.error("**Bottleneck Stages**")
            for _, row in bottlenecks.iterrows():
                st.write(f"- **{row['stage_name']}**: {row['avg_days_in_stage']:.1f} days avg")
        else:
            st.success("No bottleneck stages detected")

    # Full table
    st.dataframe(
        velocity_df[
            ["stage_name", "transitions_count", "avg_days_in_stage", "median_days_in_stage", "is_bottleneck"]
        ].rename(
            columns={
                "stage_name": "Stage",
                "transitions_count": "Transitions",
                "avg_days_in_stage": "Avg Days",
                "median_days_in_stage": "Median Days",
                "is_bottleneck": "Bottleneck?",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No velocity data available. Need opportunity history records.")

st.divider()


# =========================================================================
# REP PERFORMANCE
# =========================================================================

st.header("👥 Rep Performance")
st.caption("Who are top performers? Who needs coaching?")

rep_df = query_df("""
    SELECT * FROM reports.rpt_win_rate_by_owner
    ORDER BY won_revenue DESC NULLS LAST
""")

if not rep_df.empty:
    # Performance tier summary
    tier_counts = rep_df["performance_tier"].value_counts()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        high = tier_counts.get("High Performer", 0)
        st.metric("High Performers", high, help="Win rate >= 40%")

    with col2:
        avg = tier_counts.get("Average", 0)
        st.metric("Average", avg, help="Win rate 25-39%")

    with col3:
        needs = tier_counts.get("Needs Coaching", 0)
        st.metric("Needs Coaching", needs, help="Win rate < 25%")

    with col4:
        no_closed = tier_counts.get("No Closed Deals", 0)
        st.metric("No Closed Deals", no_closed)

    st.divider()

    # Full leaderboard
    st.subheader("Leaderboard")

    display_df = rep_df[
        [
            "owner_name",
            "total_opportunities",
            "won_opportunities",
            "win_rate_pct",
            "won_revenue",
            "avg_won_deal_size",
            "avg_days_to_close",
            "performance_tier",
        ]
    ].copy()

    display_df.columns = [
        "Rep",
        "Total Opps",
        "Won",
        "Win Rate %",
        "Won Revenue",
        "Avg Deal Size",
        "Avg Days to Close",
        "Tier",
    ]

    # Format currency columns
    display_df["Won Revenue"] = display_df["Won Revenue"].apply(
        lambda x: f"${x:,.0f}" if pd.notna(x) else "N/A"
    )
    display_df["Avg Deal Size"] = display_df["Avg Deal Size"].apply(
        lambda x: f"${x:,.0f}" if pd.notna(x) else "N/A"
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("No rep performance data available.")

st.divider()


# =========================================================================
# ACTIVITY COVERAGE
# =========================================================================

st.header("📞 Activity Coverage")
st.caption("Do more activities correlate with higher win rates?")

coverage_df = query_df("""
    SELECT * FROM reports.rpt_activity_coverage
""")

if not coverage_df.empty:
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Win Rate by Activity Level")
        chart_data = coverage_df[["activity_bucket", "win_rate_pct"]].copy()
        chart_data.columns = ["Activity Level", "Win Rate %"]
        st.bar_chart(chart_data.set_index("Activity Level"))

    with col_right:
        st.subheader("Revenue by Activity Level")
        chart_data = coverage_df[["activity_bucket", "won_revenue"]].copy()
        chart_data.columns = ["Activity Level", "Won Revenue"]
        st.bar_chart(chart_data.set_index("Activity Level"))

    # Insight callout
    high_activity = coverage_df[coverage_df["activity_bucket"] == "11+ High"]
    low_activity = coverage_df[coverage_df["activity_bucket"] == "0 - No activities"]

    if not high_activity.empty and not low_activity.empty:
        high_win = high_activity["win_rate_pct"].iloc[0] or 0
        low_win = low_activity["win_rate_pct"].iloc[0] or 0

        if high_win > low_win:
            diff = high_win - low_win
            st.success(
                f"**Insight:** High-activity opportunities have a {diff:.1f}pp higher win rate "
                f"({high_win:.1f}% vs {low_win:.1f}%)"
            )

    # Full table
    st.dataframe(
        coverage_df[
            ["activity_bucket", "opportunity_count", "won_count", "win_rate_pct", "won_revenue"]
        ].rename(
            columns={
                "activity_bucket": "Activity Level",
                "opportunity_count": "Opportunities",
                "won_count": "Won",
                "win_rate_pct": "Win Rate %",
                "won_revenue": "Won Revenue",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No activity coverage data available.")

st.divider()


# =========================================================================
# TOP OPPORTUNITIES
# =========================================================================

st.header("🎯 Top Open Opportunities")

top_opps = query_df("""
    SELECT
        opportunity_name,
        amount,
        stage_name,
        probability,
        close_date,
        days_until_close,
        total_activities,
        owner_id
    FROM marts.fct_opportunities
    WHERE opportunity_status = 'Open'
    ORDER BY amount DESC NULLS LAST
    LIMIT 15
""")

if not top_opps.empty:
    display_df = top_opps.copy()
    display_df["amount"] = display_df["amount"].apply(
        lambda x: f"${x:,.0f}" if pd.notna(x) else "N/A"
    )
    display_df["probability"] = display_df["probability"].apply(
        lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"
    )
    display_df.columns = [
        "Opportunity",
        "Amount",
        "Stage",
        "Probability",
        "Close Date",
        "Days Until Close",
        "Activities",
        "Owner ID",
    ]

    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("No open opportunities found.")


# =========================================================================
# FOOTER
# =========================================================================

st.divider()
st.caption(
    "Data powered by Dagster + dbt | "
    "Raw: `salesforce_*` → Staging: `stg_salesforce__*` → "
    "Facts: `fct_*` → Reports: `rpt_*`"
)
