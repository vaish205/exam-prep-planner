# Exam Prep Planner

## 1. Project Overview

Exam Prep Planner is a study-planning application built for a Cloud Data
Engineer Trainee portfolio project. It manages subjects, topics and exam
deadlines; turns them into an automated daily study schedule; imports a real
GATE CSE previous-year-questions (PYQ) dataset from a CSV; performs
descriptive SQL analysis over that dataset; and uses it to generate random
practice papers and a simple, frequency-based study-focus recommendation. A
dashboard brings the scheduling and PYQ data together in one view.

The project was built milestone by milestone (M1 through M8) and this
milestone (M9) is a stabilization pass - final testing, light logging,
cleanup, and documentation - with no new user-facing features.

## 2. Tech Stack

- **Python** - application logic, plain functions, no ORM
- **Streamlit** - the web UI (one file per page, under `pages/`)
- **MySQL** (or MariaDB) - persistent storage, accessed with parameterized SQL
- **Pandas** - reading and cleaning the PYQ CSV
- **unittest** (standard library) - the whole test suite
- **logging** (standard library) - the only logging in the project; no
  external logging framework

## 3. Architecture

```
Streamlit UI  (pages/*.py)
      |
Python application logic  (src/*.py)
      |
MySQL  (parameterized SQL, no ORM)
```

Each page is UI only: it calls plain functions in `src/`, which run
parameterized SQL through the small set of helpers in `src/db.py`
(`fetch_all`, `execute`, `execute_many`). No page writes SQL directly, and no
module outside `src/db.py` opens its own database connection.

## 4. Features

- **Subjects / Topics / Exams** - CRUD screens (create, list, edit, delete)
  with basic validation (empty fields, invalid or past dates, a controlled
  difficulty value)
- **Automated Study Schedule** - generates `study_tasks` from your topics,
  their difficulty, and your exam dates, spread across the available days,
  with a Done/Pending toggle
- **GATE PYQ CSV Ingestion** - imports a real 2,400-question GATE CSE
  dataset, cleans and validates it, and stores it with duplicate detection
- **PYQ Analysis** - descriptive statistics over the ingested questions:
  totals, per-topic counts/percentages, and repeated questions
- **Practice Paper Generator** - a random paper of real, already-ingested
  questions for chosen topics
- **PYQ-Aware Study Plan** - a simple, rule-based per-topic focus suggestion
  based purely on how many PYQs exist for that topic
- **Dashboard** - one page combining the PYQ statistics, study focus,
  upcoming exams, and schedule summary

## 5. Database / Data Flow

Five tables: `subjects`, `topics`, `exams`, `study_tasks`, and
`pyq_questions` (see `sql/schema.sql` for exact columns; `topics.difficulty`
and `pyq_questions.topic` are both fixed `ENUM` values, not free text).
`init_db.py` creates them from `schema.sql` and is safe to run more than
once - on a database that already has an older version of a table, it adds
any missing columns instead of failing.

The PYQ side of the app follows one straight pipeline, detailed in section 6.

## 6. GATE PYQ CSV Ingestion

The **PYQ Ingestion** page imports the GATE CSE Question Classification
Dataset: 2,400 questions, each labeled with one of 8 fixed topics (Computer
Networks, Operating Systems, Mathematics, General Aptitude,
Programming/Data Structures, Computer Organization and Architecture, Digital
Logic, Theory of Computation).

> **Dataset limitation**: this CSV has no year column, so the app performs
> no year-wise analysis anywhere - only topic and question text are used.

**CSV format** - exactly two columns:
```
Topic,Question
Operating Systems,What is a deadlock?
Computer Networks,What is a subnet mask?
```

**Flow**: CSV → Pandas → validate columns → clean each row's text (trim
whitespace, collapse repeated spaces, handle missing values) → normalize the
topic (case, whitespace, underscores/hyphens, a couple of known equivalent
wordings like "Operating System" → "Operating Systems") against the 8 fixed
values → build a lowercase `normalized_question` for duplicate detection →
insert with parameterized SQL → report statistics. Nothing is written to the
database until you click **Start Ingestion** - uploading or previewing a
file never inserts rows on its own.

**Duplicates**: two questions are duplicates if they're identical after
trimming, collapsing whitespace and lowercasing (no fuzzy matching). The
`pyq_questions` table has a `UNIQUE` constraint on a SHA-256 hash of the
normalized text (some real questions run past 1,000 characters, too long for
a normal unique index), so uploading the same CSV twice never creates a
second row for the same question - instead, that row's `occurrence_count`
goes up by one.

**Run it**: `streamlit run app.py`, open **PYQ Ingestion**, upload the CSV,
check the preview and validation counts, then click **Start Ingestion**.
Actual result from the real 2,400-row dataset (verified in this milestone,
without re-running ingestion):
```
Rows read: 2400   Inserted: 2302   Invalid rows: 0   Duplicates: 98
```

## 7. PYQ Analysis

The **PYQ Analysis** page (`pages/6_PYQ_Analysis.py`, backed by
`src/pyq_analysis.py`) reads the already-ingested `pyq_questions` table and
shows, read-only: total question count, a question-count and percentage
breakdown across all 8 canonical topics (purely descriptive, not a
best/worst ranking), and every question whose `occurrence_count` is greater
than 1, most-repeated first.

Actual current values in the real database (2,302 unique questions from one
clean ingestion of the 2,400-row CSV):

| Metric | Value |
|---|---|
| Total questions | 2,302 |
| Repeated questions | 90 |
| Extra occurrences | 98 |

## 8. Practice Paper Generator

The **Practice Paper** page (`pages/7_Practice_Paper.py`, backed by
`src/practice_paper.py`) lets you pick one or more topics and a number of
questions, then filters `pyq_questions` to those topics with a parameterized
`WHERE topic IN (...)` query and picks that many at random (Python's
`random.sample`, so no repeats within one paper) from the real,
already-ingested questions - nothing is invented, and generating a paper
never changes the database. Asking for more than exist for the selected
topics shows a clear error instead of silently returning fewer.

## 9. PYQ-Aware Study Plan

`src/study_plan.py`'s `get_topic_study_recommendations()` reuses
`pyq_analysis.py`'s existing counts/percentages (no new SQL) and, for each of
the 8 canonical topics, adds a `recommended_focus` of **High**, **Medium** or
**Low**, using one fixed, documented rule: with 8 topics, an even split is
100/8 = 12.5% each, so **High** means at-or-above that even share (≥12.5%),
**Medium** means just under it (≥11.5% and <12.5%), and **Low** means
clearly under-represented (<11.5%).

This is a **frequency-based recommendation only** - how many PYQs happen to
exist per topic in the dataset. It is **not** a prediction of actual exam
weightage, importance, or difficulty, and the app never claims otherwise.

## 10. Dashboard

The **Dashboard** page (`pages/8_Dashboard.py`) brings the PYQ statistics and
the scheduling data together in one place: total questions / repeated
questions / extra occurrences / topic count at the top, then topic
distribution, the PYQ-based study focus table, upcoming exams (reusing
`src/exams.py`), and a study-schedule summary (reusing `src/schedule.py`).
`src/dashboard.py` adds no SQL of its own - it only reuses `list_exams()` and
`list_tasks()` and filters the results in Python. Each section shows a plain
message (e.g. *"No PYQ data available yet"*, *"No upcoming exams added
yet"*, *"No study tasks available yet"*) instead of breaking the page when
that section has no data.

## 11. Testing

```bash
python -m unittest -v
```
**85 tests, 0 failures** (verified in this milestone). Coverage: CRUD (9),
schedule generation (14), PYQ ingestion (24), PYQ analysis (12), practice
paper (12), study plan (8), dashboard (6). Tests that touch the real
database only create and remove rows whose names start with `TEST_`;
`test_practice_paper.py`, `test_study_plan.py` and `test_dashboard.py` mock
the database entirely and never touch it.

## 12. Setup Instructions

1. Create the database in MySQL (once):
   ```sql
   CREATE DATABASE exam_prep_planner;
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # macOS / Linux:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create your settings file and fill in your own MySQL details (never
   commit the real `.env` - it's already in `.gitignore`):
   ```bash
   # Windows: copy .env.example .env
   cp .env.example .env
   ```
5. Create the tables (safe to run again any time):
   ```bash
   python init_db.py
   ```

## 13. How to Run

```bash
python check_db.py        # optional: test the database connection
streamlit run app.py      # open http://localhost:8501
```
Use the sidebar to open **Subjects**, **Topics**, **Exams**, **Schedule**,
**PYQ Ingestion**, **PYQ Analysis**, **Practice Paper** and **Dashboard**.

A small log of backend activity (database errors, ingestion results,
schedule/paper generation) is written to `app.log` in the project root and
also printed to the console - plain `logging` module, nothing external, and
it never logs passwords or `.env` contents.

## 14. Project Structure

```
app.py              Streamlit home page
requirements.txt     Python dependencies (streamlit, mysql-connector-python, python-dotenv, pandas)
pages/               One Streamlit page per screen (UI only)
  1_Subjects.py
  2_Topics.py
  3_Exams.py
  4_Schedule.py
  5_PYQ_Ingestion.py
  6_PYQ_Analysis.py
  7_Practice_Paper.py
  8_Dashboard.py
src/                 Application logic and SQL
  db.py              MySQL connection + small helpers (fetch_all, execute, execute_many)
  logger.py          Shared logging setup (standard library only)
  subjects.py        Subject add / list / update / delete
  topics.py          Topic add / list / update / delete
  exams.py           Exam add / list / update / delete
  schedule.py        Study-schedule generation and status updates
  pyq_ingestion.py   GATE PYQ CSV loading, cleaning, normalization and insert
  pyq_analysis.py    Topic distribution and repeated-question statistics
  practice_paper.py  Random practice-paper generation from ingested questions
  study_plan.py      Frequency-based per-topic study-focus recommendation
  dashboard.py       Dashboard aggregation helpers (reuses exams.py / schedule.py)
  validation.py      Empty-text and date checks
  ui.py              Small Streamlit helpers (messages, error handling, DB-error logging)
sql/schema.sql       Table definitions
init_db.py           Creates the tables from schema.sql (safe to re-run; adds any missing columns)
check_db.py          Command-line connection test
recompute_pyq_occurrence_counts.py   One-time repair tool - see its docstring
tests/
  test_crud.py           CRUD tests
  test_schedule.py       Schedule generation and status-toggle tests
  test_pyq_ingestion.py  PYQ ingestion tests
  test_pyq_analysis.py   PYQ analysis tests
  test_practice_paper.py Practice paper generation tests (mocked database)
  test_study_plan.py     Study-plan recommendation tests (mocked database)
  test_dashboard.py      Dashboard aggregation-helper tests (mocked database)
.env.example         Template for MySQL settings (no real credentials)
```

## 15. How to Explain This Project

> The application uses Streamlit for the user interface, Python modules for
> business logic, and MySQL for persistent storage. CSV-based GATE questions
> are loaded with Pandas, cleaned and normalized, validated against the
> allowed topics, and stored in MySQL. The application then performs
> descriptive SQL analysis and uses the stored questions to generate
> practice papers and a simple study recommendation.

**Data flow:**
```
CSV
  |
Pandas
  |
Validation / Cleaning
  |
MySQL
  |
SQL Analysis
  |
Streamlit Dashboard / Practice Paper
```

**What this project is not**: there is no AI, machine learning, or
prediction model anywhere in it. The study-focus recommendation is a fixed,
documented percentage threshold, not a trained model. Nothing here is
real-time (PYQ data updates only when you re-ingest a CSV) or
"production-ready" in the enterprise sense - it's a deliberately simple,
fully explainable Streamlit + MySQL application.
