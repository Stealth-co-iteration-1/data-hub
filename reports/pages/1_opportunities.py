"""Opportunity Pipeline Reporting Page.

Shows pipeline metrics, stage breakdown, and opportunities closing this month.
"""

from datetime import datetime

import plotly.express as px
import streamlit as st

from reports.db import query_to_df

st.set_page_config(
    page_title="Opportunities - Data Hub Reports",
    page_icon=":material/monetization_on:",
    layout="wide",
)

st.title("Opportunity Pipeline")


@st.cache_data(ttl=60)
def get_opportunity_data() -> dict:
    """Fetch all opportunity metrics in a single query."""
    sql = """
        SELECT
            data->>'Name' as name,
            (data->>'Amount')::numeric as amount,
            data->>'StageName' as stage,
            data->>'CloseDate' as close_date,
            (data->>'IsClosed')::boolean as is_closed,
            (data->>'IsWon')::boolean as is_won
        FROM salesforce_opportunities
    """
    return query_to_df(sql)


try:
    df = get_opportunity_data()

    if df.empty:
        st.info("No opportunity data available. Run the Dagster pipeline to sync data.")
    else:
        # KPI Row
        col1, col2, col3, col4 = st.columns(4)

        # Total Pipeline Value (open opportunities)
        open_opps = df[df["is_closed"] == False]  # noqa: E712
        total_pipeline = open_opps["amount"].sum() if not open_opps.empty else 0

        # Closed Won Value
        won_opps = df[df["is_won"] == True]  # noqa: E712
        closed_won_value = won_opps["amount"].sum() if not won_opps.empty else 0

        # Win Rate
        closed_opps = df[df["is_closed"] == True]  # noqa: E712
        if not closed_opps.empty:
            win_count = len(won_opps)
            closed_count = len(closed_opps)
            win_rate = (win_count / closed_count * 100) if closed_count > 0 else 0
        else:
            win_rate = 0

        # Open Opportunities count
        open_count = len(open_opps)

        with col1:
            st.metric(
                label="Total Pipeline Value",
                value=f"${total_pipeline:,.0f}",
            )

        with col2:
            st.metric(
                label="Closed Won Value",
                value=f"${closed_won_value:,.0f}",
            )

        with col3:
            st.metric(
                label="Win Rate",
                value=f"{win_rate:.1f}%",
            )

        with col4:
            st.metric(
                label="Open Opportunities",
                value=f"{open_count:,}",
            )

        st.divider()

        # Charts Section
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Pipeline by Stage")

            # Group by stage and sum amounts
            stage_data = (
                df.groupby("stage", as_index=False)["amount"]
                .sum()
                .sort_values("amount", ascending=True)
            )

            if not stage_data.empty:
                fig = px.bar(
                    stage_data,
                    x="amount",
                    y="stage",
                    orientation="h",
                    labels={"amount": "Total Value ($)", "stage": "Stage"},
                    color="amount",
                    color_continuous_scale="Blues",
                )
                fig.update_layout(
                    showlegend=False,
                    height=400,
                    margin=dict(l=0, r=0, t=10, b=0),
                )
                fig.update_traces(
                    texttemplate="$%{x:,.0f}",
                    textposition="outside",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No stage data available.")

        with col_right:
            st.subheader("Closing This Month")

            # Get current month boundaries
            today = datetime.now()
            first_of_month = today.replace(day=1).strftime("%Y-%m-%d")
            if today.month == 12:
                first_of_next_month = today.replace(
                    year=today.year + 1, month=1, day=1
                ).strftime("%Y-%m-%d")
            else:
                first_of_next_month = today.replace(
                    month=today.month + 1, day=1
                ).strftime("%Y-%m-%d")

            # Filter for open opportunities closing this month
            closing_this_month = df[
                (df["is_closed"] == False)  # noqa: E712
                & (df["close_date"] >= first_of_month)
                & (df["close_date"] < first_of_next_month)
            ][["name", "amount", "stage", "close_date"]].copy()

            if not closing_this_month.empty:
                closing_this_month = closing_this_month.sort_values(
                    "close_date", ascending=True
                )

                st.dataframe(
                    closing_this_month,
                    column_config={
                        "name": st.column_config.TextColumn("Opportunity Name"),
                        "amount": st.column_config.NumberColumn(
                            "Amount",
                            format="$%.0f",
                        ),
                        "stage": st.column_config.TextColumn("Stage"),
                        "close_date": st.column_config.TextColumn("Close Date"),
                    },
                    hide_index=True,
                    use_container_width=True,
                    height=350,
                )

                total_closing = closing_this_month["amount"].sum()
                st.caption(f"**Total closing this month:** ${total_closing:,.0f}")
            else:
                st.info("No opportunities scheduled to close this month.")

except Exception as e:
    st.error(f"Error loading opportunity data: {e}")
    st.info(
        "Make sure the database is accessible and the salesforce_opportunities table exists."
    )
