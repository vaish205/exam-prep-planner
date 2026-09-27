"""PYQ-Aware Study Plan: a simple, transparent, frequency-based recommendation
of how much study attention each topic might deserve, based only on how many
PYQs exist for it in the already-ingested pyq_questions table.

This is NOT a prediction of exam importance or difficulty - it only reflects
how many practice questions happen to be available per topic. Reuses
src/pyq_analysis.py for all the underlying counts/percentages instead of
duplicating that SQL.
"""

from src.pyq_analysis import get_topic_counts, get_total_question_count

# With 8 canonical topics, an even split works out to 100 / 8 = 12.5% each.
# These thresholds are centered on that natural average rather than an
# arbitrary number: at/above the average -> High, up to 1 point below it ->
# Medium, more than 1 point below -> Low. Simple, documented, and explainable
# in an interview: "High means at-or-above an even split; Low means clearly
# under-represented compared to the other topics."
HIGH_FOCUS_THRESHOLD = 12.5
MEDIUM_FOCUS_THRESHOLD = 11.5


def _classify(percentage):
    """High/Medium/Low, purely from a topic's share of total questions."""
    if percentage >= HIGH_FOCUS_THRESHOLD:
        return "High"
    if percentage >= MEDIUM_FOCUS_THRESHOLD:
        return "Medium"
    return "Low"


def get_topic_study_recommendations():
    """One entry per canonical topic (always all 8, in a fixed order):
    {"topic", "question_count", "percentage", "recommended_focus"}.

    recommended_focus is deterministic - purely a function of percentage
    (see _classify) - and never anything stronger than High/Medium/Low; this
    reflects how many PYQs are available per topic, not how important or
    difficult that topic actually is.
    """
    total = get_total_question_count()
    recommendations = []
    for row in get_topic_counts():
        percentage = round(row["count"] / total * 100, 2) if total else 0.0
        recommendations.append(
            {
                "topic": row["topic"],
                "question_count": row["count"],
                "percentage": percentage,
                "recommended_focus": _classify(percentage),
            }
        )
    return recommendations
