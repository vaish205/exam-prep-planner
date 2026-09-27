"""Tests for the dashboard's aggregation helpers (Milestone 8). Run from the
project root:

    python -m unittest -v

Mocks src.dashboard.list_exams / list_tasks directly - these are pure Python
filters over data src/exams.py and src/schedule.py already fetch, so there's
nothing here to insert into or clean up from the real database.
"""

import unittest
from datetime import date, timedelta
from unittest.mock import patch

from src.dashboard import get_task_status_counts, get_upcoming_exams, get_upcoming_tasks

TODAY = date.today()


def exam(name, days_from_today):
    return {"id": 1, "subject_id": 1, "subject": "Test Subject", "name": name, "exam_date": TODAY + timedelta(days=days_from_today)}


def task(status, days_from_today):
    return {
        "id": 1, "task_date": TODAY + timedelta(days=days_from_today), "subject": "Test Subject",
        "topic": "Test Topic", "difficulty": "Medium", "duration_minutes": 45, "status": status,
    }


class DashboardTests(unittest.TestCase):
    @patch("src.dashboard.list_exams")
    def test_upcoming_exams_excludes_past_exams(self, mock_list_exams):
        mock_list_exams.return_value = [exam("Past", -1), exam("Today", 0), exam("Future", 5)]
        result = [e["name"] for e in get_upcoming_exams()]
        self.assertEqual(result, ["Today", "Future"])

    @patch("src.dashboard.list_exams")
    def test_no_upcoming_exams_returns_empty_list(self, mock_list_exams):
        mock_list_exams.return_value = [exam("Past", -10)]
        self.assertEqual(get_upcoming_exams(), [])

    @patch("src.dashboard.list_tasks")
    def test_task_status_counts_tallies_correctly(self, mock_list_tasks):
        mock_list_tasks.return_value = [task("Pending", 1), task("Pending", 2), task("Done", -1)]
        self.assertEqual(get_task_status_counts(), {"Pending": 2, "Done": 1})

    @patch("src.dashboard.list_tasks")
    def test_task_status_counts_are_zero_with_no_tasks(self, mock_list_tasks):
        mock_list_tasks.return_value = []
        self.assertEqual(get_task_status_counts(), {"Pending": 0, "Done": 0})

    @patch("src.dashboard.list_tasks")
    def test_upcoming_tasks_excludes_done_and_past_tasks(self, mock_list_tasks):
        mock_list_tasks.return_value = [
            task("Done", 1),       # excluded: already done
            task("Pending", -1),   # excluded: in the past
            task("Pending", 0),
            task("Pending", 3),
        ]
        result = get_upcoming_tasks()
        self.assertEqual([t["task_date"] for t in result], [TODAY, TODAY + timedelta(days=3)])

    @patch("src.dashboard.list_tasks")
    def test_upcoming_tasks_respects_the_limit(self, mock_list_tasks):
        mock_list_tasks.return_value = [task("Pending", i) for i in range(10)]
        self.assertEqual(len(get_upcoming_tasks(limit=3)), 3)


if __name__ == "__main__":
    unittest.main()
