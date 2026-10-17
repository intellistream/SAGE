import asyncio

import pytest

from sage.runtime.async_work_service import AsyncWorkService
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_dispatcher import WorkFailure
from sage.runtime.work_journal import WorkJournal
from sage.runtime.work_service import WorkFailedError


def admit(journal):
    return journal.commit("r", result=None, tasks={"answer": {}, "deliver": {}, "finalize": {}},
                          dependencies={"deliver": ["answer"], "finalize": ["answer", "deliver"]},
                          settled=["finalize"])


def test_offline_extension_preserves_failure_and_rejects_live_or_changed_work(tmp_path):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(state, namespace="finalizers")
    try:
        journal.commit("r", result="original result", tasks={"answer": {"original": True}})
        lease = journal.claim("r", "answer", lease_seconds=30)
        extension = dict(tasks={"notice": {"safe": True}}, dependencies={"notice": ["answer"]}, settled=["notice"])
        with pytest.raises(ValueError, match="live_leases"):
            journal.extend_tasks("r", **extension)
        journal.fail(lease, code="exhausted")
        old = journal.read("r")
        record = journal.extend_tasks("r", **extension)
        assert record["result"] == old["result"]
        assert record["tasks"]["answer"] == old["tasks"]["answer"]
        assert journal.extend_tasks("r", **extension) == record
        with pytest.raises(ValueError, match="conflict"):
            journal.extend_tasks("r", tasks={"notice": {"changed": True}},
                                 dependencies={"notice": ["answer"]}, settled=["notice"])
        notice = journal.claim("r", "notice", lease_seconds=30)
        assert notice.attempt == 1
        assert journal.extend_tasks("r", **extension)["tasks"]["notice"]["attempt"] == 1
        journal.finish(notice, result="accepted")
        journal.extend_tasks("r", tasks={"dependent": {}}, dependencies={"dependent": ["answer"]})
        assert journal.read("r")["tasks"]["dependent"]["status"] == "blocked"
        assert journal.claim("r", "dependent", lease_seconds=30) is None
    finally:
        state.close()


@pytest.mark.parametrize("settled", ["finalize", ["unknown"], ["answer"], ["finalize", "finalize"]])
def test_invalid_finalizer_admission_is_atomic(tmp_path, settled):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(state, namespace="finalizers")
    try:
        with pytest.raises(ValueError):
            journal.commit("r", result=None, tasks={"answer": {}, "finalize": {}},
                           dependencies={"finalize": ["answer"]}, settled=settled)
        assert journal.read("r") is None
    finally:
        state.close()


def test_finalizer_waits_for_all_parents_and_recovers_after_failure(tmp_path):
    path = str(tmp_path / "state.db")
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = WorkJournal(state, namespace="finalizers")
    admit(journal)
    answer = journal.claim("r", "answer", lease_seconds=30)
    assert journal.claim("r", "finalize", lease_seconds=30) is None
    journal.finish(answer, result="answer")
    assert journal.claim("r", "finalize", lease_seconds=30) is None
    deliver = journal.claim("r", "deliver", lease_seconds=30)
    journal.fail(deliver, code="unavailable", retry_delay=0)
    assert journal.claim("r", "finalize", lease_seconds=30) is None
    deliver = journal.claim("r", "deliver", lease_seconds=30)
    journal.fail(deliver, code="exhausted")
    assert journal.read("r")["version"] == 5
    state.close()
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    try:
        journal = WorkJournal(state, namespace="finalizers")
        assert admit(journal)["tasks"]["finalize"]["status"] == "pending"
        lease = journal.claim("r", "finalize", lease_seconds=30)
        assert lease.attempt == 1
        journal.finish(lease, result="notice receipt")
        assert journal.read("r")["tasks"]["deliver"]["status"] == "failed"
        assert journal.claim("r", "finalize", lease_seconds=30) is None
        with pytest.raises(ValueError, match="commit_conflict"):
            journal.commit("r", result=None, tasks={"answer": {}, "deliver": {}, "finalize": {}},
                           dependencies={"deliver": ["answer"], "finalize": ["answer", "deliver"]})
    finally:
        state.close()


@pytest.mark.parametrize("fail_answer", [False, True])
def test_native_dispatch_runs_finalizer_after_success_or_blocked_dependency(tmp_path, fail_answer):
    async def scenario():
        state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
        journal = WorkJournal(state, namespace="finalizers")
        calls, finalized = [], asyncio.Event()
        async def handler(lease):
            calls.append(lease.task_id)
            if lease.task_id == "answer" and fail_answer:
                raise ValueError("fixture")
            if lease.task_id == "finalize":
                record = journal.read("r")
                assert all(record["tasks"][name]["status"] in {"done", "failed", "blocked"}
                           for name in ("answer", "deliver"))
                finalized.set()
            return lease.task_id
        service = AsyncWorkService(journal, handler, poll_interval=0.01,
                                   failure_policy=lambda *_: WorkFailure("invalid_request"))
        try:
            await service.commit("r", result=None, tasks={"answer": {}, "deliver": {}, "finalize": {}},
                                 dependencies={"deliver": ["answer"], "finalize": ["answer", "deliver"]},
                                 settled=["finalize"])
            await asyncio.wait_for(finalized.wait(), 3)
            await service.aclose()  # Drain and fence finalizer acknowledgement.
            assert calls == (["answer", "finalize"] if fail_answer else ["answer", "deliver", "finalize"])
            if fail_answer:
                with pytest.raises(WorkFailedError):
                    await service.wait("r", timeout=0)
            else:
                assert (await service.wait("r", timeout=0))["tasks"]["finalize"]["status"] == "done"
        finally:
            await service.aclose()
            state.close()
    asyncio.run(scenario())
