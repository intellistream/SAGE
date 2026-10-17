from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys

import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkJournal


def test_process_exit_before_atomic_commit_leaves_no_partial_turn(tmp_path):
    path = str(tmp_path / "state.db")
    script = '''
import os, sys
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkJournal
store = StatefulProcessRuntime(backend="sqlite", sqlite_path=sys.argv[1])
journal = WorkJournal(store, namespace="tenant")
journal.commit("previous", result="kept", tasks={"work": 1})
original = store._backend._put_uncommitted
def crash(slot, entry):
    original(slot, entry)
    os._exit(37)
store._backend._put_uncommitted = crash
journal.commit("interrupted", result="must-not-leak", tasks={"work": 2})
'''
    child = subprocess.run([sys.executable, "-c", script, path], timeout=15,
                           capture_output=True, text=True)
    assert child.returncode == 37, child.stderr
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        journal = WorkJournal(store, namespace="tenant")
        rows, _ = journal.records()
        assert [row["key"] for row in rows] == ["previous"]
        assert rows[0]["value"]["result"] == "kept"
        assert journal.claim("previous", "work", lease_seconds=30) is not None
    finally:
        store.close()


def test_atomic_commit_conflicts_recovery_and_fencing(tmp_path):
    path = str(tmp_path / "state.db")
    now = [10.0]
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = WorkJournal(store, namespace="tenant-a", clock=lambda: now[0])
    journal.commit("turn", result={"answer": "full answer"}, tasks={"memory": {"turn": "text"}})
    lease = journal.claim("turn", "memory", lease_seconds=5)
    assert lease.attempt == 1
    assert journal.claim("turn", "memory", lease_seconds=5) is None
    store.close()  # Simulate a worker disappearing before acknowledging.

    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = WorkJournal(store, namespace="tenant-a", clock=lambda: now[0])
    try:
        assert journal.records()[0][0]["value"]["result"]["answer"] == "full answer"
        now[0] = 16.0
        replacement = journal.claim("turn", "memory", lease_seconds=5)
        assert replacement.attempt == 2
        with pytest.raises(ValueError, match="stale_task_lease"):
            journal.finish(lease)
        journal.finish(replacement)
        record = journal.commit("turn", result={"answer": "full answer"}, tasks={"memory": {"turn": "text"}})
        assert record["tasks"]["memory"]["status"] == "done"
        with pytest.raises(ValueError, match="journal_commit_conflict"):
            journal.commit("turn", result="changed", tasks={})
        assert journal.claim("turn", "memory", lease_seconds=5) is None
    finally:
        store.close()


def test_only_one_connection_claims_a_task(tmp_path):
    path = str(tmp_path / "state.db")
    stores = [StatefulProcessRuntime(backend="sqlite", sqlite_path=path) for _ in range(2)]
    journals = [WorkJournal(store, namespace="tenant") for store in stores]
    try:
        journals[0].commit("turn", result="answer", tasks={"work": 1})
        with ThreadPoolExecutor(max_workers=2) as workers:
            claims = list(workers.map(lambda journal: journal.claim("turn", "work", lease_seconds=30), journals))
        assert sum(claim is not None for claim in claims) == 1
    finally:
        for store in stores:
            store.close()


def test_renewal_cannot_resurrect_expired_lease(tmp_path):
    now = [0.0]
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(store, namespace="tenant", clock=lambda: now[0])
    try:
        journal.commit("turn", result="answer", tasks={"work": 1})
        lease = journal.claim("turn", "work", lease_seconds=10)
        now[0] = 9.0
        journal.renew(lease, lease_seconds=10)
        now[0] = 11.0
        assert journal.claim("turn", "work", lease_seconds=10) is None
        now[0] = 19.0
        with pytest.raises(ValueError, match="stale_task_lease"):
            journal.renew(lease, lease_seconds=10)
        with pytest.raises(ValueError, match="stale_task_lease"):
            journal.finish(lease)
        assert journal.claim("turn", "work", lease_seconds=10).attempt == 2
    finally:
        store.close()


def test_retry_namespace_and_invalid_payload_do_not_lose_work(tmp_path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(store, namespace="a")
    other = WorkJournal(store, namespace="b")
    try:
        with pytest.raises(ValueError):
            journal.commit("bad", result="answer", tasks={"task": float("nan")})
        assert journal.records()[0] == []
        journal.commit("turn", result="answer", tasks={"work": 1})
        lease = journal.claim("turn", "work", lease_seconds=30)
        with pytest.raises(ValueError, match="namespace_mismatch"):
            other.finish(lease)
        journal.finish(lease, retry=True)
        replacement = journal.claim("turn", "work", lease_seconds=30)
        assert replacement.attempt == 2
        assert other.records()[0] == []
        with pytest.raises(ValueError, match="stale_task_lease"):
            journal.finish(lease)
    finally:
        store.close()
