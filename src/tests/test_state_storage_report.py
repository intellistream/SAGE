import sqlite3
from dataclasses import asdict

import pytest

from sage.runtime.event_journal import EventJournal
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.state_storage_report import inspect_sqlite_state
from sage.runtime.work_journal import WorkJournal


def test_report_preserves_replay_and_omits_content(tmp_path, monkeypatch):
    path = tmp_path / "state?#.sqlite3"
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(path))
    events = EventJournal(store, namespace="private-name")
    work = WorkJournal(store, namespace="private-work")
    try:
        events.append("secret-id", event_id="answer", payload="private answer", terminal=True)
        work.commit("secret-request", result="private result", tasks={})
        before = events.read("secret-id")
        with sqlite3.connect(path) as db:
            expected = db.execute("SELECT COUNT(*), SUM(length(value_blob)), MAX(length(value_blob)) FROM state_entries").fetchone()
        report = inspect_sqlite_state(path)
        assert (report.entries, report.payload_bytes, report.largest_payload_bytes) == expected
        assert all(type(value) is int and value >= 0 for value in asdict(report).values())
        assert report.allocated_page_bytes >= report.reusable_page_bytes
        assert events.read("secret-id") == before
        assert work.read("secret-request")["result"] == "private result"
        # Age alone is not permission to discard completed work or event replay.
        with monkeypatch.context() as patch:
            patch.setattr("sage.runtime.work_journal.time.time", lambda: 10000000000)
            work.commit("new-request", result="new", tasks={})
            assert work.read("secret-request")["result"] == "private result"
            assert events.read("secret-id") == before
    finally:
        store.close()
    reopened = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(path))
    try:
        assert EventJournal(reopened, namespace="private-name").read("secret-id") == before
    finally:
        reopened.close()


def test_missing_database_is_not_created(tmp_path):
    path = tmp_path / "missing.sqlite3"
    with pytest.raises(FileNotFoundError):
        inspect_sqlite_state(path)
    assert not path.exists()


def test_invalid_schema_is_not_reported_as_empty(tmp_path):
    path = tmp_path / "other.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE other (value TEXT)")
    with pytest.raises(sqlite3.OperationalError):
        inspect_sqlite_state(path)


def test_blob_is_never_deserialized(tmp_path):
    path = tmp_path / "opaque.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE state_entries (value_blob BLOB)")
        db.execute("INSERT INTO state_entries VALUES (?)", (b"not a pickle",))
    report = inspect_sqlite_state(path)
    assert report.entries == 1
    assert report.payload_bytes == len(b"not a pickle")
