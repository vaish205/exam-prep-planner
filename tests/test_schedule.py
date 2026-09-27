"""Tests for the study schedule (Milestone 3). Run from the project root:

    python -m unittest -v

Uses the real database from your .env (run 'python init_db.py' first). Every
subject created here is named 'TEST_SCHED_...', and only those rows (plus the
topics/exams/tasks that cascade from them) are removed afterwards, so your
own data is never touched. Tests also pass subject_ids= to schedule functions
so they only ever look at their own test subjects, even if you already have
other subjects, topics and exams in the database.
"""

import unittest
from datetime import date, timedelta

from src.db import execute, fetch_all
from src.exams import add_exam
from src.schedule import (
    DURATION_MINUTES,
    build_schedule,
    generate_schedule,
    generate_until_nearest_exam,
    list_tasks,
    set_task_status,
)
from src.subjects import add_subject
from src.topics import add_topic

TODAY = date.today()


def clean_up():
    execute("DELETE FROM subjects WHERE name LIKE %s", ("TEST\\_SCHED\\_%",))  # cascades


def subject_id(name):
    return fetch_all("SELECT id FROM subjects WHERE name = %s", (name,))[0]["id"]


def tasks_for(subject_name):
    return [t for t in list_tasks() if t["subject"] == subject_name]


class ScheduleGenerationTests(unittest.TestCase):
    """End-to-end: subjects/topics/exams in MySQL -> study_tasks rows."""

    def setUp(self):
        clean_up()

    def tearDown(self):
        clean_up()

    def test_generates_one_task_per_topic_with_duration_by_difficulty(self):
        add_subject("TEST_SCHED_Networks")
        sid = subject_id("TEST_SCHED_Networks")
        add_topic(sid, "TEST_Easy", "Easy")
        add_topic(sid, "TEST_Medium", "Medium")
        add_topic(sid, "TEST_Hard", "Hard")
        add_exam(sid, "TEST_SCHED_Final", TODAY + timedelta(days=30))

        result = generate_schedule(TODAY, TODAY + timedelta(days=10), subject_ids=[sid])

        self.assertEqual(result["created"], 3)
        self.assertEqual(result["already_scheduled"], 0)
        self.assertEqual(result["skipped_no_exam"], 0)
        durations = {t["topic"]: t["duration_minutes"] for t in tasks_for("TEST_SCHED_Networks")}
        self.assertEqual(durations["TEST_Easy"], DURATION_MINUTES["Easy"])
        self.assertEqual(durations["TEST_Medium"], DURATION_MINUTES["Medium"])
        self.assertEqual(durations["TEST_Hard"], DURATION_MINUTES["Hard"])

    def test_no_duplicate_tasks_on_a_second_run(self):
        add_subject("TEST_SCHED_OS")
        sid = subject_id("TEST_SCHED_OS")
        add_topic(sid, "TEST_Scheduling", "Medium")
        add_topic(sid, "TEST_Deadlock", "Hard")
        add_exam(sid, "TEST_SCHED_Final", TODAY + timedelta(days=30))

        first = generate_schedule(TODAY, TODAY + timedelta(days=10), subject_ids=[sid])
        second = generate_schedule(TODAY, TODAY + timedelta(days=10), subject_ids=[sid])

        self.assertEqual(first["created"], 2)
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["already_scheduled"], 2)
        # exactly one task per topic in the period, not two
        self.assertEqual(len(tasks_for("TEST_SCHED_OS")), 2)

    def test_topics_without_an_upcoming_exam_are_skipped_not_failed(self):
        add_subject("TEST_SCHED_WithExam")
        add_subject("TEST_SCHED_NoExam")
        with_exam_id = subject_id("TEST_SCHED_WithExam")
        no_exam_id = subject_id("TEST_SCHED_NoExam")
        add_topic(with_exam_id, "TEST_Ready", "Medium")
        add_topic(no_exam_id, "TEST_NotReady", "Medium")
        add_exam(with_exam_id, "TEST_SCHED_Final", TODAY + timedelta(days=30))

        result = generate_schedule(
            TODAY, TODAY + timedelta(days=10), subject_ids=[with_exam_id, no_exam_id]
        )

        self.assertEqual(result["created"], 1)
        self.assertEqual(result["skipped_no_exam"], 1)
        self.assertEqual([t["topic"] for t in tasks_for("TEST_SCHED_WithExam")], ["TEST_Ready"])
        self.assertEqual(tasks_for("TEST_SCHED_NoExam"), [])

    def test_generate_until_nearest_exam(self):
        add_subject("TEST_SCHED_Soon")
        sid = subject_id("TEST_SCHED_Soon")
        add_topic(sid, "TEST_Topic", "Easy")
        exam_date = TODAY + timedelta(days=5)
        add_exam(sid, "TEST_SCHED_Final", exam_date)

        result = generate_until_nearest_exam(TODAY, subject_ids=[sid])

        self.assertEqual(result["created"], 1)
        self.assertEqual(result["end_date"], exam_date - timedelta(days=1))
        task = tasks_for("TEST_SCHED_Soon")[0]
        self.assertLess(task["task_date"], exam_date)

    # ---------- validation ----------
    def test_no_topics_raises(self):
        add_subject("TEST_SCHED_Empty")
        sid = subject_id("TEST_SCHED_Empty")
        add_exam(sid, "TEST_SCHED_Final", TODAY + timedelta(days=10))
        with self.assertRaisesRegex(ValueError, "no topics"):
            generate_schedule(TODAY, TODAY + timedelta(days=5), subject_ids=[sid])

    def test_no_upcoming_exams_raises(self):
        add_subject("TEST_SCHED_NoExamAtAll")
        sid = subject_id("TEST_SCHED_NoExamAtAll")
        add_topic(sid, "TEST_Topic", "Easy")
        with self.assertRaisesRegex(ValueError, "no upcoming exams"):
            generate_schedule(TODAY, TODAY + timedelta(days=5), subject_ids=[sid])

    def test_invalid_date_range_raises(self):
        add_subject("TEST_SCHED_Range")
        sid = subject_id("TEST_SCHED_Range")
        add_topic(sid, "TEST_Topic", "Easy")
        add_exam(sid, "TEST_SCHED_Final", TODAY + timedelta(days=10))
        with self.assertRaisesRegex(ValueError, "on or after"):
            generate_schedule(TODAY + timedelta(days=5), TODAY, subject_ids=[sid])

    def test_start_date_in_the_past_raises(self):
        add_subject("TEST_SCHED_Past")
        sid = subject_id("TEST_SCHED_Past")
        add_topic(sid, "TEST_Topic", "Easy")
        add_exam(sid, "TEST_SCHED_Final", TODAY + timedelta(days=10))
        with self.assertRaisesRegex(ValueError, "past"):
            generate_schedule(TODAY - timedelta(days=1), TODAY + timedelta(days=5), subject_ids=[sid])

    # ---------- status toggle ----------
    def test_mark_task_done_and_back_to_pending(self):
        add_subject("TEST_SCHED_Status")
        sid = subject_id("TEST_SCHED_Status")
        add_topic(sid, "TEST_Topic", "Easy")
        add_exam(sid, "TEST_SCHED_Final", TODAY + timedelta(days=10))
        generate_schedule(TODAY, TODAY + timedelta(days=5), subject_ids=[sid])
        task_id = tasks_for("TEST_SCHED_Status")[0]["id"]

        set_task_status(task_id, "Done")
        self.assertEqual(tasks_for("TEST_SCHED_Status")[0]["status"], "Done")

        set_task_status(task_id, "Pending")
        self.assertEqual(tasks_for("TEST_SCHED_Status")[0]["status"], "Pending")

        with self.assertRaises(ValueError):
            set_task_status(task_id, "Not a real status")


class BuildScheduleTests(unittest.TestCase):
    """Pure-Python tests for the ranking/placement algorithm - no database needed."""

    def test_harder_difficulty_is_ranked_first(self):
        far = TODAY + timedelta(days=60)
        topics = [
            {"topic_id": 1, "subject": "S", "topic": "Easy one", "difficulty": "Easy", "exam_date": far},
            {"topic_id": 2, "subject": "S", "topic": "Hard one", "difficulty": "Hard", "exam_date": far},
            {"topic_id": 3, "subject": "S", "topic": "Medium one", "difficulty": "Medium", "exam_date": far},
        ]
        days = [TODAY, TODAY + timedelta(days=1), TODAY + timedelta(days=2)]

        planned, could_not_fit = build_schedule(topics, days)

        self.assertEqual([t["topic"] for t, _day in planned], ["Hard one", "Medium one", "Easy one"])
        self.assertEqual(could_not_fit, [])

    def test_earlier_exam_date_is_ranked_first_within_same_difficulty(self):
        soon = TODAY + timedelta(days=3)
        later = TODAY + timedelta(days=20)
        topics = [
            {"topic_id": 1, "subject": "B", "topic": "Later exam", "difficulty": "Medium", "exam_date": later},
            {"topic_id": 2, "subject": "A", "topic": "Sooner exam", "difficulty": "Medium", "exam_date": soon},
        ]
        days = [TODAY, TODAY + timedelta(days=1)]

        planned, _ = build_schedule(topics, days)

        self.assertEqual([t["topic"] for t, _day in planned], ["Sooner exam", "Later exam"])
        # and it's spread across two different days, not both on day 0
        self.assertEqual(len({day for _t, day in planned}), 2)

    def test_topics_are_spread_across_days_not_piled_on_one_day(self):
        far = TODAY + timedelta(days=60)
        topics = [
            {"topic_id": i, "subject": "S", "topic": f"T{i}", "difficulty": "Medium", "exam_date": far}
            for i in range(4)
        ]
        days = [TODAY, TODAY + timedelta(days=1)]

        planned, _ = build_schedule(topics, days)

        counts = {}
        for _t, day in planned:
            counts[day] = counts.get(day, 0) + 1
        self.assertEqual(sorted(counts.values()), [2, 2])  # 4 topics, 2 days -> 2 each

    def test_topic_is_not_scheduled_on_or_after_its_own_exam_date(self):
        tomorrow = TODAY + timedelta(days=1)
        topics = [{"topic_id": 1, "subject": "S", "topic": "Urgent", "difficulty": "Hard", "exam_date": tomorrow}]
        days = [TODAY, tomorrow, TODAY + timedelta(days=2)]  # only TODAY is before the exam

        planned, could_not_fit = build_schedule(topics, days)

        self.assertEqual(planned, [(topics[0], TODAY)])
        self.assertEqual(could_not_fit, [])

    def test_topic_that_cannot_fit_before_its_exam_is_reported(self):
        # 2 days, 3 topics -> capacity 2 per day (ceil(3 / 2)).
        # The two Hard topics (far-off exam) outrank "TooLate" and fill day 0
        # to capacity, and "TooLate"'s own exam is day 1, so day 0 is its
        # only option before its exam - and that option is already full.
        days = [TODAY, TODAY + timedelta(days=1)]
        blockers = [
            {"topic_id": 1, "subject": "S", "topic": "Blocker1", "difficulty": "Hard", "exam_date": TODAY + timedelta(days=60)},
            {"topic_id": 2, "subject": "S", "topic": "Blocker2", "difficulty": "Hard", "exam_date": TODAY + timedelta(days=60)},
        ]
        too_late = {"topic_id": 3, "subject": "S", "topic": "TooLate", "difficulty": "Easy", "exam_date": TODAY + timedelta(days=1)}

        planned, could_not_fit = build_schedule(blockers + [too_late], days)

        self.assertEqual(len(planned), 2)
        self.assertEqual([t["topic"] for t in could_not_fit], ["TooLate"])


if __name__ == "__main__":
    unittest.main()
