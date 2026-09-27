"""Command-line database connection test.  Run:  python check_db.py"""

import sys

from src.db import test_connection

ok, message = test_connection()
print(("OK: " if ok else "FAILED: ") + message)
sys.exit(0 if ok else 1)
