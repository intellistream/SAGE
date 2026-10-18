import os
import subprocess
import sys

import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkCapacityError, WorkJournal


def test_capacity_replay_finalizer_and_reopen(tmp_path):
    path = str(tmp_path / "state.db")
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = WorkJournal(state, namespace="test")
    journal.configure_capacity(max_active_requests=1)
    payload = dict(result="canonical", tasks={"answer": {}, "final": {}},
                   dependencies={"final": ["answer"]}, settled=["final"])
    journal.commit("a", **payload)
    assert journal.commit("a", **payload)["result"] == "canonical"
    with pytest.raises(WorkCapacityError):
        journal.commit("b", result=None, tasks={"answer": {}})
    assert journal.read("b") is None
    journal.cancel("a", "answer")
    with pytest.raises(WorkCapacityError):
        journal.commit("b", result=None, tasks={"answer": {}})
    lease = journal.claim("a", "final", lease_seconds=30)
    journal.finish(lease)
    state.close()
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        journal = WorkJournal(state, namespace="test")
        journal.commit("b", result=None, tasks={"answer": {}})
        assert journal.commit("a", **payload)["result"] == "canonical"
        assert [row["key"] for row in journal.active_records()[0]] == ["b"]
    finally:
        state.close()


def test_prepared_rejection_and_failed_destination_roll_back():
    state = StatefulProcessRuntime()
    journal = WorkJournal(state, namespace="test")
    journal.configure_capacity(max_active_requests=1)
    prepared = journal.prepare_commit("a", result=None, tasks={"answer": {}})
    destination = ("application", "test", "receipt")

    def broken(values):
        prepared.apply(values)
        raise RuntimeError("injected")

    with pytest.raises(RuntimeError, match="injected"):
        state.update_many((*prepared.slots, destination), broken)
    assert journal.read("a") is None
    journal.commit("b", result=None, tasks={"answer": {}})
    with pytest.raises(WorkCapacityError):
        state.update_many((*prepared.slots, destination),
                          lambda values: {**prepared.apply(values), destination: "receipt"})
    assert state.peek(destination) is None
    assert journal.read("a") is None
    state.close()


def test_offline_migration_preserves_backlog_and_rejects_too_small_limit():
    state = StatefulProcessRuntime()
    journal = WorkJournal(state, namespace="test")
    for key in ("a", "b"):
        journal.commit(key, result=key, tasks={"task": {}})
    with pytest.raises(WorkCapacityError, match="below_existing"):
        journal.configure_capacity(max_active_requests=1)
    assert journal.read("a")["version"] == 5
    journal.configure_capacity(max_active_requests=2)
    with pytest.raises(WorkCapacityError):
        journal.commit("c", result=None, tasks={"task": {}})
    lease = journal.claim("a", "task", lease_seconds=30)
    with pytest.raises(ValueError, match="live_leases"):
        journal.configure_capacity(max_active_requests=3)
    journal.finish(lease)
    journal.commit("c", result=None, tasks={"task": {}})
    assert journal.read("a")["result"] == "a"
    state.close()


def test_independent_processes_cannot_over_admit(tmp_path):
    path = str(tmp_path / "state.db")
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    WorkJournal(state, namespace="test").configure_capacity(max_active_requests=3)
    state.close()
    script = '''
import sys
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkJournal, WorkCapacityError
state = StatefulProcessRuntime(backend="sqlite", sqlite_path=sys.argv[1])
try:
    WorkJournal(state, namespace="test").commit(sys.argv[2], result=None, tasks={"task": {}})
except WorkCapacityError:
    sys.exit(2)
finally:
    state.close()
'''
    processes = [subprocess.Popen([sys.executable, "-c", script, path, str(i)],
                                  env=os.environ.copy()) for i in range(12)]
    try:
        codes = [process.wait(timeout=30) for process in processes]
        assert codes.count(0) == 3
        assert codes.count(2) == 9
        state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
        try:
            journal = WorkJournal(state, namespace="test")
            assert len(journal.active_records()[0]) == 3
            assert len(journal.records()[0]) == 3
        finally:
            state.close()
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait()


def test_process_exit_during_admission_does_not_leak_capacity(tmp_path):
    path = str(tmp_path / "state.db")
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    WorkJournal(state, namespace="test").configure_capacity(max_active_requests=1)
    state.close()
    script = '''
import os, sys
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkJournal
state = StatefulProcessRuntime(backend="sqlite", sqlite_path=sys.argv[1])
original = state._backend._put_uncommitted
def crash(slot, entry):
    original(slot, entry)
    if slot[0] == "sage-work-capacity-v1":
        os._exit(73)
state._backend._put_uncommitted = crash
WorkJournal(state, namespace="test").commit("aborted", result="answer", tasks={"task": {}})
'''
    result = subprocess.run([sys.executable, "-c", script, path], timeout=30, check=False)
    assert result.returncode == 73
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        journal = WorkJournal(state, namespace="test")
        assert journal.read("aborted") is None
        journal.commit("accepted", result="answer", tasks={"task": {}})
        with pytest.raises(WorkCapacityError):
            journal.commit("overflow", result=None, tasks={"task": {}})
    finally:
        state.close()


def test_missing_capacity_metadata_fails_closed():
    state = StatefulProcessRuntime()
    journal = WorkJournal(state, namespace="test")
    journal.configure_capacity(max_active_requests=1)
    journal.commit("a", result=None, tasks={"task": {}})
    state.delete(("sage-work-capacity-v1", "test", "policy"))
    with pytest.raises(ValueError, match="capacity_state_missing"):
        journal.claim("a", "task", lease_seconds=30)
    assert journal.read("a")["tasks"]["task"]["status"] == "pending"
    state.close()


def test_offline_disable_preserves_history_pending_work_and_reenable(tmp_path):
    path = str(tmp_path / "state.db")
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = WorkJournal(state, namespace="test")
    journal.configure_capacity(max_active_requests=2)
    journal.commit("done", result={"answer": "full original"}, tasks={"task": {"body": "full"}})
    journal.finish(journal.claim("done", "task", lease_seconds=30), result="side effect receipt")
    journal.commit("pending", result="canonical", tasks={"task": {"body": "not executed"}})
    before = {key: journal.read(key) for key in ("done", "pending")}
    journal.disable_capacity()
    journal.disable_capacity()
    assert state.peek(("sage-work-capacity-v1", "test", "policy")) is None
    for key, record in before.items():
        assert journal.read(key) == {**record, "version": 5}
    state.close()
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        journal = WorkJournal(state, namespace="test")
        assert [row["key"] for row in journal.active_records()[0]] == ["pending"]
        journal.configure_capacity(max_active_requests=1)
        with pytest.raises(WorkCapacityError):
            journal.commit("overflow", result=None, tasks={"task": {}})
        journal.finish(journal.claim("pending", "task", lease_seconds=30))
        assert journal.read("done")["result"] == {"answer": "full original"}
    finally:
        state.close()


def test_disable_rejects_live_lease_and_rolls_back_storage_failure(tmp_path, monkeypatch):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(state, namespace="test")
    journal.configure_capacity(max_active_requests=1)
    journal.commit("a", result="answer", tasks={"task": {}})
    lease = journal.claim("a", "task", lease_seconds=30)
    with pytest.raises(ValueError, match="live_leases"):
        journal.disable_capacity()
    journal.finish(lease)
    before = journal.read("a")
    original = state._backend._put_uncommitted
    def fail(slot, entry):
        original(slot, entry)
        raise OSError("injected after write")
    with monkeypatch.context() as patch:
        patch.setattr(state._backend, "_put_uncommitted", fail)
        with pytest.raises(OSError, match="injected"):
            journal.disable_capacity()
    assert journal.read("a") == before
    assert state.peek(("sage-work-capacity-v1", "test", "policy"))["limit"] == 1
    state.close()
