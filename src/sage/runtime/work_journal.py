"""Atomic result/outbox records on SAGE state storage.

Tasks are at-least-once: consumers must use (namespace, request_id, task_id)
as an idempotency key at the side-effect destination. Leases fence journal
acknowledgements, not effects in an external system. Durable use requires a
persistent state backend; this class does not own or close the supplied store.
"""

from __future__ import annotations

import json
import math
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime

_UNSET = object()


class StaleTaskLeaseError(ValueError):
    """A worker no longer owns the task and may not acknowledge its result."""


def _json_snapshot(value):
    return json.loads(json.dumps(value, allow_nan=False, sort_keys=True))


def _name(value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("journal_identifier_must_be_nonempty_and_trimmed")
    return value


@dataclass(frozen=True)
class TaskLease:
    namespace: str
    request_id: str
    task_id: str
    token: str
    attempt: int
    payload: Any


@dataclass(frozen=True)
class PreparedWorkCommit:
    """Pure journal mutation for composition in one state transaction.

    Not a persisted record or a transaction by itself. Apply the transform to
    this slot's value inside the journal's state store. Other destinations
    must implement their own replay/conflict checks in the same transaction.
    """

    slot: tuple[str, str, str]
    transform: Callable[[Any], Any]


class WorkJournal:
    """One atomic record contains a committed result and its task intents."""

    def __init__(self, store: StatefulProcessRuntime, *, namespace: str,
                 clock: Callable[[], float] = time.time):
        self._store = store
        self.namespace = _name(namespace)
        self._clock = clock

    def _slot(self, request_id):
        return ("sage-work-journal-v1", self.namespace, _name(request_id))

    def commit(self, request_id: str, *, result: Any, tasks: dict[str, Any],
               mutations: Mapping[tuple[str, str, str], Callable[[Any], Any]] | None = None):
        """Commit intent with optional pure destination mutations in this store.

        Every destination owns replay/conflict checks. No callback may perform
        external effects or re-enter storage. Journal slots are reserved so a
        destination cannot bypass the task protocol. This is not cross-store
        atomicity, and successful replay must not reapply non-idempotent effects.
        """
        prepared = self.prepare_commit(request_id, result=result, tasks=tasks)
        return self._apply_with_destinations(prepared.slot, prepared.transform, mutations)

    def _apply_with_destinations(self, journal_slot, journal_transform, mutations):
        """Fence journal state before evaluating pure destination transforms."""
        transforms = dict(mutations) if mutations is not None else {}
        for slot, transform in transforms.items():
            if not isinstance(slot, tuple) or len(slot) != 3:
                raise ValueError("invalid_destination_slot")
            for part in slot:
                _name(part)
            if slot[0] == "sage-work-journal-v1":
                raise ValueError("destination_cannot_mutate_journal")
            if not callable(transform):
                raise TypeError("destination_transform_not_callable")
        if not transforms:
            return self._store.update(journal_slot, journal_transform)
        transforms = {journal_slot: journal_transform, **transforms}
        committed = self._store.update_many(
            transforms, lambda values: {slot: transform(values[slot])
                                       for slot, transform in transforms.items()},
        )
        return committed[journal_slot]

    def prepare_commit(self, request_id: str, *, result: Any, tasks: dict[str, Any]) -> PreparedWorkCommit:
        """Capture immutable JSON inputs without writing or starting work.

        Compose with destination mutations using this store's update_many.
        Never invoke a destination's own storage methods inside the callback.
        A successful prepare is not a successful commit or delivery receipt.
        """
        slot = self._slot(request_id)
        result = _json_snapshot(result)
        tasks = {_name(key): _json_snapshot(value) for key, value in tasks.items()}

        def apply(old):
            if old is not None:
                self._validate(old)
                original = {key: value["payload"] for key, value in old["tasks"].items()}
                if old["result"] != result or original != tasks:
                    raise ValueError("journal_commit_conflict")
                return old
            return {"version": 1, "result": _json_snapshot(result), "tasks": {
                key: {"payload": _json_snapshot(value), "status": "pending", "attempt": 0,
                      "token": None, "lease_until": 0.0, "available_at": 0.0}
                for key, value in tasks.items()
            }}

        return PreparedWorkCommit(slot, apply)

    @staticmethod
    def _validate(record):
        if record is None:
            raise KeyError("journal_request_not_found")
        if record.get("version") != 1:
            raise ValueError("unsupported_journal_version")

    def claim(self, request_id: str, task_id: str, *, lease_seconds: float) -> TaskLease | None:
        _name(task_id)
        if not math.isfinite(lease_seconds) or lease_seconds <= 0:
            raise ValueError("lease_seconds_must_be_positive_and_finite")
        token = uuid.uuid4().hex
        claimed = []

        def apply(record):
            self._validate(record)
            task = record["tasks"][task_id]
            now = self._clock()
            if task.get("available_at", 0.0) > now or task["status"] == "done" or (
                task["status"] == "running" and task["lease_until"] > now
            ):
                return record
            task.update(status="running", token=token, lease_until=now + lease_seconds,
                        attempt=task["attempt"] + 1)
            claimed.append(TaskLease(self.namespace, request_id, task_id, token, task["attempt"],
                                     _json_snapshot(task["payload"])))
            return record

        self._store.update(self._slot(request_id), apply)
        return claimed[0] if claimed else None

    def finish(self, lease: TaskLease, *, retry: bool = False, retry_delay: float = 0.0,
               result: Any = _UNSET,
               mutations: Mapping[tuple[str, str, str], Callable[[Any], Any]] | None = None) -> None:
        """Fence ownership and atomically publish result and destination state.

        Destinations follow commit's pure, same-store mutation contract. Retry
        cannot publish destination state. A stale lease rolls back everything;
        external effects are never protected by this transaction.
        """
        if not math.isfinite(retry_delay) or retry_delay < 0:
            raise ValueError("retry_delay_must_be_nonnegative_and_finite")
        if lease.namespace != self.namespace:
            raise ValueError("task_lease_namespace_mismatch")
        if retry and result is not _UNSET:
            raise ValueError("retry_cannot_publish_task_result")
        if retry and mutations:
            raise ValueError("retry_cannot_publish_destination_state")
        snapshot = _json_snapshot(result) if result is not _UNSET else _UNSET
        def apply(record):
            self._validate(record)
            task = record["tasks"][lease.task_id]
            if (task["status"] != "running" or task["token"] != lease.token
                    or task["lease_until"] <= self._clock()):
                raise StaleTaskLeaseError("stale_task_lease")
            task.update(status="pending" if retry else "done", token=None, lease_until=0.0,
                        available_at=self._clock() + retry_delay if retry else 0.0)
            if snapshot is not _UNSET:
                task["result"] = snapshot
            return record

        self._apply_with_destinations(self._slot(lease.request_id), apply, mutations)

    def read(self, request_id: str) -> dict[str, Any] | None:
        """Read a detached committed result and task states for one request."""
        record = self._store.peek(self._slot(request_id))
        if record is None:
            return None
        self._validate(record)
        return _json_snapshot(record)

    def renew(self, lease: TaskLease, *, lease_seconds: float) -> None:
        if lease.namespace != self.namespace:
            raise ValueError("task_lease_namespace_mismatch")
        if not math.isfinite(lease_seconds) or lease_seconds <= 0:
            raise ValueError("lease_seconds_must_be_positive_and_finite")

        def apply(record):
            self._validate(record)
            task = record["tasks"][lease.task_id]
            now = self._clock()
            if (task["status"] != "running" or task["token"] != lease.token
                    or task["lease_until"] <= now):
                raise StaleTaskLeaseError("stale_task_lease")
            task["lease_until"] = now + lease_seconds
            return record

        self._store.update(self._slot(lease.request_id), apply)

    def records(self, *, cursor: int = 0, limit: int = 100):
        """Read-only paginated recovery scan; claims revalidate all eligibility.

        A scan is not a snapshot across pages. Repeat from zero after each sweep
        to discover records inserted before the previous cursor.
        """
        rows, next_cursor = self._store.query_namespace_entries(
            namespace=self.namespace, prefix="", limit=limit, cursor=cursor,
        )
        return [row for row in rows if row["stage_id"] == "sage-work-journal-v1"], next_cursor
