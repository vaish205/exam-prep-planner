"""One-time repair for pyq_questions.occurrence_count.

Only needed if you re-uploaded an already-fully-ingested CSV to try to
recover historical duplicate counts (which incorrectly inflates every row's
count - see the note in src/pyq_ingestion.py:recompute_occurrence_counts).
This resets occurrence_count to the exact count found in the CSV you pass
it, instead of incrementing against whatever is already stored.

Usage (run once, from the project root):

    python recompute_pyq_occurrence_counts.py path\\to\\questions-data-new.csv

Safe to run more than once with the same file - it always SETS counts to
what's actually in the file, so it never double-counts.
"""

import sys

from src.pyq_ingestion import recompute_occurrence_counts


def main():
    if len(sys.argv) != 2:
        print("Usage: python recompute_pyq_occurrence_counts.py <path-to-csv>")
        sys.exit(1)

    result = recompute_occurrence_counts(sys.argv[1])
    print(f"Distinct questions found in file: {result['distinct_questions_in_file']}")
    print(f"Matching rows in pyq_questions updated: {result['questions_updated']}")


if __name__ == "__main__":
    main()
