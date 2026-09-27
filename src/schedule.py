"""Study schedule: turn topics, difficulty and exam dates into study_tasks rows."""

import math
from datetime import date, timedelta

from src.db import execute, execute_many, fetch_all
from src.logger import get_logger
from src.topics import DIFFICULTY_LEVELS
from src.validation import parse_date

logger = get_logger(__name__)

DURATION_MINUTES = {"Easy": 30, "Medium": 45, "Hard": 60}
STATUSES = ["Pending", "Done"]  # must match the ENUM in sql/schema.sql


# ---------------------------------------------------------------------------
# Date checks
# ---------------------------------------------------------------------------
def _check_start(start_date):
    start_date = parse_date(start_date, "Start date")
    if start_date < date.today():
        raise ValueError("Start date cannot be in the past.")
    return start_date


def validate_range(start_date, end_date):
    """Return (start, end) as dates, or raise ValueError if the range is not allowed."""
    start_date = _check_start(start_date)
    end_date = parse_date(end_date, "End date")
    if end_date < start_date:
        raise ValueError("End date must be on or after the start date.")
    return start_date, end_date


def list_days(start_date, end_date):
    """Every date from start to end, inclusive."""
    number_of_days = (end_date - start_date).days + 1
    return [start_date + timedelta(days=i) for i in range(number_of_days)]


# ---------------------------------------------------------------------------
# Reading from MySQL
# ---------------------------------------------------------------------------
def _only_subjects(subject_ids, column):
    """Extra SQL + parameters that limit a query to some subjects.

    subject_ids=None means "all subjects" (what the app uses). The tests pass a
    list so they only ever touch their own TEST_ subjects. Only %s placeholders
    are added to the SQL text; the ids themselves travel as parameters.
    """
    if subject_ids is None:
        return "", ()
    if not subject_ids:
        return " AND 1 = 0", ()
    placeholders = ", ".join(["%s"] * len(subject_ids))
    return f" AND {column} IN ({placeholders})", tuple(subject_ids)


def count_topics(subject_ids=None):
    extra_sql, extra_params = _only_subjects(subject_ids, "t.subject_id")
    rows = fetch_all("SELECT COUNT(*) AS total FROM topics t WHERE 1 = 1" + extra_sql, extra_params)
    return rows[0]["total"]


def count_upcoming_exams(today, subject_ids=None):
    extra_sql, extra_params = _only_subjects(subject_ids, "e.subject_id")
    rows = fetch_all(
        "SELECT COUNT(*) AS total FROM exams e WHERE e.exam_date >= %s" + extra_sql,
        (today,) + extra_params,
    )
    return rows[0]["total"]


def nearest_exam_date(today, subject_ids=None):
    """Date of the earliest exam that is today or later (None if there is none)."""
    extra_sql, extra_params = _only_subjects(subject_ids, "e.subject_id")
    rows = fetch_all(
        "SELECT MIN(e.exam_date) AS nearest FROM exams e WHERE e.exam_date >= %s" + extra_sql,
        (today,) + extra_params,
    )
    return rows[0]["nearest"]


def find_topics_to_plan(today, subject_ids=None):
    """Topics whose subject has an upcoming exam, each with its NEAREST upcoming exam date."""
    extra_sql, extra_params = _only_subjects(subject_ids, "s.id")
    return fetch_all(
        """
        SELECT t.id AS topic_id, s.name AS subject, t.name AS topic, t.difficulty,
               MIN(e.exam_date) AS exam_date
        FROM topics t
        JOIN subjects s ON s.id = t.subject_id
        JOIN exams e ON e.subject_id = s.id
        WHERE e.exam_date >= %s
        """
        + extra_sql
        + """
        GROUP BY t.id, s.name, t.name, t.difficulty
        """,
        (today,) + extra_params,
    )


def topics_already_scheduled(start_date, end_date):
    """Ids of topics that already have a study task inside this period."""
    rows = fetch_all(
        "SELECT DISTINCT topic_id FROM study_tasks WHERE task_date BETWEEN %s AND %s",
        (start_date, end_date),
    )
    return {row["topic_id"] for row in rows}


# ---------------------------------------------------------------------------
# The planning algorithm (no database here, so it is easy to test and explain)
# ---------------------------------------------------------------------------
def _first_free_day(topic, days, load, per_day):
    """Earliest day that is before the topic's exam and not yet full (or None)."""
    for day in days:
        if day < topic["exam_date"] and load[day] < per_day:
            return day
    return None


def build_schedule(topics, days):
    """Decide which topic is studied on which day.

    1. Rank the topics: harder difficulty first, then earlier exam date.
    2. Work out how many topics fit per day: ceil(number of topics / number of days).
    3. Walk through the ranked topics and give each one the earliest day that
       is before its exam and still has room.

    Returns (planned, could_not_fit) where planned is a list of (topic, day).
    """
    ranked = sorted(
        topics,
        key=lambda t: (
            -DIFFICULTY_LEVELS.index(t["difficulty"]),  # Hard (2) sorts before Easy (0)
            t["exam_date"],                              # earlier exam first
            t["subject"],
            t["topic"],                                  # same every time we run it
        ),
    )
    per_day = math.ceil(len(ranked) / len(days))
    load = {day: 0 for day in days}

    planned, could_not_fit = [], []
    for topic in ranked:
        day = _first_free_day(topic, days, load, per_day)
        if day is None:
            could_not_fit.append(topic)
        else:
            load[day] += 1
            planned.append((topic, day))
    return planned, could_not_fit


# ---------------------------------------------------------------------------
# Generating and saving the schedule
# ---------------------------------------------------------------------------
def generate_schedule(start_date, end_date, subject_ids=None):
    """Create study_tasks for the period start_date..end_date (both included).

    Returns a summary dictionary. Raises ValueError (and saves nothing) when the
    dates are invalid, there are no topics, or there are no upcoming exams.
    """
    start_date, end_date = validate_range(start_date, end_date)
    today = date.today()

    if count_topics(subject_ids) == 0:
        raise ValueError("There are no topics yet. Add some topics first.")
    if count_upcoming_exams(today, subject_ids) == 0:
        raise ValueError("There are no upcoming exams. Add an exam with a future date first.")

    topics = find_topics_to_plan(today, subject_ids)
    if not topics:
        raise ValueError("None of your topics belong to a subject with an upcoming exam.")

    # Topics that already have a task in this period are left alone (no duplicates).
    already = topics_already_scheduled(start_date, end_date)
    new_topics = [t for t in topics if t["topic_id"] not in already]

    planned, could_not_fit = build_schedule(new_topics, list_days(start_date, end_date))

    rows = [(t["topic_id"], day, DURATION_MINUTES[t["difficulty"]]) for t, day in planned]
    execute_many(
        "INSERT INTO study_tasks (topic_id, task_date, duration_minutes) VALUES (%s, %s, %s)",
        rows,
    )

    logger.info(
        "Schedule generated: %s to %s, created=%d already_scheduled=%d skipped_no_exam=%d could_not_fit=%d",
        start_date, end_date, len(rows), len(topics) - len(new_topics),
        count_topics(subject_ids) - len(topics), len(could_not_fit),
    )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "created": len(rows),
        "already_scheduled": len(topics) - len(new_topics),
        "skipped_no_exam": count_topics(subject_ids) - len(topics),
        "could_not_fit": could_not_fit,
    }


def generate_until_nearest_exam(start_date, subject_ids=None):
    """Same as generate_schedule, ending the day before the nearest upcoming exam."""
    start_date = _check_start(start_date)
    nearest = nearest_exam_date(date.today(), subject_ids)
    if nearest is None:
        raise ValueError("There are no upcoming exams. Add an exam with a future date first.")

    end_date = nearest - timedelta(days=1)
    if end_date < start_date:
        raise ValueError(
            f"The nearest exam is on {nearest}, so there is no day left before it. "
            "Choose a custom date range instead."
        )
    return generate_schedule(start_date, end_date, subject_ids)


# ---------------------------------------------------------------------------
# Showing tasks and changing their status
# ---------------------------------------------------------------------------
def list_tasks():
    """All study tasks, oldest date first; on one day the hardest topics come first."""
    return fetch_all(
        """
        SELECT st.id, st.task_date, s.name AS subject, t.name AS topic,
               t.difficulty, st.duration_minutes, st.status
        FROM study_tasks st
        JOIN topics t ON t.id = st.topic_id
        JOIN subjects s ON s.id = t.subject_id
        ORDER BY st.task_date, t.difficulty DESC, s.name, t.name
        """
    )


def set_task_status(task_id, status):
    if status not in STATUSES:
        raise ValueError("Status must be one of: " + ", ".join(STATUSES) + ".")
    execute("UPDATE study_tasks SET status = %s WHERE id = %s", (status, task_id))
