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
from dataclasses import dataclass
from typing import Any, Callable

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


class WorkJournal:
    """One atomic record contains a committed result and its task intents."""

    def __init__(self, store: StatefulProcessRuntime, *, namespace: str,
                 clock: Callable[[], float] = time.time):
        self._store = store
        self.namespace = _name(namespace)
        self._clock = clock

    def _slot(self, request_id):
        return ("sage-work-journal-v1", self.namespace, _name(request_id))

    def commit(self, request_id: str, *, result: Any, tasks: dict[str, Any]):
        result = _json_snapshot(result)
        tasks = {_name(key): _json_snapshot(value) for key, value in tasks.items()}

        def apply(old):
            if old is not None:
                self._validate(old)
                original = {key: value["payload"] for key, value in old["tasks"].items()}
                if old["result"] != result or original != tasks:
                    raise ValueError("journal_commit_conflict")
                return old
            return {"version": 1, "result": result, "tasks": {
                key: {"payload": value, "status": "pending", "attempt": 0,
                      "token": None, "lease_until": 0.0, "available_at": 0.0}
                for key, value in tasks.items()
            }}

        return self._store.update(self._slot(request_id), apply)

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
               result: Any = _UNSET) -> None:
        """Atomically acknowledge ownership and publish an optional JSON result."""
        if not math.isfinite(retry_delay) or retry_delay < 0:
            raise ValueError("retry_delay_must_be_nonnegative_and_finite")
        if lease.namespace != self.namespace:
            raise ValueError("task_lease_namespace_mismatch")
        if retry and result is not _UNSET:
            raise ValueError("retry_cannot_publish_task_result")
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

        self._store.update(self._slot(lease.request_id), apply)

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
