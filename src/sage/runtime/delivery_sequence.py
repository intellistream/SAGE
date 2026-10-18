"""Fenced ordered external-delivery receipts inside an existing work attempt.

This is not a worker, scheduler, transport or exactly-once external protocol.
Only metadata/receipts are stored here; payloads and credentials belong elsewhere.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from sage.runtime.async_work_service import complete_sync_call
from sage.runtime.work_journal import StaleTaskLeaseError, WorkJournal, _name


class DeliveryConflict(ValueError):
    """A delivery identity was reused with different immutable inputs."""


class DeliveryAttemptPending(RuntimeError):
    """This source attempt already armed an unacknowledged external part."""


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DeliveryPlan:
    fingerprint: str
    _destination_json: str = field(repr=False)
    _payloads_json: tuple[str, ...] = field(repr=False)

    @classmethod
    def capture(cls, *, destination: dict, payloads: Sequence[dict]):
        """Capture JSON transport bodies, never headers, tokens or bearer URLs.

        The application supplies already formatted, bounded payloads. This API
        does not summarize, truncate or guess Markdown boundaries.
        """
        if not isinstance(destination, dict) or not destination:
            raise ValueError("delivery_requires_destination_identity")
        if not isinstance(payloads, (list, tuple)) or not payloads:
            raise ValueError("delivery_requires_nonempty_payloads")
        if any(not isinstance(payload, dict) or not payload for payload in payloads):
            raise ValueError("delivery_requires_json_objects")
        destination_json = _json(destination)
        encoded = tuple(_json(payload) for payload in payloads)
        fingerprint = _digest(_json([1, json.loads(destination_json), [json.loads(item) for item in encoded]]))
        return cls(fingerprint, destination_json, encoded)

    def validate(self):
        expected = DeliveryPlan.capture(destination=json.loads(self._destination_json),
                                      payloads=[json.loads(item) for item in self._payloads_json])
        if self != expected:
            raise DeliveryConflict("delivery_plan_invalid")


@dataclass(frozen=True)
class DeliveryFrame:
    part_id: str
    index: int
    total: int
    _payload_json: str = field(repr=False)

    @property
    def payload(self):
        """A fresh detached body; mutation cannot change the captured plan."""
        return json.loads(self._payload_json)


@dataclass(frozen=True)
class DeliveryReceipt:
    accepted: Literal[True] = True
    external_id: str | None = None

    def validate(self):
        if self.accepted is not True or (self.external_id is not None and (
                not isinstance(self.external_id, str) or not self.external_id
                or self.external_id != self.external_id.strip() or len(self.external_id) > 256)):
            raise ValueError("delivery_requires_accepted_receipt")

    def to_dict(self):
        self.validate()
        return {"accepted": True, "external_id": self.external_id}


class DeliverySequence:
    """Resume ordered parts under the calling WorkJournal's current lease.

    Uses the existing worker's heartbeat/capacity and the existing state store.
    The caller reauthorizes every invocation and part through an async port.
    Unacknowledged external calls can be duplicated on retry. Stable part IDs
    let capable transports deduplicate, but are not themselves that guarantee.
    """

    def __init__(self, journal: WorkJournal, *, namespace: str):
        if not isinstance(journal, WorkJournal):
            raise TypeError("delivery_requires_work_journal")
        self.journal = journal
        self.namespace = _name(namespace)

    def _identity(self, request_id, task_id):
        return {"namespace": self.journal.namespace, "request_id": _name(request_id),
                "task_id": _name(task_id)}

    def _slot(self, origin):
        return ("sage-delivery-sequence-v1", self.namespace, _digest(_json(origin)))

    @staticmethod
    def _validate(record):
        if (not isinstance(record, dict) or set(record) != {
                "version", "origin", "plan", "receipts", "attempts", "source_attempts"}
                or type(record["version"]) is not int or record["version"] != 1
                or not isinstance(record["plan"], dict)
                or set(record["plan"]) != {"fingerprint", "part_ids", "payload_digests"}):
            raise DeliveryConflict("invalid_delivery_record")
        ids = record["plan"]["part_ids"]
        if (not isinstance(record["origin"], dict) or set(record["origin"]) != {"namespace", "request_id", "task_id"}
                or any(not isinstance(value, str) or not value or value != value.strip()
                       for value in record["origin"].values())
                or not isinstance(record["plan"]["fingerprint"], str)
                or re.fullmatch(r"[0-9a-f]{64}", record["plan"]["fingerprint"]) is None
                or not isinstance(ids, list) or not ids
                or any(not isinstance(part, str) or re.fullmatch(r"delivery:[0-9a-f]{64}", part) is None for part in ids)
                or len(set(ids)) != len(ids)
                or not isinstance(record["plan"]["payload_digests"], list)
                or any(not isinstance(part, str) or re.fullmatch(r"[0-9a-f]{64}", part) is None
                       for part in record["plan"]["payload_digests"])
                or not isinstance(record["receipts"], list) or not isinstance(record["attempts"], list)
                or not isinstance(record["source_attempts"], list)
                or len(record["plan"]["payload_digests"]) != len(ids)
                or len(record["receipts"]) != len(ids) or len(record["attempts"]) != len(ids)
                or len(record["source_attempts"]) != len(ids)
                or any(type(count) is not int or count < 0
                       for count in [*record["attempts"], *record["source_attempts"]])):
            raise DeliveryConflict("invalid_delivery_record")
        unfinished = False
        previous_source_attempt = 0
        for index, receipt in enumerate(record["receipts"]):
            count, attempt = record["attempts"][index], record["source_attempts"][index]
            if ((count == 0) != (attempt == 0) or count > attempt
                    or (attempt and attempt < previous_source_attempt) or (unfinished and count)):
                raise DeliveryConflict("invalid_delivery_attempt_order")
            previous_source_attempt = attempt or previous_source_attempt
            if receipt is None:
                unfinished = True
            else:
                if (unfinished or not isinstance(receipt, dict)
                        or set(receipt) != {"accepted", "external_id"}
                        or record["attempts"][index] < 1 or record["source_attempts"][index] < 1):
                    raise DeliveryConflict("invalid_delivery_receipt_order")
                DeliveryReceipt(**receipt).validate()

    def _prepare(self, lease, plan):
        guard = self.journal.prepare_guard(lease)
        guard.validate_store(self.journal._store)
        origin = self._identity(lease.request_id, lease.task_id)
        slot = self._slot(origin)
        frames = tuple(DeliveryFrame(
            part_id="delivery:" + _digest(_json([self.namespace, origin, plan.fingerprint, index])),
            index=index, total=len(plan._payloads_json), _payload_json=payload)
            for index, payload in enumerate(plan._payloads_json))
        descriptor = {"fingerprint": plan.fingerprint, "part_ids": [frame.part_id for frame in frames],
                      "payload_digests": [_digest(payload) for payload in plan._payloads_json]}
        return guard, origin, slot, frames, descriptor, lease.attempt

    def _mutate(self, prepared, transition):
        guard, origin, slot, frames, descriptor, source_attempt = prepared

        def apply(values):
            updates = guard.apply(values)
            if values[guard.slot]["tasks"][origin["task_id"]]["attempt"] != source_attempt:
                raise StaleTaskLeaseError("delivery_source_attempt_mismatch")
            record = values[slot]
            if record is None:
                record = {"version": 1, "origin": origin, "plan": descriptor,
                          "receipts": [None] * len(frames), "attempts": [0] * len(frames),
                          "source_attempts": [0] * len(frames)}
            else:
                self._validate(record)
                if record["origin"] != origin or record["plan"] != descriptor:
                    raise DeliveryConflict("delivery_plan_conflict")
            transition(record)
            self._validate(record)
            updates[slot] = record
            return updates

        result = self.journal._store.update_many((guard.slot, slot), apply)
        return result[slot], frames

    def read(self, request_id, task_id):
        """Content-free detached record; caller must authorize this identity."""
        origin = self._identity(request_id, task_id)
        record = self.journal._store.peek(self._slot(origin))
        if record is None:
            return None
        self._validate(record)
        if record["origin"] != origin:
            raise DeliveryConflict("delivery_origin_conflict")
        return json.loads(_json(record))

    async def deliver(self, lease, plan: DeliveryPlan, *, send: Callable, authorize: Callable):
        """Return all accepted receipts, without acknowledging the source task.

        send(DeliveryFrame) and authorize() are async. An authorization failure
        must raise; no denial text or credentials are stored by this primitive.
        Storage operations drain through observer cancellation before returning.
        Payload validation/planning must finish before invoking this method.
        """
        if not isinstance(plan, DeliveryPlan):
            raise TypeError("delivery_requires_plan")
        plan.validate()
        prepared = self._prepare(lease, plan)

        async def permitted():
            if await authorize() is not None:
                raise PermissionError("delivery_authorization_rejected")

        await permitted()
        record, frames = await complete_sync_call(self._mutate, prepared, lambda record: None)
        for frame in frames:
            await permitted()
            send_part = []

            def begin(current, frame=frame, send_part=send_part):
                if current["receipts"][frame.index] is not None:
                    return
                if any(receipt is None for receipt in current["receipts"][:frame.index]):
                    raise DeliveryConflict("delivery_part_out_of_order")
                if current["source_attempts"][frame.index] >= lease.attempt:
                    raise DeliveryAttemptPending("delivery_part_unconfirmed_in_current_attempt")
                current["attempts"][frame.index] += 1
                current["source_attempts"][frame.index] = lease.attempt
                send_part.append(True)

            record, _ = await complete_sync_call(self._mutate, prepared, begin)
            if not send_part:
                continue
            receipt = await send(frame)
            if not isinstance(receipt, DeliveryReceipt):
                raise TypeError("delivery_requires_typed_receipt")
            receipt.validate()

            def acknowledge(current, frame=frame, receipt=receipt):
                old = current["receipts"][frame.index]
                if old is not None and old != receipt.to_dict():
                    raise DeliveryConflict("delivery_receipt_conflict")
                current["receipts"][frame.index] = receipt.to_dict()

            record, _ = await complete_sync_call(self._mutate, prepared, acknowledge)
        if any(receipt is None for receipt in record["receipts"]):
            raise DeliveryConflict("delivery_incomplete")
        return record
