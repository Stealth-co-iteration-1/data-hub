"""Streamlit dashboard for data-hub metrics and Salesforce insights.

Displays data from the Dagster-synced Salesforce tables:
- salesforce_opportunities
- salesforce_opportunity_history
- salesforce_events
- salesforce_tasks
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from sqlalchemy import Engine, create_engine

# Page config
st.set_page_config(
    page_title="Data Hub Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("Data Hub Dashboard")


@st.cache_resource
def get_db_connection() -> Engine:
    """Create database connection from environment variables."""
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://datahub:datahub@localhost:5432/datahub",
    )
    return create_engine(db_url)


# =========================================================================
# DATA LOADING FUNCTIONS
# =========================================================================


def load_table_counts() -> dict[str, int]:
    """Load record counts for each Salesforce table."""
    engine = get_db_connection()
    tables = [
        "salesforce_opportunities",
        "salesforce_opportunity_history",
        "salesforce_events",
        "salesforce_tasks",
    ]
    counts: dict[str, int] = {}
    for table in tables:
        try:
            result = pd.read_sql(f"SELECT COUNT(*) as count FROM {table}", engine)
            counts[table] = int(result["count"].iloc[0])
        except Exception:
            counts[table] = 0
    return counts


def load_last_sync() -> str | None:
    """Get the most recent sync time across all tables."""
    engine = get_db_connection()
    tables = [
        "salesforce_opportunities",
        "salesforce_opportunity_history",
        "salesforce_events",
        "salesforce_tasks",
    ]
    latest = None
    for table in tables:
        try:
            result = pd.read_sql(f"SELECT MAX(synced_at) as last_sync FROM {table}", engine)
            sync_time = result["last_sync"].iloc[0]
            if sync_time is not None and (latest is None or sync_time > latest):
                latest = sync_time
        except Exception:
            continue
    return str(latest) if latest else None


def load_opportunities() -> pd.DataFrame:
    """Load Opportunity records from salesforce_opportunities table."""
    engine = get_db_connection()
    query = """
        SELECT
            salesforce_id,
            connection_id,
            data->>'Name' as name,
            (data->>'Amount')::numeric as amount,
            data->>'StageName' as stage_name,
            data->>'CloseDate' as close_date,
            (data->>'IsClosed')::boolean as is_closed,
            (data->>'IsWon')::boolean as is_won,
            (data->>'Probability')::numeric as probability,
            data->>'ForecastCategoryName' as forecast_category,
            data->>'Type' as type,
            data->'Account'->>'Name' as account_name,
            data->'Account'->>'Industry' as account_industry,
            data->'Owner'->>'Name' as owner_name,
            synced_at
        FROM salesforce_opportunities
    """
    return pd.read_sql(query, engine)


def load_events() -> pd.DataFrame:
    """Load Event records from salesforce_events table."""
    engine = get_db_connection()
    query = """
        SELECT
            salesforce_id,
            connection_id,
            data->>'Subject' as subject,
            data->>'StartDateTime' as start_datetime,
            data->>'EndDateTime' as end_datetime,
            synced_at
        FROM salesforce_events
        ORDER BY data->>'StartDateTime' DESC
    """
    return pd.read_sql(query, engine)


def load_tasks() -> pd.DataFrame:
    """Load Task records from salesforce_tasks table."""
    engine = get_db_connection()
    query = """
        SELECT
            salesforce_id,
            connection_id,
            data->>'Subject' as subject,
            data->>'Status' as status,
            data->>'Priority' as priority,
            data->>'ActivityDate' as activity_date,
            synced_at
        FROM salesforce_tasks
        ORDER BY data->>'ActivityDate' DESC
    """
    return pd.read_sql(query, engine)


# =========================================================================
# MAIN DASHBOARD
# =========================================================================

try:
    # Data Overview Section
    st.header("📊 Data Overview")

    counts = load_table_counts()
    total_records = sum(counts.values())

    if total_records == 0:
        st.warning("No data found. Run the Dagster pipeline to sync Salesforce data.")
        st.stop()

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Opportunities", f"{counts.get('salesforce_opportunities', 0):,}")

    with col2:
        st.metric("Opportunity History", f"{counts.get('salesforce_opportunity_history', 0):,}")

    with col3:
        st.metric("Events", f"{counts.get('salesforce_events', 0):,}")

    with col4:
        st.metric("Tasks", f"{counts.get('salesforce_tasks', 0):,}")

    # Last sync info
    last_sync = load_last_sync()
    if last_sync:
        st.info(f"**Last data sync:** {last_sync}")

    st.divider()

    # =========================================================================
    # OPPORTUNITY INSIGHTS SECTION
    # =========================================================================
    st.header("🎯 Opportunity Insights")

    opps_df = load_opportunities()

    if opps_df.empty:
        st.info("No Opportunity records found. Sync Salesforce Opportunities to see insights.")
    else:
        # Handle NaN values in Amount
        opps_df["amount"] = pd.to_numeric(opps_df["amount"], errors="coerce").fillna(0)

        # Key metrics
        opp_col1, opp_col2, opp_col3, opp_col4 = st.columns(4)

        open_opps = opps_df[opps_df["is_closed"] == False]  # noqa: E712
        won_opps = opps_df[opps_df["is_won"] == True]  # noqa: E712
        closed_opps = opps_df[opps_df["is_closed"] == True]  # noqa: E712

        total_pipeline = open_opps["amount"].sum() if not open_opps.empty else 0
        closed_won = won_opps["amount"].sum() if not won_opps.empty else 0
        avg_deal_size = opps_df["amount"].mean() if len(opps_df) > 0 else 0
        win_rate = (len(won_opps) / len(closed_opps) * 100) if len(closed_opps) > 0 else 0

        with opp_col1:
            st.metric("Total Pipeline", f"${total_pipeline:,.0f}")

        with opp_col2:
            st.metric("Closed Won", f"${closed_won:,.0f}")

        with opp_col3:
            st.metric("Avg Deal Size", f"${avg_deal_size:,.0f}")

        with opp_col4:
            st.metric("Win Rate", f"{win_rate:.1f}%")

        st.divider()

        # Two columns for charts
        opp_left, opp_right = st.columns(2)

        with opp_left:
            st.subheader("Pipeline by Stage")
            stage_pipeline = (
                open_opps.groupby("stage_name")["amount"]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
            )
            if not stage_pipeline.empty:
                st.bar_chart(stage_pipeline.set_index("stage_name"))

        with opp_right:
            st.subheader("Deals by Forecast Category")
            forecast_counts = opps_df["forecast_category"].value_counts().reset_index()
            forecast_counts.columns = ["forecast_category", "count"]
            if not forecast_counts.empty:
                st.bar_chart(forecast_counts.set_index("forecast_category"))

        st.divider()

        # Industry breakdown
        opp_left2, opp_right2 = st.columns(2)

        with opp_left2:
            st.subheader("Pipeline by Industry")
            industry_data = open_opps[open_opps["account_industry"].notna()]
            if not industry_data.empty:
                industry_pipeline = (
                    industry_data.groupby("account_industry")["amount"]
                    .sum()
                    .sort_values(ascending=False)
                    .reset_index()
                )
                st.bar_chart(industry_pipeline.set_index("account_industry"))
            else:
                st.info("No industry data available.")

        with opp_right2:
            st.subheader("Deals by Type")
            type_data = opps_df[opps_df["type"].notna()]
            if not type_data.empty:
                type_counts = type_data["type"].value_counts().reset_index()
                type_counts.columns = ["type", "count"]
                st.bar_chart(type_counts.set_index("type"))
            else:
                st.info("No type data available.")

        st.divider()

        # Top opportunities table
        st.subheader("Top 10 Open Opportunities")
        if not open_opps.empty:
            top_opps = (
                open_opps.nlargest(10, "amount")[
                    ["name", "amount", "stage_name", "probability", "close_date", "account_name", "owner_name"]
                ].copy()
            )
            top_opps["amount"] = top_opps["amount"].apply(lambda x: f"${x:,.0f}")
            top_opps["probability"] = top_opps["probability"].apply(
                lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"
            )
            st.dataframe(top_opps, use_container_width=True, hide_index=True)
        else:
            st.info("No open opportunities found.")

    # =========================================================================
    # ACTIVITY SECTION
    # =========================================================================
    st.divider()
    st.header("📅 Sales Activity")

    activity_tab1, activity_tab2 = st.tabs(["Events", "Tasks"])

    with activity_tab1:
        events_df = load_events()
        if events_df.empty:
            st.info("No Event records found.")
        else:
            st.metric("Total Events", f"{len(events_df):,}")
            st.subheader("Recent Events")
            st.dataframe(
                events_df.head(20)[["subject", "start_datetime", "synced_at"]],
                use_container_width=True,
                hide_index=True,
            )

    with activity_tab2:
        tasks_df = load_tasks()
        if tasks_df.empty:
            st.info("No Task records found.")
        else:
            task_col1, task_col2 = st.columns(2)

            with task_col1:
                st.metric("Total Tasks", f"{len(tasks_df):,}")

            with task_col2:
                completed = len(tasks_df[tasks_df["status"] == "Completed"])
                st.metric("Completed Tasks", f"{completed:,}")

            st.divider()

            # Tasks by status chart
            task_left, task_right = st.columns(2)

            with task_left:
                st.subheader("Tasks by Status")
                status_counts = tasks_df["status"].value_counts().reset_index()
                status_counts.columns = ["status", "count"]
                if not status_counts.empty:
                    st.bar_chart(status_counts.set_index("status"))

            with task_right:
                st.subheader("Tasks by Priority")
                priority_counts = tasks_df["priority"].value_counts().reset_index()
                priority_counts.columns = ["priority", "count"]
                if not priority_counts.empty:
                    st.bar_chart(priority_counts.set_index("priority"))

            st.divider()
            st.subheader("Recent Tasks")
            st.dataframe(
                tasks_df.head(20)[["subject", "status", "priority", "activity_date"]],
                use_container_width=True,
                hide_index=True,
            )

except Exception as e:
    st.error(f"Error connecting to database: {e}")
    st.info(
        "Make sure PostgreSQL is running and DATABASE_URL is set correctly.\n\n"
        "Expected format: postgresql://user:password@host:port/database"
    )