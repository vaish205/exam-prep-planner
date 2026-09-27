# Exam Prep Planner

A simple **study-planning and GATE CSE PYQ analysis application** built as a portfolio project for a Cloud Data Engineer Trainee role.

The project combines **Python, Streamlit, MySQL, Pandas, SQL, data validation, automated testing, and data analysis** into one end-to-end application.

## Features

- 📚 **Subject & Topic Management** — Create, edit, and delete subjects and topics
- 🗓️ **Exam Management** — Manage exam dates and deadlines
- 📅 **Automated Study Schedule** — Generate study tasks based on topic difficulty and upcoming exams
- 📥 **PYQ CSV Ingestion** — Import and validate a real GATE CSE question dataset
- 🧹 **Data Cleaning & Normalization** — Clean question text and normalize topic labels
- 🔍 **Duplicate Detection** — Detect repeated questions using normalized text and SHA-256 hashing
- 📊 **PYQ Analysis** — View topic-wise question counts, percentages, and repeated questions
- 📝 **Practice Paper Generator** — Generate random practice papers from ingested questions
- 🎯 **PYQ-Based Study Focus** — Generate simple frequency-based topic recommendations
- 📈 **Dashboard** — Combine PYQ statistics, study focus, exams, and schedule information
- 🧪 **Automated Testing** — 85 tests with 0 failures

---

## Tech Stack

| Technology | Purpose |
|---|---|
| **Python** | Application logic and data processing |
| **Streamlit** | Web application UI |
| **MySQL** | Relational database |
| **Pandas** | CSV processing and data cleaning |
| **SQL** | Data storage and analysis |
| **unittest** | Automated testing |
| **logging** | Application logging |

---

## Architecture

```text
             GATE CSE PYQ CSV
                    │
                    ▼
                Pandas
                    │
                    ▼
        Validation & Cleaning
                    │
                    ▼
          Topic Normalization
                    │
                    ▼
                 MySQL
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
   Python Logic          SQL Analysis
          │                   │
          └─────────┬─────────┘
                    ▼
                Streamlit
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
      Schedule   Practice   Dashboard
                  Papers
