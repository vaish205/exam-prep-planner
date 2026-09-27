"""Tests for the Practice Paper Generator (Milestone 6). Run from the
project root:

    python -m unittest -v

These tests mock src.practice_paper.fetch_all directly, so they never touch
the real database or the real ingested GATE questions - appropriate here
since practice_paper.py is pure "read and pick", with no data of its own to
set up or clean up.
"""

import unittest
from unittest.mock import patch

from src.practice_paper import generate_practice_paper, get_available_question_count
from src.pyq_ingestion import ALLOWED_TOPICS


def fake_questions(n, topic="Mathematics", start_id=1):
    return [{"id": i, "topic": topic, "question": f"Fake question {i}"} for i in range(start_id, start_id + n)]


class ValidationTests(unittest.TestCase):
    """No database call should even happen for these - validation runs first."""

    def test_no_topics_selected_raises(self):
        with self.assertRaisesRegex(ValueError, "at least one topic"):
            generate_practice_paper([], 5)
        with self.assertRaisesRegex(ValueError, "at least one topic"):
            get_available_question_count([])

    def test_unknown_topic_raises(self):
        with self.assertRaisesRegex(ValueError, "Unknown topic"):
            generate_practice_paper(["Underwater Basket Weaving"], 5)
        with self.assertRaisesRegex(ValueError, "Unknown topic"):
            get_available_question_count(["Not A Real Topic"])

    def test_invalid_question_count_raises(self):
        for bad_count in [0, -1, 3.5, "5", True, False]:
            with self.assertRaises(ValueError):
                generate_practice_paper(["Mathematics"], bad_count)


class GenerationTests(unittest.TestCase):
    """These mock the database layer with controlled fake rows."""

    @patch("src.practice_paper.fetch_all")
    def test_request_larger_than_available_raises(self, mock_fetch_all):
        mock_fetch_all.return_value = fake_questions(3)
        with self.assertRaisesRegex(ValueError, "Only 3 question"):
            generate_practice_paper(["Mathematics"], 5)

    @patch("src.practice_paper.fetch_all")
    def test_correct_number_of_questions_returned(self, mock_fetch_all):
        mock_fetch_all.return_value = fake_questions(10)
        paper = generate_practice_paper(["Mathematics"], 5)
        self.assertEqual(len(paper), 5)

    @patch("src.practice_paper.fetch_all")
    def test_requesting_exactly_all_available_questions_works(self, mock_fetch_all):
        mock_fetch_all.return_value = fake_questions(4)
        paper = generate_practice_paper(["Mathematics"], 4)
        self.assertEqual(len(paper), 4)

    @patch("src.practice_paper.fetch_all")
    def test_no_duplicate_question_ids_in_one_paper(self, mock_fetch_all):
        mock_fetch_all.return_value = fake_questions(50)
        paper = generate_practice_paper(["Mathematics"], 20)
        ids = [item["id"] for item in paper]
        self.assertEqual(len(ids), len(set(ids)))

    @patch("src.practice_paper.fetch_all")
    def test_generated_questions_have_the_expected_fields(self, mock_fetch_all):
        mock_fetch_all.return_value = fake_questions(5, topic="Digital Logic")
        paper = generate_practice_paper(["Digital Logic"], 2)
        for item in paper:
            self.assertEqual(set(item.keys()), {"id", "topic", "question"})
            self.assertEqual(item["topic"], "Digital Logic")

    @patch("src.practice_paper.fetch_all")
    def test_selected_topics_are_passed_through_to_the_query(self, mock_fetch_all):
        mock_fetch_all.return_value = fake_questions(5)
        chosen = ["Mathematics", "Digital Logic"]

        generate_practice_paper(chosen, 1)

        sql_used, params_used = mock_fetch_all.call_args[0]
        self.assertIn("WHERE topic IN (%s, %s)", sql_used)
        self.assertEqual(params_used, tuple(chosen))

    @patch("src.practice_paper.fetch_all")
    def test_available_question_count_reads_the_count_column(self, mock_fetch_all):
        mock_fetch_all.return_value = [{"count": 42}]
        self.assertEqual(get_available_question_count(["Mathematics"]), 42)

    @patch("src.practice_paper.fetch_all")
    def test_empty_database_gives_zero_available_questions(self, mock_fetch_all):
        mock_fetch_all.return_value = [{"count": 0}]  # COUNT(*) always returns one row, even when it's 0
        self.assertEqual(get_available_question_count(ALLOWED_TOPICS), 0)

    @patch("src.practice_paper.fetch_all")
    def test_empty_database_means_no_questions_can_be_generated(self, mock_fetch_all):
        mock_fetch_all.return_value = []  # no eligible question rows at all
        with self.assertRaisesRegex(ValueError, "Only 0 question"):
            generate_practice_paper(ALLOWED_TOPICS, 1)


if __name__ == "__main__":
    unittest.main()
