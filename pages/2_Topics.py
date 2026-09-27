"""Topics page: add, list, edit, delete."""

import streamlit as st

from src.subjects import list_subjects
from src.topics import DIFFICULTY_LEVELS, add_topic, delete_topic, list_topics, update_topic
from src.ui import clear_field, flash, fresh_key, load_or_stop, show_flash

st.title("Topics")
show_flash()

subjects = load_or_stop(list_subjects)
if not subjects:
    st.info("Add a subject first (Subjects page), then come back to add topics.")
    st.stop()
subject_names = {s["id"]: s["name"] for s in subjects}
subject_ids = list(subject_names)

# ----- Add -----
st.subheader("Add a topic")
with st.form("add_topic_form"):
    subject_id = st.selectbox("Subject", subject_ids, format_func=subject_names.get, key="new_topic_subject")
    topic_name = st.text_input("Topic name", key=fresh_key("new_topic_name"))
    difficulty = st.selectbox("Difficulty", DIFFICULTY_LEVELS, index=1, key="new_topic_difficulty")
    if st.form_submit_button("Add topic"):
        try:
            add_topic(subject_id, topic_name, difficulty)
            flash(f"Added topic '{topic_name.strip()}'.")
            clear_field("new_topic_name")
            st.rerun()
        except ValueError as error:
            st.error(str(error))

# ----- List -----
topics = load_or_stop(list_topics)
st.subheader("All topics")
if not topics:
    st.info("No topics yet. Add your first one above.")
    st.stop()
st.dataframe(
    [{"Subject": t["subject"], "Topic": t["name"], "Difficulty": t["difficulty"]} for t in topics],
    hide_index=True,
)

# ----- Edit / Delete -----
st.subheader("Edit or delete a topic")
labels = {t["id"]: f"{t['subject']} - {t['name']}" for t in topics}
topic_id = st.selectbox("Choose a topic", list(labels), format_func=labels.get, key="topic_to_edit")
current = next(t for t in topics if t["id"] == topic_id)

with st.form("edit_topic_form"):
    edited_subject_id = st.selectbox(
        "Subject", subject_ids, index=subject_ids.index(current["subject_id"]),
        format_func=subject_names.get, key=f"edit_topic_subject_{topic_id}",
    )
    edited_name = st.text_input("Topic name", value=current["name"], key=f"edit_topic_name_{topic_id}")
    edited_difficulty = st.selectbox(
        "Difficulty", DIFFICULTY_LEVELS, index=DIFFICULTY_LEVELS.index(current["difficulty"]),
        key=f"edit_topic_difficulty_{topic_id}",
    )
    if st.form_submit_button("Save changes"):
        try:
            update_topic(topic_id, edited_subject_id, edited_name, edited_difficulty)
            flash("Topic updated.")
            st.rerun()
        except ValueError as error:
            st.error(str(error))

confirm = st.checkbox("Yes, delete this topic", key=f"confirm_delete_topic_{topic_id}")
if st.button("Delete topic"):
    if confirm:
        delete_topic(topic_id)
        flash(f"Deleted topic '{current['name']}'.")
        st.rerun()
    else:
        st.error("Tick the confirmation box first.")
