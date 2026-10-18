"""Ordered external receipts without another worker or a false exactly-once claim."""

import asyncio
import json
import multiprocessing
import os
import sqlite3
from dataclasses import replace
from pathlib import Path
from threading import Event

import pytest

from sage.runtime.async_work_service import AsyncWorkService
from sage.runtime.delivery_sequence import (
    DeliveryAttemptPending,
    DeliveryConflict,
    DeliveryPlan,
    DeliveryReceipt,
    DeliverySequence,
)
from sage.runtime.flownet.runtime.operator_runtime.stateful import (
    StatefulProcessRuntime,
)
from sage.runtime.work_journal import StaleTaskLeaseError, WorkJournal


async def allow():
    return None


def plan(count=3, **destination):
    return DeliveryPlan.capture(destination={"recipient": "fixture", **destination},
        payloads=[{"text": f"private body {index}"} for index in range(count)])


def source(tmp_path, *, clock=None):
    state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    journal = WorkJournal(state, namespace="source", **({"clock": clock} if clock else {}))
    journal.commit("request", result="fixed answer", tasks={"deliver": {}})
    return state, journal, DeliverySequence(journal, namespace="transport")


def test_captured_plan_round_trip_is_detached_and_redacted():
    original = plan(2)
    exported = original.to_dict()
    restored = DeliveryPlan.from_dict(json.loads(json.dumps(exported)))
    assert restored == original
    exported["destination"]["recipient"] = "wrong recipient"
    exported["payloads"][0]["text"] = "wrong answer"
    assert restored.to_dict() == original.to_dict()
    assert "private body" not in repr(restored)
    assert "fixture" not in repr(restored)


@pytest.mark.parametrize("change", [
    {"version": True}, {"version": 2}, {"fingerprint": "forged"},
    {"payloads": [{"text": "changed"}]}, {"destination": {"recipient": "other"}},
    {"payloads": []}, {"destination": None}, {"unexpected": "extra"},
])
def test_captured_plan_rejects_corruption_or_unknown_schema(change):
    captured = plan(2).to_dict()
    captured.update(change)
    with pytest.raises(DeliveryConflict, match="delivery_plan_invalid"):
        DeliveryPlan.from_dict(captured)


def test_reopen_uses_upstream_captured_plan_and_only_resumes_unconfirmed_parts(tmp_path):
    async def run():
        path = str(tmp_path / "captured.db")
        state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
        journal = WorkJournal(state, namespace="captured")
        journal.commit("request", result={}, tasks={"answer": {}, "deliver": {}},
                       dependencies={"deliver": ["answer"]})
        produced = plan(3)
        answer = journal.claim("request", "answer", lease_seconds=30)
        journal.finish(answer, result=produced.to_dict())
        sequence = DeliverySequence(journal, namespace="transport")
        delivery = journal.claim("request", "deliver", lease_seconds=30)
        calls = []

        async def send(frame):
            calls.append((frame.part_id, frame.payload))
            if len(calls) == 2:
                raise ConnectionError("unconfirmed external outcome")
            return DeliveryReceipt(external_id=str(frame.index))

        try:
            captured = DeliveryPlan.from_dict(journal.read("request")["tasks"]["answer"]["result"])
            with pytest.raises(ConnectionError):
                await sequence.deliver(delivery, captured, send=send, authorize=allow)
            journal.finish(delivery, retry=True)
        finally:
            state.close()

        # Actual reopen: no original plan object, formatter or answer port is
        # available to this worker. The upstream committed result is sufficient.
        state = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
        journal = WorkJournal(state, namespace="captured")
        sequence = DeliverySequence(journal, namespace="transport")
        try:
            record = journal.read("request")
            assert record["tasks"]["answer"]["status"] == "done"
            assert record["tasks"]["answer"]["attempt"] == 1
            captured = DeliveryPlan.from_dict(record["tasks"]["answer"]["result"])
            delivery = journal.claim("request", "deliver", lease_seconds=30)
            saved = await sequence.deliver(delivery, captured, send=send, authorize=allow)
            journal.finish(delivery, result={"accepted_parts": len(saved["receipts"])})
            assert [item[1]["text"] for item in calls] == [
                "private body 0", "private body 1", "private body 1", "private body 2"]
            assert calls[1] == calls[2]
            assert len({item[0] for item in calls}) == 3
            assert journal.read("request")["tasks"]["deliver"]["status"] == "done"
            assert all(receipt["accepted"] is True for receipt in saved["receipts"])
            assert "private body" not in json.dumps(saved)
        finally:
            state.close()

    asyncio.run(run())


def test_real_native_worker_delivers_in_order_and_alone_acknowledges_source(tmp_path):
    async def run():
        state, journal, sequence = source(tmp_path)
        body = plan()
        calls, leases = [], []

        async def send(frame):
            calls.append((frame.index, frame.part_id, frame.payload))
            mutated = frame.payload
            mutated["text"] = "not the captured body"
            assert frame.payload != mutated
            return DeliveryReceipt(external_id=f"receipt-{frame.index}")

        async def handler(lease):
            leases.append(lease)
            result = await sequence.deliver(lease, body, send=send, authorize=allow)
            assert journal.read("request")["tasks"]["deliver"]["status"] == "running"
            return {"parts": result["plan"]["part_ids"]}

        service = AsyncWorkService(journal, handler, poll_interval=0.01)
        try:
            await service.start()
            result = await service.wait("request", timeout=5)
            assert result["result"] == "fixed answer"
            assert result["tasks"]["deliver"]["status"] == "done"
            assert [item[0] for item in calls] == [0, 1, 2]
            assert len({item[1] for item in calls}) == 3
            saved = sequence.read("request", "deliver")
            assert all(receipt["accepted"] for receipt in saved["receipts"])
            assert "private body" not in repr(saved) and "private body" not in repr(body)
            assert leases[0].token not in repr(saved)
            with pytest.raises(StaleTaskLeaseError):
                await sequence.deliver(leases[0], body, send=send, authorize=allow)
            assert len(calls) == 3
        finally:
            await service.aclose()
            state.close()

    asyncio.run(run())


def test_partial_failure_retries_only_unconfirmed_parts_in_a_new_source_attempt(tmp_path):
    async def run():
        state, journal, sequence = source(tmp_path)
        lease = journal.claim("request", "deliver", lease_seconds=30)
        body, calls = plan(), []

        async def send(frame):
            calls.append((frame.index, frame.part_id))
            if len(calls) == 2:
                raise ConnectionError("unconfirmed external outcome")
            return DeliveryReceipt(external_id=str(frame.index))

        try:
            with pytest.raises(ConnectionError):
                await sequence.deliver(lease, body, send=send, authorize=allow)
            before = sequence.read("request", "deliver")
            assert [receipt is not None for receipt in before["receipts"]] == [True, False, False]
            assert before["attempts"] == [1, 1, 0]
            with pytest.raises(DeliveryAttemptPending):
                await sequence.deliver(lease, body, send=send, authorize=allow)
            assert len(calls) == 2
            journal.finish(lease, retry=True)
            replacement = journal.claim("request", "deliver", lease_seconds=30)
            saved = await sequence.deliver(replacement, body, send=send, authorize=allow)
            assert [item[0] for item in calls] == [0, 1, 1, 2]
            assert calls[1][1] == calls[2][1]
            assert saved["attempts"] == [1, 2, 1]
            assert saved["source_attempts"] == [1, 2, 2]
            assert saved["receipts"][0] == before["receipts"][0]
            assert journal.read("request")["tasks"]["deliver"]["status"] == "running"
        finally:
            state.close()

    asyncio.run(run())


def test_same_lease_concurrent_delivery_cannot_send_the_same_part_twice(tmp_path):
    async def run():
        state, journal, sequence = source(tmp_path)
        lease = journal.claim("request", "deliver", lease_seconds=30)
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []

        async def send(frame):
            calls.append(frame.part_id)
            entered.set()
            await release.wait()
            return DeliveryReceipt(external_id="accepted")

        first = asyncio.create_task(sequence.deliver(lease, plan(1), send=send, authorize=allow))
        try:
            await asyncio.wait_for(entered.wait(), timeout=3)
            with pytest.raises(DeliveryAttemptPending):
                await sequence.deliver(lease, plan(1), send=send, authorize=allow)
            release.set()
            await first
            assert len(calls) == 1
            await sequence.deliver(lease, plan(1), send=send, authorize=allow)
            assert len(calls) == 1  # All confirmed receipts may be replayed.
        finally:
            release.set()
            await first
            state.close()

    asyncio.run(run())


def test_plan_and_destination_conflicts_and_denial_never_send(tmp_path):
    async def run():
        state, journal, sequence = source(tmp_path)
        lease = journal.claim("request", "deliver", lease_seconds=30)
        calls = []

        async def send(frame):
            calls.append(frame.part_id)
            return DeliveryReceipt(external_id="accepted")

        async def deny():
            return "permission denied"  # Returning denial must not accidentally authorize.

        try:
            with pytest.raises(PermissionError):
                await sequence.deliver(lease, plan(1), send=send, authorize=deny)
            assert sequence.read("request", "deliver") is None and calls == []
            body = plan(1)
            with pytest.raises(StaleTaskLeaseError, match="attempt_mismatch"):
                await sequence.deliver(replace(lease, attempt=lease.attempt + 1), body,
                                       send=send, authorize=allow)
            assert sequence.read("request", "deliver") is None and calls == []
            with pytest.raises(DeliveryConflict):
                await sequence.deliver(lease, replace(body, fingerprint="forged"), send=send, authorize=allow)
            assert calls == []
            await sequence.deliver(lease, body, send=send, authorize=allow)
            before = sequence.read("request", "deliver")
            for other in (plan(2), plan(1, recipient="other")):
                with pytest.raises(DeliveryConflict):
                    await sequence.deliver(lease, other, send=send, authorize=allow)
            with pytest.raises(PermissionError):
                await sequence.deliver(lease, body, send=send, authorize=deny)
            assert len(calls) == 1 and sequence.read("request", "deliver") == before
        finally:
            state.close()

    asyncio.run(run())


def test_late_external_receipt_cannot_advance_an_expired_source_lease(tmp_path):
    async def run():
        now = [0.0]
        state, journal, sequence = source(tmp_path, clock=lambda: now[0])
        lease = journal.claim("request", "deliver", lease_seconds=1)
        ids = []

        async def late(frame):
            ids.append(frame.part_id)
            now[0] = 2
            return DeliveryReceipt(external_id="external accepted")

        try:
            with pytest.raises(StaleTaskLeaseError):
                await sequence.deliver(lease, plan(1), send=late, authorize=allow)
            saved = sequence.read("request", "deliver")
            assert saved["receipts"] == [None] and saved["attempts"] == [1]
            current = journal.claim("request", "deliver", lease_seconds=30)

            async def accepted(frame):
                ids.append(frame.part_id)
                return DeliveryReceipt(external_id="external accepted")

            await sequence.deliver(current, plan(1), send=accepted, authorize=allow)
            assert ids[0] == ids[1]  # External duplicate is possible without receiver deduplication.
            assert journal.read("request")["tasks"]["deliver"]["status"] == "running"
        finally:
            state.close()

    asyncio.run(run())


@pytest.mark.parametrize("lost_ack", [False, True])
def test_receipt_storage_failure_and_lost_ack_keep_truthful_replay(tmp_path, monkeypatch, lost_ack):
    async def run():
        state, journal, sequence = source(tmp_path)
        lease = journal.claim("request", "deliver", lease_seconds=30)
        calls = []

        async def send(frame):
            calls.append(frame.part_id)
            return DeliveryReceipt(external_id="accepted")

        original = state.update_many if lost_ack else state._backend._put_uncommitted

        def lose(*args, **kwargs):
            if lost_ack:
                result = original(*args, **kwargs)
                if any(slot[0] == "sage-delivery-sequence-v1" and value["receipts"][0] is not None
                       for slot, value in result.items()):
                    raise ConnectionError("lost receipt acknowledgement")
                return result
            slot, entry = args
            original(slot, entry)
            if slot[0] == "sage-delivery-sequence-v1" and entry.value["receipts"][0] is not None:
                raise OSError("receipt storage failure")

        try:
            with monkeypatch.context() as patch:
                patch.setattr(state if lost_ack else state._backend,
                              "update_many" if lost_ack else "_put_uncommitted", lose)
                with pytest.raises((ConnectionError, OSError)):
                    await sequence.deliver(lease, plan(1), send=send, authorize=allow)
            saved = sequence.read("request", "deliver")
            assert (saved["receipts"][0] is not None) == lost_ack
            if not lost_ack:
                journal.finish(lease, retry=True)
                lease = journal.claim("request", "deliver", lease_seconds=30)
            await sequence.deliver(lease, plan(1), send=send, authorize=allow)
            assert len(calls) == (1 if lost_ack else 2)
            assert len(set(calls)) == 1
        finally:
            state.close()

    asyncio.run(run())


def test_part_ids_are_distinct_for_different_legitimate_requests(tmp_path):
    async def run():
        state, journal, sequence = source(tmp_path)
        journal.commit("another", result="fixed answer", tasks={"deliver": {}})
        ids = []

        async def send(frame):
            ids.append(frame.part_id)
            return DeliveryReceipt()

        try:
            for request in ("request", "another"):
                lease = journal.claim(request, "deliver", lease_seconds=30)
                await sequence.deliver(lease, plan(1), send=send, authorize=allow)
            another_transport = DeliverySequence(journal, namespace="another-transport")
            await another_transport.deliver(lease, plan(1), send=send, authorize=allow)
            assert len(ids) == len(set(ids)) == 3
        finally:
            state.close()

    asyncio.run(run())


def test_authority_revocation_stops_before_arming_the_next_part(tmp_path):
    async def run():
        state, journal, sequence = source(tmp_path)
        lease = journal.claim("request", "deliver", lease_seconds=30)
        permitted, sent = [True], []

        async def authorize():
            return None if permitted[0] else False

        async def send(frame):
            sent.append(frame.index)
            permitted[0] = False
            return DeliveryReceipt()

        try:
            with pytest.raises(PermissionError):
                await sequence.deliver(lease, plan(), send=send, authorize=authorize)
            assert sent == [0]
            saved = sequence.read("request", "deliver")
            assert saved["attempts"] == [1, 0, 0]
            assert [receipt is not None for receipt in saved["receipts"]] == [True, False, False]
        finally:
            state.close()

    asyncio.run(run())


@pytest.mark.parametrize("reply", [None, {"accepted": True}, DeliveryReceipt(accepted=False)])
def test_untyped_or_rejected_receipt_never_confirms_delivery(tmp_path, reply):
    async def run():
        state, journal, sequence = source(tmp_path)
        lease = journal.claim("request", "deliver", lease_seconds=30)

        async def send(frame):
            return reply

        try:
            with pytest.raises((TypeError, ValueError)):
                await sequence.deliver(lease, plan(1), send=send, authorize=allow)
            saved = sequence.read("request", "deliver")
            assert saved["receipts"] == [None] and saved["attempts"] == [1]
            assert journal.read("request")["tasks"]["deliver"]["status"] == "running"
        finally:
            state.close()

    asyncio.run(run())


def test_cancelled_observer_waits_for_arming_transaction_without_sending(tmp_path, monkeypatch):
    async def run():
        state, journal, sequence = source(tmp_path)
        lease = journal.claim("request", "deliver", lease_seconds=30)
        entered, release = Event(), Event()
        sent = []
        original = state._backend._put_uncommitted

        def blocked(slot, entry):
            original(slot, entry)
            if slot[0] == "sage-delivery-sequence-v1" and entry.value["attempts"] == [1]:
                entered.set()
                assert release.wait(3)

        async def send(frame):
            sent.append(frame.index)
            return DeliveryReceipt()

        task = None
        try:
            with monkeypatch.context() as patch:
                patch.setattr(state._backend, "_put_uncommitted", blocked)
                task = asyncio.create_task(sequence.deliver(lease, plan(1), send=send, authorize=allow))
                assert await asyncio.to_thread(entered.wait, 3)
                task.cancel()
                await asyncio.sleep(0)
                assert not task.done() and sent == []
                release.set()
                with pytest.raises(asyncio.CancelledError):
                    await task
            saved = sequence.read("request", "deliver")
            assert saved["attempts"] == [1] and saved["receipts"] == [None]
            assert sent == []
        finally:
            release.set()
            if task is not None:
                await asyncio.gather(task, return_exceptions=True)
            state.close()

    asyncio.run(run())


def receiver(directory, frame):
    with sqlite3.connect(Path(directory) / "receiver.db") as db:
        db.execute("CREATE TABLE IF NOT EXISTS calls (part TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS accepted (part TEXT PRIMARY KEY)")
        db.execute("INSERT INTO calls VALUES (?)", (frame.part_id,))
        db.execute("INSERT OR IGNORE INTO accepted VALUES (?)", (frame.part_id,))
    return DeliveryReceipt(external_id=frame.part_id)


def crash_after_external_acceptance(directory):
    async def run():
        state, journal, sequence = source(Path(directory), clock=lambda: 10.0)
        lease = journal.claim("request", "deliver", lease_seconds=1)

        async def send(frame):
            accepted = receiver(directory, frame)
            if frame.index == 1:
                os._exit(44)
            return accepted

        await sequence.deliver(lease, plan(2), send=send, authorize=allow)
        state.close()

    asyncio.run(run())


def test_real_process_crash_retains_confirmed_parts_and_ambiguous_external_outcome(tmp_path):
    child = multiprocessing.get_context("spawn").Process(target=crash_after_external_acceptance, args=(str(tmp_path),))
    child.start()
    try:
        child.join(10)
        assert child.exitcode == 44
        state = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
        journal = WorkJournal(state, namespace="source", clock=lambda: 12.0)
        sequence = DeliverySequence(journal, namespace="transport")

        async def run():
            lease = journal.claim("request", "deliver", lease_seconds=30)
            assert lease.attempt == 2
            sent = []

            async def send(frame):
                sent.append(frame.index)
                return receiver(tmp_path, frame)

            saved = await sequence.deliver(lease, plan(2), send=send, authorize=allow)
            assert sent == [1] and saved["attempts"] == [1, 2]
            assert all(receipt is not None for receipt in saved["receipts"])
            assert journal.read("request")["result"] == "fixed answer"
            assert journal.read("request")["tasks"]["deliver"]["status"] == "running"

        try:
            asyncio.run(run())
            with sqlite3.connect(tmp_path / "receiver.db") as db:
                assert db.execute("SELECT count(*) FROM calls").fetchone() == (3,)
                assert db.execute("SELECT count(*) FROM accepted").fetchone() == (2,)
        finally:
            state.close()
    finally:
        if child.is_alive():
            child.kill()
            child.join(5)
