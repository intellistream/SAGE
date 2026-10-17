import asyncio

import pytest

from sage.runtime.async_work_service import AsyncWorkService
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_dispatcher import WorkFailure
from sage.runtime.work_journal import StaleTaskLeaseError, WorkJournal
from sage.runtime.work_service import WorkFailedError


def test_terminal_failure_blocks_descendants_and_survives_restart(tmp_path):
    path = str(tmp_path / "state.db")
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = WorkJournal(state, namespace="failure")
    journal.commit("r", result=None, tasks={"a": {}, "b": {}, "c": {}},
                   dependencies={"b": ["a"], "c": ["b"]})
    lease = journal.claim("r", "a", lease_seconds=30)
    journal.fail(lease, code="invalid_request")
    state.close()
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        journal = WorkJournal(state, namespace="failure")
        record = journal.read("r")
        assert record["version"] == 3
        assert [record["tasks"][key]["status"] for key in ("a", "b", "c")] == ["failed", "blocked", "blocked"]
        for key in record["tasks"]:
            assert journal.claim("r", key, lease_seconds=30) is None
        with pytest.raises(StaleTaskLeaseError):
            journal.fail(lease, code="late_worker")
    finally:
        state.close()


def test_retry_failure_is_fenced_and_delayed(tmp_path):
    clock = [0.0]
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(state, namespace="failure", clock=lambda: clock[0])
    try:
        journal.commit("r", result=None, tasks={"a": {}})
        lease = journal.claim("r", "a", lease_seconds=1)
        clock[0] = 2
        with pytest.raises(StaleTaskLeaseError):
            journal.fail(lease, code="temporary", retry_delay=3)
        current = journal.claim("r", "a", lease_seconds=10)
        with pytest.raises(ValueError, match="failure_code"):
            journal.fail(current, code="raw error text: credential")
        journal.fail(current, code="temporary", retry_delay=3)
        assert journal.claim("r", "a", lease_seconds=10) is None
        clock[0] = 6
        last = journal.claim("r", "a", lease_seconds=10)
        assert last.attempt == 3
        journal.finish(last, result="recovered")
        assert journal.read("r")["tasks"]["a"]["result"] == "recovered"
    finally:
        state.close()


def test_async_policy_stops_at_attempt_limit_without_delivering_or_exposing_exception(tmp_path):
    async def scenario():
        state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
        journal = WorkJournal(state, namespace="failure")
        calls = []
        async def handler(lease):
            calls.append(lease.task_id)
            raise OSError("private exception text")
        def policy(lease, error):
            assert isinstance(error, OSError)
            return WorkFailure("transport_unavailable", 0 if lease.attempt < 2 else None)
        service = AsyncWorkService(journal, handler, poll_interval=0.01, failure_policy=policy)
        try:
            await service.commit("r", result=None, tasks={"answer": {}, "deliver": {}},
                                 dependencies={"deliver": ["answer"]})
            with pytest.raises(WorkFailedError):
                await service.wait("r", timeout=3)
            assert calls == ["answer", "answer"]
            record = journal.read("r")
            assert record["tasks"]["answer"]["attempt"] == 2
            assert record["tasks"]["deliver"]["attempt"] == 0
            assert "private exception" not in str(record)
            await service.aclose()
            replacement = AsyncWorkService(journal, handler, poll_interval=0.01, failure_policy=policy)
            try:
                await replacement.start()
                with pytest.raises(WorkFailedError):
                    await replacement.wait("r", timeout=3)
                await asyncio.sleep(0.03)
                assert calls == ["answer", "answer"]
            finally:
                await replacement.aclose()
        finally:
            await service.aclose()
            state.close()
    asyncio.run(scenario())
