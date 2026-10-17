"""Atomic result/outbox records on SAGE state storage.

Tasks are at-least-once: consumers must use (namespace, request_id, task_id)
as an idempotency key at the side-effect destination. Leases fence journal
acknowledgements, not effects in an external system. Durable use requires a
persistent state backend; this class does not own or close the supplied store.
"""

from __future__ import annotations

import json
import math
import re
import time
import uuid
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from sage.runtime.flownet.runtime.operator_runtime.stateful import (
    StatefulProcessRuntime,
    StateMutation,
)

_UNSET = object()


class StaleTaskLeaseError(ValueError):
    """A worker no longer owns the task and may not acknowledge its result."""


def _json_snapshot(value):
    return json.loads(json.dumps(value, allow_nan=False, sort_keys=True))


def _name(value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("journal_identifier_must_be_nonempty_and_trimmed")
    return value


def _dependencies(tasks, dependencies):
    if dependencies is None:
        return {}
    if not isinstance(dependencies, Mapping) or set(dependencies) - set(tasks):
        raise ValueError("invalid_work_dependencies")
    normalized = {}
    followers = {key: [] for key in tasks}
    degrees = {key: 0 for key in tasks}
    for key, prerequisites in dependencies.items():
        if not isinstance(prerequisites, (list, tuple)):
            raise ValueError("invalid_work_dependencies")
        names = [_name(name) for name in prerequisites]
        if len(set(names)) != len(names) or set(names) - set(tasks):
            raise ValueError("invalid_work_dependencies")
        if names:
            normalized[key] = sorted(names)
        degrees[key] = len(names)
        for prerequisite in names:
            followers[prerequisite].append(key)
    ready = deque(key for key, degree in degrees.items() if degree == 0)
    count = 0
    while ready:
        key = ready.popleft()
        count += 1
        for child in followers[key]:
            degrees[child] -= 1
            if degrees[child] == 0:
                ready.append(child)
    if count != len(tasks):
        raise ValueError("cyclic_work_dependencies")
    return normalized


def _settled_dependencies(dependencies, settled):
    if settled is None:
        return []
    if not isinstance(settled, (list, tuple)):
        raise ValueError("invalid_settled_dependencies")
    names = [_name(name) for name in settled]
    if len(set(names)) != len(names) or set(names) - set(dependencies):
        raise ValueError("invalid_settled_dependencies")
    return sorted(names)


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

    Not a persisted record or a transaction by itself. Apply all slots with
    apply() inside the journal's state store. Other destinations
    must implement their own replay/conflict checks in the same transaction.
    """

    slot: tuple[str, str, str]
    index_slot: tuple[str, str, str]
    _record_transform: Callable[[Any], Any]

    @property
    def slots(self):
        return (self.slot, self.index_slot)

    def apply(self, values):
        record = self._record_transform(values[self.slot])
        record["version"] = 5  # Index-unaware workers must fail closed.
        active = any(task["status"] in {"pending", "running"}
                     for task in record["tasks"].values())
        return {self.slot: record, self.index_slot: True if active else StateMutation.DELETE}


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
               dependencies=None, settled=None,
               mutations: Mapping[tuple[str, str, str], Callable[[Any], Any]] | None = None):
        """Commit intent with optional pure destination mutations in this store.

        Every destination owns replay/conflict checks. No callback may perform
        external effects or re-enter storage. Journal slots are reserved so a
        destination cannot bypass the task protocol. This is not cross-store
        atomicity, and successful replay must not reapply non-idempotent effects.
        """
        prepared = self.prepare_commit(request_id, result=result, tasks=tasks, dependencies=dependencies,
                                       settled=settled)
        return self._apply_with_destinations(prepared.slot, prepared._record_transform, mutations)

    def _apply_with_destinations(self, journal_slot, journal_transform, mutations):
        """Fence journal state before evaluating pure destination transforms."""
        transforms = dict(mutations) if mutations is not None else {}
        for slot, transform in transforms.items():
            if not isinstance(slot, tuple) or len(slot) != 3:
                raise ValueError("invalid_destination_slot")
            for part in slot:
                _name(part)
            if slot[0] in {"sage-work-journal-v1", "sage-work-active-v1"}:
                raise ValueError("destination_cannot_mutate_journal")
            if not callable(transform):
                raise TypeError("destination_transform_not_callable")
        prepared = PreparedWorkCommit(journal_slot,
            ("sage-work-active-v1", journal_slot[1], journal_slot[2]), journal_transform)
        def apply(values):
            # Evaluate journal fencing before any destination transform.
            result = prepared.apply(values)
            result.update({slot: transform(values[slot]) for slot, transform in transforms.items()})
            return result
        committed = self._store.update_many(
            (*prepared.slots, *transforms), apply,
        )
        return committed[journal_slot]

    def prepare_commit(self, request_id: str, *, result: Any, tasks: dict[str, Any], dependencies=None,
                       settled=None) -> PreparedWorkCommit:
        """Capture immutable JSON inputs without writing or starting work.

        Compose with destination mutations using this store's update_many.
        Never invoke a destination's own storage methods inside the callback.
        A successful prepare is not a successful commit or delivery receipt.
        """
        slot = self._slot(request_id)
        result = _json_snapshot(result)
        tasks = {_name(key): _json_snapshot(value) for key, value in tasks.items()}
        dependencies = _dependencies(tasks, dependencies)
        settled = _settled_dependencies(dependencies, settled)

        def apply(old):
            if old is not None:
                self._validate(old)
                original = {key: value["payload"] for key, value in old["tasks"].items()}
                if (old["result"] != result or original != tasks
                        or old.get("dependencies", {}) != dependencies or old.get("settled", []) != settled):
                    raise ValueError("journal_commit_conflict")
                return old
            return {"version": 4 if settled else 2 if dependencies else 1,
                    **({"settled": list(settled)} if settled else {}),
                    **({"dependencies": _json_snapshot(dependencies)} if dependencies else {}),
                    "result": _json_snapshot(result), "tasks": {
                key: {"payload": _json_snapshot(value), "status": "pending", "attempt": 0,
                      "token": None, "lease_until": 0.0, "available_at": 0.0}
                for key, value in tasks.items()
            }}

        return PreparedWorkCommit(slot, ("sage-work-active-v1", slot[1], slot[2]), apply)

    @staticmethod
    def _validate(record):
        if record is None:
            raise KeyError("journal_request_not_found")
        if record.get("version") not in {1, 2, 3, 4, 5}:
            raise ValueError("unsupported_journal_version")
        dependencies = record.get("dependencies", {})
        if record["version"] == 1 and dependencies:
            raise ValueError("dependencies_require_journal_v2")
        if _dependencies(record["tasks"], dependencies) != dependencies:
            raise ValueError("invalid_work_dependencies")
        settled = record.get("settled", [])
        if settled and record["version"] < 4:
            raise ValueError("settled_dependencies_require_journal_v4")
        if _settled_dependencies(dependencies, settled) != settled:
            raise ValueError("invalid_settled_dependencies")

    @staticmethod
    def dependencies_ready(record, task_id):
        """Readiness snapshot only; claim rechecks within its transaction."""
        accepted = {"done", "failed", "blocked"} if task_id in record.get("settled", []) else {"done"}
        return all(record["tasks"][parent]["status"] in accepted
                   for parent in record.get("dependencies", {}).get(task_id, []))

    def upgrade_dependencies(self, request_id, dependencies):
        """Explicit offline upgrade of independent tasks; never change a graph.

        Stop old workers first. Live leases and inconsistent completed children
        reject the upgrade. V2 records fail closed in dependency-unaware workers.
        """
        def upgrade(record):
            self._validate(record)
            graph = _dependencies(record["tasks"], dependencies)
            previous = record.get("dependencies", {})
            if previous == graph:
                return record
            if previous:
                raise ValueError("work_dependency_graph_immutable")
            now = self._clock()
            if any(task["status"] == "running" and task["lease_until"] > now
                   for task in record["tasks"].values()):
                raise ValueError("cannot_upgrade_dependencies_with_live_leases")
            if any(record["tasks"][child]["status"] == "done" and any(
                    record["tasks"][parent]["status"] != "done" for parent in parents)
                   for child, parents in graph.items()):
                raise ValueError("completed_work_has_unfinished_dependencies")
            record.update(version=max(2, record["version"]), dependencies=graph)
            return record
        return self._apply_with_destinations(self._slot(request_id), upgrade, None)

    def extend_tasks(self, request_id, *, tasks, dependencies=None, settled=None):
        """Offline additive migration; preserve existing payloads and graph edges.

        Stop old workers first. Replaying the same extension is idempotent;
        live leases reject changes. This never requeues terminal tasks.
        """
        tasks = {_name(key): _json_snapshot(value) for key, value in tasks.items()}
        edges = _json_snapshot({} if dependencies is None else dependencies)
        settled = list(settled) if isinstance(settled, tuple) else settled
        if not isinstance(edges, dict) or set(edges) - set(tasks):
            raise ValueError("extension_dependencies_must_belong_to_extended_tasks")
        settled = _settled_dependencies(edges, settled)

        def apply(record):
            self._validate(record)
            graph = record.get("dependencies", {})
            current_settled = record.get("settled", [])
            combined_graph = _dependencies({**record["tasks"], **tasks}, {**graph, **edges})
            combined_settled = _settled_dependencies(combined_graph, sorted(set(current_settled + settled)))
            for key, payload in tasks.items():
                if key in record["tasks"]:
                    if (record["tasks"][key]["payload"] != payload
                            or graph.get(key, []) != sorted(edges.get(key, []))
                            or (key in current_settled) != (key in settled)):
                        raise ValueError("work_extension_conflict")
            additions = set(tasks) - set(record["tasks"])
            if not additions:
                return record
            now = self._clock()
            if any(task["status"] == "running" and task["lease_until"] > now
                   for task in record["tasks"].values()):
                raise ValueError("cannot_extend_work_with_live_leases")
            for key in additions:
                record["tasks"][key] = {"payload": _json_snapshot(tasks[key]), "status": "pending",
                                        "attempt": 0, "token": None, "lease_until": 0.0, "available_at": 0.0}
            record.update(dependencies=combined_graph, settled=combined_settled,
                          version=max(record["version"], 4 if combined_settled else 2))
            changed = True
            while changed:
                changed = False
                for child, parents in combined_graph.items():
                    task = record["tasks"][child]
                    if (child not in combined_settled and task["status"] == "pending" and any(
                            record["tasks"][parent]["status"] in {"failed", "blocked"} for parent in parents)):
                        task.update(status="blocked", failure_code="dependency_failed")
                        record["version"] = max(record["version"], 3)
                        changed = True
            return record
        return self._apply_with_destinations(self._slot(request_id), apply, None)

    def claim(self, request_id: str, task_id: str, *, lease_seconds: float) -> TaskLease | None:
        _name(task_id)
        if not math.isfinite(lease_seconds) or lease_seconds <= 0:
            raise ValueError("lease_seconds_must_be_positive_and_finite")
        token = uuid.uuid4().hex
        claimed = []

        def apply(record):
            self._validate(record)
            task = record["tasks"][task_id]
            if not self.dependencies_ready(record, task_id):
                return record
            now = self._clock()
            if task.get("available_at", 0.0) > now or task["status"] in {"done", "failed", "blocked"} or (
                task["status"] == "running" and task["lease_until"] > now
            ):
                return record
            task.update(status="running", token=token, lease_until=now + lease_seconds,
                        attempt=task["attempt"] + 1)
            claimed.append(TaskLease(self.namespace, request_id, task_id, token, task["attempt"],
                                     _json_snapshot(task["payload"])))
            return record

        self._apply_with_destinations(self._slot(request_id), apply, None)
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

    def fail(self, lease: TaskLease, *, code: str, retry_delay: float | None = None):
        """Fence a classified failure; None delay is terminal, not success.

        Store only an application-defined code, never exception text. Terminal
        failure blocks dependent tasks atomically. Version 3 prevents older
        workers from interpreting these states as claimable pending work.
        """
        if not isinstance(code, str) or re.fullmatch(r"[a-z][a-z0-9_]{0,63}", code) is None:
            raise ValueError("invalid_work_failure_code")
        if retry_delay is not None and (not math.isfinite(retry_delay) or retry_delay < 0):
            raise ValueError("invalid_failure_retry_delay")
        if lease.namespace != self.namespace:
            raise ValueError("task_lease_namespace_mismatch")

        def apply(record):
            self._validate(record)
            task = record["tasks"][lease.task_id]
            now = self._clock()
            if (task["status"] != "running" or task["token"] != lease.token
                    or task["lease_until"] <= now):
                raise StaleTaskLeaseError("stale_task_lease")
            record["version"] = max(3, record["version"])
            task.update(status="failed" if retry_delay is None else "pending",
                        failure_code=code, token=None, lease_until=0.0,
                        available_at=0.0 if retry_delay is None else now + retry_delay)
            if retry_delay is None:
                changed = True
                while changed:
                    changed = False
                    for child, parents in record.get("dependencies", {}).items():
                        if child in record.get("settled", []):
                            continue
                        dependent = record["tasks"][child]
                        if dependent["status"] == "pending" and any(
                            record["tasks"][parent]["status"] in {"failed", "blocked"}
                            for parent in parents
                        ):
                            dependent.update(status="blocked", failure_code="dependency_failed")
                            changed = True
            return record
        return self._apply_with_destinations(self._slot(lease.request_id), apply, None)

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

        self._apply_with_destinations(self._slot(lease.request_id), apply, None)

    def records(self, *, cursor: int = 0, limit: int = 100):
        """Read-only paginated recovery scan; claims revalidate all eligibility.

        A scan is not a snapshot across pages. Repeat from zero after each sweep
        to discover records inserted before the previous cursor.
        """
        rows, next_cursor = self._store.query_namespace_entries(
            namespace=self.namespace, prefix="", limit=limit, cursor=cursor,
        )
        return [row for row in rows if row["stage_id"] == "sage-work-journal-v1"], next_cursor
