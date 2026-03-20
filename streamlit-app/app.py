"""Streamlit dashboard for data-hub metrics and Salesforce insights."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from sqlalchemy import Engine, create_engine

# Page config
st.set_page_config(  # type: ignore[no-untyped-call]
    page_title="Data Hub Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("Data Hub Dashboard")  # type: ignore[no-untyped-call]


@st.cache_resource  # type: ignore[misc]
def get_db_connection() -> Engine:
    """Create database connection from environment variables."""
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://datahub:datahub@localhost:5432/datahub",
    )
    return create_engine(db_url)


def load_audit_data() -> pd.DataFrame:
    """Load audit_log data from PostgreSQL."""
    engine = get_db_connection()
    query = """
        SELECT
            id,
            record_id,
            model_name,
            connection_id,
            status,
            occurred_at
        FROM audit_log
        ORDER BY occurred_at DESC
    """
    return pd.read_sql(query, engine)  # type: ignore[return-value]


# Load data
try:
    df = load_audit_data()

    if df.empty:
        st.warning("No audit log entries found. Start syncing data to see metrics.")  # type: ignore[no-untyped-call]
        st.stop()  # type: ignore[no-untyped-call]

    # Sidebar filters
    st.sidebar.header("Filters")  # type: ignore[no-untyped-call]

    models: list[str] = ["All"] + sorted(df["model_name"].unique().tolist())
    selected_model = st.sidebar.selectbox("Model", models)  # type: ignore[no-untyped-call]

    connections: list[str] = ["All"] + sorted(df["connection_id"].unique().tolist())
    selected_connection = st.sidebar.selectbox("Connection ID", connections)  # type: ignore[no-untyped-call]

    statuses: list[str] = ["All"] + sorted(df["status"].unique().tolist())
    selected_status = st.sidebar.selectbox("Status", statuses)  # type: ignore[no-untyped-call]

    # Apply filters
    filtered_df = df.copy()
    if selected_model != "All":
        filtered_df = filtered_df[filtered_df["model_name"] == selected_model]
    if selected_connection != "All":
        filtered_df = filtered_df[filtered_df["connection_id"] == selected_connection]
    if selected_status != "All":
        filtered_df = filtered_df[filtered_df["status"] == selected_status]

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)  # type: ignore[no-untyped-call]

    with col1:
        st.metric("Total Records", len(filtered_df))  # type: ignore[no-untyped-call]

    with col2:
        added_count = len(filtered_df[filtered_df["status"] == "added"])
        st.metric("Added", added_count)  # type: ignore[no-untyped-call]

    with col3:
        duplicate_count = len(filtered_df[filtered_df["status"] == "duplicate"])
        st.metric("Duplicates", duplicate_count)  # type: ignore[no-untyped-call]

    with col4:
        if len(filtered_df) > 0:
            dup_rate = (duplicate_count / len(filtered_df)) * 100
            st.metric("Duplicate Rate", f"{dup_rate:.1f}%")  # type: ignore[no-untyped-call]
        else:
            st.metric("Duplicate Rate", "N/A")  # type: ignore[no-untyped-call]

    st.divider()  # type: ignore[no-untyped-call]

    # Two columns for charts
    left_col, right_col = st.columns(2)  # type: ignore[no-untyped-call]

    with left_col:
        st.subheader("Records by Model")  # type: ignore[no-untyped-call]
        model_counts = filtered_df.groupby("model_name").size().reset_index(name="count")
        st.bar_chart(model_counts.set_index("model_name"))  # type: ignore[no-untyped-call]

    with right_col:
        st.subheader("Records by Status")  # type: ignore[no-untyped-call]
        status_counts = filtered_df.groupby("status").size().reset_index(name="count")
        st.bar_chart(status_counts.set_index("status"))  # type: ignore[no-untyped-call]

    st.divider()  # type: ignore[no-untyped-call]

    # Records by connection
    st.subheader("Records by Connection ID")  # type: ignore[no-untyped-call]
    connection_counts = filtered_df.groupby("connection_id").size().reset_index(name="count")
    connection_counts = connection_counts.sort_values("count", ascending=False)
    st.bar_chart(connection_counts.set_index("connection_id"))  # type: ignore[no-untyped-call]

    st.divider()  # type: ignore[no-untyped-call]

    # Model x Status breakdown
    st.subheader("Model x Status Breakdown")  # type: ignore[no-untyped-call]
    pivot = filtered_df.pivot_table(
        index="model_name",
        columns="status",
        values="id",
        aggfunc="count",
        fill_value=0,
    )
    st.dataframe(pivot, use_container_width=True)  # type: ignore[no-untyped-call]

    st.divider()  # type: ignore[no-untyped-call]

    # Recent entries table
    st.subheader("Recent Audit Log Entries")  # type: ignore[no-untyped-call]
    st.dataframe(  # type: ignore[no-untyped-call]
        filtered_df.head(100),
        use_container_width=True,
        hide_index=True,
    )

    # =========================================================================
    # OPPORTUNITY INSIGHTS SECTION
    # =========================================================================
    st.divider()  # type: ignore[no-untyped-call]
    st.header("🎯 Opportunity Insights")  # type: ignore[no-untyped-call]

    # Load Opportunity data from data_records
    def load_opportunities() -> pd.DataFrame:
        """Load Opportunity records from data_records table."""
        engine = get_db_connection()
        query = """
            SELECT data
            FROM data_records
            WHERE model_name = 'Opportunity'
        """
        result = pd.read_sql(query, engine)
        if result.empty:
            return pd.DataFrame()

        # Parse JSON data column into flat dataframe
        records = [row["data"] for _, row in result.iterrows()]
        return pd.json_normalize(records)  # type: ignore[return-value]

    opps_df = load_opportunities()

    if opps_df.empty:
        st.info("No Opportunity records found. Sync Salesforce Opportunities to see insights.")  # type: ignore[no-untyped-call]
    else:
        # Key metrics
        opp_col1, opp_col2, opp_col3, opp_col4 = st.columns(4)  # type: ignore[no-untyped-call]

        # Handle NaN values in Amount
        opps_df["Amount"] = pd.to_numeric(opps_df["Amount"], errors="coerce").fillna(0)

        total_pipeline = opps_df[~opps_df["IsClosed"]]["Amount"].sum()
        closed_won = opps_df[opps_df["IsWon"] == True]["Amount"].sum()  # noqa: E712
        avg_deal_size = opps_df["Amount"].mean() if len(opps_df) > 0 else 0
        closed_deals = opps_df[opps_df["IsClosed"] == True]  # noqa: E712
        won_deals = opps_df[opps_df["IsWon"] == True]  # noqa: E712
        win_rate = (len(won_deals) / len(closed_deals) * 100) if len(closed_deals) > 0 else 0

        with opp_col1:
            st.metric("Total Pipeline", f"${total_pipeline:,.0f}")  # type: ignore[no-untyped-call]

        with opp_col2:
            st.metric("Closed Won", f"${closed_won:,.0f}")  # type: ignore[no-untyped-call]

        with opp_col3:
            st.metric("Avg Deal Size", f"${avg_deal_size:,.0f}")  # type: ignore[no-untyped-call]

        with opp_col4:
            st.metric("Win Rate", f"{win_rate:.1f}%")  # type: ignore[no-untyped-call]

        st.divider()  # type: ignore[no-untyped-call]

        # Two columns for charts
        opp_left, opp_right = st.columns(2)  # type: ignore[no-untyped-call]

        with opp_left:
            st.subheader("Pipeline by Stage")  # type: ignore[no-untyped-call]
            stage_pipeline = (
                opps_df[~opps_df["IsClosed"]]
                .groupby("StageName")["Amount"]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
            )
            if not stage_pipeline.empty:
                st.bar_chart(stage_pipeline.set_index("StageName"))  # type: ignore[no-untyped-call]

        with opp_right:
            st.subheader("Deals by Forecast Category")  # type: ignore[no-untyped-call]
            forecast_counts = opps_df.groupby("ForecastCategoryName").size().reset_index(name="count")
            if not forecast_counts.empty:
                st.bar_chart(forecast_counts.set_index("ForecastCategoryName"))  # type: ignore[no-untyped-call]

        st.divider()  # type: ignore[no-untyped-call]

        # Industry breakdown
        opp_left2, opp_right2 = st.columns(2)  # type: ignore[no-untyped-call]

        with opp_left2:
            st.subheader("Pipeline by Industry")  # type: ignore[no-untyped-call]
            if "Account.Industry" in opps_df.columns:
                industry_pipeline = (
                    opps_df[~opps_df["IsClosed"]]
                    .groupby("Account.Industry")["Amount"]
                    .sum()
                    .sort_values(ascending=False)
                    .reset_index()
                )
                if not industry_pipeline.empty:
                    st.bar_chart(industry_pipeline.set_index("Account.Industry"))  # type: ignore[no-untyped-call]

        with opp_right2:
            st.subheader("Deals by Type")  # type: ignore[no-untyped-call]
            type_counts = opps_df.groupby("Type").size().reset_index(name="count")
            if not type_counts.empty:
                st.bar_chart(type_counts.set_index("Type"))  # type: ignore[no-untyped-call]

        st.divider()  # type: ignore[no-untyped-call]

        # Top opportunities table
        st.subheader("Top 10 Open Opportunities")  # type: ignore[no-untyped-call]
        top_opps = (
            opps_df[~opps_df["IsClosed"]]
            .nlargest(10, "Amount")[["Name", "Amount", "StageName", "Probability", "CloseDate", "Account.Name", "Owner.Name"]]
            .copy()
        )
        top_opps["Amount"] = top_opps["Amount"].apply(lambda x: f"${x:,.0f}")
        top_opps["Probability"] = top_opps["Probability"].apply(lambda x: f"{x}%")
        st.dataframe(top_opps, use_container_width=True, hide_index=True)  # type: ignore[no-untyped-call]

except Exception as e:
    st.error(f"Error connecting to database: {e}")  # type: ignore[no-untyped-call]
    st.info(  # type: ignore[no-untyped-call]
        "Make sure PostgreSQL is running and DATABASE_URL is set correctly.\n\n"
        "Expected format: postgresql://user:password@host:port/database"
    )
