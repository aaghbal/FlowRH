"""
log_handlers.py

Logging handlers referenced from LOGGING in horilla/settings.py.
"""

import logging.handlers


class WatchedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    RotatingFileHandler that reopens its file when it was deleted, replaced, or
    rotated by another process. Passenger runs several worker processes on the
    same log: without this, the workers that did not rotate (or every worker,
    once the file is deleted by hand) keep writing into a file that is no longer
    on disk, and the visible log stays empty.
    """

    _statstream = logging.handlers.WatchedFileHandler._statstream
    reopenIfNeeded = logging.handlers.WatchedFileHandler.reopenIfNeeded

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dev, self.ino = -1, -1
        self._statstream()

    def emit(self, record):
        self.reopenIfNeeded()
        super().emit(record)
