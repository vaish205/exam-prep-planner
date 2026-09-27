"""Exams: business logic and SQL."""

from datetime import date

import mysql.connector

from src.db import execute, fetch_all
from src.validation import clean_text, parse_date


def _check(name, exam_date):
    name = clean_text(name, "Exam name", 150)
    exam_date = parse_date(exam_date, "Exam date")
    return name, exam_date


def _reject_past(exam_date):
    if exam_date < date.today():
        raise ValueError("Exam date cannot be in the past.")


def list_exams():
    return fetch_all(
        """
        SELECT e.id, e.subject_id, s.name AS subject, e.name, e.exam_date
        FROM exams e
        JOIN subjects s ON s.id = e.subject_id
        ORDER BY e.exam_date, e.name
        """
    )


def add_exam(subject_id, name, exam_date):
    name, exam_date = _check(name, exam_date)
    _reject_past(exam_date)
    try:
        execute(
            "INSERT INTO exams (subject_id, name, exam_date) VALUES (%s, %s, %s)",
            (subject_id, name, exam_date),
        )
    except mysql.connector.IntegrityError:
        raise ValueError("The selected subject no longer exists.")


def update_exam(exam_id, subject_id, name, exam_date):
    name, exam_date = _check(name, exam_date)
    # A past date is only rejected when the date is being changed, so the
    # name or subject of an exam that has already happened can still be edited.
    saved = fetch_all("SELECT exam_date FROM exams WHERE id = %s", (exam_id,))
    if not saved or saved[0]["exam_date"] != exam_date:
        _reject_past(exam_date)
    try:
        execute(
            "UPDATE exams SET subject_id = %s, name = %s, exam_date = %s WHERE id = %s",
            (subject_id, name, exam_date, exam_id),
        )
    except mysql.connector.IntegrityError:
        raise ValueError("The selected subject no longer exists.")


def delete_exam(exam_id):
    execute("DELETE FROM exams WHERE id = %s", (exam_id,))
