"""Salesforce Data Hub Reports - Main Streamlit Application.

Entry point for the Streamlit dashboard. Run with:
    source .env && streamlit run reports/app.py
"""

import streamlit as st

from reports.db import query_to_df

# Page configuration
st.set_page_config(
    page_title="Salesforce Data Hub Reports",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar navigation
st.sidebar.title("Navigation")
st.sidebar.page_link("app.py", label="Home", icon=":material/home:")
st.sidebar.page_link("pages/1_opportunities.py", label="Opportunities", icon=":material/monetization_on:")
st.sidebar.page_link("pages/2_activity.py", label="Activity", icon=":material/task:")

# Main content
st.title("Salesforce Data Hub Reports")
st.markdown(
    """
    Welcome to the Salesforce Data Hub reporting dashboard. This dashboard provides
    visibility into the Salesforce data synced by the Dagster pipeline.

    **Available Reports:**
    - **Opportunities**: Pipeline metrics, stage breakdown, and closing forecast
    - **Activity**: Events and tasks tracking with status breakdowns
    """
)

st.divider()


# Quick stats section
@st.cache_data(ttl=60)
def get_table_counts() -> dict[str, int]:
    """Get record counts for each Salesforce table."""
    tables = [
        "salesforce_opportunities",
        "salesforce_opportunity_history",
        "salesforce_events",
        "salesforce_tasks",
    ]
    counts: dict[str, int] = {}

    for table in tables:
        try:
            df = query_to_df(f"SELECT COUNT(*) as count FROM {table}")
            counts[table] = int(df["count"].iloc[0])
        except Exception:
            counts[table] = 0

    return counts


@st.cache_data(ttl=60)
def get_last_sync_time() -> str | None:
    """Get the most recent sync time across all tables."""
    tables = [
        "salesforce_opportunities",
        "salesforce_opportunity_history",
        "salesforce_events",
        "salesforce_tasks",
    ]

    latest_sync = None
    for table in tables:
        try:
            df = query_to_df(f"SELECT MAX(synced_at) as last_sync FROM {table}")
            if df["last_sync"].iloc[0] is not None:
                sync_time = df["last_sync"].iloc[0]
                if latest_sync is None or sync_time > latest_sync:
                    latest_sync = sync_time
        except Exception:
            continue

    if latest_sync is not None:
        return str(latest_sync)
    return None


st.subheader("Data Overview")

# Display record counts
try:
    counts = get_table_counts()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Opportunities",
            value=f"{counts.get('salesforce_opportunities', 0):,}",
        )

    with col2:
        st.metric(
            label="Opportunity History",
            value=f"{counts.get('salesforce_opportunity_history', 0):,}",
        )

    with col3:
        st.metric(
            label="Events",
            value=f"{counts.get('salesforce_events', 0):,}",
        )

    with col4:
        st.metric(
            label="Tasks",
            value=f"{counts.get('salesforce_tasks', 0):,}",
        )

    # Last sync time
    st.divider()
    last_sync = get_last_sync_time()
    if last_sync:
        st.info(f"**Last data sync:** {last_sync}")
    else:
        st.warning("No data has been synced yet. Run the Dagster pipeline to load data.")

except Exception as e:
    st.error(f"Error connecting to database: {e}")
    st.info(
        "Make sure the DATABASE_URL environment variable is set and the database is accessible."
    )
