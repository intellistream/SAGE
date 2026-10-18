"""Real SQLite contention during the first open of a persistent runtime."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from types import SimpleNamespace

import pytest

from sage.runtime.flownet.runtime.operator_runtime import stateful


def test_first_open_waits_for_actual_wal_lock_and_preserves_state(tmp_path, monkeypatch):
    path = str(tmp_path / "state.db")
    writer = sqlite3.connect(path)
    writer.execute("BEGIN EXCLUSIVE")
    busy = Event()
    failures = []
    connect = sqlite3.connect

    class ObservedConnection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            try:
                return super().execute(sql, *args, **kwargs)
            except sqlite3.OperationalError as error:
                if sql == "PRAGMA journal_mode=WAL":
                    failures.append(error)
                    busy.set()
                raise

    def observed_connect(*args, **kwargs):
        # Ensure the actual SQLite operation reports contention immediately.
        # This deliberately exercises the WAL retry, not SQLite's busy handler.
        kwargs.update(timeout=0, factory=ObservedConnection)
        return connect(*args, **kwargs)

    monkeypatch.setattr(stateful.sqlite3, "connect", observed_connect)
    with ThreadPoolExecutor(max_workers=1) as pool:
        opening = pool.submit(stateful.StatefulProcessRuntime, backend="sqlite", sqlite_path=path)
        try:
            assert busy.wait(5), "fixture did not produce an actual SQLite WAL lock"
        finally:
            writer.rollback()
            writer.close()
        runtime = opening.result(timeout=10)
    try:
        assert failures
        assert runtime._backend._conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert runtime._backend._conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        runtime.update(("fixture", "owner", "value"), lambda _: "durable")
    finally:
        runtime.close()
    reopened = stateful.StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        assert reopened.peek(("fixture", "owner", "value")) == "durable"
    finally:
        reopened.close()


def test_wal_lock_deadline_closes_connection_and_retains_original_error(tmp_path, monkeypatch):
    path = str(tmp_path / "state.db")
    writer = sqlite3.connect(path)
    writer.execute("BEGIN EXCLUSIVE")
    connect = sqlite3.connect
    opened = []
    clock = [0.0]
    sleeps = []

    def sleep(delay):
        assert 0 < delay <= 0.1
        sleeps.append(delay)
        clock[0] += delay

    def observed_connect(*args, **kwargs):
        kwargs["timeout"] = 0
        connection = connect(*args, **kwargs)
        opened.append(connection)
        return connection

    monkeypatch.setattr(stateful.sqlite3, "connect", observed_connect)
    monkeypatch.setattr(stateful, "time", SimpleNamespace(time=lambda: 0, monotonic=lambda: clock[0], sleep=sleep))
    try:
        with pytest.raises(sqlite3.OperationalError) as raised:
            stateful.StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
        assert raised.value.sqlite_errorcode & 0xFF == sqlite3.SQLITE_BUSY
        assert sleeps, "startup lock was not retried"
        assert clock[0] == pytest.approx(5.0)
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            opened[0].execute("SELECT 1")
    finally:
        writer.rollback()
        writer.close()


def test_non_lock_initialization_error_is_not_retried_and_closes_connection(tmp_path, monkeypatch):
    path = tmp_path / "not-a-database.db"
    path.write_bytes(b"not a SQLite database" * 100)
    connect = sqlite3.connect
    opened = []

    def observed_connect(*args, **kwargs):
        connection = connect(*args, **kwargs)
        opened.append(connection)
        return connection

    def unexpected_sleep(delay):
        pytest.fail("non-lock database error was retried")

    monkeypatch.setattr(stateful.sqlite3, "connect", observed_connect)
    monkeypatch.setattr(stateful, "time", SimpleNamespace(time=lambda: 0, monotonic=lambda: 0, sleep=unexpected_sleep))
    with pytest.raises(sqlite3.DatabaseError, match="not a database"):
        stateful.StatefulProcessRuntime(backend="sqlite", sqlite_path=str(path))
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        opened[0].execute("SELECT 1")


def test_independent_cold_connections_preserve_all_atomic_updates(tmp_path):
    path = str(tmp_path / "state.db")
    barrier = Barrier(8)
    slot = ("fixture", "owner", "counter")

    def update():
        barrier.wait(timeout=10)
        runtime = stateful.StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
        try:
            for _ in range(10):
                runtime.update(slot, lambda value: (value or 0) + 1)
        finally:
            runtime.close()

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(update) for _ in range(8)]
        for future in futures:
            future.result(timeout=20)
    reopened = stateful.StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        assert reopened.peek(slot) == 80
    finally:
        reopened.close()
