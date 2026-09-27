"""Study Schedule page: generate tasks, see them grouped by date, mark Done / Pending."""

from datetime import date, timedelta

import streamlit as st

from src.schedule import (
    STATUSES,
    generate_schedule,
    generate_until_nearest_exam,
    list_tasks,
    set_task_status,
)
from src.ui import flash, load_or_stop, show_flash

st.title("Study Schedule")
show_flash()


def summary_message(result):
    """Turn the result of generate_schedule into (message type, text) for the user."""
    text = f"Created {result['created']} study task(s) from {result['start_date']} to {result['end_date']}."
    if result["already_scheduled"]:
        text += f" {result['already_scheduled']} topic(s) already had a task in this period."
    if result["skipped_no_exam"]:
        text += f" {result['skipped_no_exam']} topic(s) skipped because their subject has no upcoming exam."
    if result["could_not_fit"]:
        names = ", ".join(f"{t['subject']} - {t['topic']}" for t in result["could_not_fit"])
        text += f" Could not fit before the exam day: {names}."
        return "warning", text
    if result["created"] == 0:
        return "info", text
    return "success", text


def change_status(task_id, widget_key):
    """Called by Streamlit when a Status dropdown changes."""
    set_task_status(task_id, st.session_state[widget_key])


# ----- Generate -----
st.subheader("Generate a schedule")
mode = st.radio(
    "Schedule period",
    ["Up to the nearest upcoming exam", "Custom date range"],
    key="schedule_mode",
)
start_date = st.date_input("Start date", value=date.today(), key="schedule_start")
end_date = None
if mode == "Custom date range":
    end_date = st.date_input("End date", value=date.today() + timedelta(days=14), key="schedule_end")
st.caption(
    "Only topics whose subject has an upcoming exam are scheduled. "
    "Harder topics and topics with earlier exams come first, and every task is placed before its exam day."
)

if st.button("Generate Study Schedule"):
    try:
        if mode == "Custom date range":
            result = load_or_stop(lambda: generate_schedule(start_date, end_date))
        else:
            result = load_or_stop(lambda: generate_until_nearest_exam(start_date))
        kind, text = summary_message(result)
        flash(text, kind)
        st.rerun()
    except ValueError as error:
        st.error(str(error))

# ----- Show -----
tasks = load_or_stop(list_tasks)
st.subheader("Study tasks")
if not tasks:
    st.info("No study tasks yet. Generate a schedule above.")
    st.stop()

tasks_by_date = {}
for task in tasks:
    tasks_by_date.setdefault(task["task_date"], []).append(task)

COLUMN_WIDTHS = [2, 3, 1.3, 1.3, 1.6]
for day, day_tasks in tasks_by_date.items():
    st.markdown(f"#### {day:%A, %d %b %Y}")
    header = st.columns(COLUMN_WIDTHS)
    for column, label in zip(header, ["Subject", "Topic", "Difficulty", "Duration", "Status"]):
        column.markdown(f"**{label}**")

    for task in day_tasks:
        subject_col, topic_col, difficulty_col, duration_col, status_col = st.columns(COLUMN_WIDTHS)
        subject_col.write(task["subject"])
        topic_col.write(task["topic"])
        difficulty_col.write(task["difficulty"])
        duration_col.write(f"{task['duration_minutes']} min")
        widget_key = f"task_status_{task['id']}"
        status_col.selectbox(
            "Status",
            STATUSES,
            index=STATUSES.index(task["status"]),
            key=widget_key,
            label_visibility="collapsed",
            on_change=change_status,
            args=(task["id"], widget_key),
        )
