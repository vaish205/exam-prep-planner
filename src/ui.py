"""Small Streamlit helpers shared by the CRUD pages (no business logic here)."""

import mysql.connector
import streamlit as st

from src.logger import get_logger

logger = get_logger(__name__)


def flash(message, kind="success"):
    """Remember a message so it can be shown after st.rerun().

    kind is "success" (green, the default), "warning" (yellow) or "info" (blue).
    """
    st.session_state["flash_message"] = (kind, message)


def show_flash():
    saved = st.session_state.pop("flash_message", None)
    if saved:
        kind, message = saved
        if kind == "warning":
            st.warning(message)
        elif kind == "info":
            st.info(message)
        else:
            st.success(message)


def load_or_stop(loader):
    """Call loader(); if the database fails, show a friendly error and stop the page."""
    try:
        return loader()
    except mysql.connector.Error as error:
        logger.error("Database error: %s", error)
        st.error(f"Database problem: {error}. Check your .env file and run 'python init_db.py'.")
        st.stop()


def fresh_key(name):
    """Widget key that changes after clear_field(name), which empties that input."""
    return f"{name}_{st.session_state.get(name + '_version', 0)}"


def clear_field(name):
    st.session_state[name + "_version"] = st.session_state.get(name + "_version", 0) + 1
