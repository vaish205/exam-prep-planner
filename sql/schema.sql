-- Exam Prep Planner schema (safe to run more than once)

CREATE TABLE IF NOT EXISTS subjects (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS topics (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    subject_id INT NOT NULL,
    name       VARCHAR(150) NOT NULL,
    difficulty ENUM('Easy', 'Medium', 'Hard') NOT NULL DEFAULT 'Medium',
    UNIQUE (subject_id, name),
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS exams (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    subject_id INT NOT NULL,
    name       VARCHAR(150) NOT NULL,
    exam_date  DATE NOT NULL,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

-- One row per planned study session for a topic on a date (see src/schedule.py
-- for how these are generated, and src/dashboard.py for the pending/done summary).
CREATE TABLE IF NOT EXISTS study_tasks (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    topic_id         INT NOT NULL,
    task_date        DATE NOT NULL,
    duration_minutes INT NOT NULL,
    status           ENUM('Pending', 'Done') NOT NULL DEFAULT 'Pending',
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

-- GATE CSE previous-year questions, imported from a CSV (Topic, Question columns).
-- normalized_question is a cleaned, lowercased copy used only to catch duplicates.
-- Real questions can be very long (some are 1000+ characters), and MySQL can't put
-- a UNIQUE index directly on an unbounded TEXT column, so normalized_question_hash
-- stores a fixed-length SHA-256 fingerprint of normalized_question instead - the
-- UNIQUE constraint on that hash is what stops the same question being stored
-- twice, even if the same CSV is imported more than once.
-- occurrence_count (added for Milestone 5's repeated-question analysis): since the
-- UNIQUE constraint means a repeated question is never stored as a second row,
-- this column is what remembers that it appeared more than once. It defaults to 1
-- and only ever changes during ingestion (see src/pyq_ingestion.py).
CREATE TABLE IF NOT EXISTS pyq_questions (
    id                       INT AUTO_INCREMENT PRIMARY KEY,
    topic                    ENUM(
                                 'Computer Networks',
                                 'Operating Systems',
                                 'Mathematics',
                                 'General Aptitude',
                                 'Programming/Data Structures',
                                 'Computer Organization and Architecture',
                                 'Digital Logic',
                                 'Theory of Computation'
                             ) NOT NULL,
    question                 TEXT NOT NULL,
    normalized_question      TEXT NOT NULL,
    normalized_question_hash CHAR(64) NOT NULL,
    occurrence_count         INT NOT NULL DEFAULT 1,
    created_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_pyq_normalized_question_hash (normalized_question_hash)
);
