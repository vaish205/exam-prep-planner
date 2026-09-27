"""Tests for the PYQ-aware study plan (Milestone 7). Run from the project
root:

    python -m unittest -v

These mock src.pyq_analysis.fetch_all directly - study_plan.py is a pure
read/compute layer on top of pyq_analysis.py, so there's no data of its own
to set up or clean up, and mocking keeps these tests independent of whatever
is actually in your database.
"""

import unittest
from unittest.mock import patch

from src.pyq_ingestion import ALLOWED_TOPICS
from src.study_plan import get_topic_study_recommendations


def mock_counts(counts_by_topic):
    """counts_by_topic: {topic: count}, missing topics default to 0.
    Returns the rows src.pyq_analysis.fetch_all would produce for
    'SELECT topic, COUNT(*) ... GROUP BY topic' (only non-zero topics)."""
    return [{"topic": t, "count": c} for t, c in counts_by_topic.items() if c > 0]


class StudyPlanTests(unittest.TestCase):
    @patch("src.pyq_analysis.fetch_all")
    def test_all_8_canonical_topics_are_represented(self, mock_fetch_all):
        mock_fetch_all.side_effect = [[{"count": 10}], mock_counts({"Mathematics": 10})]
        recommendations = get_topic_study_recommendations()
        self.assertEqual({row["topic"] for row in recommendations}, set(ALLOWED_TOPICS))
        self.assertEqual(len(recommendations), 8)

    @patch("src.pyq_analysis.fetch_all")
    def test_counts_are_correctly_calculated(self, mock_fetch_all):
        counts = {"Mathematics": 30, "Digital Logic": 70}
        mock_fetch_all.side_effect = [[{"count": 100}], mock_counts(counts)]
        recommendations = {row["topic"]: row for row in get_topic_study_recommendations()}
        self.assertEqual(recommendations["Mathematics"]["question_count"], 30)
        self.assertEqual(recommendations["Digital Logic"]["question_count"], 70)
        self.assertEqual(recommendations["General Aptitude"]["question_count"], 0)

    @patch("src.pyq_analysis.fetch_all")
    def test_percentages_are_correctly_calculated(self, mock_fetch_all):
        counts = {"Mathematics": 25, "Digital Logic": 75}
        mock_fetch_all.side_effect = [[{"count": 100}], mock_counts(counts)]
        recommendations = {row["topic"]: row for row in get_topic_study_recommendations()}
        self.assertEqual(recommendations["Mathematics"]["percentage"], 25.0)
        self.assertEqual(recommendations["Digital Logic"]["percentage"], 75.0)

    @patch("src.pyq_analysis.fetch_all")
    def test_recommendation_rule_is_deterministic_and_uses_the_documented_thresholds(self, mock_fetch_all):
        # Mathematics well above the 12.5% "even split" line -> High
        # Operating Systems between 11.5% and 12.5% -> Medium
        # everything else absorbs the remainder, clearly below 11.5% -> Low
        counts = {"Mathematics": 20, "Operating Systems": 12}
        remaining_topics = [t for t in ALLOWED_TOPICS if t not in counts]
        for topic in remaining_topics:
            counts[topic] = 68 // len(remaining_topics)
        total = sum(counts.values())
        mock_fetch_all.side_effect = [[{"count": total}], mock_counts(counts)]

        first_call = {row["topic"]: row["recommended_focus"] for row in get_topic_study_recommendations()}

        mock_fetch_all.side_effect = [[{"count": total}], mock_counts(counts)]
        second_call = {row["topic"]: row["recommended_focus"] for row in get_topic_study_recommendations()}

        self.assertEqual(first_call, second_call)  # same input -> same output, every time
        self.assertEqual(first_call["Mathematics"], "High")
        self.assertEqual(first_call["Operating Systems"], "Medium")
        for topic in remaining_topics:
            self.assertEqual(first_call[topic], "Low")

    @patch("src.pyq_analysis.fetch_all")
    def test_boundary_percentages_are_classified_correctly(self, mock_fetch_all):
        # Exactly on the documented thresholds
        counts = {"Mathematics": 125, "Operating Systems": 115}
        counts["Digital Logic"] = 1000 - sum(counts.values())
        mock_fetch_all.side_effect = [[{"count": 1000}], mock_counts(counts)]
        recommendations = {row["topic"]: row for row in get_topic_study_recommendations()}
        self.assertEqual(recommendations["Mathematics"]["percentage"], 12.5)
        self.assertEqual(recommendations["Mathematics"]["recommended_focus"], "High")
        self.assertEqual(recommendations["Operating Systems"]["percentage"], 11.5)
        self.assertEqual(recommendations["Operating Systems"]["recommended_focus"], "Medium")

    @patch("src.pyq_analysis.fetch_all")
    def test_empty_database_behavior(self, mock_fetch_all):
        mock_fetch_all.side_effect = [[{"count": 0}], []]
        recommendations = get_topic_study_recommendations()
        self.assertEqual(len(recommendations), 8)
        for row in recommendations:
            self.assertEqual(row["question_count"], 0)
            self.assertEqual(row["percentage"], 0.0)
            self.assertEqual(row["recommended_focus"], "Low")

    @patch("src.pyq_analysis.fetch_all")
    def test_no_unexpected_topic_is_returned(self, mock_fetch_all):
        # Even if the (mocked) database somehow returned a stray topic, the
        # canonical topic list is the single source of truth for what's
        # returned - get_topic_counts()/get_topic_percentages() only ever
        # report on ALLOWED_TOPICS.
        mock_fetch_all.side_effect = [[{"count": 5}], mock_counts({"Mathematics": 5})]
        recommendations = get_topic_study_recommendations()
        self.assertTrue(all(row["topic"] in ALLOWED_TOPICS for row in recommendations))

    @patch("src.pyq_analysis.fetch_all")
    def test_output_structure_has_the_expected_fields(self, mock_fetch_all):
        mock_fetch_all.side_effect = [[{"count": 10}], mock_counts({"Mathematics": 10})]
        for row in get_topic_study_recommendations():
            self.assertEqual(set(row.keys()), {"topic", "question_count", "percentage", "recommended_focus"})
            self.assertIn(row["recommended_focus"], {"High", "Medium", "Low"})


if __name__ == "__main__":
    unittest.main()
