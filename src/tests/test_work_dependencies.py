import asyncio

import pytest

from sage.runtime.async_work_service import AsyncWorkService
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkJournal


def make(path, **kwargs):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(path))
    return state, WorkJournal(state, namespace="dependencies", **kwargs)


@pytest.mark.parametrize("graph", [{"b": ["missing"]}, {"unknown": ["a"]}, {"a": ["a"]},
                                    {"a": ["b"], "b": ["a"]}, {"b": "a"}, {"b": ["a", "a"]}])
def test_invalid_graph_never_admits(tmp_path, graph):
    state, journal = make(tmp_path / "state.db")
    try:
        with pytest.raises(ValueError):
            journal.commit("turn", result=None, tasks={"a": {}, "b": {}}, dependencies=graph)
        assert journal.read("turn") is None
    finally:
        state.close()


def test_dependency_claim_is_fenced_by_all_completed_parents_across_reopen(tmp_path):
    path = tmp_path / "state.db"
    state, journal = make(path)
    journal.commit("turn", result=None, tasks={"a": {}, "b": {}, "c": {}}, dependencies={"c": ["b", "a"]})
    a = journal.claim("turn", "a", lease_seconds=60)
    journal.finish(a, retry=True)
    assert journal.claim("turn", "c", lease_seconds=60) is None
    a = journal.claim("turn", "a", lease_seconds=60)
    journal.finish(a, result="A")
    state.close()
    state, journal = make(path)
    try:
        assert journal.claim("turn", "c", lease_seconds=60) is None
        assert journal.read("turn")["tasks"]["c"]["attempt"] == 0
        b = journal.claim("turn", "b", lease_seconds=60)
        journal.finish(b, result="B")
        assert journal.claim("turn", "c", lease_seconds=60).attempt == 1
        with pytest.raises(ValueError, match="commit_conflict"):
            journal.commit("turn", result=None, tasks={"a": {}, "b": {}, "c": {}}, dependencies={"c": ["a"]})
    finally:
        state.close()


def test_upgrade_rejects_live_leases_and_preserves_immutable_graph(tmp_path):
    clock = [0.0]
    state, journal = make(tmp_path / "state.db", clock=lambda: clock[0])
    try:
        journal.commit("turn", result=None, tasks={"a": {}, "b": {}})
        journal.claim("turn", "a", lease_seconds=1)
        with pytest.raises(ValueError, match="live_leases"):
            journal.upgrade_dependencies("turn", {"b": ["a"]})
        assert journal.read("turn")["version"] == 1
        clock[0] = 2
        journal.upgrade_dependencies("turn", {"b": ["a"]})
        assert journal.read("turn")["version"] == 2
        assert journal.claim("turn", "b", lease_seconds=1) is None
        with pytest.raises(ValueError, match="immutable"):
            journal.upgrade_dependencies("turn", {"a": ["b"]})
    finally:
        state.close()


def test_upgrade_rejects_already_completed_child_with_pending_parent(tmp_path):
    state, journal = make(tmp_path / "state.db")
    try:
        journal.commit("turn", result=None, tasks={"a": {}, "b": {}})
        b = journal.claim("turn", "b", lease_seconds=60)
        journal.finish(b, result=None)
        with pytest.raises(ValueError, match="unfinished_dependencies"):
            journal.upgrade_dependencies("turn", {"b": ["a"]})
        assert journal.read("turn")["version"] == 1
    finally:
        state.close()


def test_async_dispatch_dependency_does_not_retry_or_pay_failure_backoff(tmp_path):
    async def scenario():
        state, journal = make(tmp_path / "state.db")
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []
        async def handler(lease):
            calls.append(lease.task_id)
            if lease.task_id == "answer":
                entered.set()
                await release.wait()
            else:
                assert journal.read("turn")["tasks"]["answer"]["status"] == "done"
            return lease.task_id
        service = AsyncWorkService(journal, handler, poll_interval=0.01, retry_delay=60)
        try:
            await service.commit("turn", result=None, tasks={"answer": {}, "deliver": {}},
                                 dependencies={"deliver": ["answer"]})
            await asyncio.wait_for(entered.wait(), 3)
            await asyncio.sleep(0.05)
            assert calls == ["answer"]
            assert journal.read("turn")["tasks"]["deliver"]["attempt"] == 0
            release.set()
            result = await service.wait("turn", timeout=1)
            assert calls == ["answer", "deliver"]
            assert result["tasks"]["deliver"]["attempt"] == 1
        finally:
            release.set()
            await service.aclose()
            state.close()
    asyncio.run(scenario())
