"""Exam Prep Dashboard: one page bringing together PYQ statistics, the
frequency-based study focus, upcoming exams, and the study schedule. Purely
read-only - this page never writes to the database. Each section handles its
own "no data yet" case so one empty section never breaks the rest of the
page."""

import streamlit as st

from src.dashboard import get_task_status_counts, get_upcoming_exams, get_upcoming_tasks
from src.pyq_analysis import (
    get_extra_occurrence_count,
    get_repeated_question_count,
    get_topic_counts,
    get_topic_percentages,
    get_total_question_count,
)
from src.pyq_ingestion import ALLOWED_TOPICS
from src.study_plan import get_topic_study_recommendations
from src.ui import load_or_stop

st.title("Exam Prep Dashboard")
st.caption(
    "Combines the planner's scheduling data with descriptive PYQ statistics. The study-focus "
    "section is a simple rule based on how many PYQs exist per topic - it does not predict "
    "actual exam weightage."
)

# --- Top summary metrics ---------------------------------------------------
total_questions = load_or_stop(get_total_question_count)
repeated_questions = load_or_stop(get_repeated_question_count)
extra_occurrences = load_or_stop(get_extra_occurrence_count)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total PYQ Questions", total_questions)
col2.metric("Repeated Questions", repeated_questions)
col3.metric("Extra Occurrences", extra_occurrences)
col4.metric("Number of Topics", len(ALLOWED_TOPICS))

st.divider()

# --- Topic distribution + PYQ-based study focus -----------------------------
if total_questions == 0:
    st.info("No PYQ data available yet. Import the dataset from the PYQ Ingestion page.")
else:
    st.subheader("Topic Distribution")
    topic_counts = load_or_stop(get_topic_counts)
    topic_percentages = {row["topic"]: row["percentage"] for row in load_or_stop(get_topic_percentages)}
    st.dataframe(
        [
            {"Topic": row["topic"], "Questions": row["count"], "Percentage": f"{topic_percentages[row['topic']]}%"}
            for row in topic_counts
        ],
        hide_index=True,
    )
    st.bar_chart({row["topic"]: row["count"] for row in topic_counts})

    st.subheader("PYQ-Based Study Focus")
    st.caption("A frequency-based recommendation, not a prediction of exam importance.")
    recommendations = load_or_stop(get_topic_study_recommendations)
    st.dataframe(
        [
            {
                "Topic": row["topic"],
                "Questions": row["question_count"],
                "Percentage": f"{row['percentage']}%",
                "Recommended Focus": row["recommended_focus"],
            }
            for row in recommendations
        ],
        hide_index=True,
    )

st.divider()

# --- Upcoming exams ----------------------------------------------------------
st.subheader("Upcoming Exams")
upcoming_exams = load_or_stop(get_upcoming_exams)
if not upcoming_exams:
    st.info("No upcoming exams added yet.")
else:
    st.dataframe(
        [{"Exam": e["name"], "Subject": e["subject"], "Date": e["exam_date"]} for e in upcoming_exams],
        hide_index=True,
    )

st.divider()

# --- Study schedule summary --------------------------------------------------
st.subheader("Study Schedule Summary")
status_counts = load_or_stop(get_task_status_counts)
if status_counts["Pending"] == 0 and status_counts["Done"] == 0:
    st.info("No study tasks available yet.")
else:
    sched_col1, sched_col2 = st.columns(2)
    sched_col1.metric("Pending Tasks", status_counts["Pending"])
    sched_col2.metric("Completed Tasks", status_counts["Done"])

    upcoming_tasks = load_or_stop(get_upcoming_tasks)
    if upcoming_tasks:
        st.caption("Next few pending tasks:")
        st.dataframe(
            [
                {"Date": t["task_date"], "Subject": t["subject"], "Topic": t["topic"], "Difficulty": t["difficulty"]}
                for t in upcoming_tasks
            ],
            hide_index=True,
        )

st.divider()

# --- Quick navigation ---------------------------------------------------------
st.subheader("Quick Navigation")
st.caption("Use the sidebar to open any page, or jump straight to one of these:")
nav_col1, nav_col2, nav_col3 = st.columns(3)
nav_col1.markdown("📅 **Schedule** \n_(page 4 in the sidebar)_")
nav_col2.markdown("📊 **PYQ Analysis** \n_(page 6 in the sidebar)_")
nav_col3.markdown("📝 **Practice Paper** \n_(page 7 in the sidebar)_")
