"""Practice Paper Generator page: pick topics + a question count, get a paper
made only of real, already-ingested GATE questions. Read-only - this page
never writes to the database."""

import streamlit as st

from src.practice_paper import generate_practice_paper, get_available_question_count
from src.pyq_ingestion import ALLOWED_TOPICS
from src.ui import load_or_stop

st.title("Practice Paper Generator")
st.caption(
    "Select one or more topics and how many questions you want. Every question in the paper is "
    "picked at random, without repeats, from the questions already ingested on the PYQ Ingestion page."
)

topics = st.multiselect("Select Topics", ALLOWED_TOPICS)
question_count = st.number_input("Number of Questions", min_value=1, step=1, value=10)

if topics:
    available = load_or_stop(lambda: get_available_question_count(topics))
    st.caption(f"{available} question(s) available for the selected topic(s).")

if st.button("Generate Practice Paper", type="primary"):
    try:
        paper = generate_practice_paper(topics, int(question_count))
    except ValueError as error:
        st.error(str(error))
    else:
        st.session_state["practice_paper"] = paper
        st.session_state["practice_paper_topics"] = list(topics)

if "practice_paper" in st.session_state:
    paper = st.session_state["practice_paper"]
    used_topics = st.session_state["practice_paper_topics"]

    st.divider()
    st.success(f"Generated {len(paper)} question(s) from {len(used_topics)} selected topic(s).")
    st.caption("Topics: " + ", ".join(used_topics))

    for position, item in enumerate(paper, start=1):
        st.markdown(f"**{position}. ({item['topic']})** {item['question']}")

    if st.button("Generate New Paper"):
        try:
            st.session_state["practice_paper"] = generate_practice_paper(used_topics, len(paper))
        except ValueError as error:
            st.error(str(error))
        else:
            st.rerun()
