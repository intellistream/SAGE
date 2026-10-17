import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import StaleTaskLeaseError, WorkJournal

DESTINATION = ("memory", "tenant", "answer")


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
@pytest.mark.parametrize("loss", ["expiry", "reclaim", "finish", "failure"])
def test_lost_upstream_lease_cannot_admit_downstream_answer(tmp_path, backend, loss):
    store = StatefulProcessRuntime(backend=backend, sqlite_path=str(tmp_path / "state.db"))
    now = [10.0]
    source = WorkJournal(store, namespace="source", clock=lambda: now[0])
    target = WorkJournal(store, namespace="target", clock=lambda: now[0])
    source.commit("request", result=None, tasks={"answer": {}})
    lease = source.claim("request", "answer", lease_seconds=5)
    guard = source.prepare_guard(lease)
    called = []
    try:
        if loss in {"expiry", "reclaim"}:
            now[0] = 15.0
        if loss == "reclaim":
            assert source.claim("request", "answer", lease_seconds=5).token != lease.token
        if loss == "finish":
            source.finish(lease, result="done")
        if loss == "failure":
            source.fail(lease, code="cancelled")
        before = source.read("request")
        with pytest.raises(StaleTaskLeaseError):
            target.commit("turn", result="answer", tasks={"post": {}}, guard=guard,
                          mutations={DESTINATION: lambda old: called.append(True) or "new"})
        assert called == []
        assert target.read("turn") is None
        assert store.peek(DESTINATION) is None
        assert store.peek(("sage-work-active-v1", "target", "turn")) is None
        assert source.read("request") == before
    finally:
        store.close()


def test_guard_reads_renewed_lease_and_composes_atomic_rollback(tmp_path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    now = [10.0]
    source = WorkJournal(store, namespace="source", clock=lambda: now[0])
    target = WorkJournal(store, namespace="target", clock=lambda: now[0])
    source.commit("request", result=None, tasks={"answer": {}})
    lease = source.claim("request", "answer", lease_seconds=5)
    guard = source.prepare_guard(lease)
    try:
        now[0] = 14.0
        source.renew(lease, lease_seconds=5)
        now[0] = 16.0  # Captured lease's original deadline has passed.
        before = source.read("request")
        with pytest.raises((TypeError, AttributeError)):
            target.commit("turn", result="answer", tasks={"post": {}}, guard=guard,
                          mutations={DESTINATION: lambda old: lambda: None})
        assert target.read("turn") is None and store.peek(DESTINATION) is None
        assert source.read("request") == before
        target.commit("turn", result="answer", tasks={"post": {}}, guard=guard,
                      mutations={DESTINATION: lambda old: old or "canonical"})
        assert store.peek(DESTINATION) == "canonical"
        assert source.read("request") == before  # No implicit acknowledgement or renewal.
        assert target.read("turn")["tasks"]["post"]["status"] == "pending"
        with pytest.raises(ValueError, match="overlap"):
            source.commit("request", result=None, tasks={"answer": {}}, guard=guard)
        other = StatefulProcessRuntime(backend="memory")
        try:
            with pytest.raises(ValueError, match="share_state_store"):
                WorkJournal(other, namespace="other").commit("turn", result=None, tasks={}, guard=guard)
        finally:
            other.close()
    finally:
        store.close()


def test_other_connection_reclaim_is_seen_inside_guard_transaction(tmp_path):
    path = str(tmp_path / "state.db")
    first = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    second = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    now = [0.0]
    source = WorkJournal(first, namespace="source", clock=lambda: now[0])
    replacement = WorkJournal(second, namespace="source", clock=lambda: now[0])
    source.commit("request", result=None, tasks={"answer": {}})
    guard = source.prepare_guard(source.claim("request", "answer", lease_seconds=5))
    try:
        now[0] = 5.0
        current = replacement.claim("request", "answer", lease_seconds=5)
        with pytest.raises(StaleTaskLeaseError):
            WorkJournal(first, namespace="target").commit("turn", result="stale", tasks={}, guard=guard,
                mutations={DESTINATION: lambda old: "stale"})
        WorkJournal(second, namespace="target").commit("turn", result="current", tasks={},
            guard=replacement.prepare_guard(current), mutations={DESTINATION: lambda old: "current"})
        assert first.peek(DESTINATION) == "current"
    finally:
        second.close()
        first.close()
