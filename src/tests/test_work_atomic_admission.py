import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkJournal
from sage.runtime.work_service import WorkService

DESTINATION = ("memory", "tenant", "turn")


def save_once(old):
    expected = {"answer": "complete", "writes": 1}
    if old is not None and old != expected:
        raise ValueError("destination_conflict")
    return expected


@pytest.fixture
def storage(tmp_path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    yield store
    store.close()


def test_worker_can_only_observe_committed_destination_and_replay_keeps_done(storage):
    journal = WorkJournal(storage, namespace="work")
    observed = []
    def handler(lease):
        observed.append(storage.peek(DESTINATION))
        return "derived"
    service = WorkService(journal, handler, poll_interval=0.01)
    try:
        service.commit("turn", result="complete", tasks={"post": {}},
                       mutations={DESTINATION: save_once})
        done = service.wait("turn", timeout=3)
        assert observed == [{"answer": "complete", "writes": 1}]
        assert service.commit("turn", result="complete", tasks={"post": {}},
                              mutations={DESTINATION: save_once}) == done
        assert service.wait("turn", timeout=0) == done
        assert len(observed) == 1
        assert storage.peek(DESTINATION)["writes"] == 1
    finally:
        service.close()


@pytest.mark.parametrize("failure", ["destination", "journal", "second_sql_write"])
def test_atomic_failure_never_admits_half_a_turn_or_starts_worker(storage, monkeypatch, failure):
    journal = WorkJournal(storage, namespace="work")
    service = WorkService(journal, lambda lease: pytest.fail("unexpected task"))
    if failure == "journal":
        journal.commit("turn", result="different", tasks={})
    before = journal.read("turn")
    original = storage._backend._put_uncommitted
    def fail_sql(slot, entry):
        original(slot, entry)
        if slot[0] == "sage-work-journal-v1":
            raise ValueError("second_sql_write")
    def fail_destination(old):
        raise ValueError("destination_failure")
    try:
        if failure == "second_sql_write":
            monkeypatch.setattr(storage._backend, "_put_uncommitted", fail_sql)
        with pytest.raises(ValueError):
            service.commit("turn", result="complete", tasks={"post": {}}, mutations={
                DESTINATION: fail_destination if failure == "destination" else save_once,
            })
        assert storage.peek(DESTINATION) is None
        assert journal.read("turn") == before
        assert service._thread is None
    finally:
        service.close()


def test_lost_ack_then_restart_recovers_both_records_once(tmp_path, monkeypatch):
    path = str(tmp_path / "ack.db")
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = WorkJournal(store, namespace="work")
    service = WorkService(journal, lambda lease: pytest.fail("must not start"))
    original = store.update_many
    def lost_ack(*args, **kwargs):
        original(*args, **kwargs)
        raise ConnectionError("ack lost")
    try:
        with monkeypatch.context() as patch:
            patch.setattr(store, "update_many", lost_ack)
            with pytest.raises(ConnectionError, match="ack lost"):
                service.commit("turn", result="complete", tasks={"post": {}},
                               mutations={DESTINATION: save_once})
        assert service._thread is None
    finally:
        service.close()
        store.close()
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = WorkJournal(store, namespace="work")
    recovered = WorkService(journal, lambda lease: store.peek(DESTINATION), poll_interval=0.01)
    try:
        recovered.start()
        done = recovered.wait("turn", timeout=3)
        assert done["tasks"]["post"]["result"] == {"answer": "complete", "writes": 1}
        assert recovered.commit("turn", result="complete", tasks={"post": {}},
                                mutations={DESTINATION: save_once}) == done
        assert store.peek(DESTINATION)["writes"] == 1
    finally:
        recovered.close()
        store.close()


def test_close_serializes_after_admitted_transaction_and_rejects_new_mutations(storage):
    entered, release, closing = Event(), Event(), Event()
    journal = WorkJournal(storage, namespace="work")
    service = WorkService(journal, lambda lease: "done", poll_interval=0.01)
    def gated(old):
        entered.set()
        assert release.wait(5)
        return save_once(old)
    def close():
        closing.set()
        service.close(timeout=3)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = pool.submit(service.commit, "turn", result="complete", tasks={"post": {}},
                                  mutations={DESTINATION: gated})
            assert entered.wait(3)
            stopped = pool.submit(close)
            assert closing.wait(3)
            assert not stopped.done()
            release.set()
            pending.result(timeout=3)
            stopped.result(timeout=3)
        assert storage.peek(DESTINATION) == {"answer": "complete", "writes": 1}
        assert journal.read("turn") is not None
        with pytest.raises(RuntimeError, match="closing"):
            service.commit("later", result="none", tasks={}, mutations={
                ("memory", "tenant", "later"): lambda old: pytest.fail("unadmitted mutation"),
            })
        assert journal.read("later") is None
        assert storage.peek(("memory", "tenant", "later")) is None
    finally:
        release.set()
        service.close()


@pytest.mark.parametrize("mutations,error", [
    ({("sage-work-journal-v1", "work", "turn"): save_once}, ValueError),
    ({("sage-work-journal-v1", "other", "other"): save_once}, ValueError),
    ({("short",): save_once}, ValueError),
    ({("memory", " tenant", "turn"): save_once}, ValueError),
    ({DESTINATION: 42}, TypeError),
])
def test_invalid_mutation_contract_has_no_writes(storage, mutations, error):
    journal = WorkJournal(storage, namespace="work")
    with pytest.raises(error):
        journal.commit("turn", result="complete", tasks={}, mutations=mutations)
    assert journal.read("turn") is None
    assert storage.peek(DESTINATION) is None


@pytest.mark.parametrize("phase,exit_code", [("before_commit", 37), ("after_commit", 38)])
def test_process_exit_never_leaves_partial_admission(tmp_path, phase, exit_code):
    path = str(tmp_path / "crash.db")
    script = '''
import os, sys
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkJournal
from sage.runtime.work_service import WorkService
store = StatefulProcessRuntime(backend="sqlite", sqlite_path=sys.argv[1])
journal = WorkJournal(store, namespace="work")
service = WorkService(journal, lambda lease: "must not run")
if sys.argv[2] == "before_commit":
    original = store._backend._put_uncommitted
    def crash(slot, entry):
        original(slot, entry)
        os._exit(37)
    store._backend._put_uncommitted = crash
else:
    service.start = lambda: os._exit(38)
service.commit("turn", result="complete", tasks={"post": {}}, mutations={
    ("memory", "tenant", "turn"): lambda old: {"answer": "complete", "writes": 1},
})
'''
    child = subprocess.run([sys.executable, "-c", script, path, phase], capture_output=True,
                           timeout=20, env={**os.environ, "PYTHONNOUSERSITE": "1"})
    assert child.returncode == exit_code, child.stderr.decode(errors="replace")
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = WorkJournal(store, namespace="work")
    recovered = WorkService(journal, lambda lease: store.peek(DESTINATION), poll_interval=0.01)
    try:
        if phase == "before_commit":
            assert journal.read("turn") is None
            assert store.peek(DESTINATION) is None
        else:
            assert journal.read("turn")["tasks"]["post"]["status"] == "pending"
            recovered.start()
            done = recovered.wait("turn", timeout=3)
            assert done["tasks"]["post"]["result"] == {"answer": "complete", "writes": 1}
    finally:
        recovered.close()
        store.close()
