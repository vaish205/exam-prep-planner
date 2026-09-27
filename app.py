"""Exam Prep Planner - Streamlit home page."""

import streamlit as st

from src.db import test_connection

st.set_page_config(page_title="Exam Prep Planner", page_icon="📚")

st.title("📚 Exam Prep Planner")
st.write("A simple study planner for exam preparation.")

st.subheader("Database connection")
if st.button("Test MySQL connection"):
    ok, message = test_connection()
    if ok:
        st.success(message)
    else:
        st.error(message)

st.caption(
    "Use the sidebar to manage Subjects, Topics and Exams; generate a Study Schedule; "
    "import and analyze GATE PYQs; generate a Practice Paper; and view it all on the Dashboard."
)
