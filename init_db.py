"""Create the database tables from sql/schema.sql.  Run:  python init_db.py"""

import sys
from pathlib import Path

import mysql.connector

from src.db import get_connection

SCHEMA_FILE = Path(__file__).parent / "sql" / "schema.sql"

# Columns added to a table after it was first created. CREATE TABLE IF NOT
# EXISTS (in schema.sql) only helps on a brand-new database - on a database
# that already has an older version of the table, it's a no-op, so we check
# for and add any missing columns here instead. Safe to run any number of
# times: a column already present is simply skipped.
COLUMNS_ADDED_LATER = {
    "pyq_questions": [
        ("occurrence_count", "INT NOT NULL DEFAULT 1"),
    ],
}


def _add_missing_columns(cursor):
    for table, columns in COLUMNS_ADDED_LATER.items():
        cursor.execute(
            "SELECT COLUMN_NAME FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = %s",
            (table,),
        )
        existing = {row[0] for row in cursor.fetchall()}
        for column_name, column_definition in columns:
            if column_name not in existing:
                print(f"Adding missing column {table}.{column_name} ...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_definition}")


def main():
    # Drop comment lines, then split the file into one statement per ";"
    lines = SCHEMA_FILE.read_text(encoding="utf-8").splitlines()
    sql_text = "\n".join(line for line in lines if not line.strip().startswith("--"))
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]

    try:
        connection = get_connection()
        cursor = connection.cursor()
        for statement in statements:
            cursor.execute(statement)
        _add_missing_columns(cursor)
        connection.commit()
        cursor.execute("SHOW TABLES")
        print("Tables in database:", ", ".join(row[0] for row in cursor.fetchall()))
        cursor.close()
        connection.close()
    except mysql.connector.Error as error:
        print(f"FAILED: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
