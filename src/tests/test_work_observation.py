import subprocess
import sys
from threading import Barrier, Event

import pytest

from sage.runtime.event_journal import EventJournal
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_dispatcher import WorkDispatcher, WorkFailure
from sage.runtime.work_journal import StaleTaskLeaseError, WorkJournal
from sage.runtime.work_observation import WorkEventDestination, WorkObserver
from sage.runtime.work_service import WorkFailedError, WorkService


def setup(path, clock=lambda: 0):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(path))
    journal = WorkJournal(state, namespace="owned-work", clock=clock)
    events = EventJournal(state, namespace="owned-events")
    observer = WorkObserver(journal, lambda lease: WorkEventDestination(events, "owned-stream"))
    return state, journal, events, observer


def observed(events):
    return [frame["payload"]["event"] for frame in events.read("owned-stream")["events"]
            if frame["payload"]["type"] == "work-event"]


def test_running_handler_is_not_completed_and_ack_precedes_application_terminal(tmp_path):
    path = tmp_path / "state.db"
    state, journal, events, observer = setup(path)
    entered, release = Event(), Event()

    def handler(lease):
        entered.set()
        assert release.wait(3)
        return {"result": "private-result"}

    def completion(lease, result):
        append = events.prepare_append("owned-stream", event_id="terminal", terminal=True,
            payload={"type": "complete"})
        return {append.slot: append.transform}

    service = WorkService(journal, handler, observer=observer, completion_mutations=completion,
        poll_interval=0.01)
    try:
        service.commit("request", result=None, tasks={"post": {"body": "private-input"}})
        assert entered.wait(3)
        assert [event["state"] for event in observed(events)] == ["started"]
        assert journal.read("request")["tasks"]["post"]["status"] == "running"
        release.set()
        service.wait("request", timeout=3)
        page = events.read("owned-stream")
        assert [event["state"] for event in observed(events)] == ["started", "completed"]
        assert page["closed"] and page["events"][-1]["payload"] == {"type": "complete"}
        assert "private-input" not in repr(page) and "private-result" not in repr(page)
        assert journal.read("request")["tasks"]["post"]["result"] == {"result": "private-result"}
        saved = page
    finally:
        release.set()
        service.close()
        state.close()
    reopened = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(path))
    try:
        assert EventJournal(reopened, namespace="owned-events").read("owned-stream") == saved
    finally:
        reopened.close()


def test_retry_events_are_atomic_and_do_not_relax_business_mutation_prohibition(tmp_path):
    now = [0]
    state, journal, events, observer = setup(tmp_path / "state.db", clock=lambda: now[0])
    calls = []

    def handler(lease):
        calls.append(lease.attempt)
        if lease.attempt == 1:
            raise ValueError("private-exception-content")
        return "private-result"

    dispatcher = WorkDispatcher(journal, handler, observer=observer, retry_delay=1, poll_interval=0.01)
    try:
        journal.commit("request", result=None, tasks={"post": "private-payload"})
        dispatcher.run_once()
        future, lease = next(iter(dispatcher._active.items()))
        with pytest.raises(ValueError):
            future.result(timeout=3)
        with pytest.raises(ValueError, match="retry_cannot_publish_destination"):
            journal.finish(lease, retry=True, mutations={("business", "owned", "effect"): lambda _: True})
        dispatcher.run_once()
        assert journal.read("request")["tasks"]["post"]["status"] == "pending"
        assert [(event["attempt"], event["state"]) for event in observed(events)] == [(1, "started"), (1, "retrying")]
        now[0] = 1
        dispatcher.run_once()
        next(iter(dispatcher._active)).result(timeout=3)
        dispatcher.run_once()
        assert [(event["attempt"], event["state"]) for event in observed(events)] == [
            (1, "started"), (1, "retrying"), (2, "started"), (2, "completed")]
        assert observed(events)[1]["error_type"] == "ValueError"
        assert "private-" not in repr(events.read("owned-stream"))
        assert lease.token not in repr(events.read("owned-stream"))
        assert calls == [1, 2]
        assert not dispatcher._observations
    finally:
        dispatcher.close()
        state.close()


def test_terminal_failure_does_not_fabricate_child_execution(tmp_path):
    state, journal, events, observer = setup(tmp_path / "state.db")

    def handler(lease):
        raise PermissionError("private-denial")

    service = WorkService(journal, handler, observer=observer, poll_interval=0.01,
        failure_policy=lambda lease, error: WorkFailure("denied"))
    try:
        service.commit("request", result=None, tasks={"parent": {}, "child": {}}, dependencies={"child": ["parent"]})
        with pytest.raises(WorkFailedError):
            service.wait("request", timeout=3)
        record = journal.read("request")
        assert record["tasks"]["parent"]["status"] == "failed"
        assert record["tasks"]["child"]["status"] == "blocked"
        assert [(event["task_id"], event["state"]) for event in observed(events)] == [
            ("parent", "started"), ("parent", "failed")]
        assert observed(events)[-1]["failure_code"] == "denied"
        assert "private-denial" not in repr(events.read("owned-stream"))
    finally:
        service.close()
        state.close()


def test_storage_failure_rolls_back_completion_and_stale_observation_cannot_publish(tmp_path, monkeypatch):
    now = [0]
    state, journal, events, observer = setup(tmp_path / "state.db", clock=lambda: now[0])
    try:
        journal.commit("request", result=None, tasks={"post": {}})
        lease = journal.claim("request", "post", lease_seconds=1)
        attempt = observer.bind(lease)
        attempt.started()
        done = attempt.prepare("completed")
        before = events.read("owned-stream")
        put = state._backend._put_uncommitted

        def fail(slot, value):
            put(slot, value)
            if slot[0] == "sage-event-journal-v1":
                raise OSError("private-write-failure")

        with monkeypatch.context() as patch:
            patch.setattr(state._backend, "_put_uncommitted", fail)
            with pytest.raises(OSError):
                journal.finish(lease, result="unacknowledged", observation=done)
        assert events.read("owned-stream") == before
        assert journal.read("request")["tasks"]["post"]["status"] == "running"
        assert "result" not in journal.read("request")["tasks"]["post"]
        with pytest.raises(ValueError, match="scope_or_state"):
            journal.observe(lease, done)
        now[0] = 2
        replacement = journal.claim("request", "post", lease_seconds=1)
        with pytest.raises(StaleTaskLeaseError):
            journal.finish(lease, result="stale", observation=done)
        with pytest.raises(ValueError, match="scope_or_state"):
            journal.finish(replacement, result="wrong-attempt", observation=done)
        assert events.read("owned-stream") == before
        new = observer.bind(replacement)
        new.started()
        journal.finish(replacement, result="current", observation=new.prepare("completed"))
    finally:
        state.close()


def test_failed_start_publication_never_enters_handler(tmp_path, monkeypatch):
    state, journal, events, observer = setup(tmp_path / "state.db")
    calls = []
    dispatcher = WorkDispatcher(journal, lambda lease: calls.append(True), observer=observer, poll_interval=0.01)
    put = state._backend._put_uncommitted

    def fail(slot, value):
        put(slot, value)
        if slot[0] == "sage-event-journal-v1":
            raise OSError("private-start-failure")

    try:
        journal.commit("request", result=None, tasks={"post": {}})
        with monkeypatch.context() as patch:
            patch.setattr(state._backend, "_put_uncommitted", fail)
            dispatcher.run_once()
            with pytest.raises(OSError):
                next(iter(dispatcher._active)).result(timeout=3)
        assert not calls
        assert not events.read("owned-stream")["events"]
        dispatcher.run_once()
        assert [event["state"] for event in observed(events)] == ["retrying"]
        assert journal.read("request")["tasks"]["post"]["status"] == "pending"
    finally:
        dispatcher.close()
        state.close()


def test_process_death_before_ack_keeps_unfinished_attempt_and_recovers(tmp_path):
    path = tmp_path / "crash.db"
    script = """
import os,time,sys
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkJournal
from sage.runtime.event_journal import EventJournal
from sage.runtime.work_observation import WorkObserver,WorkEventDestination
from sage.runtime.work_service import WorkService
s=StatefulProcessRuntime(backend='sqlite',sqlite_path=sys.argv[1])
j=WorkJournal(s,namespace='owned-work',clock=lambda:0)
e=EventJournal(s,namespace='owned-events')
o=WorkObserver(j,lambda lease:WorkEventDestination(e,'owned-stream'))
w=WorkService(j,lambda lease:os._exit(44),observer=o,lease_seconds=1,poll_interval=.01)
w.commit('request',result=None,tasks={'post':{}})
time.sleep(10)
"""
    result = subprocess.run([sys.executable, "-c", script, str(path)], timeout=5, capture_output=True)
    assert result.returncode == 44
    state, journal, events, observer = setup(path, clock=lambda: 2)
    dispatcher = WorkDispatcher(journal, lambda lease: "recovered", observer=observer, poll_interval=0.01)
    try:
        assert [(event["attempt"], event["state"]) for event in observed(events)] == [(1, "started")]
        dispatcher.run_once()
        next(iter(dispatcher._active)).result(timeout=3)
        dispatcher.run_once()
        assert [(event["attempt"], event["state"]) for event in observed(events)] == [
            (1, "started"), (2, "started"), (2, "completed")]
        assert journal.read("request")["tasks"]["post"]["result"] == "recovered"
    finally:
        dispatcher.close()
        state.close()


def test_concurrent_tasks_keep_native_scope_and_dependency_metadata(tmp_path):
    state, journal, events, _ = setup(tmp_path / "state.db")
    observer = WorkObserver(journal, lambda lease: WorkEventDestination(events, lease.request_id))
    barrier = Barrier(2)

    def handler(lease):
        if lease.task_id == "parent":
            barrier.wait(timeout=3)
        return lease.request_id

    service = WorkService(journal, handler, observer=observer, max_workers=2, poll_interval=0.01)
    try:
        for request in ("owner-a", "owner-b"):
            journal.commit(request, result=None, tasks={"parent": {}, "child": {}},
                           dependencies={"child": ["parent"]})
        service.start()
        for request in ("owner-a", "owner-b"):
            service.wait(request, timeout=3)
            page = events.read(request)
            native = [frame["payload"]["event"] for frame in page["events"]]
            assert {event["request_id"] for event in native} == {request}
            assert [(event["task_id"], event["state"]) for event in native] == [
                ("parent", "started"), ("parent", "completed"), ("child", "started"), ("child", "completed")]
            assert all(event["dependency_task_ids"] == ["parent"] for event in native if event["task_id"] == "child")
            assert all(event["dependency_mode"] == "success" for event in native)
    finally:
        service.close()
        state.close()


def test_lost_ack_reopens_as_done_without_running_handler_or_republishing(tmp_path, monkeypatch):
    path = tmp_path / "state.db"
    state, journal, events, observer = setup(path)
    try:
        journal.commit("request", result=None, tasks={"post": {}})
        lease = journal.claim("request", "post", lease_seconds=1)
        attempt = observer.bind(lease)
        attempt.started()
        update = state.update_many

        def lost_ack(*args, **kwargs):
            update(*args, **kwargs)
            raise ConnectionError("private-lost-ack")

        with monkeypatch.context() as patch:
            patch.setattr(state, "update_many", lost_ack)
            with pytest.raises(ConnectionError):
                journal.finish(lease, result="durable", observation=attempt.prepare("completed"))
        assert journal.read("request")["tasks"]["post"]["status"] == "done"
        saved = events.read("owned-stream")
    finally:
        state.close()
    reopened, journal, events, observer = setup(path, clock=lambda: 2)
    dispatcher = WorkDispatcher(journal, lambda lease: pytest.fail("already completed handler reran"), observer=observer)
    try:
        assert dispatcher.run_once() == 0
        assert events.read("owned-stream") == saved
    finally:
        dispatcher.close()
        reopened.close()


def test_failure_event_and_dependency_blocking_roll_back_together(tmp_path, monkeypatch):
    state, journal, events, observer = setup(tmp_path / "state.db")
    try:
        journal.commit("request", result=None, tasks={"parent": {}, "child": {}}, dependencies={"child": ["parent"]})
        lease = journal.claim("request", "parent", lease_seconds=1)
        attempt = observer.bind(lease)
        attempt.started()
        failed = attempt.prepare("failed", error=PermissionError("private"), failure_code="denied")
        put = state._backend._put_uncommitted

        def fail(slot, value):
            put(slot, value)
            if slot[0] == "sage-event-journal-v1":
                raise OSError("private-commit-failure")

        with monkeypatch.context() as patch:
            patch.setattr(state._backend, "_put_uncommitted", fail)
            with pytest.raises(OSError):
                journal.fail(lease, code="denied", observation=failed)
        assert journal.read("request")["tasks"]["parent"]["status"] == "running"
        assert journal.read("request")["tasks"]["child"]["status"] == "pending"
        assert [event["state"] for event in observed(events)] == ["started"]
        with pytest.raises(ValueError, match="failure_code_mismatch"):
            journal.fail(lease, code="different", observation=failed)
        journal.fail(lease, code="denied", observation=failed)
        assert journal.read("request")["tasks"]["child"]["status"] == "blocked"
        assert observed(events)[-1]["state"] == "failed"
    finally:
        state.close()


def test_observation_rejects_other_store_and_other_journal(tmp_path):
    state, journal, events, observer = setup(tmp_path / "one.db")
    other, wrong, other_events, _ = setup(tmp_path / "two.db")
    try:
        journal.commit("request", result=None, tasks={"post": {}})
        lease = journal.claim("request", "post", lease_seconds=1)
        target = WorkObserver(journal, lambda lease: WorkEventDestination(other_events, "wrong"))
        with pytest.raises(ValueError, match="same_store"):
            target.bind(lease)
        with pytest.raises(ValueError, match="journal_mismatch"):
            WorkDispatcher(wrong, lambda lease: None, observer=observer)
        with pytest.raises(TypeError, match="required"):
            journal.observe(lease, None)
        attempt = observer.bind(lease)
        with pytest.raises(ValueError, match="scope_or_state"):
            journal.finish(lease, result=None, observation=attempt.prepare("started"))
        assert not events.read("owned-stream")["events"]
    finally:
        state.close()
        other.close()


def test_settled_finalizer_reports_actual_dependency_mode_after_failure(tmp_path):
    state, journal, events, observer = setup(tmp_path / "state.db")

    def handler(lease):
        if lease.task_id == "parent":
            raise ValueError("private-failure")
        return "settled"

    dispatcher = WorkDispatcher(journal, handler, observer=observer,
        failure_policy=lambda lease, error: WorkFailure("denied"))
    try:
        journal.commit("request", result=None, tasks={"parent": {}, "finalizer": {}},
                       dependencies={"finalizer": ["parent"]}, settled=["finalizer"])
        dispatcher.run_once()
        with pytest.raises(ValueError):
            next(iter(dispatcher._active)).result(timeout=3)
        dispatcher.run_once()
        next(iter(dispatcher._active)).result(timeout=3)
        dispatcher.run_once()
        finalizer = [event for event in observed(events) if event["task_id"] == "finalizer"]
        assert [event["state"] for event in finalizer] == ["started", "completed"]
        assert all(event["dependency_mode"] == "settled" for event in finalizer)
        assert journal.read("request")["tasks"]["parent"]["status"] == "failed"
        assert journal.read("request")["tasks"]["finalizer"]["status"] == "done"
    finally:
        dispatcher.close()
        state.close()
