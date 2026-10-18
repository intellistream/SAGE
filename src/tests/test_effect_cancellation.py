import asyncio
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import pytest

from sage.runtime.effect_cancellation import CancellationService, EffectCancelled, EffectFences
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.operation_receipts import OperationReceipts
from sage.runtime.work_journal import WorkJournal
from sage.runtime.work_service import WorkWaitTimeoutError

SLOT = ("fixture", "effects", "records")


@pytest.fixture
def stores(tmp_path):
    opened = []

    def create(name):
        store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / name))
        opened.append(store)
        return store

    yield create
    for store in reversed(opened):
        store.close()


def effect(store, guard, *, operation="create"):
    return OperationReceipts(store, namespace="effects").commit(
        operation, inputs={}, slots=[SLOT],
        transition=lambda values: ("created", {SLOT: (values[SLOT] or 0) + 1}), guard=guard)


def service(origin, targets, **options):
    return CancellationService(origin, task_id="answer", targets=targets,
                               poll_interval=0.01, retry_delay=0.01,
                               max_retry_delay=0.02, **options)


def test_prepared_guard_sees_other_connection_seal_and_denies_replay(stores):
    writer, canceller = stores("destination.db"), stores("destination.db")
    fences = EffectFences(writer, namespace="request")
    other = EffectFences(canceller, namespace="request")
    assert fences.identity == other.identity
    guard = fences.prepare_guard("turn")
    assert effect(writer, guard) == "created"
    other.seal("turn")
    for operation in ("create", "later"):
        with pytest.raises(EffectCancelled):
            effect(writer, guard, operation=operation)
    assert writer.peek(SLOT) == 1  # Past committed effects are not undone.
    assert fences.is_sealed("turn")
    assert effect(writer, fences.prepare_guard("different"), operation="different") == "created"


def test_cross_store_guard_and_overlap_fail_before_effect(stores):
    first, second = stores("first.db"), stores("second.db")
    guard = EffectFences(first, namespace="request").prepare_guard("turn")
    with pytest.raises(ValueError, match="share_state_store"):
        effect(second, guard)
    with pytest.raises(ValueError, match="overlap"):
        OperationReceipts(first, namespace="effects").commit(
            "attempt", inputs={}, slots=[guard.slot], transition=lambda _: None, guard=guard)
    assert first.peek(SLOT) is second.peek(SLOT) is None


def test_bad_persisted_fence_fails_closed(stores):
    store = stores("destination.db")
    fences = EffectFences(store, namespace="request")
    guard = fences.prepare_guard("turn")
    store.update(guard.slot, lambda _: {"version": 999, "sealed": False})
    with pytest.raises(ValueError, match="invalid_effect_fence"):
        effect(store, guard)
    with pytest.raises(ValueError, match="invalid_effect_fence"):
        fences.seal("turn")
    assert store.peek(SLOT) is None


def test_seal_race_serializes_with_destination_commit(stores):
    writer, canceller = stores("destination.db"), stores("destination.db")
    fences = EffectFences(writer, namespace="request")
    other = EffectFences(canceller, namespace="request")
    barrier = Barrier(2)

    def write():
        barrier.wait(3)
        try:
            return effect(writer, fences.prepare_guard("turn"))
        except EffectCancelled:
            return "denied"

    def seal():
        barrier.wait(3)
        other.seal("turn")

    with ThreadPoolExecutor(max_workers=2) as pool:
        writing, sealing = pool.submit(write), pool.submit(seal)
        result = writing.result(timeout=5)
        sealing.result(timeout=5)
    assert writer.peek(SLOT) == (1 if result == "created" else None)
    with pytest.raises(EffectCancelled):
        effect(writer, fences.prepare_guard("turn"), operation="after-ack")


def test_partial_destination_outage_never_acknowledges_cancellation(stores):
    source, first, second = stores("origin.db"), stores("one.db"), stores("two.db")
    origin = WorkJournal(source, namespace="http")
    origin.commit("turn", result=None, tasks={"answer": {}})
    available, attempted = Event(), Event()

    def late():
        attempted.set()
        if not available.is_set():
            raise OSError("private endpoint or credential must not persist")
        return EffectFences(second, namespace="request")

    # Resolve initial destination identity, then make its seal unavailable.
    second_fences = EffectFences(second, namespace="request")
    instance = service(origin, {"one": EffectFences(first, namespace="request"), "two": second_fences})
    original_start = instance._work.start
    instance._work.start = lambda: None
    try:
        instance._targets["two"] = late
        available.set()
        assert instance.request("turn") == "accepted"
        available.clear()
        attempted.clear()
        instance._work.start = original_start
        instance.start()
        assert attempted.wait(3)
        with pytest.raises(WorkWaitTimeoutError):
            instance.wait("turn", timeout=0.05)
        assert origin.read("turn")["tasks"]["answer"]["status"] == "pending"
        assert "private endpoint" not in repr(instance.journal.read("turn"))
        available.set()
        assert instance.wait("turn", timeout=5) == "cancelled"
        assert origin.read("turn")["tasks"]["answer"]["failure_code"] == "request_cancelled"
        assert EffectFences(first, namespace="request").is_sealed("turn")
        assert second_fences.is_sealed("turn")
    finally:
        available.set()
        instance.close()


def test_lost_origin_cancel_ack_is_recovered_as_cancelled(stores, monkeypatch):
    source, destination = stores("origin.db"), stores("target.db")
    origin = WorkJournal(source, namespace="http")
    origin.commit("turn", result=None, tasks={"answer": {}})
    cancel = origin.cancel
    attempts = []

    def lost(*args, **kwargs):
        result = cancel(*args, **kwargs)
        attempts.append(True)
        if len(attempts) == 1:
            raise OSError("lost cancel acknowledgement")
        return result

    monkeypatch.setattr(origin, "cancel", lost)
    instance = service(origin, {"target": EffectFences(destination, namespace="request")})
    try:
        instance.request("turn")
        assert instance.wait("turn", timeout=5) == "cancelled"
        assert len(attempts) == 2
        assert instance.request("turn") == "accepted"
        assert instance.wait("turn", timeout=5) == "cancelled"
    finally:
        instance.close()


def test_canonical_answer_protection_wins_without_undoing_effects(stores):
    source, destination = stores("origin.db"), stores("target.db")
    origin = WorkJournal(source, namespace="http")
    origin.commit("turn", result=None, tasks={"answer": {}})
    answer = ("fixture", "answers", "turn")
    source.update(answer, lambda _: "canonical answer")
    target = EffectFences(destination, namespace="request")
    effect(destination, target.prepare_guard("turn"))
    instance = service(origin, {"target": target}, protection=lambda _: {answer: lambda value: value is not None})
    try:
        instance.request("turn")
        assert instance.wait("turn", timeout=5) == "protected"
        assert source.peek(answer) == "canonical answer"
        assert destination.peek(SLOT) == 1
        assert origin.read("turn")["tasks"]["answer"]["status"] == "pending"
    finally:
        instance.close()


def test_destination_remapping_cannot_inherit_old_ack(stores):
    source, old, wrong = stores("origin.db"), stores("old.db"), stores("wrong.db")
    origin = WorkJournal(source, namespace="http")
    origin.commit("turn", result=None, tasks={"answer": {}})
    target = EffectFences(old, namespace="request")
    instance = service(origin, {"target": target})
    original_start = instance._work.start
    instance._work.start = lambda: None
    try:
        assert instance.request("turn") == "accepted"
        instance._targets["target"] = EffectFences(wrong, namespace="request")
        instance._work.start = original_start
        instance.start()
        with pytest.raises(WorkWaitTimeoutError):
            instance.wait("turn", timeout=0.08)
        assert origin.read("turn")["tasks"]["answer"]["status"] == "pending"
        instance._targets["target"] = target
        assert instance.wait("turn", timeout=5) == "cancelled"
    finally:
        instance.close()


def test_restart_rechecks_already_acknowledged_destination_binding(stores):
    source, old, wrong = stores("origin.db"), stores("old.db"), stores("wrong.db")
    origin = WorkJournal(source, namespace="http")
    origin.commit("turn", result=None, tasks={"answer": {}})
    target = EffectFences(old, namespace="request")
    entered = Event()

    def unavailable_protection(_):
        entered.set()
        raise OSError("origin temporarily unavailable")

    first = service(origin, {"target": target}, protection=unavailable_protection)
    try:
        first.request("turn")
        assert entered.wait(3)
    finally:
        first.close()
    record = first.journal.read("turn")
    assert record["tasks"]["seal:target"]["status"] == "done"
    second = service(origin, {"target": EffectFences(wrong, namespace="request")})
    try:
        second.start()
        with pytest.raises(WorkWaitTimeoutError):
            second.wait("turn", timeout=0.08)
        assert origin.read("turn")["tasks"]["answer"]["status"] == "pending"
        second._targets["target"] = target
        assert second.wait("turn", timeout=5) == "cancelled"
    finally:
        second.close()


def test_zero_destinations_still_uses_native_cancellation_and_missing_is_noop(stores):
    origin = WorkJournal(stores("origin.db"), namespace="http")
    origin.commit("turn", result=None, tasks={"answer": {}})
    instance = service(origin, {})
    try:
        assert instance.request("absent") == "missing"
        assert instance.journal.read("absent") is None
        assert instance.request("turn") == "accepted"
        assert instance.wait("turn", timeout=5) == "cancelled"
    finally:
        instance.close()


def test_real_process_death_after_seal_before_ack_recovers(tmp_path):
    script = """
import os,sys
from pathlib import Path
from sage.runtime.effect_cancellation import CancellationService,EffectFences
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
from sage.runtime.work_journal import WorkJournal
root=Path(sys.argv[1])
source=StatefulProcessRuntime(backend="sqlite",sqlite_path=str(root/"origin.db"))
target=StatefulProcessRuntime(backend="sqlite",sqlite_path=str(root/"target.db"))
origin=WorkJournal(source,namespace="http")
origin.commit("turn",result=None,tasks={"answer":{}})
fences=EffectFences(target,namespace="request")
seal=fences.seal
def crash(scope):
 seal(scope)
 os._exit(37)
fences.seal=crash
instance=CancellationService(origin,task_id="answer",targets={"target":fences},
                             poll_interval=0.01,lease_seconds=0.3)
instance.request("turn")
instance.wait("turn",timeout=10)
"""
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path)], check=False, timeout=15)
    assert result.returncode == 37
    source = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "origin.db"))
    target = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "target.db"))
    origin = WorkJournal(source, namespace="http")
    fences = EffectFences(target, namespace="request")
    instance = service(origin, {"target": fences}, lease_seconds=0.3)
    try:
        assert fences.is_sealed("turn")
        assert origin.read("turn")["tasks"]["answer"]["status"] == "pending"
        instance.start()  # No second request is needed to recover the intent.
        assert instance.wait("turn", timeout=5) == "cancelled"
        with pytest.raises(EffectCancelled):
            effect(target, fences.prepare_guard("turn"))
    finally:
        instance.close()
        target.close()
        source.close()


def test_async_observer_repeated_cancel_waits_for_native_settlement(stores):
    async def scenario():
        origin = WorkJournal(stores("origin.db"), namespace="http")
        origin.commit("turn", result=None, tasks={"answer": {}})
        target = EffectFences(stores("target.db"), namespace="request")
        entered, release = Event(), Event()
        seal = target.seal

        def blocked(scope):
            entered.set()
            assert release.wait(5)
            seal(scope)

        target.seal = blocked
        instance = service(origin, {"target": target})
        observer = None
        try:
            await instance.astart()
            assert await instance.arequest("turn") == "accepted"
            assert await asyncio.to_thread(entered.wait, 3)
            observer = asyncio.create_task(instance.await_result("turn", timeout=3))
            await asyncio.sleep(0.02)
            for _ in range(2):
                observer.cancel()
                await asyncio.sleep(0.02)
                assert not observer.done(), "cancelled observer abandoned borrowed storage"
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await observer
            assert instance.wait("turn", timeout=3) == "cancelled"
        finally:
            release.set()
            if observer is not None and not observer.done():
                await asyncio.gather(observer, return_exceptions=True)
            await instance.aclose()
    asyncio.run(scenario())
