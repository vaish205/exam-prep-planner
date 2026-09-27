"""Tests for PYQ Analysis (Milestone 5). Run from the project root:

    python -m unittest -v

Uses the real database from your .env. Every test question's text starts
with 'TEST_', and only those rows are removed afterward - the real ingested
GATE questions are never touched or deleted. Because these functions read
the *whole* pyq_questions table (that's the point of Milestone 5 - analyze
everything that's been ingested), tests compare before/after counts around
their own TEST_ rows instead of assuming the table starts empty.
"""

import io
import unittest
from unittest.mock import patch

from src.db import execute
from src.pyq_ingestion import (
    ALLOWED_TOPICS,
    ingest_csv,
    recompute_occurrence_counts,
)
from src.pyq_analysis import (
    get_extra_occurrence_count,
    get_repeated_question_count,
    get_repeated_questions,
    get_top_topic,
    get_topic_counts,
    get_topic_percentages,
    get_total_question_count,
)


def clean_up():
    execute("DELETE FROM pyq_questions WHERE question LIKE %s", ("TEST\\_%",))


def csv_file(text):
    return io.StringIO(text)


class TopicAnalysisTests(unittest.TestCase):
    """These add and then remove their own TEST_ rows, checking the *change*
    in the numbers rather than an absolute value - the table may already
    hold real, previously-ingested questions that must be left alone."""

    def setUp(self):
        clean_up()

    def tearDown(self):
        clean_up()

    def test_total_question_count_increases_by_exactly_the_rows_added(self):
        before = get_total_question_count()
        ingest_csv(csv_file("Topic,Question\nMathematics,TEST_Q1\nDigital Logic,TEST_Q2\n"))
        self.assertEqual(get_total_question_count(), before + 2)

    def test_topic_counts_cover_all_8_canonical_topics_in_a_fixed_order(self):
        counts = get_topic_counts()
        self.assertEqual([row["topic"] for row in counts], ALLOWED_TOPICS)
        # every count is a real number, never negative, and no stray topic sneaks in
        for row in counts:
            self.assertIsInstance(row["count"], int)
            self.assertGreaterEqual(row["count"], 0)

    def test_topic_counts_reflect_newly_ingested_rows_for_their_topic(self):
        before = {row["topic"]: row["count"] for row in get_topic_counts()}
        ingest_csv(csv_file("Topic,Question\nComputer Networks,TEST_A\nComputer Networks,TEST_B\n"))
        after = {row["topic"]: row["count"] for row in get_topic_counts()}
        self.assertEqual(after["Computer Networks"], before["Computer Networks"] + 2)
        # unrelated topics are untouched
        self.assertEqual(after["Mathematics"], before["Mathematics"])

    def test_topic_percentages_sum_to_100_and_match_their_counts(self):
        ingest_csv(csv_file("Topic,Question\nMathematics,TEST_Q1\nDigital Logic,TEST_Q2\n"))
        total = get_total_question_count()
        counts = {row["topic"]: row["count"] for row in get_topic_counts()}
        percentages = get_topic_percentages()

        self.assertEqual([row["topic"] for row in percentages], ALLOWED_TOPICS)
        for row in percentages:
            expected = round(counts[row["topic"]] / total * 100, 2)
            self.assertEqual(row["percentage"], expected)
        # allow a tiny rounding tolerance across 8 independently-rounded percentages
        self.assertAlmostEqual(sum(row["percentage"] for row in percentages), 100.0, delta=0.1)

    def test_top_topic_is_the_one_with_the_highest_count(self):
        if get_total_question_count() == 0:
            self.assertIsNone(get_top_topic())
            return
        counts = {row["topic"]: row["count"] for row in get_topic_counts()}
        expected = max(counts, key=counts.get)
        self.assertEqual(get_top_topic(), expected)

    def test_empty_database_gives_zero_percentages_and_no_top_topic(self):
        # Simulated, not real: the actual table (with real ingested questions)
        # is never truncated. This only checks the empty-table math is safe.
        with patch("src.pyq_analysis.get_total_question_count", return_value=0):
            percentages = get_topic_percentages()
            self.assertTrue(all(row["percentage"] == 0.0 for row in percentages))
            self.assertIsNone(get_top_topic())


class RepeatedQuestionTests(unittest.TestCase):
    def setUp(self):
        clean_up()

    def tearDown(self):
        clean_up()

    def test_a_question_ingested_twice_is_reported_as_repeated_with_count_2(self):
        before = get_repeated_question_count()
        ingest_csv(csv_file("Topic,Question\nTheory of Computation,TEST_What is a DFA?\n"))
        ingest_csv(csv_file("Topic,Question\nTheory of Computation,TEST_What is a DFA?\n"))

        self.assertEqual(get_repeated_question_count(), before + 1)
        test_rows = [r for r in get_repeated_questions() if r["question"].startswith("TEST_")]
        self.assertEqual(len(test_rows), 1)
        self.assertEqual(test_rows[0]["occurrence_count"], 2)
        self.assertEqual(test_rows[0]["topic"], "Theory of Computation")

    def test_repeated_within_a_single_file_is_also_counted(self):
        csv_text = "Topic,Question\nGeneral Aptitude,TEST_Repeat me\nGeneral Aptitude,TEST_Repeat me\n"
        ingest_csv(csv_file(csv_text))

        test_rows = [r for r in get_repeated_questions() if r["question"] == "TEST_Repeat me"]
        self.assertEqual(len(test_rows), 1)
        self.assertEqual(test_rows[0]["occurrence_count"], 2)

    def test_a_question_seen_only_once_is_not_reported_as_repeated(self):
        ingest_csv(csv_file("Topic,Question\nOperating Systems,TEST_Only once\n"))
        questions = [r["question"] for r in get_repeated_questions()]
        self.assertNotIn("TEST_Only once", questions)

    def test_repeated_questions_are_ordered_most_repeated_first(self):
        ingest_csv(csv_file(
            "Topic,Question\n"
            "Mathematics,TEST_Seen twice\n"
            "Mathematics,TEST_Seen twice\n"
            "Mathematics,TEST_Seen thrice\n"
            "Mathematics,TEST_Seen thrice\n"
            "Mathematics,TEST_Seen thrice\n"
        ))
        test_rows = [r for r in get_repeated_questions() if r["question"].startswith("TEST_")]
        self.assertEqual([r["question"] for r in test_rows], ["TEST_Seen thrice", "TEST_Seen twice"])

    def test_repeated_question_count_is_distinct_questions_not_total_occurrences(self):
        # "Seen twice" and "Seen thrice" are 2 DISTINCT repeated questions,
        # even though "Seen thrice" alone shows up 3 times. This is exactly
        # the distinction that was unclear on the page: repeated_question_count
        # must stay 2 here, not 3, and must never equal the total row count
        # just because more than one question happens to repeat.
        before_repeated = get_repeated_question_count()
        before_extra = get_extra_occurrence_count()
        before_total = get_total_question_count()

        ingest_csv(csv_file(
            "Topic,Question\n"
            "Mathematics,TEST_Seen twice\n"
            "Mathematics,TEST_Seen twice\n"
            "Digital Logic,TEST_Seen thrice\n"
            "Digital Logic,TEST_Seen thrice\n"
            "Digital Logic,TEST_Seen thrice\n"
            "General Aptitude,TEST_Seen once\n"  # not repeated - must not be counted
        ))

        self.assertEqual(get_repeated_question_count(), before_repeated + 2)
        # extra occurrences: 1 extra for "twice" + 2 extra for "thrice" = 3
        self.assertEqual(get_extra_occurrence_count(), before_extra + 3)
        # sanity: repeated count must never equal total count just because
        # more than one question repeated (would indicate the old bug: every
        # row counted as "repeated" instead of only rows with occurrence_count > 1)
        self.assertLess(get_repeated_question_count(), get_total_question_count())
        self.assertEqual(get_total_question_count(), before_total + 3)

    def test_recompute_occurrence_counts_fixes_a_bad_reingest_of_the_same_file(self):
        # Reproduces exactly the bug this test file was written for: ingest a
        # file once (only some questions repeat), then - simulating the
        # mistaken "re-upload the same file to recover counts" advice -
        # ingest_csv() the identical file again. Because every question is
        # already in the table, that second run treats ALL of them as
        # repeated, wrongly inflating occurrence_count for questions that
        # were only ever seen once in the source data.
        csv_text = (
            "Topic,Question\n"
            "Mathematics,TEST_Seen twice\n"
            "Mathematics,TEST_Seen twice\n"
            "General Aptitude,TEST_Seen once\n"
        )
        ingest_csv(csv_file(csv_text))
        ingest_csv(csv_file(csv_text))  # the mistaken "recovery" re-upload

        test_rows = {r["question"]: r for r in get_repeated_questions() if r["question"].startswith("TEST_")}
        # Bug reproduced: "Seen once" now wrongly shows as repeated too.
        self.assertIn("TEST_Seen once", test_rows)

        # The fix: recompute_occurrence_counts() resets counts to what the
        # original file actually contains, not what accumulated from re-runs.
        result = recompute_occurrence_counts(csv_file(csv_text))
        self.assertEqual(result["distinct_questions_in_file"], 2)

        rows_after = {
            r["question"]: r["occurrence_count"]
            for r in get_repeated_questions()
            if r["question"].startswith("TEST_")
        }
        self.assertEqual(rows_after, {"TEST_Seen twice": 2})  # "Seen once" no longer listed as repeated

        # Running the repair again with the same file is a no-op (idempotent)
        recompute_occurrence_counts(csv_file(csv_text))
        rows_again = {
            r["question"]: r["occurrence_count"]
            for r in get_repeated_questions()
            if r["question"].startswith("TEST_")
        }
        self.assertEqual(rows_again, rows_after)


if __name__ == "__main__":
    unittest.main()
