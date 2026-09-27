"""GATE PYQ ingestion: CSV -> pandas -> validate -> clean -> normalize -> MySQL.

Same style as subjects.py / topics.py / exams.py / schedule.py: plain
functions, parameterized SQL, no ORM. Pandas is only used to read the CSV
into rows; all the cleaning below is plain Python (no NLP, no embeddings).
"""

import hashlib
import re

import mysql.connector
import pandas as pd

from src.db import execute, fetch_all
from src.logger import get_logger

logger = get_logger(__name__)

REQUIRED_COLUMNS = ["Topic", "Question"]

# Must match the ENUM in sql/schema.sql exactly - this is the fixed list of
# 8 topics the GATE CSE Question Classification Dataset uses. These are the
# only values ever stored in pyq_questions.topic.
ALLOWED_TOPICS = [
    "Computer Networks",
    "Operating Systems",
    "Mathematics",
    "General Aptitude",
    "Programming/Data Structures",
    "Computer Organization and Architecture",
    "Digital Logic",
    "Theory of Computation",
]

# Other wordings for a canonical topic that show up in real GATE datasets/
# syllabi (e.g. the actual dataset uses "Operating System" and "Programming
# and Data Structure", singular, instead of the plural canonical forms).
# Keys here are already run through _normalize_topic_text, so they only need
# to list the wording difference - case, spacing, underscores and hyphens
# are handled separately.
TOPIC_SYNONYMS = {
    "operating system": "Operating Systems",
    "programming and data structure": "Programming/Data Structures",
    "programming and data structures": "Programming/Data Structures",
    "programming & data structure": "Programming/Data Structures",
    "programming & data structures": "Programming/Data Structures",
}

_WHITESPACE_RE = re.compile(r"\s+")
_SEPARATOR_RE = re.compile(r"[_\-]+")


# ---------------------------------------------------------------------------
# Loading and cleaning (no database here, so this part is easy to unit test)
# ---------------------------------------------------------------------------
def load_csv(file):
    """Read the CSV (a file path or an uploaded-file object) into a DataFrame."""
    return pd.read_csv(file)


def validate_columns(df):
    """Raise ValueError if the CSV is missing 'Topic' or 'Question'."""
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        logger.warning("CSV rejected: missing required column(s) %s", missing)
        raise ValueError("CSV is missing required column(s): " + ", ".join(missing))


def _clean_text(value):
    """Missing/NaN -> None. Anything else -> plain text, trimmed, with repeated
    whitespace (spaces, tabs, newlines) collapsed to a single space."""
    if pd.isna(value):
        return None
    text = _WHITESPACE_RE.sub(" ", str(value)).strip()
    return text or None


def clean_question(value):
    return _clean_text(value)


def clean_topic(value):
    return _clean_text(value)


# Canonical topic, keyed by a loosely-normalized form of itself, e.g.
# "computer networks" -> "Computer Networks". Built once at import time.
_CANONICAL_TOPIC_LOOKUP = {}


def _normalize_topic_text(text):
    """Lowercase, with underscores/hyphens treated as spaces and repeated
    whitespace collapsed - so harmless formatting differences drop out
    before we compare a topic to the canonical list."""
    text = _SEPARATOR_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip().lower()


for _topic in ALLOWED_TOPICS:
    _CANONICAL_TOPIC_LOOKUP[_normalize_topic_text(_topic)] = _topic
for _alt_wording, _topic in TOPIC_SYNONYMS.items():
    _CANONICAL_TOPIC_LOOKUP[_alt_wording] = _topic
del _topic, _alt_wording


def normalize_topic(topic):
    """Match a cleaned topic string to one of the 8 canonical topic names.

    Handles capitalization, extra/leading/trailing whitespace, and
    underscores or hyphens used in place of spaces (e.g. "Computer_Networks",
    "computer-networks"), plus a couple of known equivalent wordings (see
    TOPIC_SYNONYMS). Returns the canonical name, or None if the topic isn't
    one of the 8 - an unrelated or misspelled topic is never accepted.
    """
    if topic is None:
        return None
    return _CANONICAL_TOPIC_LOOKUP.get(_normalize_topic_text(topic))


def normalize_question(question):
    """Lowercase, whitespace-collapsed text used only to catch duplicates.

    " What is   OS? " and "What is OS?" both normalize to "what is os?".
    """
    return _WHITESPACE_RE.sub(" ", question.strip()).lower()


def hash_question(normalized_question):
    """A fixed-length (64 hex char) fingerprint of a normalized question.

    Questions can be very long (some GATE questions run past 1000
    characters), and MySQL can't put a UNIQUE index directly on an unbounded
    column - so this hash, not the question text itself, is what the
    database's UNIQUE constraint is actually built on.
    """
    return hashlib.sha256(normalized_question.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Turning raw CSV rows into clean rows ready to insert (still no database)
# ---------------------------------------------------------------------------
def analyze(df):
    """Validate columns, clean and classify every row, without touching MySQL.

    Returns a dict with:
      rows_read              - total rows in the CSV
      valid_rows             - list of {"topic", "question", "normalized_question", "normalized_question_hash"}
      missing_question_count - rows with no usable question text
      invalid_topic_count    - rows whose topic isn't one of the 8 allowed topics
    """
    validate_columns(df)
    valid_rows = []
    missing_question_count = 0
    invalid_topic_count = 0

    for _, row in df.iterrows():
        question = clean_question(row["Question"])
        if question is None:
            missing_question_count += 1
            continue
        topic = normalize_topic(clean_topic(row["Topic"]))
        if topic is None:
            invalid_topic_count += 1
            continue
        normalized = normalize_question(question)
        valid_rows.append(
            {
                "topic": topic,
                "question": question,
                "normalized_question": normalized,
                "normalized_question_hash": hash_question(normalized),
            }
        )

    return {
        "rows_read": len(df),
        "valid_rows": valid_rows,
        "missing_question_count": missing_question_count,
        "invalid_topic_count": invalid_topic_count,
    }


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def existing_normalized_question_hashes():
    return {row["normalized_question_hash"] for row in fetch_all("SELECT normalized_question_hash FROM pyq_questions")}


def ingest_rows(valid_rows):
    """Insert clean rows, skipping any whose normalized question already
    exists - either already in the table, or seen earlier in this same file.

    A duplicate is never inserted as a second row (the UNIQUE constraint on
    normalized_question_hash guarantees that), but it isn't silently thrown
    away either: the existing row's occurrence_count goes up by one. That
    count is what Milestone 5's repeated-question analysis reads - it's the
    only place "this question showed up more than once" is remembered, since
    a duplicate never gets a row of its own.

    Returns (inserted_count, duplicate_count, topic_counts).
    """
    seen = existing_normalized_question_hashes()
    inserted = 0
    duplicates = 0
    topic_counts = {}

    for row in valid_rows:
        if row["normalized_question_hash"] in seen:
            execute(
                "UPDATE pyq_questions SET occurrence_count = occurrence_count + 1 "
                "WHERE normalized_question_hash = %s",
                (row["normalized_question_hash"],),
            )
            duplicates += 1
            continue
        try:
            execute(
                "INSERT INTO pyq_questions (topic, question, normalized_question, normalized_question_hash) "
                "VALUES (%s, %s, %s, %s)",
                (row["topic"], row["question"], row["normalized_question"], row["normalized_question_hash"]),
            )
        except mysql.connector.IntegrityError:
            # Safety net: the table's UNIQUE constraint caught a duplicate our
            # own in-memory check missed (e.g. inserted by someone else in
            # between). Either way, it's a duplicate, not an error - and the
            # row that's already there still needs its count bumped.
            execute(
                "UPDATE pyq_questions SET occurrence_count = occurrence_count + 1 "
                "WHERE normalized_question_hash = %s",
                (row["normalized_question_hash"],),
            )
            duplicates += 1
            continue
        seen.add(row["normalized_question_hash"])
        inserted += 1
        topic_counts[row["topic"]] = topic_counts.get(row["topic"], 0) + 1

    return inserted, duplicates, topic_counts


def ingest_csv(file):
    """Full pipeline: CSV -> pandas -> validate -> clean -> normalize -> MySQL -> stats.

    Raises ValueError (and inserts nothing) if a required column is missing.
    """
    df = load_csv(file)
    analysis = analyze(df)
    inserted, duplicates, topic_counts = ingest_rows(analysis["valid_rows"])

    logger.info(
        "PYQ ingestion complete: rows_read=%d inserted=%d missing_question=%d "
        "invalid_topic=%d duplicates=%d",
        analysis["rows_read"],
        inserted,
        analysis["missing_question_count"],
        analysis["invalid_topic_count"],
        duplicates,
    )

    return {
        "rows_read": analysis["rows_read"],
        "inserted": inserted,
        "missing_question_count": analysis["missing_question_count"],
        "invalid_topic_count": analysis["invalid_topic_count"],
        "invalid_rows": analysis["missing_question_count"] + analysis["invalid_topic_count"],
        "duplicate_count": duplicates,
        "topic_counts": topic_counts,
    }


def recompute_occurrence_counts(file):
    """One-time repair, NOT part of normal ingestion: recompute occurrence_count
    directly from a source CSV, rather than incrementing against whatever is
    already in the table.

    Why this exists: ingest_csv()/ingest_rows() correctly treat "this question's
    hash is already in pyq_questions" as a new occurrence - which is exactly
    right when a genuinely new CSV happens to repeat an old question. But if
    occurrence_count is uninitialized (e.g. the column was just added to a
    table that was already fully loaded) and you re-upload the *original*
    file to try to recover the true counts, every single question in that
    file is already in the table - so ingest_csv would treat all of them as
    "seen again" and inflate every row's count, not just the ones that were
    genuinely repeated in the source data. This function avoids that: it
    counts how many times each question appears within THIS file only, and
    SETS (never increments) occurrence_count on the matching row(s) already
    in pyq_questions to that exact count. Running it more than once with the
    same file gives the same result every time.

    Rows in the table with no matching question in this file are left alone.
    Returns {"questions_updated": int, "distinct_questions_in_file": int}.
    """
    analysis = analyze(load_csv(file))
    counts_by_hash = {}
    for row in analysis["valid_rows"]:
        h = row["normalized_question_hash"]
        counts_by_hash[h] = counts_by_hash.get(h, 0) + 1

    questions_updated = 0
    for question_hash, true_count in counts_by_hash.items():
        questions_updated += execute(
            "UPDATE pyq_questions SET occurrence_count = %s WHERE normalized_question_hash = %s",
            (true_count, question_hash),
        )

    return {"questions_updated": questions_updated, "distinct_questions_in_file": len(counts_by_hash)}
