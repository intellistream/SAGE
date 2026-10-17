import pytest

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import StaleTaskLeaseError, WorkJournal

ANSWER = ("answers", "owner", "turn")


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
@pytest.mark.parametrize("running", [False, True])
def test_cancel_fences_execution_and_preserves_finalizers(tmp_path, backend, running):
    state = StatefulProcessRuntime(backend=backend, sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(state, namespace="work")
    try:
        journal.commit("turn", result=None, tasks={"answer": {}, "deliver": {}, "finalize": {}},
                       dependencies={"deliver": ["answer"], "finalize": ["answer", "deliver"]},
                       settled=["finalize"])
        lease = journal.claim("turn", "answer", lease_seconds=60) if running else None
        assert journal.cancel("turn", "answer") == "cancelled"
        assert journal.cancel("turn", "answer") == "terminal"
        tasks = journal.read("turn")["tasks"]
        assert tasks["answer"]["failure_code"] == "request_cancelled"
        assert tasks["deliver"]["status"] == "blocked"
        assert tasks["finalize"]["status"] == "pending"
        assert journal.claim("turn", "answer", lease_seconds=60) is None
        if lease:
            with pytest.raises(StaleTaskLeaseError):
                journal.finish(lease, result="stale")
        finalizer = journal.claim("turn", "finalize", lease_seconds=60)
        journal.finish(finalizer)
        assert state.peek(("sage-work-active-v1", "work", "turn")) is None
    finally:
        state.close()


@pytest.mark.parametrize("answer_first", [False, True])
def test_cancel_and_canonical_commit_are_serialized_across_connections(tmp_path, answer_first):
    path = str(tmp_path / "state.db")
    first = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    second = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    source = WorkJournal(first, namespace="work")
    canceller = WorkJournal(second, namespace="work")
    target = WorkJournal(first, namespace="post")
    try:
        source.commit("turn", result=None, tasks={"answer": {}})
        lease = source.claim("turn", "answer", lease_seconds=60)
        def commit():
            target.commit("turn", result="answer", tasks={}, guard=source.prepare_guard(lease),
                          mutations={ANSWER: lambda old: "canonical"})
        if answer_first:
            commit()
        outcome = canceller.cancel("turn", "answer", protect={ANSWER: lambda old: old is not None})
        assert outcome == ("protected" if answer_first else "cancelled")
        if not answer_first:
            with pytest.raises(StaleTaskLeaseError):
                commit()
            assert target.read("turn") is None
        assert first.peek(ANSWER) == ("canonical" if answer_first else None)
    finally:
        second.close()
        first.close()


def test_missing_and_invalid_predicate_do_not_mutate_state(tmp_path):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(state, namespace="work")
    try:
        assert journal.cancel("missing", "answer") == "missing"
        assert journal.read("missing") is None
        journal.commit("turn", result=None, tasks={"answer": {}})
        before = journal.read("turn")
        with pytest.raises(TypeError, match="must_return_bool"):
            journal.cancel("turn", "answer", protect={ANSWER: lambda old: "truthy"})
        assert journal.read("turn") == before
        assert state.peek(ANSWER) is None
    finally:
        state.close()


def test_concurrent_cancel_and_answer_have_exactly_one_winner(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    path = str(tmp_path / "state.db")
    first = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    second = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    source = WorkJournal(first, namespace="work")
    canceller = WorkJournal(second, namespace="work")
    target = WorkJournal(first, namespace="post")
    try:
        for index in range(12):
            key = str(index)
            destination = ("answers", "owner", key)
            source.commit(key, result=None, tasks={"answer": {}})
            lease = source.claim(key, "answer", lease_seconds=60)
            barrier = Barrier(2)
            def answer(barrier=barrier, key=key, lease=lease, destination=destination):
                barrier.wait(timeout=3)
                try:
                    target.commit(key, result="answer", tasks={}, guard=source.prepare_guard(lease),
                                  mutations={destination: lambda old: "canonical"})
                    return "committed"
                except StaleTaskLeaseError:
                    return "fenced"
            def cancel(barrier=barrier, key=key, destination=destination):
                barrier.wait(timeout=3)
                return canceller.cancel(key, "answer", protect={destination: lambda old: old is not None})
            with ThreadPoolExecutor(max_workers=2) as pool:
                completed, cancelled = pool.submit(answer), pool.submit(cancel)
                result = (completed.result(timeout=5), cancelled.result(timeout=5))
            assert result in {("committed", "protected"), ("fenced", "cancelled")}
            assert (first.peek(destination) is not None) == (result[0] == "committed")
    finally:
        second.close()
        first.close()


def test_cancellation_storage_failure_rolls_back_lease_and_index(tmp_path, monkeypatch):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(state, namespace="work")
    try:
        journal.commit("turn", result=None, tasks={"answer": {}})
        lease = journal.claim("turn", "answer", lease_seconds=60)
        before = journal.read("turn")
        original = state._backend._put_uncommitted
        def unavailable(slot, entry):
            original(slot, entry)
            if slot[0] == "sage-work-journal-v1":
                raise OSError("injected cancellation write failure")
        monkeypatch.setattr(state._backend, "_put_uncommitted", unavailable)
        with pytest.raises(OSError, match="injected"):
            journal.cancel("turn", "answer")
        assert journal.read("turn") == before
        assert state.peek(("sage-work-active-v1", "work", "turn")) is True
        monkeypatch.setattr(state._backend, "_put_uncommitted", original)
        journal.finish(lease, result="still valid")
        assert journal.cancel("turn", "answer") == "terminal"
    finally:
        state.close()


def test_async_service_cancels_queued_work_without_executing_it(tmp_path):
    import asyncio

    from sage.runtime.async_work_service import AsyncWorkService
    from sage.runtime.work_service import WorkFailedError

    async def scenario():
        state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
        journal = WorkJournal(state, namespace="work")
        entered, release = asyncio.Event(), asyncio.Event()
        seen = []
        async def handler(lease):
            seen.append(lease.request_id)
            entered.set()
            await release.wait()
        service = AsyncWorkService(journal, handler, max_workers=1, poll_interval=0.01)
        try:
            await service.commit("a", result=None, tasks={"answer": {}})
            await asyncio.wait_for(entered.wait(), 3)
            await service.commit("b", result=None, tasks={"answer": {}})
            assert await service.cancel("b", "answer") == "cancelled"
            with pytest.raises(WorkFailedError):
                await service.wait("b", timeout=3)
            release.set()
            await service.wait("a", timeout=3)
            assert seen == ["a"]
            assert journal.read("b")["tasks"]["answer"]["attempt"] == 0
        finally:
            release.set()
            await service.aclose()
            state.close()
    asyncio.run(scenario())
