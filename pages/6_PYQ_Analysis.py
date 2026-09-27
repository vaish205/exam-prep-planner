"""PYQ Analysis page: descriptive statistics over the already-ingested
GATE PYQ data. Read-only - this page never writes to the database."""

import streamlit as st

from src.pyq_analysis import (
    get_extra_occurrence_count,
    get_repeated_question_count,
    get_repeated_questions,
    get_top_topic,
    get_topic_counts,
    get_topic_percentages,
    get_total_question_count,
)
from src.ui import load_or_stop

st.title("PYQ Analysis")
st.caption(
    "Descriptive statistics over the questions already ingested on the PYQ Ingestion page. "
    "A question counts as 'repeated' if the same normalized question was seen more than once "
    "during ingestion - exact text match after cleaning, no fuzzy or semantic matching."
)

total = load_or_stop(get_total_question_count)

if total == 0:
    st.info("No questions have been ingested yet. Use the PYQ Ingestion page first.")
    st.stop()

st.subheader("Total questions")
st.metric("Total questions", total)

st.subheader("Topic-wise question distribution")
topic_counts = load_or_stop(get_topic_counts)
st.dataframe(
    [{"Topic": row["topic"], "Questions": row["count"]} for row in topic_counts],
    hide_index=True,
)
st.bar_chart({row["topic"]: row["count"] for row in topic_counts})

st.subheader("Topic percentages")
topic_percentages = load_or_stop(get_topic_percentages)
st.dataframe(
    [{"Topic": row["topic"], "Percentage": f"{row['percentage']}%"} for row in topic_percentages],
    hide_index=True,
)
st.caption(f"Topic with the most questions: **{load_or_stop(get_top_topic)}** (descriptive only, not a ranking).")

st.subheader("Repeated questions")
st.caption(
    "'Repeated questions' counts distinct questions seen more than once - each one counts as "
    "1 here no matter how many times it repeated. 'Extra occurrences' is the total number of "
    "times those repeats appeared beyond their first occurrence (e.g. a question seen 3 times "
    "counts as 2 extra occurrences)."
)
repeated_count = load_or_stop(get_repeated_question_count)
extra_occurrences = load_or_stop(get_extra_occurrence_count)
col1, col2 = st.columns(2)
col1.metric("Repeated questions", repeated_count)
col2.metric("Extra occurrences", extra_occurrences)
if repeated_count == 0:
    st.write("No question has appeared more than once in an ingested CSV.")
else:
    repeated = load_or_stop(get_repeated_questions)
    st.dataframe(
        [
            {"Topic": row["topic"], "Question": row["question"], "Times seen": row["occurrence_count"]}
            for row in repeated
        ],
        hide_index=True,
    )
