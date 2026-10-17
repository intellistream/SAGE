from threading import Event

import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkJournal
from sage.runtime.work_service import WorkService


def test_start_recovers_existing_tasks_and_wait_returns_durable_result(tmp_path):
    path = str(tmp_path / "state.db")
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = WorkJournal(store, namespace="work")
    journal.commit("turn", result="original answer", tasks={"post": {"value": 1}})
    store.close()
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = WorkJournal(store, namespace="work")
    service = WorkService(journal, lambda lease: {"value": lease.payload["value"] + 1}, poll_interval=0.01)
    try:
        service.start()
        service.start()
        record = service.wait("turn", timeout=3)
        assert record["result"] == "original answer"
        assert record["tasks"]["post"]["result"] == {"value": 2}
        assert record["tasks"]["post"]["attempt"] == 1
    finally:
        service.close()
        store.close()


def test_wait_timeout_does_not_cancel_and_close_timeout_keeps_drain_alive(tmp_path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    entered, release = Event(), Event()

    def handler(lease):
        entered.set()
        assert release.wait(5)
        return "done"

    journal = WorkJournal(store, namespace="work")
    service = WorkService(journal, handler, poll_interval=0.01, max_workers=1)
    try:
        service.commit("turn", result="answer", tasks={"post": 1, "queued": 2})
        assert entered.wait(3)
        with pytest.raises(TimeoutError, match="wait_timeout"):
            service.wait("turn", timeout=0)
        with pytest.raises(TimeoutError, match="drain_timeout"):
            service.close(timeout=0)
        with pytest.raises(RuntimeError, match="closing"):
            service.commit("another", result="not admitted", tasks={})
        assert journal.read("another") is None
        release.set()
        service.close(timeout=3)
        assert journal.read("turn")["tasks"]["post"]["result"] == "done"
        assert journal.read("turn")["tasks"]["queued"]["status"] == "pending"
        service.close()
        recovered = WorkService(journal, lambda lease: "recovered", poll_interval=0.01)
        try:
            recovered.start()
            completed = recovered.wait("turn", timeout=3)
            assert completed["tasks"]["queued"]["result"] == "recovered"
            assert completed["tasks"]["post"]["attempt"] == 1
        finally:
            recovered.close()
    finally:
        release.set()
        service.close()
        store.close()


def test_dispatch_failure_is_reported_not_silently_restarted(tmp_path, monkeypatch):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(store, namespace="work")
    journal.commit("turn", result="answer", tasks={"post": 1})
    service = WorkService(journal, lambda lease: None, poll_interval=0.01)

    def fail(*args, **kwargs):
        raise OSError("storage unavailable")

    monkeypatch.setattr(service._dispatcher, "run", fail)
    try:
        service.start()
        assert service._stopped.wait(3)
        with pytest.raises(RuntimeError, match="work_service_failed"):
            service.wait("turn", timeout=3)
        with pytest.raises(RuntimeError, match="work_service_failed"):
            service.commit("another", result="not admitted", tasks={})
        with pytest.raises(RuntimeError, match="work_service_failed"):
            service.close()
        assert journal.read("turn")["tasks"]["post"]["status"] == "pending"
        assert journal.read("another") is None
    finally:
        store.close()
