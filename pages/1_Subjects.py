"""Subjects page: add, list, edit, delete."""

import streamlit as st

from src.subjects import add_subject, delete_subject, list_subjects, update_subject
from src.ui import clear_field, flash, fresh_key, load_or_stop, show_flash

st.title("Subjects")
show_flash()

# ----- Add -----
st.subheader("Add a subject")
with st.form("add_subject_form"):
    new_name = st.text_input("Subject name", key=fresh_key("new_subject_name"))
    if st.form_submit_button("Add subject"):
        try:
            add_subject(new_name)
            flash(f"Added subject '{new_name.strip()}'.")
            clear_field("new_subject_name")
            st.rerun()
        except ValueError as error:
            st.error(str(error))

# ----- List -----
subjects = load_or_stop(list_subjects)
st.subheader("All subjects")
if not subjects:
    st.info("No subjects yet. Add your first one above.")
    st.stop()
st.dataframe([{"Subject": s["name"]} for s in subjects], hide_index=True)

# ----- Edit / Delete -----
st.subheader("Edit or delete a subject")
names = {s["id"]: s["name"] for s in subjects}
subject_id = st.selectbox("Choose a subject", list(names), format_func=names.get, key="subject_to_edit")

with st.form("edit_subject_form"):
    edited_name = st.text_input("Subject name", value=names[subject_id], key=f"edit_subject_name_{subject_id}")
    if st.form_submit_button("Save changes"):
        try:
            update_subject(subject_id, edited_name)
            flash("Subject updated.")
            st.rerun()
        except ValueError as error:
            st.error(str(error))

confirm = st.checkbox(
    "Yes, delete this subject together with all its topics and exams",
    key=f"confirm_delete_subject_{subject_id}",
)
if st.button("Delete subject"):
    if confirm:
        delete_subject(subject_id)
        flash(f"Deleted subject '{names[subject_id]}'.")
        st.rerun()
    else:
        st.error("Tick the confirmation box first.")
