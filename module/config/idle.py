"""Idle scheduling contract. Task adapters opt in only after providing safe exits.

Never infer completion from TaskEnd, a screenshot, or the mere presence of limits.
Adapters call idle_checkpoint after rewards and implement their own cleanup.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import time
import uuid
import json
from threading import Lock

from module.exception import TaskEnd
from tasks.SixRealms.config import idle_limits as six_realms_limits
from tasks.Chess.config import idle_limits as chess_limits, idle_natural_goal as chess_natural_goal


TIMED = '定时执行'
IDLE = '闲时执行'
DAILY = '每日目标'
WEEKLY = '每周目标'
SESSION = '本次目标'
TIME_FIELDS = {'next_run', 'success_interval', 'failure_interval', 'server_update',
               'server_update_am', 'server_update_pm', 'kirin_time', 'netherworld_time',
               'delay_date', 'float_time', 'saturday_time'}
IDLE_FIELDS = {'idle_goal', 'idle_start_minutes', 'idle_stop_minutes'}

# task key -> adapter(configured task model) -> (count limit, seconds limit).
# Register here as tasks receive reward checkpoints and task-specific safe cleanup.
# A UI switch alone cannot make a task resumable.
ADAPTERS = {'six_realms': six_realms_limits, 'chess': chess_limits}
# Explicit natural completion permits (0, 0); never fake a huge numeric limit.
NATURAL_GOALS = {'chess': chess_natural_goal}

_SCHEMA_LOCK = Lock()
_SCHEMA_READY = {}


class IdleYield(TaskEnd):
    """A safe idle exit; carries no normal task success/failure scheduling."""


def limits_for(key, model):
    adapter = ADAPTERS.get(key)
    if adapter is None:
        return None
    count, seconds = adapter(model)
    count, seconds = max(0, int(count or 0)), max(0, float(seconds or 0))
    natural = NATURAL_GOALS.get(key)
    return (count, seconds) if count or seconds or (natural and natural(model)) else None


class IdleStore:
    def __init__(self, name, path=None):
        self.name = name
        self.path = Path(path or Path(__file__).resolve().parents[2] / 'config/activity/idle.sqlite3')

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        try:
            # Config/IdleStore instances are reconstructed by overview queries.
            # Share only schema readiness, never live progress/session data.
            stamp = self.path.stat()
            identity = (stamp.st_dev, stamp.st_ino)
            path = str(self.path.resolve())
            with _SCHEMA_LOCK:
                if _SCHEMA_READY.get(path) != identity or stamp.st_size == 0:
                    with db:
                        self._create_schema(db)
                    _SCHEMA_READY[path] = identity
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _create_schema(db):
        db.execute('CREATE TABLE IF NOT EXISTS sessions (name TEXT PRIMARY KEY, token TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS goals ('
                   'name TEXT, task TEXT, scope TEXT, period TEXT, count INTEGER, seconds REAL, '
                   'done INTEGER, retry TEXT, PRIMARY KEY(name, task, scope, period))')
        db.execute('CREATE TABLE IF NOT EXISTS task_blocks ('
                   'name TEXT, task TEXT, until_time TEXT, reason TEXT, PRIMARY KEY(name,task))')
        db.execute('CREATE TABLE IF NOT EXISTS task_state ('
                   'name TEXT, task TEXT, data TEXT, PRIMARY KEY(name,task))')

    def session(self, *, reset=False):
        with self.connect() as db:
            return self._session(db, reset=reset)

    def _session(self, db, *, reset=False):
        if reset:
            db.execute('DELETE FROM sessions WHERE name=?', (self.name,))
        row = db.execute('SELECT token FROM sessions WHERE name=?', (self.name,)).fetchone()
        if row is None:
            db.execute('INSERT OR IGNORE INTO sessions VALUES (?, ?)', (self.name, uuid.uuid4().hex))
            row = db.execute('SELECT token FROM sessions WHERE name=?', (self.name,)).fetchone()
        return row[0]

    def period(self, scope, now):
        # Shared default: local calendar day, Monday 00:00. Task-specific game
        # refresh boundaries can be supplied by a later adapter.
        if scope == DAILY:
            return now.date().isoformat()
        if scope == WEEKLY:
            return (now.date() - timedelta(days=now.weekday())).isoformat()
        return self.session()

    def read(self, task, scope, period):
        with self.connect() as db:
            row = db.execute('SELECT count, seconds, done, retry FROM goals '
                             'WHERE name=? AND task=? AND scope=? AND period=?',
                             (self.name, task, scope, period)).fetchone()
        return self._goal_state(row)

    @staticmethod
    def _goal_state(row):
        return dict(count=row[0], seconds=row[1], done=bool(row[2]),
                    retry=datetime.fromisoformat(row[3]) if row[3] else None) if row else dict(
                        count=0, seconds=0., done=False, retry=None)

    def snapshot(self, scopes, now):
        """One connection for all overview goals/blocks; no cached runtime data."""
        if not scopes:
            return {}, {}
        with self.connect() as db:
            session = self._session(db) if SESSION in scopes.values() else None
            periods = {key: session if scope == SESSION else self.period(scope, now)
                       for key, scope in scopes.items()}
            clause = ' OR '.join('(task=? AND scope=? AND period=?)' for _ in scopes)
            args = [self.name]
            for key, scope in scopes.items():
                args.extend((key, scope, periods[key]))
            rows = db.execute('SELECT task, count, seconds, done, retry FROM goals '
                              f'WHERE name=? AND ({clause})', args).fetchall()
            states = {key: self._goal_state(None) for key in scopes}
            states.update((row[0], self._goal_state(row[1:])) for row in rows)
            placeholders = ','.join('?' for _ in scopes)
            rows = db.execute('SELECT task, until_time, reason FROM task_blocks '
                              f'WHERE name=? AND task IN ({placeholders})',
                              [self.name, *scopes]).fetchall()
            blocks = {key: dict(until=datetime.fromisoformat(until), reason=reason)
                      for key, until, reason in rows if datetime.fromisoformat(until) > now}
        return states, blocks

    def add(self, task, scope, period, *, count=0, seconds=0, done=False, retry=None):
        with self.connect() as db:
            db.execute('INSERT INTO goals VALUES (?, ?, ?, ?, ?, ?, ?, ?) '
                       'ON CONFLICT(name,task,scope,period) DO UPDATE SET '
                       'count=count+excluded.count, seconds=seconds+excluded.seconds, '
                       'done=MAX(done,excluded.done), retry=excluded.retry',
                       (self.name, task, scope, period, count, seconds, int(done),
                        retry.isoformat() if retry else None))

    def block(self, task, until, reason):
        """Task-wide inhibition, independent of goal scope, sessions, or mode."""
        with self.connect() as db:
            db.execute('INSERT INTO task_blocks VALUES (?, ?, ?, ?) '
                       'ON CONFLICT(name,task) DO UPDATE SET '
                       'until_time=MAX(until_time,excluded.until_time), reason=excluded.reason',
                       (self.name, task, until.isoformat(), reason))

    def blocked(self, task, now):
        with self.connect() as db:
            row = db.execute('SELECT until_time, reason FROM task_blocks WHERE name=? AND task=?',
                             (self.name, task)).fetchone()
        if row and datetime.fromisoformat(row[0]) > now:
            return dict(until=datetime.fromisoformat(row[0]), reason=row[1])
        return None

    def read_task_state(self, task):
        with self.connect() as db:
            row = db.execute('SELECT data FROM task_state WHERE name=? AND task=?',
                             (self.name, task)).fetchone()
        return json.loads(row[0]) if row else {}

    def update_task_state(self, task, **values):
        with self.connect() as db:
            row = db.execute('SELECT data FROM task_state WHERE name=? AND task=?',
                             (self.name, task)).fetchone()
            data = json.loads(row[0]) if row else {}
            data.update(values)
            db.execute('INSERT INTO task_state VALUES (?, ?, ?) '
                       'ON CONFLICT(name,task) DO UPDATE SET data=excluded.data',
                       (self.name, task, json.dumps(data)))


def reached(state, limits):
    count, seconds = limits
    return state['done'] or (count > 0 and state['count'] >= count) or (
        seconds > 0 and state['seconds'] >= seconds)


def select_idle(config, now, normal_pending, normal_waiting):
    """Read-only selection shared by execution and overview; never runs adapters."""
    from module.config.capabilities import unavailable_reason
    store = config.idle_store
    statuses, candidates = [], []
    next_time = min((t.next_run for t in normal_waiting), default=None)
    models = {key: getattr(config.model, key) for key in config.model.model_fields
              if not unavailable_reason(key)
              and getattr(getattr(config.model, key), 'scheduler', None) is not None
              and getattr(config.model, key).scheduler.enable
              and getattr(config.model, key).scheduler.execution_mode == IDLE}
    states, blocks = store.snapshot({key: model.scheduler.idle_goal for key, model in models.items()}, now)
    for key, model in models.items():
        scheduler = model.scheduler
        scope = scheduler.idle_goal
        state = states[key]
        limits = limits_for(key, model)
        blocked = blocks.get(key)
        if blocked:
            status = blocked['reason']
        elif limits is None:
            status = '待适配' if key not in ADAPTERS else '未设置有效目标限制'
        elif reached(state, limits):
            status = '目标完成'
        elif state['retry'] and state['retry'] > now:
            status = '失败冷却'
        elif normal_pending or (next_time and (next_time - now).total_seconds() <= scheduler.idle_start_minutes * 60):
            status = '等待空档'
        else:
            status = '可执行'
            candidates.append(key)
        statuses.append(dict(name=config.model.type(key), status=status,
                             goal=scope, count=state['count'], seconds=state['seconds'],
                             count_limit=limits[0] if limits else None,
                             seconds_limit=limits[1] if limits else None,
                             resume_at=str(blocked['until']) if blocked else None))
    candidates.sort(key=lambda key: getattr(config.model, key).scheduler.priority)
    return candidates, statuses


class IdleExecution:
    """One running fragment; counts are deltas committed only at safe checkpoints."""
    def __init__(self, config, key, *, now=datetime.now, monotonic=time.monotonic):
        self.config, self.key = config, key
        self.now, self.monotonic = now, monotonic
        self.store = config.idle_store
        self.scope = self.scheduler.idle_goal
        self.period = self.store.period(self.scope, now())
        self.last_tick = monotonic()
        self.wait_seconds = 0.
        self.config_path = Path(__file__).resolve().parents[2] / 'config' / f'{config.config_name}.json'
        self.config_stamp = self.config_path.stat().st_mtime_ns if self.config_path.exists() else None

    @property
    def scheduler(self):
        return getattr(self.config.model, self.key).scheduler

    @property
    def progress(self):
        return self.store.read(self.key, self.scope, self.period)

    def exclude_wait(self, seconds):
        self.wait_seconds += max(0, seconds)

    def record(self, count=0):
        if not isinstance(count, int) or count < 0:
            raise ValueError('完成次数增量必须为非负整数')
        tick = self.monotonic()
        seconds = max(0, tick - self.last_tick - self.wait_seconds)
        self.store.add(self.key, self.scope, self.period, count=count, seconds=seconds)
        self.last_tick, self.wait_seconds = tick, 0.

    def decision(self):
        scheduler = self.scheduler
        if not scheduler.enable or scheduler.execution_mode != IDLE or scheduler.idle_goal != self.scope:
            return '配置已更改'
        blocked = self.store.blocked(self.key, self.now())
        if blocked:
            return blocked['reason']
        limits = limits_for(self.key, getattr(self.config.model, self.key))
        if limits is None:
            return '目标适配不可用'
        if reached(self.progress, limits):
            self.store.add(self.key, self.scope, self.period, done=True)
            return '目标完成'
        if self.period != self.store.period(self.scope, self.now()):
            return '目标周期已刷新'
        # Refresh normal queue after invitations, scheduling edits, and task calls.
        self.config.update_scheduler()
        if self.config.normal_pending_task:
            return '普通任务已到期'
        next_time = min((t.next_run for t in self.config.normal_waiting_task), default=None)
        if next_time and (next_time - self.now()).total_seconds() <= scheduler.idle_stop_minutes * 60:
            return '已到让位余量'
        return None

    def checkpoint(self, task, *, completed=0, goal_complete=False):
        """Caller guarantees rewards drained and provides idle_return_to_main()."""
        self.record(completed)
        self.refresh_config()
        if goal_complete:
            self.store.add(self.key, self.scope, self.period, done=True)
        reason = self.decision()
        if reason is None:
            return False
        self.yield_task(task, reason)

    def refresh_config(self):
        if self.config_stamp is not None:
            stamp = self.config_path.stat().st_mtime_ns
            if stamp != self.config_stamp:
                self.config.reload()
                self.config_stamp = stamp

    def yield_task(self, task, reason, *, retry_seconds=None):
        task.idle_return_to_main()
        self.config.task_runtime_outcome = {'task': self.config.model.type(self.key),
                                            'status': 'idle_yield', 'reason': reason}
        if retry_seconds is not None:
            retry = self.now() + timedelta(seconds=retry_seconds)
            self.config.task_runtime_outcome['idle_retry_until'] = retry
            self.store.add(self.key, self.scope, self.period, retry=retry)
        raise IdleYield(reason)

    def finish(self):
        # Failed fragments consume runtime too, but never fabricate completed rounds.
        self.record()
        outcome = self.config.__dict__.get('task_runtime_outcome') or {}
        if outcome.get('status') == 'idle_yield' and outcome.get('idle_retry_until'):
            self.store.add(self.key, self.scope, self.period, retry=outcome['idle_retry_until'])
        elif outcome.get('status') != 'idle_yield':
            self.store.add(self.key, self.scope, self.period, retry=self.now() + timedelta(minutes=1))
