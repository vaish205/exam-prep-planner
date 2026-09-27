"""Database helper: reads MySQL settings from .env and opens connections."""

import os

import mysql.connector
from dotenv import load_dotenv

# Read the .env file (if present) into environment variables.
load_dotenv()


def get_connection():
    """Open and return a new MySQL connection using settings from .env."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "exam_prep_planner"),
        connection_timeout=5,
    )


def test_connection():
    """Try to connect and run a tiny query.

    Returns (True, message) on success or (False, error message) on failure,
    so callers (Streamlit page or command line) can simply print the message.
    """
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE(), VERSION()")
        database_name, version = cursor.fetchone()
        cursor.close()
        connection.close()
        return True, f"Connected to database '{database_name}' (MySQL/MariaDB {version})"
    except mysql.connector.Error as error:
        return False, f"Could not connect to MySQL: {error}"


def fetch_all(sql, params=()):
    """Run a SELECT and return all rows as a list of dictionaries.

    Values are passed separately in `params` (never pasted into the SQL text),
    which is what makes the query safe from SQL injection.
    """
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        connection.close()


def execute(sql, params=()):
    """Run an INSERT / UPDATE / DELETE, save (commit) it, and return the row count."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        connection.commit()
        row_count = cursor.rowcount
        cursor.close()
        return row_count
    finally:
        connection.close()


def execute_many(sql, params_list):
    """Run the same INSERT / UPDATE / DELETE for many rows in one connection,
    save (commit) it, and return the total row count."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.executemany(sql, params_list)
        connection.commit()
        row_count = cursor.rowcount
        cursor.close()
        return row_count
    finally:
        connection.close()
