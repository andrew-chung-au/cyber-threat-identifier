#!/usr/bin/env python3
"""
Monitoring Dashboard — live PostgreSQL system telemetry.

The dashboard provides five charts and one recent-query table:
1. User feedback ratio
2. Incident query volume
3. Top retrieved ATT&CK techniques
4. Retrieval-latency distribution
5. Feedback volume over time
6. Recent incident logs table
"""

from __future__ import annotations

from datetime import datetime as dt

import pandas as pd
import plotly.express as px
import streamlit as st

from src.database.db_connection import get_connection


def fetch_telemetry_data() -> pd.DataFrame:
    """Fetch query telemetry and optional feedback from PostgreSQL."""
    sql = """
        SELECT
            iq.query_id,
            iq.query_text,
            iq.model_id,
            iq.retrieved_technique_ids,
            iq.retrieval_ms,
            iq.created_at AS timestamp_utc,
            f.feedback,
            f.created_at AS feedback_timestamp_utc
        FROM incident_queries iq
        LEFT JOIN feedback f
            ON iq.query_id = f.query_id
        ORDER BY iq.created_at DESC;
    """

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]

        return pd.DataFrame(rows, columns=columns)

    except Exception as error:
        st.error(f"Failed to connect to the telemetry database: {error}")
        return pd.DataFrame()


def render_monitoring_dashboard() -> None:
    """Render the operational monitoring dashboard."""

    st.markdown("### 📊 Live System Telemetry")

    df = fetch_telemetry_data()

    if df.empty:
        st.info(
            "No queries logged yet. Run a narrative through the "
            "Query Interface to populate the dashboard."
        )
        return

    # Data preparation
    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        errors="coerce",
    )
    df["feedback_timestamp_utc"] = pd.to_datetime(
        df["feedback_timestamp_utc"],
        errors="coerce",
    )
    df["retrieval_ms"] = pd.to_numeric(
        df["retrieval_ms"],
        errors="coerce",
    )
    df["date"] = df["timestamp_utc"].dt.strftime("%Y-%m-%d")

    feedback_df = df.dropna(subset=["feedback"]).copy()

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    total_queries = len(df)

    thumbs_up_count = len(
        feedback_df[feedback_df["feedback"] == "thumbs_up"]
    )
    helpfulness_rate = (
        thumbs_up_count / len(feedback_df)
        if not feedback_df.empty
        else 0
    )

    unique_techniques = 0
    if "retrieved_technique_ids" in df.columns:
        all_techniques = (
            df["retrieved_technique_ids"]
            .dropna()
            .astype(str)
            .str.split("|")
            .explode()
            .str.strip()
        )
        unique_techniques = all_techniques[all_techniques != ""].nunique()

    average_latency = (
        df["retrieval_ms"].mean()
        if not df["retrieval_ms"].isna().all()
        else 0
    )

    col1.metric("Total Queries Logged", total_queries)
    col2.metric(
        "Helpfulness Rate",
        f"{helpfulness_rate:.0%}" if not feedback_df.empty else "N/A",
    )
    col3.metric("Unique Techniques Retrieved", unique_techniques)
    col4.metric(
        "Average Latency (ms)",
        f"{average_latency:.0f}" if average_latency > 0 else "N/A",
    )

    st.divider()

    # Layout row 1
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        # Chart 1: User Feedback Ratio
        st.subheader("1️⃣ User Feedback Ratio")

        if not feedback_df.empty:
            feedback_counts = (
                feedback_df["feedback"]
                .value_counts()
                .rename_axis("Feedback Type")
                .reset_index(name="Count")
            )

            figure_1 = px.pie(
                feedback_counts,
                names="Feedback Type",
                values="Count",
                hole=0.4,
                color="Feedback Type",
                color_discrete_map={
                    "thumbs_up": "#2ecc71",
                    "thumbs_down": "#e74c3c",
                },
            )
            figure_1.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
            )
            st.plotly_chart(
                figure_1,
                use_container_width=True,
            )
        else:
            st.info("No feedback has been submitted yet.")

    with row1_col2:
        # Chart 2: Query Volume Over Time
        st.subheader("2️⃣ Incident Query Volume")

        daily_query_counts = (
            df.dropna(subset=["date"])
            .groupby("date")
            .size()
            .reset_index(name="Queries")
        )

        figure_2 = px.bar(
            daily_query_counts,
            x="date",
            y="Queries",
            labels={
                "date": "Date",
                "Queries": "Number of Queries",
            },
            color_discrete_sequence=["#3498db"],
        )
        figure_2.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
        )
        st.plotly_chart(
            figure_2,
            use_container_width=True,
        )

    # Layout row 2
    row2_col1, row2_col2 = st.columns(2)

    with row2_col1:
        # Chart 3: Top Retrieved ATT&CK Techniques
        st.subheader("3️⃣ Top Retrieved ATT&CK Techniques")

        if "retrieved_technique_ids" in df.columns:
            exploded_techniques = (
                df["retrieved_technique_ids"]
                .dropna()
                .astype(str)
                .str.split("|")
                .explode()
                .str.strip()
            )
            exploded_techniques = exploded_techniques[
                exploded_techniques != ""
            ]

            if not exploded_techniques.empty:
                top_techniques = (
                    exploded_techniques
                    .value_counts()
                    .head(10)
                    .rename_axis("Technique ID")
                    .reset_index(name="Count")
                    .sort_values("Count", ascending=True)
                )

                figure_3 = px.bar(
                    top_techniques,
                    x="Count",
                    y="Technique ID",
                    orientation="h",
                    color_discrete_sequence=["#9b59b6"],
                )
                figure_3.update_layout(
                    margin=dict(t=20, b=20, l=20, r=20),
                )
                st.plotly_chart(
                    figure_3,
                    use_container_width=True,
                )
            else:
                st.info("No techniques retrieved yet.")
        else:
            st.info("Technique telemetry is unavailable.")

    with row2_col2:
        # Chart 4: Retrieval Latency Distribution
        st.subheader("4️⃣ Retrieval Latency (ms)")

        latency_df = df.dropna(subset=["retrieval_ms"])

        if not latency_df.empty:
            figure_4 = px.histogram(
                latency_df,
                x="retrieval_ms",
                nbins=20,
                labels={
                    "retrieval_ms": "Latency (ms)",
                },
                color_discrete_sequence=["#e67e22"],
            )
            figure_4.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                xaxis_title="Milliseconds",
                yaxis_title="Count",
            )
            st.plotly_chart(
                figure_4,
                use_container_width=True,
            )
        else:
            st.info(
                "Latency data will appear once new queries are logged."
            )

    # Chart 5: Feedback Volume Over Time
    st.subheader("5️⃣ Feedback Volume Over Time")

    feedback_volume_df = feedback_df.dropna(
        subset=["feedback_timestamp_utc"],
    ).copy()

    if not feedback_volume_df.empty:
        feedback_volume_df["feedback_date"] = (
            feedback_volume_df["feedback_timestamp_utc"]
            .dt.strftime("%Y-%m-%d")
        )

        daily_feedback_counts = (
            feedback_volume_df
            .groupby("feedback_date")
            .size()
            .reset_index(name="Feedback Submissions")
        )

        figure_5 = px.bar(
            daily_feedback_counts,
            x="feedback_date",
            y="Feedback Submissions",
            labels={
                "feedback_date": "Date",
                "Feedback Submissions": (
                    "Number of Feedback Submissions"
                ),
            },
            color_discrete_sequence=["#1abc9c"],
        )
        figure_5.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
        )
        st.plotly_chart(
            figure_5,
            use_container_width=True,
        )
    else:
        st.info(
            "Feedback volume will appear after users submit feedback."
        )

    # Recent incident logs table
    st.subheader("6️⃣ Recent Incident Logs")

    display_columns = [
        "timestamp_utc",
        "query_id",
        "model_id",
        "retrieval_ms",
        "feedback",
        "query_text",
    ]

    available_columns = [
        column
        for column in display_columns
        if column in df.columns
    ]

    recent_df = df[available_columns].copy()

    if "timestamp_utc" in recent_df.columns:
        recent_df["timestamp_utc"] = recent_df[
            "timestamp_utc"
        ].dt.strftime("%Y-%m-%d %H:%M:%S")

    if "query_text" in recent_df.columns:
        recent_df["query_text"] = recent_df["query_text"].apply(
            lambda value: (
                f"{value[:100]}..."
                if isinstance(value, str) and len(value) > 100
                else value
            )
        )

    st.dataframe(
        recent_df.head(20),
        use_container_width=True,
        hide_index=True,
    )

    # Footer
    st.divider()
    st.markdown(
        f"""
        <div style='text-align: center; color: gray; font-size: 0.9em;'>
            <b>Live Telemetry Dashboard</b> |
            Last updated: {dt.now().strftime("%Y-%m-%d %H:%M")}
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    st.set_page_config(
        page_title="Dashboard",
        page_icon="📊",
        layout="wide",
    )
    render_monitoring_dashboard()