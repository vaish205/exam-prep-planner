"""Dashboard aggregation helpers.

No new SQL here - this only reuses src/exams.py:list_exams() and
src/schedule.py:list_tasks() and does plain Python filtering, so the
Dashboard page itself can stay UI-only, like every other page in this app.
"""

from datetime import date

from src.exams import list_exams
from src.schedule import list_tasks


def get_upcoming_exams():
    """Exams dated today or later, soonest first (list_exams() is already
    sorted by exam_date, so no re-sorting is needed here)."""
    today = date.today()
    return [exam for exam in list_exams() if exam["exam_date"] >= today]


def get_task_status_counts():
    """{"Pending": n, "Done": n} across every study task in the planner."""
    counts = {"Pending": 0, "Done": 0}
    for task in list_tasks():
        counts[task["status"]] = counts.get(task["status"], 0) + 1
    return counts


def get_upcoming_tasks(limit=5):
    """Up to `limit` still-pending tasks dated today or later, soonest
    first (list_tasks() is already sorted by task_date)."""
    today = date.today()
    upcoming = [task for task in list_tasks() if task["status"] == "Pending" and task["task_date"] >= today]
    return upcoming[:limit]
