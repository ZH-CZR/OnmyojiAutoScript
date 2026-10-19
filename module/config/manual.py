"""One-shot frontend requests, shared by the server and scheduler process."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import uuid

MANUAL = '手动执行'
# Server-side copies of live child-process suspension snapshots, never config.
active_task_suspensions = {}


class ManualStore:
    def __init__(self, name, path=None):
        self.name = name
        self.path = Path(path or Path(__file__).resolve().parents[2] / 'config/activity/manual.sqlite3')

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute('CREATE TABLE IF NOT EXISTS requests '
                       '(name TEXT, task TEXT, token TEXT, PRIMARY KEY(name, task))')
            with db:
                yield db
        finally:
            db.close()

    def pending(self):
        if not self.path.exists():
            return {}
        with self.connect() as db:
            return dict(db.execute('SELECT task, token FROM requests WHERE name=? ORDER BY rowid', (self.name,)))

    def request(self, task):
        with self.connect() as db:
            # Repeated clicks while queued coalesce. A click during execution
            # gets a new token and cannot be erased by the previous run.
            db.execute('INSERT OR IGNORE INTO requests VALUES (?, ?, ?)',
                       (self.name, task, uuid.uuid4().hex))

    def consume(self, task, token):
        with self.connect() as db:
            return db.execute('DELETE FROM requests WHERE name=? AND task=? AND token=?',
                              (self.name, task, token)).rowcount == 1

    def clear(self, task=None):
        if not self.path.exists():
            return
        with self.connect() as db:
            if task is None:
                db.execute('DELETE FROM requests WHERE name=?', (self.name,))
            else:
                db.execute('DELETE FROM requests WHERE name=? AND task=?', (self.name, task))
