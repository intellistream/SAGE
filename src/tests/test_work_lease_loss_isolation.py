from threading import Event

import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_dispatcher import WorkDispatcher
from sage.runtime.work_journal import WorkJournal
from sage.runtime.work_service import WorkService


@pytest.mark.parametrize("finished", [False, True])
@pytest.mark.parametrize("failed", [False, True])
def test_other_connection_reclaims_without_stopping_unrelated_work(tmp_path, finished, failed):
    path = str(tmp_path / "state.db")
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    other = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    now = [0.0]
    journal = WorkJournal(state, namespace="jobs", clock=lambda: now[0])
    replacement = WorkJournal(other, namespace="jobs", clock=lambda: now[0])
    journal.commit("a", result=None, tasks={"work": 1})
    entered, release = Event(), Event()

    def handler(lease):
        if lease.request_id == "a":
            entered.set()
            assert release.wait(5)
            if failed:
                raise RuntimeError("old worker failed")
        return "old" if lease.request_id == "a" else "unrelated"

    worker = WorkDispatcher(journal, handler, max_workers=2, lease_seconds=10)
    try:
        worker.run_once()
        assert entered.wait(3)
        stale = next(iter(worker._active))
        now[0] = 11
        lease = replacement.claim("a", "work", lease_seconds=10)
        replacement.finish(lease, result="new owner")
        if finished:
            release.set()
            if failed:
                with pytest.raises(RuntimeError, match="old worker"):
                    stale.result(timeout=3)
            else:
                stale.result(timeout=3)
        journal.commit("b", result=None, tasks={"work": 2})
        assert worker.run_once() == 1
        assert worker.lease_losses == 1
        for future, active in list(worker._active.items()):
            if active.request_id == "b":
                future.result(timeout=3)
        worker.run_once(admit=False)
        assert journal.read("b")["tasks"]["work"]["result"] == "unrelated"
        assert journal.read("a")["tasks"]["work"]["result"] == "new owner"
        assert worker.completed == 1 and worker.failed == 0
        release.set()
        if failed:
            with pytest.raises(RuntimeError, match="old worker"):
                stale.result(timeout=3)
        else:
            stale.result(timeout=3)
        worker.run_once(admit=False)
        assert worker.lease_losses == 1
        assert not worker._active
    finally:
        release.set()
        worker.close()
        other.close()
        state.close()


def test_storage_error_remains_fatal(tmp_path, monkeypatch):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(state, namespace="jobs")
    journal.commit("a", result=None, tasks={"work": 1})
    entered, release = Event(), Event()

    def handler(lease):
        entered.set()
        assert release.wait(5)

    worker = WorkDispatcher(journal, handler)
    try:
        worker.run_once()
        assert entered.wait(3)
        def unavailable(*args, **kwargs):
            raise OSError("store unavailable")
        monkeypatch.setattr(journal, "renew", unavailable)
        with pytest.raises(OSError, match="store unavailable"):
            worker.run_once()
        assert worker.lease_losses == 0
    finally:
        release.set()
        for future in worker._active:
            future.result(timeout=3)
        worker.run_once(admit=False)
        worker.close()
        state.close()


def test_lost_running_handler_still_counts_toward_capacity(tmp_path):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    now = [0.0]
    journal = WorkJournal(state, namespace="jobs", clock=lambda: now[0])
    journal.commit("a", result=None, tasks={"work": 1})
    entered, release = Event(), Event()

    def handler(lease):
        if lease.request_id == "a":
            entered.set()
            assert release.wait(5)
        return lease.request_id

    worker = WorkDispatcher(journal, handler, max_workers=1, lease_seconds=10)
    try:
        worker.run_once()
        assert entered.wait(3)
        stale = next(iter(worker._active))
        now[0] = 11
        replacement = journal.claim("a", "work", lease_seconds=10)
        journal.finish(replacement, result="replacement")
        journal.commit("b", result=None, tasks={"work": 2})
        assert worker.run_once() == 0
        assert worker.run_once() == 0
        assert journal.read("b")["tasks"]["work"]["attempt"] == 0
        with pytest.raises(RuntimeError, match="not_drained"):
            worker.close()
        release.set()
        stale.result(timeout=3)
        assert worker.run_once() == 1
        next(iter(worker._active)).result(timeout=3)
        worker.run_once(admit=False)
        assert worker.completed == 1 and worker.lease_losses == 1
    finally:
        release.set()
        worker.close()
        state.close()


def test_managed_service_keeps_running_after_remote_lease_loss(tmp_path):
    path = str(tmp_path / "state.db")
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    other = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = WorkJournal(state, namespace="jobs")
    # The remote clock deliberately observes the original lease as expired.
    import time
    remote = WorkJournal(other, namespace="jobs", clock=lambda: time.time() + 100)
    entered, release = Event(), Event()

    def handler(lease):
        if lease.request_id == "a":
            entered.set()
            assert release.wait(5)
        return lease.request_id

    service = WorkService(journal, handler, max_workers=2, poll_interval=0.01)
    try:
        service.commit("a", result=None, tasks={"work": 1})
        assert entered.wait(3)
        lease = remote.claim("a", "work", lease_seconds=10)
        remote.finish(lease, result="remote")
        service.commit("b", result=None, tasks={"work": 2})
        result = service.wait("b", timeout=3)
        assert result["tasks"]["work"]["result"] == "b"
        assert journal.read("a")["tasks"]["work"]["result"] == "remote"
        assert service._dispatcher.lease_losses == 1
    finally:
        release.set()
        service.close(timeout=3)
        other.close()
        state.close()
