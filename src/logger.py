"""Small shared logging setup - standard library only, no external framework.

Any module that wants to log something calls get_logger(__name__). Configured
once, here, so every module's log lines share the same format and go to the
same place: the console, plus app.log in the project root. Never logs
credentials, .env contents, or question/answer content - just what happened
and, on failure, the exception message.
"""

import logging
from pathlib import Path

_LOG_FILE = Path(__file__).resolve().parent.parent / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.FileHandler(_LOG_FILE), logging.StreamHandler()],
)

# The mysql-connector-python library logs its own internal connection/auth
# chatter at INFO level (never credential values, but noisy and not this
# app's own activity) - quiet it down to warnings and above.
logging.getLogger("mysql.connector").setLevel(logging.WARNING)


def get_logger(name):
    return logging.getLogger(name)
