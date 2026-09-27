"""CRUD tests for subjects, topics and exams.  Run from the project root:

    python -m unittest -v

They use the real database from your .env, so run 'python init_db.py' first.
Every test row is named 'TEST_...' and only those rows are removed afterwards,
so your own data is never touched.
"""

import unittest
from datetime import date, timedelta

from src.db import execute, fetch_all
from src.exams import add_exam, delete_exam, list_exams, update_exam
from src.subjects import add_subject, delete_subject, list_subjects, update_subject
from src.topics import add_topic, delete_topic, list_topics, update_topic

FUTURE = date.today() + timedelta(days=30)


def clean_up():
    execute("DELETE FROM subjects WHERE name LIKE %s", ("TEST\\_%",))  # cascades to topics/exams


def subject_id(name):
    return fetch_all("SELECT id FROM subjects WHERE name = %s", (name,))[0]["id"]


class CrudTests(unittest.TestCase):
    def setUp(self):
        clean_up()

    def tearDown(self):
        clean_up()

    # ---------- subjects ----------
    def test_subject_create_read_update_delete(self):
        add_subject("  TEST_Databases  ")  # spaces are trimmed
        self.assertIn("TEST_Databases", [s["name"] for s in list_subjects()])

        sid = subject_id("TEST_Databases")
        update_subject(sid, "TEST_DBMS")
        names = [s["name"] for s in list_subjects()]
        self.assertIn("TEST_DBMS", names)
        self.assertNotIn("TEST_Databases", names)

        delete_subject(sid)
        self.assertNotIn("TEST_DBMS", [s["name"] for s in list_subjects()])

    def test_subject_validation(self):
        with self.assertRaises(ValueError):
            add_subject("   ")
        with self.assertRaises(ValueError):
            add_subject("TEST_" + "x" * 200)
        add_subject("TEST_OS")
        with self.assertRaises(ValueError):
            add_subject("TEST_OS")  # duplicate

    def test_sql_injection_text_is_stored_as_plain_text(self):
        evil = "TEST_x'; DROP TABLE subjects; --"
        add_subject(evil)
        self.assertIn(evil, [s["name"] for s in list_subjects()])  # table still exists

    # ---------- topics ----------
    def test_topic_create_read_update_delete(self):
        add_subject("TEST_Networks")
        add_subject("TEST_Compilers")
        net, comp = subject_id("TEST_Networks"), subject_id("TEST_Compilers")

        add_topic(net, "TEST_Routing", "Hard")
        topic = [t for t in list_topics() if t["name"] == "TEST_Routing"][0]
        self.assertEqual((topic["subject"], topic["difficulty"]), ("TEST_Networks", "Hard"))

        update_topic(topic["id"], comp, "TEST_Parsing", "Easy")
        topic = [t for t in list_topics() if t["id"] == topic["id"]][0]
        self.assertEqual((topic["subject"], topic["name"], topic["difficulty"]),
                         ("TEST_Compilers", "TEST_Parsing", "Easy"))

        delete_topic(topic["id"])
        self.assertEqual([t for t in list_topics() if t["id"] == topic["id"]], [])

    def test_topic_validation(self):
        add_subject("TEST_Maths")
        sid = subject_id("TEST_Maths")
        with self.assertRaises(ValueError):
            add_topic(sid, "", "Easy")  # empty name
        with self.assertRaises(ValueError):
            add_topic(sid, "TEST_Graphs", "Impossible")  # not an allowed difficulty
        add_topic(sid, "TEST_Graphs", "Medium")
        with self.assertRaises(ValueError):
            add_topic(sid, "TEST_Graphs", "Easy")  # duplicate in same subject
        with self.assertRaises(ValueError):
            add_topic(99999999, "TEST_Ghost", "Easy")  # subject does not exist

    # ---------- exams ----------
    def test_exam_create_read_update_delete(self):
        add_subject("TEST_Algorithms")
        sid = subject_id("TEST_Algorithms")

        add_exam(sid, "TEST_Midterm", FUTURE)
        exam = [e for e in list_exams() if e["name"] == "TEST_Midterm"][0]
        self.assertEqual((exam["subject"], exam["exam_date"]), ("TEST_Algorithms", FUTURE))

        new_date = FUTURE + timedelta(days=7)
        update_exam(exam["id"], sid, "TEST_Final", new_date.isoformat())  # ISO string is accepted
        exam = [e for e in list_exams() if e["id"] == exam["id"]][0]
        self.assertEqual((exam["name"], exam["exam_date"]), ("TEST_Final", new_date))

        delete_exam(exam["id"])
        self.assertEqual([e for e in list_exams() if e["id"] == exam["id"]], [])

    def test_exam_validation(self):
        add_subject("TEST_Theory")
        sid = subject_id("TEST_Theory")
        with self.assertRaises(ValueError):
            add_exam(sid, "", FUTURE)  # empty name
        with self.assertRaises(ValueError):
            add_exam(sid, "TEST_Quiz", "2026-02-30")  # impossible date
        with self.assertRaises(ValueError):
            add_exam(sid, "TEST_Quiz", "not a date")
        with self.assertRaises(ValueError):
            add_exam(sid, "TEST_Quiz", None)
        with self.assertRaises(ValueError):
            add_exam(sid, "TEST_Quiz", date.today() - timedelta(days=1))  # in the past
        with self.assertRaises(ValueError):
            add_exam(99999999, "TEST_Quiz", FUTURE)  # subject does not exist

    def test_past_exam_can_be_renamed_but_not_moved_into_the_past(self):
        add_subject("TEST_History")
        sid = subject_id("TEST_History")
        past = date.today() - timedelta(days=10)
        # Insert a past exam directly (add_exam would refuse it)
        execute("INSERT INTO exams (subject_id, name, exam_date) VALUES (%s, %s, %s)",
                (sid, "TEST_Old", past))
        exam = [e for e in list_exams() if e["name"] == "TEST_Old"][0]

        update_exam(exam["id"], sid, "TEST_Old_Renamed", past)  # same date: allowed
        with self.assertRaises(ValueError):
            update_exam(exam["id"], sid, "TEST_Old_Renamed", past - timedelta(days=1))

    # ---------- relationships ----------
    def test_deleting_subject_removes_topics_exams_and_tasks(self):
        add_subject("TEST_Cascade")
        sid = subject_id("TEST_Cascade")
        add_topic(sid, "TEST_T1", "Easy")
        add_exam(sid, "TEST_E1", FUTURE)
        tid = [t for t in list_topics() if t["name"] == "TEST_T1"][0]["id"]
        execute(
            "INSERT INTO study_tasks (topic_id, task_date, duration_minutes) VALUES (%s, %s, %s)",
            (tid, FUTURE, 45),
        )

        delete_subject(sid)

        self.assertEqual([t for t in list_topics() if t["name"] == "TEST_T1"], [])
        self.assertEqual([e for e in list_exams() if e["name"] == "TEST_E1"], [])
        self.assertEqual(fetch_all("SELECT id FROM study_tasks WHERE topic_id = %s", (tid,)), [])


if __name__ == "__main__":
    unittest.main()
