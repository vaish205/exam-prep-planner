"""Practice Paper Generator: build a paper from questions already sitting in
pyq_questions. Read-only - generating a paper never inserts, updates, or
deletes anything.

Same style as pyq_analysis.py / pyq_ingestion.py: plain functions,
parameterized SQL, no ORM. Selection is a plain SQL topic filter followed by
Python's random.sample() - no ranking, no ML, nothing beyond picking N
questions at random without replacement (which is also what guarantees no
duplicate question IDs in one paper).
"""

import random

from src.db import fetch_all
from src.logger import get_logger
from src.pyq_ingestion import ALLOWED_TOPICS

logger = get_logger(__name__)


def _validate_topics(topics):
    if not topics:
        raise ValueError("Select at least one topic.")
    unknown = [topic for topic in topics if topic not in ALLOWED_TOPICS]
    if unknown:
        raise ValueError("Unknown topic(s): " + ", ".join(unknown))


def _validate_question_count(question_count):
    if not isinstance(question_count, int) or isinstance(question_count, bool) or question_count <= 0:
        raise ValueError("Number of questions must be a whole number greater than 0.")


def get_available_question_count(topics):
    """How many questions in pyq_questions match the given topics."""
    _validate_topics(topics)
    placeholders = ", ".join(["%s"] * len(topics))
    row = fetch_all(
        f"SELECT COUNT(*) AS count FROM pyq_questions WHERE topic IN ({placeholders})",
        tuple(topics),
    )[0]
    return row["count"]


def generate_practice_paper(topics, question_count):
    """Return `question_count` real, distinct questions from the selected topics.

    Raises ValueError if no topic is selected, an unknown topic is given,
    question_count isn't a positive whole number, or fewer questions exist
    for the selected topics than were requested (never silently returns
    fewer than asked for).

    Each item is a dict: {"id", "topic", "question"}.
    """
    _validate_topics(topics)
    _validate_question_count(question_count)

    placeholders = ", ".join(["%s"] * len(topics))
    eligible = fetch_all(
        f"SELECT id, topic, question FROM pyq_questions WHERE topic IN ({placeholders})",
        tuple(topics),
    )

    if question_count > len(eligible):
        raise ValueError(
            f"Only {len(eligible)} question(s) available for the selected topic(s), "
            f"but {question_count} were requested."
        )

    logger.info("Practice paper generated: topics=%s question_count=%d", topics, question_count)
    return random.sample(eligible, question_count)
