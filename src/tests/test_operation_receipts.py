import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.operation_receipts import OperationConflict, OperationReceipts
from sage.runtime.work_journal import StaleTaskLeaseError, WorkCapacityError, WorkJournal

SLOT = ("destination", "bookings", "all")


def increment(values):
    count = (values[SLOT] or 0) + 1
    return {"count": count}, {SLOT: count}


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_replay_preserves_current_destination_and_detaches_result(tmp_path, backend):
    store = StatefulProcessRuntime(backend=backend, sqlite_path=str(tmp_path / "state.db"))
    receipts = OperationReceipts(store, namespace="owner:fixture")
    try:
        result = receipts.commit("op", inputs={"a": 1}, slots=[SLOT], transition=increment)
        result["count"] = 900
        store.update(SLOT, lambda _: 20)
        def forbidden(_):
            pytest.fail("replayed transition")
        assert receipts.commit("op", inputs={"a": 1}, slots=[SLOT], transition=forbidden) == {"count": 1}
        assert store.peek(SLOT) == 20
        with pytest.raises(OperationConflict):
            receipts.commit("op", inputs={"a": True}, slots=[SLOT], transition=forbidden)
        assert store.peek(SLOT) == 20
    finally:
        store.close()


def test_independent_connections_concurrent_commit_and_restart(tmp_path):
    path = str(tmp_path / "state.db")
    stores = [StatefulProcessRuntime(backend="sqlite", sqlite_path=path) for _ in range(2)]
    receipts = [OperationReceipts(store, namespace="owner") for store in stores]
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda i: receipts[i % 2].commit(
                "op", inputs={"request": "same"}, slots=[SLOT], transition=increment), range(20)))
        assert results == [{"count": 1}] * 20
        assert stores[0].peek(SLOT) == 1
    finally:
        for store in stores:
            store.close()
    reopened = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        assert OperationReceipts(reopened, namespace="owner").commit(
            "op", inputs={"request": "same"}, slots=[SLOT], transition=increment) == {"count": 1}
        assert reopened.peek(SLOT) == 1
    finally:
        reopened.close()


def test_failed_transaction_and_lost_ack(tmp_path, monkeypatch):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    receipts = OperationReceipts(store, namespace="owner")
    original = store._backend._put_uncommitted
    def fail_receipt(slot, entry):
        original(slot, entry)
        if slot[0] == "sage-operation-receipts-v1":
            raise OSError("injected receipt failure")
    try:
        with monkeypatch.context() as patch:
            patch.setattr(store._backend, "_put_uncommitted", fail_receipt)
            with pytest.raises(OSError):
                receipts.commit("op", inputs={}, slots=[SLOT], transition=increment)
        assert store.peek(SLOT) is None
        original_update = store.update_many
        def lost_ack(*args, **kwargs):
            original_update(*args, **kwargs)
            raise ConnectionError("committed but acknowledgement lost")
        with monkeypatch.context() as patch:
            patch.setattr(store, "update_many", lost_ack)
            with pytest.raises(ConnectionError):
                receipts.commit("op", inputs={}, slots=[SLOT], transition=increment)
        assert receipts.commit("op", inputs={}, slots=[SLOT], transition=increment) == {"count": 1}
        assert store.peek(SLOT) == 1
    finally:
        store.close()


def test_invalid_transition_publishes_nothing(tmp_path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    receipts = OperationReceipts(store, namespace="owner")
    try:
        for transition in (lambda values: ({}, {}), lambda values: (float("nan"), {SLOT: 99})):
            with pytest.raises(ValueError):
                receipts.commit("op", inputs={}, slots=[SLOT], transition=transition)
            assert store.peek(SLOT) is None
        assert receipts.commit("op", inputs={}, slots=[SLOT], transition=increment) == {"count": 1}
    finally:
        store.close()


def _process_commit(path, ready, start, output):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        receipts = OperationReceipts(store, namespace="owner")
        ready.put(True)
        assert start.wait(10)
        output.put(receipts.commit("op", inputs={}, slots=[SLOT], transition=increment))
    finally:
        store.close()


def test_distinct_processes_share_one_receipt(tmp_path):
    path = str(tmp_path / "state.db")
    StatefulProcessRuntime(backend="sqlite", sqlite_path=path).close()
    context = multiprocessing.get_context("spawn")
    ready, output, start = context.Queue(), context.Queue(), context.Event()
    processes = [context.Process(target=_process_commit, args=(path, ready, start, output))
                 for _ in range(2)]
    try:
        for process in processes:
            process.start()
        for _ in processes:
            assert ready.get(timeout=15)
        start.set()
        assert [output.get(timeout=15) for _ in processes] == [{"count": 1}] * 2
        for process in processes:
            process.join(15)
            assert process.exitcode == 0
    finally:
        start.set()
        for process in processes:
            if process.is_alive():
                process.kill()
                process.join(5)
        ready.close()
        output.close()


def test_guard_checked_on_initial_commit_and_replay(tmp_path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    other = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "other.db"))
    journal = WorkJournal(store, namespace="work")
    receipts = OperationReceipts(store, namespace="owner")
    try:
        journal.commit("request", result={}, tasks={"task": {}})
        lease = journal.claim("request", "task", lease_seconds=60)
        guard = journal.prepare_guard(lease)
        with pytest.raises(ValueError, match="share_state_store"):
            OperationReceipts(other, namespace="owner").commit(
                "op", inputs={}, slots=[SLOT], transition=increment, guard=guard)
        assert receipts.commit("op", inputs={}, slots=[SLOT], transition=increment, guard=guard) == {"count": 1}
        journal.cancel("request", "task")
        for operation_id in ("op", "new"):
            with pytest.raises(StaleTaskLeaseError):
                receipts.commit(operation_id, inputs={}, slots=[SLOT], transition=increment, guard=guard)
        assert store.peek(SLOT) == 1
    finally:
        store.close()
        other.close()


def test_destination_conflict_and_owner_namespace_isolation(tmp_path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    try:
        alice = OperationReceipts(store, namespace="alice")
        bob = OperationReceipts(store, namespace="bob")
        alice.commit("op", inputs={}, slots=[SLOT], transition=increment)
        with pytest.raises(OperationConflict):
            alice.commit("op", inputs={}, slots=[("destination", "other", "all")],
                         transition=lambda _: pytest.fail("conflict must not execute"))
        assert bob.commit("op", inputs={}, slots=[SLOT], transition=increment) == {"count": 2}
    finally:
        store.close()


def _crash_at_commit(path, after_commit):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    if after_commit:
        original = store.update_many
        def crash(*args, **kwargs):
            original(*args, **kwargs)
            os._exit(23)  # Our isolated child, after commit and before acknowledgement.
        store.update_many = crash
    else:
        original = store._backend._put_uncommitted
        def crash(slot, entry):
            original(slot, entry)
            if slot[0] == "sage-operation-receipts-v1":
                os._exit(23)  # Both writes prepared, SQLite transaction not committed.
        store._backend._put_uncommitted = crash
    OperationReceipts(store, namespace="owner").commit(
        "op", inputs={}, slots=[SLOT], transition=increment)


@pytest.mark.parametrize("after_commit", [False, True])
def test_process_death_at_transaction_boundary(tmp_path, after_commit):
    path = str(tmp_path / "state.db")
    StatefulProcessRuntime(backend="sqlite", sqlite_path=path).close()
    process = multiprocessing.get_context("spawn").Process(target=_crash_at_commit,
                                                           args=(path, after_commit))
    process.start()
    try:
        process.join(15)
        assert process.exitcode == 23
    finally:
        if process.is_alive():
            process.kill()
            process.join(5)
    reopened = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        assert reopened.peek(SLOT) == (1 if after_commit else None)
        assert OperationReceipts(reopened, namespace="owner").commit(
            "op", inputs={}, slots=[SLOT], transition=increment) == {"count": 1}
        assert reopened.peek(SLOT) == 1
    finally:
        reopened.close()


def test_destination_receipt_and_outbox_admission_are_atomic(tmp_path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    receipts = OperationReceipts(store, namespace="owner")
    outbox = WorkJournal(store, namespace="index")
    outbox.configure_capacity(max_active_requests=1)
    def operation(key):
        work = outbox.prepare_commit(key, result={}, tasks={"index": {"document": key}})
        def transition(values):
            result, destination = increment(values)
            return result, {**destination, **work.apply(values)}
        return receipts.commit(key, inputs={"document": key}, slots=[SLOT, *work.slots],
                               transition=transition)
    try:
        assert operation("one") == {"count": 1}
        with pytest.raises(WorkCapacityError):
            operation("two")
        assert store.peek(SLOT) == 1
        assert outbox.read("two") is None
        assert operation("one") == {"count": 1}  # Replay still works at capacity.
        outbox.finish(outbox.claim("one", "index", lease_seconds=60), result={})
        assert operation("two") == {"count": 2}
        assert operation("one") == {"count": 1}
        assert store.peek(SLOT) == 2
    finally:
        store.close()
