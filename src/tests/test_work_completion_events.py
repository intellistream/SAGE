"""Completion/event atomicity, fencing and worker recovery contracts."""

from concurrent.futures import Future

import pytest

from sage.runtime.event_journal import EventJournal
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_dispatcher import WorkDispatcher
from sage.runtime.work_journal import StaleTaskLeaseError, WorkJournal
from sage.runtime.work_service import WorkService


def terminal(events, result):
    prepared = events.prepare_append("stream", event_id="terminal", payload=result, terminal=True)
    return {prepared.slot: prepared.transform}


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_completion_and_event_commit_together(tmp_path, backend):
    state = StatefulProcessRuntime(backend=backend, sqlite_path=str(tmp_path / "state.db"))
    work = WorkJournal(state, namespace="work")
    events = EventJournal(state, namespace="events")
    try:
        work.commit("turn", result="answer", tasks={"post": {}})
        lease = work.claim("turn", "post", lease_seconds=30)
        work.finish(lease, result={"complete": True}, mutations=terminal(events, {"complete": True}))
        assert work.read("turn")["tasks"]["post"]["result"] == {"complete": True}
        assert events.read("stream")["closed"]
        assert events.read("stream")["events"][0]["payload"] == {"complete": True}
    finally:
        state.close()


@pytest.mark.parametrize("failure", ["stale", "conflict", "sql"])
def test_failed_completion_never_publishes_half_a_commit(tmp_path, monkeypatch, failure):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    now = [0.0]
    work = WorkJournal(state, namespace="work", clock=lambda: now[0])
    events = EventJournal(state, namespace="events")
    work.commit("turn", result="answer", tasks={"post": {}})
    lease = work.claim("turn", "post", lease_seconds=30)
    if failure == "conflict":
        events.append("stream", event_id="terminal", payload="other", terminal=True)
    if failure == "stale":
        now[0] = 31.0
    before_work, before_events = work.read("turn"), events.read("stream")
    original = state._backend._put_uncommitted

    def fail_sql(slot, entry):
        original(slot, entry)
        if slot[0] == "sage-event-journal-v1":
            raise OSError("injected event write failure")

    try:
        if failure == "sql":
            monkeypatch.setattr(state._backend, "_put_uncommitted", fail_sql)
        with pytest.raises((StaleTaskLeaseError, ValueError, OSError)):
            work.finish(lease, result="done", mutations=terminal(events, "done"))
        assert work.read("turn") == before_work
        assert events.read("stream") == before_events
    finally:
        state.close()


def test_lost_completion_ack_survives_reopen_without_rerunning_handler(tmp_path, monkeypatch):
    path = str(tmp_path / "state.db")
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    work = WorkJournal(state, namespace="work")
    events = EventJournal(state, namespace="events")
    work.commit("turn", result="answer", tasks={"post": {}})
    lease = work.claim("turn", "post", lease_seconds=30)
    original = state.update_many

    def lose_ack(*args, **kwargs):
        original(*args, **kwargs)
        raise ConnectionError("lost completion ack")

    with monkeypatch.context() as patch:
        patch.setattr(state, "update_many", lose_ack)
        with pytest.raises(ConnectionError):
            work.finish(lease, result="done", mutations=terminal(events, "done"))
    state.close()
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    work = WorkJournal(state, namespace="work")
    events = EventJournal(state, namespace="events")
    service = WorkService(work, lambda lease: pytest.fail("completed work replayed"), poll_interval=0.01)
    try:
        service.start()
        assert service.wait("turn", timeout=3)["tasks"]["post"]["status"] == "done"
        assert len(events.read("stream")["events"]) == 1
        assert events.read("stream")["closed"]
    finally:
        service.close()
        state.close()


def test_worker_recovers_pending_completion_with_event(tmp_path):
    path = str(tmp_path / "state.db")
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    WorkJournal(state, namespace="work").commit("turn", result="answer", tasks={"post": {}})
    state.close()
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    work = WorkJournal(state, namespace="work")
    events = EventJournal(state, namespace="events")
    service = WorkService(work, lambda lease: "done", poll_interval=0.01,
                          completion_mutations=lambda lease, result: terminal(events, result))
    try:
        service.start()
        assert service.wait("turn", timeout=3)["tasks"]["post"]["result"] == "done"
        assert events.read("stream")["events"][0]["payload"] == "done"
        assert events.read("stream")["closed"]
    finally:
        service.close()
        state.close()


@pytest.mark.parametrize("mode", ["retry", "reserved", "replaced_owner"])
def test_completion_rejects_invalid_destinations_before_publication(tmp_path, mode):
    state = StatefulProcessRuntime(backend="memory")
    now = [0.0]
    work = WorkJournal(state, namespace="work", clock=lambda: now[0])
    events = EventJournal(state, namespace="events")
    work.commit("turn", result="answer", tasks={"post": {}})
    lease = work.claim("turn", "post", lease_seconds=30)
    mutations = terminal(events, "done")
    if mode == "reserved":
        mutations = {("sage-work-journal-v1", "other", "turn"): lambda old: {}}
    if mode == "replaced_owner":
        now[0] = 31.0
        assert work.claim("turn", "post", lease_seconds=30) is not None
    before = work.read("turn")
    try:
        with pytest.raises(ValueError):
            work.finish(lease, retry=mode == "retry", mutations=mutations)
        assert work.read("turn") == before
        assert events.read("stream")["events"] == []
    finally:
        state.close()


def test_completion_preparation_failure_does_not_acknowledge_or_rerun_handler():
    state = StatefulProcessRuntime(backend="memory")
    work = WorkJournal(state, namespace="work")
    events = EventJournal(state, namespace="events")
    work.commit("turn", result="answer", tasks={"post": {}})
    lease = work.claim("turn", "post", lease_seconds=30)

    def fail(lease, result):
        raise ValueError("invalid completion projection")

    dispatcher = WorkDispatcher(work, lambda lease: pytest.fail("handler rerun"), completion_mutations=fail)
    future = Future()
    future.set_result("done")
    dispatcher._active[future] = lease
    try:
        with pytest.raises(ValueError, match="invalid completion projection"):
            dispatcher.run_once(admit=False)
        assert work.read("turn")["tasks"]["post"]["status"] == "running"
        assert events.read("stream")["events"] == []
        dispatcher.completion_mutations = lambda lease, result: terminal(events, result)
        dispatcher.run_once(admit=False)
        assert work.read("turn")["tasks"]["post"]["status"] == "done"
        assert events.read("stream")["closed"]
    finally:
        dispatcher.close()
        state.close()
