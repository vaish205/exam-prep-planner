"""Topics: business logic and SQL."""

import mysql.connector

from src.db import execute, fetch_all
from src.validation import clean_text

DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard"]  # must match the ENUM in sql/schema.sql


def _check(name, difficulty):
    name = clean_text(name, "Topic name", 150)
    if difficulty not in DIFFICULTY_LEVELS:
        raise ValueError("Difficulty must be one of: " + ", ".join(DIFFICULTY_LEVELS) + ".")
    return name


def _explain(error):
    """Turn a MySQL integrity error into a message the user can understand."""
    if error.errno == 1062:  # duplicate key
        return "This subject already has a topic with that name."
    if error.errno == 1452:  # foreign key: subject not found
        return "The selected subject no longer exists."
    raise error


def list_topics():
    return fetch_all(
        """
        SELECT t.id, t.subject_id, s.name AS subject, t.name, t.difficulty
        FROM topics t
        JOIN subjects s ON s.id = t.subject_id
        ORDER BY s.name, t.name
        """
    )


def add_topic(subject_id, name, difficulty):
    name = _check(name, difficulty)
    try:
        execute(
            "INSERT INTO topics (subject_id, name, difficulty) VALUES (%s, %s, %s)",
            (subject_id, name, difficulty),
        )
    except mysql.connector.IntegrityError as error:
        raise ValueError(_explain(error))


def update_topic(topic_id, subject_id, name, difficulty):
    name = _check(name, difficulty)
    try:
        execute(
            "UPDATE topics SET subject_id = %s, name = %s, difficulty = %s WHERE id = %s",
            (subject_id, name, difficulty, topic_id),
        )
    except mysql.connector.IntegrityError as error:
        raise ValueError(_explain(error))


def delete_topic(topic_id):
    execute("DELETE FROM topics WHERE id = %s", (topic_id,))
