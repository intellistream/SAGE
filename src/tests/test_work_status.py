"""Native lifecycle and durable task status without payloads or lease secrets."""

import asyncio
import json
from dataclasses import FrozenInstanceError
from threading import Event

import pytest

from sage.runtime.async_work_service import AsyncWorkService
from sage.runtime.dependency_verifier import DependencyVerifier
from sage.runtime.effect_cancellation import CancellationService
from sage.runtime.flownet.runtime.operator_runtime.stateful import (
    StatefulProcessRuntime,
)
from sage.runtime.work_journal import StaleTaskLeaseError, WorkJournal
from sage.runtime.work_service import WorkService


def test_actual_worker_lifecycle_drains_without_claiming_completion(tmp_path):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "work.db"))
    entered, release = Event(), Event()

    def handler(lease):
        entered.set()
        assert release.wait(5)
        return "committed"

    service = WorkService(WorkJournal(state, namespace="owned"), handler, poll_interval=0.01)
    try:
        initial = service.status()
        assert initial.phase == "created" and initial.accepting and not initial.ready
        with pytest.raises(FrozenInstanceError):
            initial.phase = "running"
        service.commit("one", result="private answer", tasks={"task": "private payload"})
        assert entered.wait(3)
        running = service.status()
        assert running.phase == "running" and running.ready and running.supervisor_alive
        assert service.journal.status("one").tasks[0].status == "running"
        with pytest.raises(TimeoutError, match="drain_timeout"):
            service.close(timeout=0)
        draining = service.status()
        assert draining.phase == "draining" and not draining.ready and not draining.accepting
        assert service.journal.status("one").tasks[0].status == "running"
        release.set()
        service.close(timeout=3)
        assert service.status().phase == "closed" and not service.status().ready
        assert service.journal.status("one").tasks[0].status == "done"
    finally:
        release.set()
        service.close()
        state.close()


def test_storage_supervisor_failure_is_redacted_and_restart_recovers(tmp_path, monkeypatch):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "work.db"))
    journal = WorkJournal(state, namespace="owned")
    journal.commit("one", result="private answer", tasks={"task": "private payload"})
    service = WorkService(journal, lambda lease: "unused", poll_interval=0.01)

    def unavailable(**kwargs):
        raise OSError("private storage diagnostics")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(journal, "active_records", unavailable)
            service.start()
            assert service._stopped.wait(3)
        failure = service.status()
        assert failure.phase == "failed" and failure.error_type == "OSError"
        assert not failure.accepting and not failure.ready
        assert "private" not in json.dumps(failure.to_dict())
        with pytest.raises(RuntimeError, match="work_service_failed"):
            service.commit("late", result=None, tasks={})
        assert journal.read("late") is None
        with pytest.raises(RuntimeError, match="work_service_failed"):
            service.close()
        assert service.status().phase == "failed"  # Closing must not erase failure.
        calls = []
        recovered = WorkService(journal, lambda lease: calls.append(lease.request_id), poll_interval=0.01)
        try:
            recovered.start()
            result = recovered.wait("one", timeout=3)
            assert calls == ["one"] and result["result"] == "private answer"
            assert recovered.status().ready
        finally:
            recovered.close()
    finally:
        state.close()


def test_unexpected_supervisor_stop_rejects_admission_without_writing(tmp_path, monkeypatch):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "work.db"))
    service = WorkService(WorkJournal(state, namespace="owned"), lambda lease: None)
    monkeypatch.setattr(service._dispatcher, "run", lambda stop: None)
    try:
        service.start()
        assert service._stopped.wait(3)
        status = service.status()
        assert status.phase == "stopped" and status.error_type is None
        assert not status.accepting and not status.ready
        with pytest.raises(RuntimeError, match="work_service_stopped"):
            service.commit("stranded", result=None, tasks={"task": {}})
        assert service.journal.read("stranded") is None
        with pytest.raises(RuntimeError, match="work_service_stopped"):
            service.start()
    finally:
        service.close()
        state.close()


def test_async_status_distinguishes_owner_loop_from_live_supervisor():
    state = StatefulProcessRuntime()
    loop = asyncio.new_event_loop()

    async def handler(lease):
        return "done"

    async def create():
        return AsyncWorkService(WorkJournal(state, namespace="async"), handler, poll_interval=0.01)

    service = loop.run_until_complete(create())
    try:
        assert not service.status().execution_context_running
        assert not service.status().accepting

        async def run():
            await service.start()
            status = service.status()
            assert status.ready and status.execution_context_running and status.accepting
            await service.commit("one", result="answer", tasks={"task": {}})
            await service.wait("one", timeout=3)

        loop.run_until_complete(run())
        snapshot = service.status()
        assert snapshot.phase == "running" and snapshot.supervisor_alive
        assert not snapshot.execution_context_running and not snapshot.ready and not snapshot.accepting
    finally:
        loop.run_until_complete(service.aclose())
        loop.close()
        assert service.status().phase == "closed" and not service.status().execution_context_running
        state.close()


def test_request_status_is_readonly_and_uses_native_claim_predicate(tmp_path):
    path = str(tmp_path / "work.db")
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    now = [10.0]
    journal = WorkJournal(state, namespace="owned", clock=lambda: now[0])
    try:
        assert journal.status("missing") is None
        journal.commit("one", result="private answer", tasks={"parent": "private payload", "child": {}},
                       dependencies={"child": ["parent"]})
        before = journal.read("one")
        initial = journal.status("one")
        tasks = {task.task_id: task for task in initial.tasks}
        assert tasks["parent"].claimable and tasks["parent"].dependencies_ready
        assert not tasks["child"].claimable and not tasks["child"].dependencies_ready
        assert journal.read("one") == before
        lease = journal.claim("one", "parent", lease_seconds=1)
        active = journal.status("one").tasks
        assert next(t for t in active if t.task_id == "parent").status == "running"
        assert not next(t for t in active if t.task_id == "parent").claimable
        now[0] = 11
        expired = journal.status("one")
        parent = next(t for t in expired.tasks if t.task_id == "parent")
        assert parent.status == "running" and parent.lease_expired and parent.claimable
        assert journal.read("one")["tasks"]["parent"]["attempt"] == 1
        other = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
        try:
            independent = WorkJournal(other, namespace="owned", clock=lambda: now[0])
            assert independent.status("one") == expired
            replacement = independent.claim("one", "parent", lease_seconds=10)
            with pytest.raises(StaleTaskLeaseError):
                journal.finish(lease)
            independent.fail(replacement, code="temporarily_unavailable", retry_delay=3)
            waiting = next(t for t in journal.status("one").tasks if t.task_id == "parent")
            assert waiting.status == "pending" and waiting.attempt == 2 and not waiting.claimable
            assert waiting.last_failure_code == "temporarily_unavailable"
            now[0] = 14
            assert next(t for t in journal.status("one").tasks if t.task_id == "parent").claimable
            final = independent.claim("one", "parent", lease_seconds=10)
            independent.finish(final, result="private result")
            done = journal.status("one")
            assert next(t for t in done.tasks if t.task_id == "child").claimable
            assert "private" not in json.dumps(done.to_dict())
            assert lease.token not in repr(done) and replacement.token not in repr(done)
            assert next(t for t in done.tasks if t.task_id == "parent").last_failure_code == "temporarily_unavailable"
        finally:
            other.close()
    finally:
        state.close()


def test_terminal_failure_and_cancel_keep_native_dependency_modes():
    state = StatefulProcessRuntime()
    journal = WorkJournal(state, namespace="owned")
    try:
        journal.commit("one", result=None, tasks={"answer": {}, "ordinary": {}, "finalizer": {}},
                       dependencies={"ordinary": ["answer"], "finalizer": ["answer"]}, settled=["finalizer"])
        journal.cancel("one", "answer")
        tasks = {task.task_id: task for task in journal.status("one").tasks}
        assert tasks["answer"].status == "failed" and tasks["answer"].last_failure_code == "request_cancelled"
        assert tasks["ordinary"].status == "blocked" and not tasks["ordinary"].claimable
        assert tasks["finalizer"].status == "pending" and tasks["finalizer"].claimable
        assert tasks["finalizer"].dependency_mode == "settled" and tasks["ordinary"].dependency_mode == "success"
        assert journal.claim("one", "ordinary", lease_seconds=10) is None
        assert journal.claim("one", "finalizer", lease_seconds=10) is not None
    finally:
        state.close()


def test_request_storage_failure_is_not_fabricated_as_empty_or_success(monkeypatch):
    state = StatefulProcessRuntime()
    journal = WorkJournal(state, namespace="owned")
    service = WorkService(journal, lambda lease: None)

    def unavailable(slot):
        raise OSError("unavailable")

    try:
        monkeypatch.setattr(state, "peek", unavailable)
        with pytest.raises(OSError, match="unavailable"):
            journal.status("one")
        # Lifecycle observation does not claim to probe storage.
        assert service.status().phase == "created" and not service.status().ready
    finally:
        service.close()
        state.close()


def test_failed_but_explicitly_drained_service_retires_resources_without_hiding_failure(tmp_path, monkeypatch):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "work.db"))
    service = WorkService(WorkJournal(state, namespace="owned"), lambda lease: None)
    released = []

    def fail(stop):
        raise OSError("storage unavailable")

    monkeypatch.setattr(service._dispatcher, "run", fail)
    try:
        service.start()
        assert service._stopped.wait(3)
        assert service.status().phase == "failed" and not service.status().drained
        with pytest.raises(RuntimeError, match="work_service_failed"):
            service.close()
        assert service.status().phase == "failed" and service.status().drained

        def release():
            assert service.status().phase == "failed" and service.status().drained
            released.append(True)
            state.close()

        service.retire(release)
        assert released == [True] and service.status().phase == "failed"
        with pytest.raises(RuntimeError, match="already_retiring"):
            service.retire(release)
        assert released == [True]
    finally:
        state.close()


def test_dependency_and_cancellation_facades_preserve_native_lifecycle():
    state = StatefulProcessRuntime()
    verifier = DependencyVerifier(state, name="fixture", probe=lambda: True, poll_interval=0.01)
    cancellation = CancellationService(WorkJournal(state, namespace="origin"),
                                       task_id="answer", targets={}, poll_interval=0.01)
    try:
        assert verifier.work_status().phase == cancellation.work_status().phase == "created"
        verifier.start()
        verifier._work.wait(verifier._binding, timeout=3)
        cancellation.start()
        assert verifier.ready() and verifier.work_status().ready and cancellation.work_status().ready
    finally:
        verifier.close()
        cancellation.close()
        assert verifier.work_status().phase == cancellation.work_status().phase == "closed"
        state.close()
