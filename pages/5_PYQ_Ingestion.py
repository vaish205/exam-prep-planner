"""GATE PYQ Ingestion page: upload a CSV, preview it, validate it, then (only
when the button is clicked) insert the clean rows into pyq_questions."""

import streamlit as st

from src.logger import get_logger
from src.pyq_ingestion import ALLOWED_TOPICS, analyze, ingest_csv, load_csv
from src.ui import flash, load_or_stop, show_flash

logger = get_logger(__name__)

st.title("GATE PYQ Ingestion")
show_flash()

st.caption(
    "Upload a CSV with 'Topic' and 'Question' columns (topics must be one of the "
    "8 GATE CSE categories). This dataset has no year column, so there is no "
    "year-wise analysis here - just topic and question text."
)

uploaded_file = st.file_uploader("GATE PYQ CSV", type=["csv"])
if uploaded_file is None:
    st.info("Upload a CSV to preview and validate it.")
    st.stop()

try:
    uploaded_file.seek(0)
    df = load_csv(uploaded_file)
except Exception as error:  # not a valid CSV at all
    logger.exception("Could not parse uploaded file as CSV")
    st.error(f"Could not read this file as a CSV: {error}")
    st.stop()

st.subheader("Preview")
st.write(f"{len(df)} row(s) read.")
st.dataframe(df.head(20), hide_index=True)

try:
    analysis = analyze(df)
except ValueError as error:
    st.error(str(error))
    st.stop()

st.subheader("Validation")
col1, col2, col3 = st.columns(3)
col1.metric("Valid rows", len(analysis["valid_rows"]))
col2.metric("Missing question", analysis["missing_question_count"])
col3.metric("Invalid topic", analysis["invalid_topic_count"])
with st.expander("Allowed topics"):
    st.write(", ".join(ALLOWED_TOPICS))

if st.button("Start Ingestion", disabled=not analysis["valid_rows"]):
    uploaded_file.seek(0)
    result = load_or_stop(lambda: ingest_csv(uploaded_file))
    st.session_state["pyq_last_result"] = result
    flash(f"Ingested {result['inserted']} new question(s).")
    st.rerun()

# ----- Last ingestion result (only set right after a click above) -----
result = st.session_state.get("pyq_last_result")
if result:
    st.subheader("Ingestion results")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows read", result["rows_read"])
    col2.metric("Inserted", result["inserted"])
    col3.metric("Invalid rows", result["invalid_rows"])
    col4.metric("Duplicates", result["duplicate_count"])
    if result["topic_counts"]:
        st.write("Inserted per topic:")
        st.dataframe(
            [{"Topic": topic, "Inserted": count} for topic, count in result["topic_counts"].items()],
            hide_index=True,
        )
