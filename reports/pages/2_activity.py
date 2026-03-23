"""Sales Activity Reporting Page.

Shows events and tasks metrics with status breakdowns.
"""

from datetime import datetime, timedelta

import plotly.express as px
import streamlit as st

from reports.db import query_to_df

st.set_page_config(
    page_title="Activity - Data Hub Reports",
    page_icon=":material/task:",
    layout="wide",
)

st.title("Sales Activity")


@st.cache_data(ttl=60)
def get_events_data():
    """Fetch events data."""
    sql = """
        SELECT
            data->>'Subject' as subject,
            data->>'StartDateTime' as start_time,
            synced_at
        FROM salesforce_events
        ORDER BY data->>'StartDateTime' DESC
    """
    return query_to_df(sql)


@st.cache_data(ttl=60)
def get_tasks_data():
    """Fetch tasks data."""
    sql = """
        SELECT
            data->>'Subject' as subject,
            data->>'Status' as status,
            data->>'Priority' as priority,
            data->>'ActivityDate' as activity_date,
            synced_at
        FROM salesforce_tasks
        ORDER BY data->>'ActivityDate' DESC
    """
    return query_to_df(sql)


try:
    events_df = get_events_data()
    tasks_df = get_tasks_data()

    # KPI Row
    col1, col2, col3, col4 = st.columns(4)

    # Total Events
    total_events = len(events_df)

    # Total Tasks
    total_tasks = len(tasks_df)

    # Completed Tasks
    completed_tasks = (
        len(tasks_df[tasks_df["status"] == "Completed"]) if not tasks_df.empty else 0
    )

    # Events This Week
    if not events_df.empty:
        today = datetime.now()
        start_of_week = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        end_of_week = (today + timedelta(days=6 - today.weekday())).strftime("%Y-%m-%d")

        # Filter events that start this week (handle datetime string comparison)
        events_this_week = events_df[
            (events_df["start_time"].str[:10] >= start_of_week)
            & (events_df["start_time"].str[:10] <= end_of_week)
        ]
        events_this_week_count = len(events_this_week)
    else:
        events_this_week_count = 0

    with col1:
        st.metric(
            label="Total Events",
            value=f"{total_events:,}",
        )

    with col2:
        st.metric(
            label="Total Tasks",
            value=f"{total_tasks:,}",
        )

    with col3:
        st.metric(
            label="Completed Tasks",
            value=f"{completed_tasks:,}",
        )

    with col4:
        st.metric(
            label="Events This Week",
            value=f"{events_this_week_count:,}",
        )

    st.divider()

    # Tabs for Events and Tasks
    events_tab, tasks_tab = st.tabs(["Events", "Tasks"])

    with events_tab:
        st.subheader("Recent Events")

        if events_df.empty:
            st.info("No events data available. Run the Dagster pipeline to sync data.")
        else:
            # Show recent events table (first 20 since already ordered by start_time desc)
            recent_events = events_df.head(20)[
                ["subject", "start_time", "synced_at"]
            ].copy()

            st.dataframe(
                recent_events,
                column_config={
                    "subject": st.column_config.TextColumn("Subject"),
                    "start_time": st.column_config.TextColumn("Start Time"),
                    "synced_at": st.column_config.DatetimeColumn(
                        "Synced At",
                        format="D MMM YYYY, HH:mm",
                    ),
                },
                hide_index=True,
                use_container_width=True,
            )

            st.caption(f"Showing most recent 20 of {total_events:,} total events")

    with tasks_tab:
        if tasks_df.empty:
            st.info("No tasks data available. Run the Dagster pipeline to sync data.")
        else:
            # Charts row
            col_left, col_right = st.columns(2)

            with col_left:
                st.subheader("Tasks by Status")

                status_counts = tasks_df["status"].value_counts().reset_index()
                status_counts.columns = ["status", "count"]

                if not status_counts.empty:
                    fig = px.pie(
                        status_counts,
                        values="count",
                        names="status",
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set2,
                    )
                    fig.update_layout(
                        height=300,
                        margin=dict(l=0, r=0, t=10, b=0),
                    )
                    fig.update_traces(
                        textposition="inside",
                        textinfo="percent+label",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No status data available.")

            with col_right:
                st.subheader("Tasks by Priority")

                priority_counts = tasks_df["priority"].value_counts().reset_index()
                priority_counts.columns = ["priority", "count"]

                if not priority_counts.empty:
                    # Define color mapping for priorities
                    color_map = {
                        "High": "#ef4444",
                        "Normal": "#3b82f6",
                        "Low": "#22c55e",
                    }

                    fig = px.bar(
                        priority_counts,
                        x="priority",
                        y="count",
                        color="priority",
                        color_discrete_map=color_map,
                        labels={"count": "Count", "priority": "Priority"},
                    )
                    fig.update_layout(
                        showlegend=False,
                        height=300,
                        margin=dict(l=0, r=0, t=10, b=0),
                    )
                    fig.update_traces(
                        texttemplate="%{y}",
                        textposition="outside",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No priority data available.")

            st.divider()

            st.subheader("Recent Tasks")

            # Show recent tasks table (first 20 since already ordered)
            recent_tasks = tasks_df.head(20)[
                ["subject", "status", "priority", "activity_date"]
            ].copy()

            st.dataframe(
                recent_tasks,
                column_config={
                    "subject": st.column_config.TextColumn("Subject"),
                    "status": st.column_config.TextColumn("Status"),
                    "priority": st.column_config.TextColumn("Priority"),
                    "activity_date": st.column_config.TextColumn("Activity Date"),
                },
                hide_index=True,
                use_container_width=True,
            )

            st.caption(f"Showing most recent 20 of {total_tasks:,} total tasks")

except Exception as e:
    st.error(f"Error loading activity data: {e}")
    st.info(
        "Make sure the database is accessible and the salesforce_events/salesforce_tasks tables exist."
    )
