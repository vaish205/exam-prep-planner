"""Tests for GATE PYQ ingestion (Milestone 4). Run from the project root:

    python -m unittest -v

Uses the real database from your .env (run 'python init_db.py' first). Every
test question's text starts with 'TEST_', and only those rows are removed
afterward, so real ingested data is never touched.
"""

import io
import unittest

from src.db import execute, fetch_all
from src.pyq_ingestion import (
    clean_question,
    clean_topic,
    ingest_csv,
    load_csv,
    normalize_question,
    normalize_topic,
    validate_columns,
)


def clean_up():
    execute("DELETE FROM pyq_questions WHERE question LIKE %s", ("TEST\\_%",))


def csv_file(text):
    """A file-like object, the same shape pandas gets from st.file_uploader."""
    return io.StringIO(text)


def test_questions():
    return [row for row in fetch_all("SELECT * FROM pyq_questions") if row["question"].startswith("TEST_")]


class CleaningAndNormalizationTests(unittest.TestCase):
    """Pure-Python checks - no database needed."""

    def test_clean_question_strips_and_collapses_whitespace(self):
        self.assertEqual(clean_question("  What   is\tOS?\n"), "What is OS?")

    def test_clean_question_handles_missing_values(self):
        self.assertIsNone(clean_question(float("nan")))
        self.assertIsNone(clean_question("   "))  # blank after stripping

    def test_clean_question_converts_non_string_values_safely(self):
        self.assertEqual(clean_question(42), "42")

    def test_clean_topic_strips_whitespace(self):
        self.assertEqual(clean_topic("  Operating Systems  "), "Operating Systems")

    def test_normalize_question_matches_the_spec_example(self):
        self.assertEqual(normalize_question(" What is   OS? "), normalize_question("What is OS?"))
        self.assertEqual(normalize_question("What is OS?"), "what is os?")


class TopicNormalizationTests(unittest.TestCase):
    """Pure-Python checks for matching messy CSV topic values to one of the
    8 canonical topics - no database needed."""

    def test_exact_canonical_topics_still_match(self):
        for topic in [
            "Computer Networks", "Operating Systems", "Mathematics", "General Aptitude",
            "Programming/Data Structures", "Computer Organization and Architecture",
            "Digital Logic", "Theory of Computation",
        ]:
            self.assertEqual(normalize_topic(topic), topic)

    def test_capitalization_differences(self):
        self.assertEqual(normalize_topic("computer networks"), "Computer Networks")
        self.assertEqual(normalize_topic("COMPUTER NETWORKS"), "Computer Networks")

    def test_leading_and_trailing_whitespace(self):
        self.assertEqual(normalize_topic("  Computer Networks  "), "Computer Networks")

    def test_repeated_spaces(self):
        self.assertEqual(normalize_topic("Computer    Networks"), "Computer Networks")

    def test_underscore_and_hyphen_formatting(self):
        self.assertEqual(normalize_topic("Computer_Networks"), "Computer Networks")
        self.assertEqual(normalize_topic("Computer-Networks"), "Computer Networks")

    def test_dataset_equivalent_wording_for_programming_data_structures(self):
        self.assertEqual(normalize_topic("Programming and Data Structures"), "Programming/Data Structures")
        self.assertEqual(normalize_topic("programming_and_data_structures"), "Programming/Data Structures")
        self.assertEqual(normalize_topic("Programming & Data Structures"), "Programming/Data Structures")

    def test_real_dataset_singular_wordings(self):
        # The actual GATE CSV uses "Operating System" and "Programming and
        # Data Structure" (singular), not the plural canonical forms.
        self.assertEqual(normalize_topic("Operating System"), "Operating Systems")
        self.assertEqual(normalize_topic("Programming and Data Structure"), "Programming/Data Structures")

    def test_genuinely_unknown_topic_is_still_rejected(self):
        self.assertIsNone(normalize_topic("Database Management Systems"))
        self.assertIsNone(normalize_topic("Not A Real Topic"))
        self.assertIsNone(normalize_topic(""))

    def test_missing_topic_is_rejected(self):
        self.assertIsNone(normalize_topic(None))


class ValidateColumnsTests(unittest.TestCase):
    def test_missing_required_column_raises(self):
        df = load_csv(csv_file("Topic\nOperating Systems\n"))
        with self.assertRaisesRegex(ValueError, "Question"):
            validate_columns(df)

    def test_present_columns_pass(self):
        df = load_csv(csv_file("Topic,Question\nOperating Systems,What is OS?\n"))
        validate_columns(df)  # should not raise


class IngestionTests(unittest.TestCase):
    def setUp(self):
        clean_up()

    def tearDown(self):
        clean_up()

    def test_valid_csv_is_ingested(self):
        csv_text = (
            "Topic,Question\n"
            "Computer Networks,TEST_What is a subnet mask?\n"
            "Operating Systems,TEST_What is a deadlock?\n"
        )
        result = ingest_csv(csv_file(csv_text))

        self.assertEqual(result["rows_read"], 2)
        self.assertEqual(result["inserted"], 2)
        self.assertEqual(result["invalid_rows"], 0)
        self.assertEqual(result["duplicate_count"], 0)
        self.assertEqual(
            result["topic_counts"], {"Computer Networks": 1, "Operating Systems": 1}
        )
        self.assertEqual(len(test_questions()), 2)

    def test_missing_question_is_skipped_not_inserted(self):
        csv_text = "Topic,Question\nMathematics,\nMathematics,TEST_What is a matrix?\n"
        result = ingest_csv(csv_file(csv_text))

        self.assertEqual(result["rows_read"], 2)
        self.assertEqual(result["missing_question_count"], 1)
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(len(test_questions()), 1)

    def test_invalid_topic_is_skipped_not_inserted(self):
        csv_text = "Topic,Question\nNot A Real Topic,TEST_What is this?\n"
        result = ingest_csv(csv_file(csv_text))

        self.assertEqual(result["invalid_topic_count"], 1)
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(test_questions(), [])

    def test_messy_topic_formatting_is_still_ingested_under_the_canonical_name(self):
        csv_text = (
            "Topic,Question\n"
            "computer networks,TEST_What is a router?\n"                    # lowercase
            "  Operating Systems  ,TEST_What is a semaphore?\n"             # padded
            "Digital_Logic,TEST_What is a flip-flop?\n"                     # underscore
            "Computer-Organization-and-Architecture,TEST_What is a bus?\n"  # hyphens
            "Programming and Data Structures,TEST_What is a linked list?\n" # equivalent wording
        )
        result = ingest_csv(csv_file(csv_text))

        self.assertEqual(result["invalid_topic_count"], 0)
        self.assertEqual(result["inserted"], 5)
        topics = {row["question"]: row["topic"] for row in test_questions()}
        self.assertEqual(topics["TEST_What is a router?"], "Computer Networks")
        self.assertEqual(topics["TEST_What is a semaphore?"], "Operating Systems")
        self.assertEqual(topics["TEST_What is a flip-flop?"], "Digital Logic")
        self.assertEqual(topics["TEST_What is a bus?"], "Computer Organization and Architecture")
        self.assertEqual(topics["TEST_What is a linked list?"], "Programming/Data Structures")

    def test_duplicate_within_the_same_file_is_only_inserted_once(self):
        csv_text = (
            "Topic,Question\n"
            "Digital Logic,TEST_What is a flip-flop?\n"
            "Digital Logic,  TEST_What   is   a  flip-flop?  \n"  # same after normalizing
        )
        result = ingest_csv(csv_file(csv_text))

        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["duplicate_count"], 1)
        self.assertEqual(len(test_questions()), 1)

    def test_uploading_the_same_csv_twice_does_not_duplicate_rows(self):
        csv_text = "Topic,Question\nTheory of Computation,TEST_What is a Turing machine?\n"

        first = ingest_csv(csv_file(csv_text))
        second = ingest_csv(csv_file(csv_text))

        self.assertEqual(first["inserted"], 1)
        self.assertEqual(second["inserted"], 0)
        self.assertEqual(second["duplicate_count"], 1)
        self.assertEqual(len(test_questions()), 1)

    def test_correct_inserted_row_count_with_a_mixed_file(self):
        csv_text = (
            "Topic,Question\n"
            "Computer Networks,TEST_What is OSI model?\n"      # valid, unique
            "Operating Systems,\n"                              # missing question
            "Not A Real Topic,TEST_Some question\n"             # invalid topic
            "Mathematics,TEST_What is OSI model?\n"              # duplicate of row 1
            "Digital Logic,  TEST_What   is   Digital Logic?  \n"  # valid, unique
            "Theory of Computation,TEST_What is a Turing machine?\n"  # valid, unique
        )
        result = ingest_csv(csv_file(csv_text))

        self.assertEqual(result["rows_read"], 6)
        self.assertEqual(result["missing_question_count"], 1)
        self.assertEqual(result["invalid_topic_count"], 1)
        self.assertEqual(result["duplicate_count"], 1)
        self.assertEqual(result["inserted"], 3)
        self.assertEqual(len(test_questions()), 3)

    def test_very_long_question_is_ingested_and_still_deduplicated(self):
        # Real GATE questions can run past 1000 characters. This must not
        # crash, truncate, or fail to be recognized as a duplicate the
        # second time it appears.
        long_question = "TEST_" + ("This is a very long GATE-style question. " * 40)
        csv_text = f"Topic,Question\nMathematics,{long_question}\nMathematics,{long_question}\n"

        result = ingest_csv(csv_file(csv_text))

        self.assertGreater(len(long_question), 500)
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["duplicate_count"], 1)
        stored = test_questions()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["question"], long_question.strip())


if __name__ == "__main__":
    unittest.main()
