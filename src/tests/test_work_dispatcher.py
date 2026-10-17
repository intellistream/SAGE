from threading import Event

import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_dispatcher import WorkDispatcher
from sage.runtime.work_journal import WorkJournal


def test_bounded_dispatch_and_drain(tmp_path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(store, namespace="tasks")
    journal.commit("turn", result="answer", tasks={"one": 1, "two": 2})
    entered, release = Event(), Event()
    seen = []

    def handler(lease):
        seen.append(lease.task_id)
        entered.set()
        assert release.wait(3)
        return {"task": lease.task_id, "value": lease.payload}

    worker = WorkDispatcher(journal, handler, max_workers=1)
    try:
        assert worker.run_once() == 1
        assert entered.wait(3)
        assert worker.run_once() == 0
        with pytest.raises(RuntimeError, match="not_drained"):
            worker.close()
        release.set()
        next(iter(worker._active)).result(timeout=3)
        assert worker.run_once() == 1
        next(iter(worker._active)).result(timeout=3)
        worker.run_once(admit=False)
        assert seen == ["one", "two"]
        assert worker.completed == 2
        assert journal.read("turn")["tasks"]["two"]["result"] == {"task": "two", "value": 2}
        assert all(task["status"] == "done" for task in journal.records()[0][0]["value"]["tasks"].values())
    finally:
        release.set()
        worker.close()
        store.close()


def test_failure_retry_is_durable_and_delayed(tmp_path):
    now = [0.0]
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(store, namespace="tasks", clock=lambda: now[0])
    journal.commit("turn", result="answer", tasks={"one": 1})

    def fail(lease):
        raise ValueError("test failure")

    worker = WorkDispatcher(journal, fail, retry_delay=10)
    try:
        worker.run_once()
        with pytest.raises(ValueError):
            next(iter(worker._active)).result(timeout=3)
        assert worker.run_once() == 0
        assert worker.failed == 1
        worker.close()
        worker = WorkDispatcher(journal, lambda lease: None, retry_delay=10)
        assert worker.run_once() == 0
        now[0] = 10.0
        assert worker.run_once() == 1
        next(iter(worker._active)).result(timeout=3)
        worker.run_once(admit=False)
        task = journal.records()[0][0]["value"]["tasks"]["one"]
        assert task["status"] == "done"
        assert task["attempt"] == 2
    finally:
        worker.close()
        store.close()


def test_run_stop_drains_without_admitting_more(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(store, namespace="tasks")
    journal.commit("turn", result="answer", tasks={"one": 1, "two": 2})
    entered, release, stop = Event(), Event(), Event()

    def handler(lease):
        entered.set()
        assert release.wait(3)

    worker = WorkDispatcher(journal, handler, max_workers=1, poll_interval=0.01)
    try:
        with ThreadPoolExecutor(max_workers=1) as thread:
            run = thread.submit(worker.run, stop)
            try:
                assert entered.wait(3)
                stop.set()
            finally:
                release.set()
            run.result(timeout=3)
        assert worker.completed == 1
        tasks = journal.records()[0][0]["value"]["tasks"]
        assert tasks["two"]["status"] == "pending"
    finally:
        release.set()
        worker.close()
        store.close()


def test_lost_lease_is_reported_and_cannot_acknowledge(tmp_path):
    now = [0.0]
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(store, namespace="tasks", clock=lambda: now[0])
    journal.commit("turn", result="answer", tasks={"one": 1})
    entered, release = Event(), Event()

    def handler(lease):
        entered.set()
        assert release.wait(3)

    worker = WorkDispatcher(journal, handler, max_workers=2, lease_seconds=10)
    try:
        worker.run_once()
        assert entered.wait(3)
        future = next(iter(worker._active))
        now[0] = 11.0
        assert worker.run_once() == 0
        assert worker.lease_losses == 1
        assert worker.run_once() == 0  # Don't duplicate our still-running stale handler.
        release.set()
        future.result(timeout=3)
        worker.run_once(admit=False)
        assert worker.completed == 0
        assert journal.records()[0][0]["value"]["tasks"]["one"]["status"] == "running"
        assert journal.claim("turn", "one", lease_seconds=10).attempt == 2
    finally:
        release.set()
        worker.close()
        store.close()
