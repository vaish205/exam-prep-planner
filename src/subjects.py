"""Subjects: business logic and SQL."""

import mysql.connector

from src.db import execute, fetch_all
from src.validation import clean_text

DUPLICATE_MESSAGE = "A subject with this name already exists."


def list_subjects():
    return fetch_all("SELECT id, name FROM subjects ORDER BY name")


def add_subject(name):
    name = clean_text(name, "Subject name", 100)
    try:
        execute("INSERT INTO subjects (name) VALUES (%s)", (name,))
    except mysql.connector.IntegrityError:
        raise ValueError(DUPLICATE_MESSAGE)


def update_subject(subject_id, name):
    name = clean_text(name, "Subject name", 100)
    try:
        execute("UPDATE subjects SET name = %s WHERE id = %s", (name, subject_id))
    except mysql.connector.IntegrityError:
        raise ValueError(DUPLICATE_MESSAGE)


def delete_subject(subject_id):
    """Also deletes the subject's topics and exams (ON DELETE CASCADE)."""
    execute("DELETE FROM subjects WHERE id = %s", (subject_id,))
