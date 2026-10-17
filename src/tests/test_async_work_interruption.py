import asyncio

import pytest

from sage.runtime.async_work_service import AsyncWorkService
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkJournal


def test_remote_cancel_interrupts_handler_but_waits_for_cleanup(tmp_path):
    async def scenario():
        path = str(tmp_path / "state.db")
        state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
        remote_state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
        journal = WorkJournal(state, namespace="jobs")
        remote = WorkJournal(remote_state, namespace="jobs")
        entered, cleaning, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        seen = []

        async def handler(lease):
            seen.append(lease.request_id)
            if lease.request_id == "a":
                entered.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cleaning.set()
                    await release.wait()
            return "done"

        service = AsyncWorkService(journal, handler, max_workers=1, poll_interval=0.01)
        try:
            await service.commit("a", result=None, tasks={"answer": {}})
            await asyncio.wait_for(entered.wait(), 3)
            assert await asyncio.to_thread(remote.cancel, "a", "answer") == "cancelled"
            await asyncio.wait_for(cleaning.wait(), 3)
            await service.commit("b", result=None, tasks={"answer": {}})
            await asyncio.sleep(0.05)
            assert seen == ["a"]
            assert journal.read("b")["tasks"]["answer"]["attempt"] == 0
            release.set()
            assert (await service.wait("b", timeout=3))["tasks"]["answer"]["result"] == "done"
            assert journal.read("a")["tasks"]["answer"]["failure_code"] == "request_cancelled"
            assert seen == ["a", "b"]
            assert not service._executions
        finally:
            release.set()
            await service.aclose()
            remote_state.close()
            state.close()
    asyncio.run(scenario())


def test_loss_before_coroutine_registration_never_starts_handler(tmp_path):
    async def scenario():
        state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
        journal = WorkJournal(state, namespace="jobs")
        calls = []
        async def handler(lease):
            calls.append(lease)
        service = AsyncWorkService(journal, handler, poll_interval=0.01)
        try:
            journal.commit("a", result=None, tasks={"answer": {}})
            lease = journal.claim("a", "answer", lease_seconds=60)
            journal.cancel("a", "answer")
            service._lease_lost(lease)
            await asyncio.sleep(0)  # Loss callback arrives before registration.
            from sage.runtime.work_journal import StaleTaskLeaseError
            with pytest.raises(StaleTaskLeaseError):
                await service._execute(lease)
            assert calls == [] and not service._executions
        finally:
            await service.aclose()
            state.close()
    asyncio.run(scenario())
