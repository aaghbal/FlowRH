"""
scheduler_guard.py

Whether this process should run the APScheduler background jobs.

Every app that has a scheduler starts it at import time, so under a WSGI server
each worker process gets its own copy: the jobs then run once per worker rather
than once, and several of them run on a 20 to 25 second interval. On a shared
host that is enough to exhaust the database connections and to leave PyMySQL
connections being used by two threads at once, which surfaces as
"Packet sequence number wrong" and InterfaceError(0, '').

Set RUN_SCHEDULERS=True in .env for the single process that should own them --
a management command or a worker started on purpose -- and leave it unset
everywhere else. Unset means off, because the safe default is not to run them.
"""

import os
import sys

# Commands that only touch the schema or open a shell have no business starting
# background jobs, whatever RUN_SCHEDULERS says.
_EXCLUDED_COMMANDS = (
    "makemigrations",
    "migrate",
    "compilemessages",
    "flush",
    "shell",
    "collectstatic",
    "createsuperuser",
    "test",
)

_TRUTHY = {"1", "true", "yes", "on"}


def schedulers_enabled():
    """True when this process should start the background schedulers."""
    if any(cmd in sys.argv for cmd in _EXCLUDED_COMMANDS):
        return False
    return os.environ.get("RUN_SCHEDULERS", "").strip().lower() in _TRUTHY
