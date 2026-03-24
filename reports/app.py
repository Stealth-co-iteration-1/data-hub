"""Streamlit dashboard for data-hub Sales Intelligence.

Sections:
1. Data Health - Audit log style metrics (record counts, sync status, coverage)
2. Revenue Overview - Key pipeline and revenue metrics
3. Deal Velocity - Where deals get stuck (per spec Section 2.5)
4. Rep Performance - Attribution and coaching insights
5. Activity Attribution - Activity to revenue correlation (per spec Section 4)
6. Contact Coverage - Data quality for attribution (per spec conditional)
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from sqlalchemy import Engine, create_engine

# Page config - wide layout for dashboards
st.set_page_config(
    page_title="Staq Sales Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
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


def format_number(val: float | None, prefix: str = "", suffix: str = "") -> str:
    """Format number with optional prefix/suffix."""
    if pd.isna(val) or val is None:
        return "N/A"
    return f"{prefix}{val:,.0f}{suffix}"


def format_currency(val: float | None) -> str:
    """Format as currency."""
    return format_number(val, prefix="$")


def format_pct(val: float | None) -> str:
    """Format as percentage."""
    if pd.isna(val) or val is None:
        return "N/A"
    return f"{val:.1f}%"


# =========================================================================
# HEADER
# =========================================================================

st.title("Staq Sales Intelligence")

# Check if data exists
marts_exist = table_exists("fct_opportunities", "public_marts")
raw_exist = table_exists("salesforce_opportunities", "public_raw")

if not raw_exist:
    st.error(
        "**No raw data found.** Run Dagster materializations to ingest Salesforce data.\n\n"
        "```bash\nsource .env && dagster dev\n```"
    )
    st.stop()

if not marts_exist:
    st.warning(
        "**dbt marts not found.** Run `dbt run` to build the analytics tables.\n\n"
        "```bash\ncd dbt_project && dbt run --profiles-dir .\n```"
    )
    st.stop()

# Last refresh timestamp
refresh_df = query_df("SELECT max(refreshed_at) as last_refresh FROM public_marts.fct_opportunities")
if not refresh_df.empty and refresh_df["last_refresh"].iloc[0]:
    st.caption(f"Last refreshed: {refresh_df['last_refresh'].iloc[0]}")

st.divider()

# =========================================================================
# TABS FOR ORGANIZED CONTENT
# =========================================================================

tab_overview, tab_velocity, tab_reps, tab_activity, tab_health = st.tabs([
    "Revenue Overview",
    "Deal Velocity",
    "Rep Performance",
    "Activity Attribution",
    "Data Health"
])


# =========================================================================
# TAB 1: REVENUE OVERVIEW
# =========================================================================

with tab_overview:
    overview_metrics = query_df("""
        SELECT
            count(*) as total_opportunities,
            count(*) filter (where opportunity_status = 'Open') as open_opportunities,
            count(*) filter (where opportunity_status = 'Won') as won_opportunities,
            count(*) filter (where opportunity_status = 'Lost') as lost_opportunities,
            sum(amount) filter (where opportunity_status = 'Open') as open_pipeline,
            sum(amount) filter (where opportunity_status = 'Won') as won_revenue,
            sum(amount) filter (where opportunity_status = 'Lost') as lost_revenue,
            avg(amount) filter (where opportunity_status = 'Won') as avg_won_deal_size,
            avg(days_to_close) filter (where opportunity_status = 'Won') as avg_days_to_close_won
        FROM public_marts.fct_opportunities
    """)

    if not overview_metrics.empty:
        m = overview_metrics.iloc[0]

        # Calculate win rate
        won = m["won_opportunities"] or 0
        lost = m["lost_opportunities"] or 0
        total_closed = won + lost
        win_rate = (won / total_closed * 100) if total_closed > 0 else 0

        # KPI Cards Row 1
        st.subheader("Key Metrics")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4, gap="medium")

        with kpi1:
            with st.container(border=True):
                st.metric("Open Pipeline", format_currency(m["open_pipeline"]))
                st.caption(f"{int(m['open_opportunities'] or 0)} open deals")

        with kpi2:
            with st.container(border=True):
                st.metric("Won Revenue", format_currency(m["won_revenue"]))
                st.caption(f"{int(m['won_opportunities'] or 0)} won deals")

        with kpi3:
            with st.container(border=True):
                st.metric("Win Rate", format_pct(win_rate))
                st.caption(f"{int(total_closed)} closed deals")

        with kpi4:
            with st.container(border=True):
                days = m["avg_days_to_close_won"]
                st.metric("Avg Days to Close", f"{days:.0f}" if pd.notna(days) else "N/A")
                st.caption("Won deals only")

        st.divider()

        # Pipeline by Stage
        st.subheader("Pipeline by Stage")

        pipeline_by_stage = query_df("""
            SELECT
                stage_name,
                count(*) as deal_count,
                sum(amount) as total_amount,
                sum(amount * probability / 100) as weighted_amount,
                avg(days_open) as avg_days_in_stage
            FROM public_marts.fct_opportunities
            WHERE opportunity_status = 'Open'
            GROUP BY stage_name
            ORDER BY total_amount DESC NULLS LAST
        """)

        if not pipeline_by_stage.empty:
            col_chart, col_table = st.columns([3, 2], gap="large")

            with col_chart:
                with st.container(border=True):
                    chart_data = pipeline_by_stage[["stage_name", "total_amount"]].copy()
                    chart_data.columns = ["Stage", "Amount"]
                    chart_data = chart_data.set_index("Stage")
                    st.bar_chart(chart_data, use_container_width=True)

            with col_table:
                with st.container(border=True):
                    display_df = pipeline_by_stage.copy()
                    display_df["total_amount"] = display_df["total_amount"].apply(format_currency)
                    display_df["weighted_amount"] = display_df["weighted_amount"].apply(format_currency)
                    display_df["avg_days_in_stage"] = display_df["avg_days_in_stage"].apply(
                        lambda x: f"{x:.0f}" if pd.notna(x) else "N/A"
                    )
                    display_df.columns = ["Stage", "Deals", "Total", "Weighted", "Avg Days"]
                    st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.divider()

        # Top Opportunities
        st.subheader("Top Open Opportunities")

        top_opps = query_df("""
            SELECT
                o.opportunity_name,
                o.amount,
                o.stage_name,
                o.probability,
                o.close_date,
                o.days_until_close,
                o.total_activities,
                ow.owner_name
            FROM public_marts.fct_opportunities o
            LEFT JOIN public_marts.dim_owners ow ON o.owner_id = ow.owner_id
            WHERE o.opportunity_status = 'Open'
            ORDER BY o.amount DESC NULLS LAST
            LIMIT 10
        """)

        if not top_opps.empty:
            with st.container(border=True):
                display_df = top_opps.copy()
                display_df["amount"] = display_df["amount"].apply(format_currency)
                display_df["probability"] = display_df["probability"].apply(
                    lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"
                )
                display_df["days_until_close"] = display_df["days_until_close"].apply(
                    lambda x: f"{x:.0f}" if pd.notna(x) else "N/A"
                )
                display_df.columns = [
                    "Opportunity", "Amount", "Stage", "Prob", "Close Date",
                    "Days Left", "Activities", "Owner"
                ]
                st.dataframe(display_df, use_container_width=True, hide_index=True)


# =========================================================================
# TAB 2: DEAL VELOCITY
# =========================================================================

with tab_velocity:
    st.subheader("Stage Velocity Analysis")
    st.caption("Where do deals get stuck? Time spent in each pipeline stage.")

    velocity_df = query_df("""
        SELECT * FROM public_reports.rpt_sales_velocity
        ORDER BY avg_days_in_stage DESC
    """)

    if not velocity_df.empty:
        # Bottleneck Alert
        bottlenecks = velocity_df[velocity_df["is_bottleneck"] == True]  # noqa: E712
        if not bottlenecks.empty:
            with st.container(border=True):
                st.error("**Bottleneck Stages Detected**")
                bcols = st.columns(len(bottlenecks))
                for i, (_, row) in enumerate(bottlenecks.iterrows()):
                    with bcols[i]:
                        st.metric(row["stage_name"], f"{row['avg_days_in_stage']:.1f} days")
                st.caption("These stages take significantly longer than average. Focus coaching here.")

        st.divider()

        # Chart and Table
        col_chart, col_table = st.columns([3, 2], gap="large")

        with col_chart:
            with st.container(border=True):
                st.write("**Average Days in Stage**")
                chart_data = velocity_df[["stage_name", "avg_days_in_stage"]].copy()
                chart_data.columns = ["Stage", "Avg Days"]
                st.bar_chart(chart_data.set_index("Stage"), use_container_width=True)

        with col_table:
            with st.container(border=True):
                st.write("**Detailed Metrics**")
                display_df = velocity_df[
                    ["stage_name", "transitions_count", "avg_days_in_stage", "median_days_in_stage", "is_bottleneck"]
                ].copy()
                display_df.columns = ["Stage", "Transitions", "Avg Days", "Median", "Bottleneck"]
                st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No velocity data available. Need opportunity history records.")


# =========================================================================
# TAB 3: REP PERFORMANCE
# =========================================================================

with tab_reps:
    st.subheader("Sales Rep Performance")

    rep_df = query_df("""
        SELECT
            r.*,
            o.email as owner_email
        FROM public_reports.rpt_win_rate_by_owner r
        LEFT JOIN public_marts.dim_owners o ON r.owner_id = o.owner_id
        ORDER BY won_revenue DESC NULLS LAST
    """)

    if not rep_df.empty:
        # Performance Tier Summary
        tier_counts = rep_df["performance_tier"].value_counts()

        tier1, tier2, tier3, tier4 = st.columns(4, gap="medium")

        with tier1:
            with st.container(border=True):
                count = tier_counts.get("High Performer", 0)
                st.metric("High Performers", count)
                st.caption("Win rate >= 40%")

        with tier2:
            with st.container(border=True):
                count = tier_counts.get("Average", 0)
                st.metric("Average", count)
                st.caption("Win rate 25-39%")

        with tier3:
            with st.container(border=True):
                count = tier_counts.get("Needs Coaching", 0)
                st.metric("Needs Coaching", count)
                st.caption("Win rate < 25%")

        with tier4:
            with st.container(border=True):
                count = tier_counts.get("No Closed Deals", 0)
                st.metric("No Closed Deals", count)
                st.caption("New or inactive")

        st.divider()

        # Leaderboard
        st.subheader("Leaderboard")

        with st.container(border=True):
            display_df = rep_df[
                ["owner_name", "total_opportunities", "won_opportunities", "win_rate_pct",
                 "won_revenue", "avg_won_deal_size", "avg_days_to_close", "performance_tier"]
            ].copy()

            display_df["won_revenue"] = display_df["won_revenue"].apply(format_currency)
            display_df["avg_won_deal_size"] = display_df["avg_won_deal_size"].apply(format_currency)
            display_df["avg_days_to_close"] = display_df["avg_days_to_close"].apply(
                lambda x: f"{x:.0f}" if pd.notna(x) else "N/A"
            )
            display_df["win_rate_pct"] = display_df["win_rate_pct"].apply(format_pct)

            display_df.columns = ["Rep", "Total", "Won", "Win Rate", "Revenue", "Avg Deal", "Avg Days", "Tier"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No rep performance data available.")


# =========================================================================
# TAB 4: ACTIVITY ATTRIBUTION
# =========================================================================

with tab_activity:
    st.subheader("Activity to Revenue Correlation")
    st.caption("Do more activities correlate with higher win rates?")

    coverage_df = query_df("""
        SELECT * FROM public_reports.rpt_activity_coverage
    """)

    if not coverage_df.empty:
        # Insight callout first
        high_activity = coverage_df[coverage_df["activity_bucket"] == "11+ High"]
        low_activity = coverage_df[coverage_df["activity_bucket"] == "0 - No activities"]

        if not high_activity.empty and not low_activity.empty:
            high_win = high_activity["win_rate_pct"].iloc[0] or 0
            low_win = low_activity["win_rate_pct"].iloc[0] or 0

            if high_win > low_win:
                diff = high_win - low_win
                with st.container(border=True):
                    st.success(
                        f"**Key Insight:** High-activity deals have a **{diff:.1f}pp higher win rate** "
                        f"({high_win:.1f}% vs {low_win:.1f}%). Activity drives outcomes."
                    )
            elif low_win > high_win:
                with st.container(border=True):
                    st.warning(
                        "**Unexpected Pattern:** Low-activity deals show higher win rate. "
                        "Check if activities are being logged properly."
                    )

        st.divider()

        # Charts side by side
        col_left, col_right = st.columns(2, gap="large")

        with col_left:
            with st.container(border=True):
                st.write("**Win Rate by Activity Level**")
                chart_data = coverage_df[["activity_bucket", "win_rate_pct"]].copy()
                chart_data.columns = ["Activity Level", "Win Rate %"]
                st.bar_chart(chart_data.set_index("Activity Level"), use_container_width=True)

        with col_right:
            with st.container(border=True):
                st.write("**Won Revenue by Activity Level**")
                chart_data = coverage_df[["activity_bucket", "won_revenue"]].copy()
                chart_data.columns = ["Activity Level", "Won Revenue"]
                st.bar_chart(chart_data.set_index("Activity Level"), use_container_width=True)

        st.divider()

        # Detailed table
        with st.expander("View Detailed Breakdown"):
            display_df = coverage_df[
                ["activity_bucket", "opportunity_count", "won_count", "win_rate_pct", "won_revenue"]
            ].copy()
            display_df["won_revenue"] = display_df["won_revenue"].apply(format_currency)
            display_df["win_rate_pct"] = display_df["win_rate_pct"].apply(format_pct)
            display_df.columns = ["Activity Level", "Opportunities", "Won", "Win Rate", "Won Revenue"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No activity coverage data available.")


# =========================================================================
# TAB 5: DATA HEALTH
# =========================================================================

with tab_health:
    st.subheader("Data Health & Sync Status")
    st.caption("Record counts, sync timestamps, and data quality metrics")

    # Raw table counts
    raw_counts = query_df("""
        SELECT
            'Opportunities' as entity,
            (SELECT count(*) FROM public_raw.salesforce_opportunities) as raw_count,
            (SELECT max(synced_at) FROM public_raw.salesforce_opportunities) as last_sync
        UNION ALL
        SELECT
            'Contacts' as entity,
            (SELECT count(*) FROM public_raw.salesforce_contacts) as raw_count,
            (SELECT max(synced_at) FROM public_raw.salesforce_contacts) as last_sync
        UNION ALL
        SELECT
            'Accounts' as entity,
            (SELECT count(*) FROM public_raw.salesforce_accounts) as raw_count,
            (SELECT max(synced_at) FROM public_raw.salesforce_accounts) as last_sync
        UNION ALL
        SELECT
            'Users' as entity,
            (SELECT count(*) FROM public_raw.salesforce_users) as raw_count,
            (SELECT max(synced_at) FROM public_raw.salesforce_users) as last_sync
        UNION ALL
        SELECT
            'Events' as entity,
            (SELECT count(*) FROM public_raw.salesforce_events) as raw_count,
            (SELECT max(synced_at) FROM public_raw.salesforce_events) as last_sync
        UNION ALL
        SELECT
            'Tasks' as entity,
            (SELECT count(*) FROM public_raw.salesforce_tasks) as raw_count,
            (SELECT max(synced_at) FROM public_raw.salesforce_tasks) as last_sync
        UNION ALL
        SELECT
            'Opportunity History' as entity,
            (SELECT count(*) FROM public_raw.salesforce_opportunity_history) as raw_count,
            (SELECT max(synced_at) FROM public_raw.salesforce_opportunity_history) as last_sync
    """)

    # Record counts in cards
    st.write("**Raw Record Counts**")
    if not raw_counts.empty:
        cols = st.columns(4, gap="medium")
        for i, (_, row) in enumerate(raw_counts.iterrows()):
            with cols[i % 4]:
                with st.container(border=True):
                    sync_time = row["last_sync"]
                    sync_str = sync_time.strftime("%m/%d %H:%M") if pd.notna(sync_time) else "Never"
                    st.metric(row["entity"], format_number(row["raw_count"]))
                    st.caption(f"Synced: {sync_str}")

    st.divider()

    # Data quality metrics
    st.write("**Data Quality Metrics**")

    quality_metrics = query_df("""
        SELECT
            -- Contacts with email (required for attribution)
            (SELECT count(*) FROM public_staging.stg_salesforce__contacts WHERE email IS NOT NULL) as contacts_with_email,
            (SELECT count(*) FROM public_staging.stg_salesforce__contacts) as total_contacts,

            -- Activities linked to opportunities
            (SELECT count(*) FROM public_staging.stg_salesforce__events WHERE what_id IS NOT NULL) as events_linked,
            (SELECT count(*) FROM public_staging.stg_salesforce__events) as total_events,
            (SELECT count(*) FROM public_staging.stg_salesforce__tasks WHERE what_id IS NOT NULL) as tasks_linked,
            (SELECT count(*) FROM public_staging.stg_salesforce__tasks) as total_tasks,

            -- Active users
            (SELECT count(*) FROM public_staging.stg_salesforce__users WHERE is_active = true) as active_users,
            (SELECT count(*) FROM public_staging.stg_salesforce__users) as total_users
    """)

    if not quality_metrics.empty:
        q = quality_metrics.iloc[0]

        contact_coverage = (q["contacts_with_email"] / q["total_contacts"] * 100) if q["total_contacts"] > 0 else 0
        event_link_rate = (q["events_linked"] / q["total_events"] * 100) if q["total_events"] > 0 else 0
        task_link_rate = (q["tasks_linked"] / q["total_tasks"] * 100) if q["total_tasks"] > 0 else 0

        qcol1, qcol2, qcol3, qcol4 = st.columns(4, gap="medium")

        with qcol1:
            with st.container(border=True):
                st.metric("Contacts with Email", format_pct(contact_coverage))
                if contact_coverage < 80:
                    st.warning("Low coverage limits attribution")
                else:
                    st.success("Good coverage")

        with qcol2:
            with st.container(border=True):
                st.metric("Events Linked to Opps", format_pct(event_link_rate))
                st.caption(f"{int(q['events_linked'])} / {int(q['total_events'])}")

        with qcol3:
            with st.container(border=True):
                st.metric("Tasks Linked to Opps", format_pct(task_link_rate))
                st.caption(f"{int(q['tasks_linked'])} / {int(q['total_tasks'])}")

        with qcol4:
            with st.container(border=True):
                st.metric("Active Users", f"{int(q['active_users'])} / {int(q['total_users'])}")
                st.caption("IsActive = true")

    st.divider()

    # Contact coverage detail
    with st.expander("Contact Coverage by Account"):
        contacts_by_account = query_df("""
            SELECT
                account_name,
                count(*) as contact_count,
                count(*) filter (where email is not null) as contacts_with_email
            FROM public_marts.dim_contacts
            WHERE account_name IS NOT NULL
            GROUP BY account_name
            ORDER BY contact_count DESC
            LIMIT 15
        """)

        if not contacts_by_account.empty:
            display_df = contacts_by_account.copy()
            display_df["email_rate"] = (
                display_df["contacts_with_email"] / display_df["contact_count"] * 100
            ).round(1)
            display_df["email_rate"] = display_df["email_rate"].apply(lambda x: f"{x:.1f}%")
            display_df.columns = ["Account", "Total Contacts", "With Email", "Email Rate"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)


# =========================================================================
# FOOTER
# =========================================================================

st.divider()
st.caption(
    "**Data Pipeline:** Nango → Dagster (`public_raw`) → dbt Staging (`public_staging`) → "
    "dbt Marts (`public_marts`) → Reports (`public_reports`)"
)
