"""Exams page: add, list, edit, delete."""

from datetime import date

import streamlit as st

from src.exams import add_exam, delete_exam, list_exams, update_exam
from src.subjects import list_subjects
from src.ui import clear_field, flash, fresh_key, load_or_stop, show_flash

st.title("Exams")
show_flash()

subjects = load_or_stop(list_subjects)
if not subjects:
    st.info("Add a subject first (Subjects page), then come back to add exams.")
    st.stop()
subject_names = {s["id"]: s["name"] for s in subjects}
subject_ids = list(subject_names)

# ----- Add -----
st.subheader("Add an exam")
with st.form("add_exam_form"):
    subject_id = st.selectbox("Subject", subject_ids, format_func=subject_names.get, key="new_exam_subject")
    exam_name = st.text_input("Exam name", key=fresh_key("new_exam_name"))
    exam_date = st.date_input("Exam date", value=date.today(), key="new_exam_date")
    if st.form_submit_button("Add exam"):
        try:
            add_exam(subject_id, exam_name, exam_date)
            flash(f"Added exam '{exam_name.strip()}'.")
            clear_field("new_exam_name")
            st.rerun()
        except ValueError as error:
            st.error(str(error))

# ----- List -----
exams = load_or_stop(list_exams)
st.subheader("All exams")
if not exams:
    st.info("No exams yet. Add your first one above.")
    st.stop()
st.dataframe(
    [{"Subject": e["subject"], "Exam": e["name"], "Date": e["exam_date"]} for e in exams],
    hide_index=True,
)

# ----- Edit / Delete -----
st.subheader("Edit or delete an exam")
labels = {e["id"]: f"{e['exam_date']} - {e['subject']} - {e['name']}" for e in exams}
exam_id = st.selectbox("Choose an exam", list(labels), format_func=labels.get, key="exam_to_edit")
current = next(e for e in exams if e["id"] == exam_id)

with st.form("edit_exam_form"):
    edited_subject_id = st.selectbox(
        "Subject", subject_ids, index=subject_ids.index(current["subject_id"]),
        format_func=subject_names.get, key=f"edit_exam_subject_{exam_id}",
    )
    edited_name = st.text_input("Exam name", value=current["name"], key=f"edit_exam_name_{exam_id}")
    edited_date = st.date_input("Exam date", value=current["exam_date"], key=f"edit_exam_date_{exam_id}")
    if st.form_submit_button("Save changes"):
        try:
            update_exam(exam_id, edited_subject_id, edited_name, edited_date)
            flash("Exam updated.")
            st.rerun()
        except ValueError as error:
            st.error(str(error))

confirm = st.checkbox("Yes, delete this exam", key=f"confirm_delete_exam_{exam_id}")
if st.button("Delete exam"):
    if confirm:
        delete_exam(exam_id)
        flash(f"Deleted exam '{current['name']}'.")
        st.rerun()
    else:
        st.error("Tick the confirmation box first.")
