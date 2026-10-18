"""Content-free durable attempt observations on the existing work engine.

Only started can be published without settling an attempt. Terminal/retry events
must compose with WorkJournal's corresponding fenced acknowledgement. A task
completion is not an acknowledgement of an effect in an external system.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field

from sage.runtime.event_journal import EventJournal


@dataclass(frozen=True)
class WorkEventDestination:
    journal: EventJournal = field(repr=False)
    stream_id: str


@dataclass(frozen=True)
class WorkEvent:
    version: int
    event_id: str
    namespace: str
    request_id: str
    task_id: str
    attempt: int
    state: str
    timestamp_ns: int
    duration_ns: int | None
    dependency_task_ids: tuple[str, ...]
    dependency_mode: str
    failure_code: str | None
    error_type: str | None

    def to_dict(self):
        return asdict(self)


def _identity(lease):
    return (lease.namespace, lease.request_id, lease.task_id, lease.attempt, lease.token)


@dataclass(frozen=True)
class PreparedWorkObservation:
    """A pure event append, not a published event or task acknowledgement."""

    event: WorkEvent
    _journal: object = field(repr=False)
    _lease_identity: tuple = field(repr=False)
    _destination: WorkEventDestination = field(repr=False)


def observation_mutations(journal, lease, state, observation, mutations=None):
    """Compose native observation BEFORE application events (possibly terminal)."""
    result = dict(mutations or {})
    if observation is None:
        return result
    if (not isinstance(observation, PreparedWorkObservation)
            or observation._journal is not journal
            or observation._lease_identity != _identity(lease)
            or observation.event.state != state
            or (observation.event.namespace, observation.event.request_id,
                observation.event.task_id, observation.event.attempt) != _identity(lease)[:4]):
        raise ValueError("work_observation_scope_or_state_mismatch")
    if state in {"started", "completed"} and (
            observation.event.failure_code is not None or observation.event.error_type is not None):
        raise ValueError("work_observation_unexpected_failure")
    target = observation._destination
    if (not isinstance(target, WorkEventDestination) or not isinstance(target.journal, EventJournal)
            or target.journal._store is not journal._store):
        raise ValueError("work_observation_requires_same_store")
    prepared = target.journal.prepare_append(target.stream_id, event_id=observation.event.event_id,
        payload={"type": "work-event", "event": observation.event.to_dict()})
    application = result.get(prepared.slot)
    if prepared.slot in result and not callable(application):
        raise TypeError("destination_transform_not_callable")

    def apply(old):
        updated = prepared.transform(old)
        return application(updated) if application is not None else updated

    result[prepared.slot] = apply
    return result


class WorkObserver:
    """A destination port; scheduling and state semantics stay inside SAGE.

    destination(lease) returns an owned WorkEventDestination, or None for an
    explicitly unobserved task. The port lives as long as the work service: do
    not capture request credentials or an application owner that must be freed.
    No task payload, result, token or exception message is emitted.
    """

    def __init__(self, journal, destination: Callable):
        from sage.runtime.work_journal import WorkJournal

        if not isinstance(journal, WorkJournal) or not callable(destination):
            raise TypeError("work_observer_requires_journal_and_destination")
        self.journal = journal
        self._destination = destination

    def bind(self, lease):
        from sage.runtime.work_journal import TaskLease

        if not isinstance(lease, TaskLease) or lease.namespace != self.journal.namespace:
            raise ValueError("work_observation_namespace_mismatch")
        target = self._destination(lease)
        if target is None:
            return None
        if (not isinstance(target, WorkEventDestination)
                or not isinstance(target.journal, EventJournal)
                or target.journal._store is not self.journal._store):
            raise ValueError("work_observation_requires_same_store")
        if (not isinstance(target.stream_id, str) or not target.stream_id
                or target.stream_id != target.stream_id.strip()):
            raise ValueError("invalid_work_observation_stream")
        record = self.journal.read(lease.request_id)
        if record is None or lease.task_id not in record["tasks"]:
            raise ValueError("work_observation_task_missing")
        return _WorkAttempt(self.journal, lease, target,
                            tuple(record.get("dependencies", {}).get(lease.task_id, ())),
                            "settled" if lease.task_id in record.get("settled", ()) else "success")


class _WorkAttempt:
    def __init__(self, journal, lease, target, dependencies, dependency_mode):
        self.journal, self.lease, self.target = journal, lease, target
        self.dependencies = dependencies
        self.dependency_mode = dependency_mode
        self._started_ns = None

    def started(self):
        self._started_ns = time.monotonic_ns()
        self.journal.observe(self.lease, self.prepare("started"))

    def prepare(self, state, *, error=None, failure_code=None):
        if state not in {"started", "completed", "retrying", "failed"}:
            raise ValueError("invalid_work_observation_state")
        if state in {"started", "completed"} and (error is not None or failure_code is not None):
            raise ValueError("work_observation_unexpected_failure")
        if failure_code is not None and (not isinstance(failure_code, str)
                or re.fullmatch(r"[a-z][a-z0-9_]{0,63}", failure_code) is None):
            raise ValueError("invalid_work_observation_failure_code")
        error_type = type(error).__name__ if error is not None else None
        if error_type is not None and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", error_type) is None:
            error_type = "Exception"
        public_identity = [self.lease.namespace, self.lease.request_id, self.lease.task_id,
                           self.lease.attempt, state]
        event_id = "work:" + hashlib.sha256(json.dumps(public_identity, separators=(",", ":")).encode()).hexdigest()
        duration = (time.monotonic_ns() - self._started_ns
                    if state != "started" and self._started_ns is not None else None)
        event = WorkEvent(1, event_id, self.lease.namespace, self.lease.request_id,
            self.lease.task_id, self.lease.attempt, state, time.time_ns(), duration,
            self.dependencies, self.dependency_mode, failure_code, error_type)
        return PreparedWorkObservation(event, self.journal, _identity(self.lease), self.target)
