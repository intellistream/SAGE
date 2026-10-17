import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkJournal
from sage.runtime.work_dispatcher import WorkDispatcher
from sage.runtime.work_service import WorkService


def test_disjoint_consumers_never_claim_another_projection(tmp_path):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(state, namespace="index")
    for key in ("a", "b", "unassigned"):
        journal.commit(key, result=None, tasks={"index": {"projection": key}})
    seen = []
    def worker(key):
        return WorkService(journal, lambda lease: seen.append(lease.payload["projection"]),
                           accept_task=lambda task, payload: payload["projection"] == key,
                           poll_interval=0.01, page_size=1)
    first, second = worker("a"), worker("b")
    try:
        first.start()
        second.start()
        first.wait("a", timeout=3)
        second.wait("b", timeout=3)
        assert sorted(seen) == ["a", "b"]
        for key in ("a", "b"):
            assert journal.read(key)["tasks"]["index"]["attempt"] == 1
        unassigned = journal.read("unassigned")["tasks"]["index"]
        assert unassigned["attempt"] == 0 and unassigned["status"] == "pending"
    finally:
        first.close()
        second.close()
        state.close()


@pytest.mark.parametrize("outcome", ["error", "not-bool"])
def test_selector_failure_does_not_claim_or_acknowledge(tmp_path, outcome):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(state, namespace="index")
    journal.commit("one", result=None, tasks={"index": {"projection": "a"}})
    def select(task, payload):
        if outcome == "error":
            raise ValueError("invalid routing configuration")
        return "yes"
    worker = WorkDispatcher(journal, lambda lease: pytest.fail("must not run"), accept_task=select)
    try:
        with pytest.raises((ValueError, TypeError)):
            worker.run_once()
        task = journal.read("one")["tasks"]["index"]
        assert task["attempt"] == 0 and task["status"] == "pending"
    finally:
        worker.close()
        state.close()


def test_selector_cannot_rewrite_authoritative_payload(tmp_path):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(state, namespace="index")
    journal.commit("one", result=None, tasks={"index": {"projection": "a"}})
    def select(task, payload):
        payload["projection"] = "tampered"
        return True
    worker = WorkService(journal, lambda lease: lease.payload, accept_task=select, poll_interval=0.01)
    try:
        worker.start()
        result = worker.wait("one", timeout=3)
        assert result["tasks"]["index"]["result"] == {"projection": "a"}
    finally:
        worker.close()
        state.close()
