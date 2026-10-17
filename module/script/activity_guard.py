"""Activity accounting and rests at explicit task checkpoints (no game input)."""
from datetime import datetime, timedelta
from contextlib import contextmanager
from pathlib import Path
import random
import re
import sqlite3
import time

from module.logger import logger


class ActivityStore:
    """Transactional deltas, isolated by config; runtime data is never configuration."""

    def __init__(self, path, name):
        self.path = Path(path)
        self.name = name

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute('CREATE TABLE IF NOT EXISTS daily (name TEXT, day TEXT, seconds REAL, PRIMARY KEY(name, day))')
            db.execute('CREATE TABLE IF NOT EXISTS cycle (name TEXT PRIMARY KEY, seconds REAL, rest_until TEXT)')
            with db:
                yield db
        finally:
            db.close()

    def add(self, start, end, seconds):
        # Use monotonic elapsed time; split it proportionally at local midnight.
        span = (end - start).total_seconds()
        pieces = []
        if span <= 0:
            pieces.append((end.date().isoformat(), seconds))
        else:
            cursor = start
            while cursor < end:
                boundary = datetime.combine(cursor.date() + timedelta(days=1), datetime.min.time())
                stop = min(end, boundary)
                pieces.append((cursor.date().isoformat(), seconds * (stop - cursor).total_seconds() / span))
                cursor = stop
        with self.connect() as db:
            for day, amount in pieces:
                db.execute('INSERT INTO daily VALUES (?, ?, ?) ON CONFLICT(name, day) DO UPDATE SET seconds=seconds+excluded.seconds',
                           (self.name, day, amount))
            db.execute('INSERT INTO cycle VALUES (?, ?, NULL) ON CONFLICT(name) DO UPDATE SET seconds=seconds+excluded.seconds',
                       (self.name, seconds))

    def read(self, now):
        with self.connect() as db:
            daily = db.execute('SELECT seconds FROM daily WHERE name=? AND day=?',
                               (self.name, now.date().isoformat())).fetchone()
            cycle = db.execute('SELECT seconds, rest_until FROM cycle WHERE name=?', (self.name,)).fetchone()
        return (daily[0] if daily else 0, cycle[0] if cycle else 0,
                datetime.fromisoformat(cycle[1]) if cycle and cycle[1] else None)

    def schedule_rest(self, until):
        with self.connect() as db:
            db.execute('INSERT INTO cycle VALUES (?, 0, ?) ON CONFLICT(name) DO UPDATE SET seconds=0, rest_until=excluded.rest_until',
                       (self.name, until.isoformat()))


class ActivityGuard:
    def __init__(self, config, name, *, refresh=lambda: None, now=datetime.now,
                 monotonic=time.monotonic, sleep=time.sleep, path=None):
        self.config = config
        self.refresh = refresh
        self.now, self.monotonic, self.sleep = now, monotonic, sleep
        self.store = ActivityStore(path or Path(__file__).resolve().parents[2] / 'config/activity/runtime.sqlite3', name)
        self.active = False
        self.pending = False
        self.reset_continuous()

    @staticmethod
    def parse_interval(value):
        match = re.fullmatch(r'\s*(\d+)\s*[,，]\s*(\d+)\s*', str(value))
        if match is None:
            raise ValueError(f'Invalid continuous task rest interval: {value!r}')
        lower, upper = map(int, match.groups())
        if not 0 < lower <= upper:
            raise ValueError(f'Invalid continuous task rest interval: {value!r}')
        return lower, upper

    @staticmethod
    def sample_rest():
        minutes = random.triangular(2, 8, 5) if random.random() < .9 else random.triangular(8, 20, 8)
        return max(120, min(1200, round(minutes * 60)))

    def reset_continuous(self):
        self.continuous_seconds = 0
        self.interval = None
        self.continuous_limit = None
        self.continuous_until = None

    def start(self):
        self.wall, self.mono = self.now(), self.monotonic()
        self.active = True

    def tick(self, force=False):
        if not self.active:
            return
        mono = self.monotonic()
        elapsed = max(0, mono - self.mono)
        if not force and elapsed < 5:
            return
        now = self.now()
        if self.config().script.anti_ban.enable and elapsed:
            self.store.add(self.wall, now, elapsed)
        self.continuous_seconds += elapsed
        self.wall, self.mono = now, mono
        self.pending = self.deadline(now, schedule=False) is not None

    def finish(self):
        try:
            self.tick(force=True)
        finally:
            self.active = False

    def deadline(self, now, schedule=True):
        cfg = self.config().script
        deadlines = []
        ab = cfg.anti_ban
        if ab.enable:
            start, end, current = ab.sleep_start, ab.sleep_end, now.time()
            inside = start <= current < end if start < end else (current >= start or current < end)
            if start != end and inside:
                wake = datetime.combine(now.date(), end)
                if wake <= now:
                    wake += timedelta(days=1)
                deadlines.append(wake)
            daily, cycle, rest = self.store.read(now)
            limit = ab.daily_runtime_limit.total_seconds()
            if limit > 0 and daily >= limit:
                deadlines.append(datetime.combine(now.date() + timedelta(days=1), datetime.min.time()))
            if rest and rest > now:
                deadlines.append(rest)
            elif ab.daily_active_limit.total_seconds() > 0 and cycle >= ab.daily_active_limit.total_seconds():
                # Preserve legacy cumulative-run-then-rest semantics, independent of daily total.
                duration = ab.long_rest_duration.total_seconds()
                if duration > 0:
                    rest = now + timedelta(seconds=duration)
                    if schedule:
                        self.store.schedule_rest(rest)
                    deadlines.append(rest)
        device = cfg.device
        if device.continuous_task_rest_enable:
            try:
                interval = self.parse_interval(device.continuous_task_rest_interval)
            except ValueError:
                interval = (60, 120)
            if self.interval != interval:
                self.interval = interval
                self.continuous_limit = random.randint(*interval) * 60
            if self.continuous_until and self.continuous_until > now:
                deadlines.append(self.continuous_until)
            elif self.continuous_seconds >= self.continuous_limit:
                if schedule:
                    self.continuous_until = now + timedelta(seconds=self.sample_rest())
                    self.continuous_seconds = 0
                    self.continuous_limit = random.randint(*interval) * 60
                    deadlines.append(self.continuous_until)
                else:
                    deadlines.append(now + timedelta(seconds=1))
        else:
            self.reset_continuous()
        return max(deadlines) if deadlines else None

    def checkpoint(self):
        """Caller must discard its old screenshot after True. Never called mid-battle."""
        self.tick(force=True)
        was_active = self.active
        waited = False
        try:
            while True:
                self.refresh()
                now = self.now()
                until = self.deadline(now)
                if until is None:
                    self.pending = False
                    return waited
                if not waited:
                    logger.info(f'Activity guard: pause at safe checkpoint until {until}')
                waited = True
                self.active = False  # Rests never count as task execution.
                self.sleep(min(1, max(0, (until - now).total_seconds())))
        finally:
            if was_active:
                self.start()
