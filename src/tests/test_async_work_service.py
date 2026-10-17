import asyncio
from threading import Event

import pytest

from sage.runtime.async_work_service import AsyncWorkService
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkJournal
from sage.runtime.work_service import WorkWaitTimeoutError


def state(path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(path))
    return store, WorkJournal(store, namespace="async-test")


def test_async_recovery_runs_on_owner_loop_and_keeps_results(tmp_path):
    path = tmp_path / "state.db"
    store, journal = state(path)
    journal.commit("turn", result="answer", tasks={"deliver": {"value": 1}})
    store.close()

    async def scenario():
        store, journal = state(path)
        loop = asyncio.get_running_loop()
        async def handler(lease):
            assert asyncio.get_running_loop() is loop
            await asyncio.sleep(0)
            return {"receipt": lease.payload["value"]}
        service = AsyncWorkService(journal, handler, poll_interval=0.01)
        try:
            await service.start()
            result = await service.wait("turn", timeout=3)
            assert result["tasks"]["deliver"]["result"] == {"receipt": 1}
            assert result["result"] == "answer"
        finally:
            await service.aclose()
            store.close()
    asyncio.run(scenario())


def test_failed_async_handler_retries_without_cancelling_observer(tmp_path):
    async def scenario():
        store, journal = state(tmp_path / "state.db")
        entered, release = asyncio.Event(), asyncio.Event()
        attempts = []
        async def handler(lease):
            attempts.append(lease.attempt)
            if len(attempts) == 1:
                raise OSError("transient")
            entered.set()
            await release.wait()
            return "delivered"
        service = AsyncWorkService(journal, handler, poll_interval=0.01, retry_delay=0)
        try:
            await service.commit("turn", result=None, tasks={"deliver": {}})
            await asyncio.wait_for(entered.wait(), 3)
            observer = asyncio.create_task(service.wait("turn", timeout=30))
            await asyncio.sleep(0.02)
            observer.cancel()
            with pytest.raises(asyncio.CancelledError):
                await observer
            release.set()
            result = await service.wait("turn", timeout=3)
            assert result["tasks"]["deliver"]["result"] == "delivered"
            assert len(attempts) == 2
        finally:
            release.set()
            await service.aclose()
            store.close()
    asyncio.run(scenario())


def test_repeated_close_cancellation_drains_before_releasing_storage(tmp_path):
    async def scenario():
        store, journal = state(tmp_path / "state.db")
        entered, release = asyncio.Event(), asyncio.Event()
        async def handler(lease):
            entered.set()
            await release.wait()
            return "done"
        service = AsyncWorkService(journal, handler, poll_interval=0.01)
        try:
            await service.commit("turn", result=None, tasks={"deliver": {}})
            await entered.wait()
            closing = asyncio.create_task(service.aclose(timeout=3))
            await asyncio.sleep(0.02)
            closing.cancel()
            await asyncio.sleep(0.02)
            closing.cancel()
            await asyncio.sleep(0.02)
            assert not closing.done()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await closing
            assert journal.read("turn")["tasks"]["deliver"]["result"] == "done"
        finally:
            release.set()
            await service.aclose()
            store.close()
    asyncio.run(scenario())


def test_cancelled_commit_drains_transaction_and_recovers_ack(tmp_path, monkeypatch):
    async def scenario():
        store, journal = state(tmp_path / "state.db")
        entered, release = Event(), Event()
        original = journal.commit
        def commit(*args, **kwargs):
            entered.set()
            assert release.wait(3)
            return original(*args, **kwargs)
        monkeypatch.setattr(journal, "commit", commit)
        async def handler(lease):
            return "done"
        service = AsyncWorkService(journal, handler, poll_interval=0.01)
        try:
            pending = asyncio.create_task(service.commit("turn", result="answer", tasks={"deliver": {}}))
            assert await asyncio.to_thread(entered.wait, 3)
            pending.cancel()
            await asyncio.sleep(0.02)
            assert not pending.done()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await pending
            assert (await service.wait("turn", timeout=3))["result"] == "answer"
        finally:
            release.set()
            await service.aclose()
            store.close()
    asyncio.run(scenario())


def test_close_timeout_keeps_pending_work_recoverable_and_rejects_admission(tmp_path):
    async def scenario():
        store, journal = state(tmp_path / "state.db")
        entered, release = asyncio.Event(), asyncio.Event()
        async def handler(lease):
            entered.set()
            await release.wait()
            return "done"
        service = AsyncWorkService(journal, handler, poll_interval=0.01, max_workers=1)
        try:
            await service.commit("turn", result=None, tasks={"first": {}, "queued": {}})
            await entered.wait()
            with pytest.raises(TimeoutError, match="drain_timeout"):
                await service.aclose(timeout=0)
            with pytest.raises(RuntimeError, match="closing"):
                await service.commit("late", result=None, tasks={})
            release.set()
            await service.aclose()
            assert journal.read("turn")["tasks"]["queued"]["status"] == "pending"
            recovered = AsyncWorkService(journal, handler, poll_interval=0.01)
            try:
                await recovered.start()
                result = await recovered.wait("turn", timeout=3)
                assert result["tasks"]["first"]["attempt"] == 1
                assert result["tasks"]["queued"]["status"] == "done"
            finally:
                await recovered.aclose()
        finally:
            release.set()
            await service.aclose()
            store.close()
    asyncio.run(scenario())


def test_handler_cannot_deadlock_its_own_service(tmp_path):
    async def scenario():
        store, journal = state(tmp_path / "state.db")
        async def handler(lease):
            with pytest.raises(RuntimeError, match="cannot_wait_or_close"):
                await service.aclose()
            with pytest.raises(RuntimeError, match="cannot_wait_or_close"):
                await service.wait("turn", timeout=1)
            return "done"
        service = AsyncWorkService(journal, handler, poll_interval=0.01)
        try:
            await service.commit("turn", result=None, tasks={"deliver": {}})
            await service.wait("turn", timeout=3)
        finally:
            await service.aclose()
            store.close()
    asyncio.run(scenario())


def test_async_handler_keeps_existing_bounds_and_atomic_completion(tmp_path):
    async def scenario():
        store, journal = state(tmp_path / "state.db")
        active, peak = 0, 0
        class Handler:
            async def __call__(self, lease):
                nonlocal active, peak
                active += 1
                peak = max(peak, active)
                await asyncio.sleep(0.03)
                active -= 1
                return lease.task_id
        def completion(lease, result):
            return {("receipts", "external", lease.task_id): lambda _: result}
        service = AsyncWorkService(journal, Handler(), max_workers=2, poll_interval=0.01,
                                   completion_mutations=completion)
        try:
            await service.commit("turn", result=None, tasks={str(index): {} for index in range(5)})
            await service.wait("turn", timeout=3)
            assert peak == 2
            for index in range(5):
                assert store.peek(("receipts", "external", str(index))) == str(index)
        finally:
            await service.aclose()
            store.close()
    asyncio.run(scenario())


def test_loop_mismatch_is_rejected_before_start(tmp_path):
    store, journal = state(tmp_path / "state.db")
    async def make():
        async def handler(lease):
            return None
        service = AsyncWorkService(journal, handler)
        await service.aclose()
        return service
    service = asyncio.run(make())
    async def wrong_loop():
        with pytest.raises(RuntimeError, match="loop_mismatch"):
            await service.start()
    try:
        asyncio.run(wrong_loop())
    finally:
        store.close()


def test_storage_timeout_is_not_hidden_as_observer_polling(tmp_path, monkeypatch):
    async def scenario():
        store, journal = state(tmp_path / "state.db")
        async def handler(lease):
            return None
        service = AsyncWorkService(journal, handler)
        failure = TimeoutError("storage failed")
        reads = []
        def read(*args):
            reads.append(args)
            raise failure
        monkeypatch.setattr(journal, "read", read)
        try:
            with pytest.raises(TimeoutError) as captured:
                await service.wait("turn", timeout=30)
            # asyncio may reconstruct a concurrent-future TimeoutError.
            assert str(captured.value) == "storage failed"
            assert not isinstance(captured.value, WorkWaitTimeoutError)
            assert len(reads) == 1
        finally:
            await service.aclose()
            store.close()
    asyncio.run(scenario())
