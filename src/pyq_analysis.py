"""PYQ Analysis: read-only statistics over the pyq_questions table.

Same style as subjects.py / schedule.py / pyq_ingestion.py: plain functions,
parameterized SQL, no ORM. No text similarity or NLP here - "repeated" is
decided purely by pyq_questions.occurrence_count, which src/pyq_ingestion.py
increments whenever the same normalized question is ingested again.
"""

from src.db import fetch_all
from src.pyq_ingestion import ALLOWED_TOPICS


def get_total_question_count():
    """Total rows in pyq_questions (each row is one distinct question)."""
    return fetch_all("SELECT COUNT(*) AS count FROM pyq_questions")[0]["count"]


def get_topic_counts():
    """Question count for every one of the 8 canonical topics, in a fixed
    order, including topics with 0 questions."""
    rows = fetch_all("SELECT topic, COUNT(*) AS count FROM pyq_questions GROUP BY topic")
    counts_by_topic = {row["topic"]: row["count"] for row in rows}
    return [{"topic": topic, "count": counts_by_topic.get(topic, 0)} for topic in ALLOWED_TOPICS]


def get_topic_percentages():
    """Each topic's share of the total, as a percentage rounded to 2 decimal
    places. All percentages are 0.0 if the table is empty (no division by
    zero)."""
    total = get_total_question_count()
    topic_counts = get_topic_counts()
    if total == 0:
        return [{"topic": row["topic"], "percentage": 0.0} for row in topic_counts]
    return [{"topic": row["topic"], "percentage": round(row["count"] / total * 100, 2)} for row in topic_counts]


def get_top_topic():
    """The canonical topic with the most questions, or None if the table is
    empty. Purely descriptive - not a claim that this topic matters more."""
    if get_total_question_count() == 0:
        return None
    return max(get_topic_counts(), key=lambda row: row["count"])["topic"]


def get_repeated_question_count():
    """How many DISTINCT questions appeared more than once in ingested CSVs.

    This counts rows, not occurrences: a question seen 5 times is still 1
    row here. If this number equals get_total_question_count(), it means
    every single question in the table has been ingested more than once
    (e.g. the same CSV was uploaded twice) - not a sign of a bug.
    """
    return fetch_all("SELECT COUNT(*) AS count FROM pyq_questions WHERE occurrence_count > 1")[0]["count"]


def get_extra_occurrence_count():
    """Total number of *extra* times repeated questions were seen, beyond
    their first occurrence - e.g. a question seen 3 times contributes 2.

    This is the "98 duplicates" style number from ingestion; it's always
    >= get_repeated_question_count(), and equal to it only when every
    repeated question was seen exactly twice.
    """
    row = fetch_all(
        "SELECT COALESCE(SUM(occurrence_count - 1), 0) AS extra "
        "FROM pyq_questions WHERE occurrence_count > 1"
    )[0]
    return int(row["extra"])


def get_repeated_questions():
    """Every question that appeared more than once, most-repeated first.

    Each ingested duplicate only ever updates occurrence_count on the one
    row already stored for that question (see src/pyq_ingestion.py) - a
    duplicate is never given a row of its own. So this is the complete
    repeated-question picture the current data can support; it can't say
    *when* or in what order the repeats happened, only how many times.
    """
    return fetch_all(
        "SELECT topic, question, occurrence_count FROM pyq_questions "
        "WHERE occurrence_count > 1 "
        "ORDER BY occurrence_count DESC, topic, question"
    )
