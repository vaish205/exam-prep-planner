"""Small input checks shared by the subjects, topics and exams modules."""

from datetime import date


def clean_text(value, field_name, max_length):
    """Trim spaces; reject empty or too-long text. Returns the cleaned text."""
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{field_name} cannot be empty.")
    if len(text) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters.")
    return text


def parse_date(value, field_name="Date"):
    """Accept a date or a 'YYYY-MM-DD' string; reject anything else."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            pass
    raise ValueError(f"{field_name} is not a valid date (use YYYY-MM-DD).")
