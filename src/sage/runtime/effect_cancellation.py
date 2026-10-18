"""Durable destination fences and native recovery for cross-store cancellation.

This does not implement distributed rollback. Each destination must check its
fence INSIDE every effect transaction. Seals are permanent for a trusted unique
request identity; already committed effects and admitted external work are not
undone. No cancellation is acknowledged until every declared seal is durable.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from uuid import uuid4

from sage.runtime.async_work_service import complete_sync_call
from sage.runtime.work_dispatcher import WorkFailure
from sage.runtime.work_journal import WorkJournal
from sage.runtime.work_service import WorkService


def _name(value):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("cancellation_identifier_required")
    return value


def _validate_fence(value):
    if value is not None and value != {"version": 1, "sealed": True}:
        raise ValueError("invalid_effect_fence")


class EffectCancelled(PermissionError):
    """The destination has durably fenced this request's future effects."""


@dataclass(frozen=True)
class PreparedEffectGuard:
    """Destination-local assertion, not a remote lease or authorization token."""

    slot: tuple[str, str, str]
    _store: object

    def validate_store(self, store):
        if store is not self._store:
            raise ValueError("effect_guard_must_share_state_store")

    def apply(self, values):
        value = values[self.slot]
        _validate_fence(value)
        if value is not None:
            raise EffectCancelled("effect_scope_cancelled")
        return {self.slot: value}


class EffectFences:
    """Borrowed destination storage. Prepare guards before, check inside commit.

    An absent seal permits a write. All participating writers, including replay,
    must use a guard. The scope is supplied by trusted ingress, never raw user
    input. A seal does not expire, reopen, delete effects or close the store.
    """

    def __init__(self, store, *, namespace):
        self._store = store
        self.namespace = _name(namespace)
        self._identity_slot = ("sage-effect-fence-destinations-v1", self.namespace, "identity")
        candidate_identity = uuid4().hex

        def identify(value):
            if value is None:
                return {"version": 1, "identity": candidate_identity}
            self._identity_value(value)
            return value

        store.update(self._identity_slot, identify)

    @staticmethod
    def _identity_value(value):
        if (not isinstance(value, dict) or set(value) != {"version", "identity"}
                or value["version"] != 1 or not isinstance(value["identity"], str)
                or len(value["identity"]) != 32):
            raise ValueError("invalid_effect_destination_identity")
        return value["identity"]

    @property
    def identity(self):
        return self._identity_value(self._store.peek(self._identity_slot))

    def _slot(self, scope):
        return ("sage-effect-fences-v1", self.namespace, _name(scope))

    def prepare_guard(self, scope):
        return PreparedEffectGuard(self._slot(scope), self._store)

    def seal(self, scope):
        def close(value):
            _validate_fence(value)
            return {"version": 1, "sealed": True}
        self._store.update(self._slot(scope), close)

    def is_sealed(self, scope):
        """Observation only; never substitute this read for a transaction guard."""
        value = self._store.peek(self._slot(scope))
        _validate_fence(value)
        return value is not None


class CancellationService:
    """Seal every destination before cancelling one origin journal task.

    WorkService owns scheduling, leases, retry and recovery. ``targets`` maps
    stable destination names to EffectFences or lazy providers returning them.
    ``protection(request_id)`` optionally prepares the origin's normal same-store
    cancellation protection predicates. It must not perform external effects.
    Authorization belongs to the caller on every request, observation and replay.

    A pending request is NOT a successful cancellation. Observe ``wait`` for a
    settled outcome. Timeouts leave native work recoverable, never acknowledge a
    partial seal. Start a replacement service on restart with all destination
    providers, including any referenced by old pending requests. Drain before
    closing ANY borrowed destination/origin stores.
    """

    def __init__(self, origin: WorkJournal, *, task_id: str, targets,
                 protection=None, retry_delay: float = 1, max_retry_delay: float = 60,
                 poll_interval: float = 0.05, lease_seconds: float = 60):
        if not isinstance(origin, WorkJournal):
            raise TypeError("cancellation_origin_journal_required")
        self._task_id = _name(task_id)
        self._targets = {_name(name): provider for name, provider in targets.items()}
        if any(not isinstance(provider, EffectFences) and not callable(provider)
               for provider in self._targets.values()):
            raise ValueError("cancellation_destinations_required")
        if protection is not None and not callable(protection):
            raise TypeError("cancellation_protection_provider_required")
        if (not all(math.isfinite(v) for v in (retry_delay, max_retry_delay))
                or not 0 < retry_delay <= max_retry_delay):
            raise ValueError("invalid_cancellation_retry_timing")
        self._origin = origin
        self._protection = protection
        self._retry_delay = retry_delay
        self._max_retry_delay = max_retry_delay
        identity = json.dumps([origin.namespace, task_id], separators=(",", ":"))
        namespace = "sage-cancellation-v1:" + hashlib.sha256(identity.encode()).hexdigest()
        self.journal = WorkJournal(origin._store, namespace=namespace)
        self._work = WorkService(self.journal, self._handle, max_workers=2,
                                 poll_interval=poll_interval, lease_seconds=lease_seconds,
                                 failure_policy=self._failure)

    def start(self):
        self._work.start()
        return self

    def work_status(self):
        return self._work.status()

    def request(self, request_id):
        """Return accepted/missing/terminal; accepted never means cancelled."""
        request_id = _name(request_id)
        existing = self.journal.read(request_id)
        source = self._origin.read(request_id)
        task = source["tasks"].get(self._task_id) if source is not None else None
        if existing is None:
            if task is None:
                return "missing"
            if task["status"] not in {"pending", "running"}:
                return "terminal"
        targets = sorted(self._targets)
        identities = {name: self._target(name).identity for name in targets}
        seals = {"seal:" + name: {"destination": name, "identity": identities[name]} for name in targets}
        self._work.commit(request_id, result={"targets": identities},
                          tasks={**seals, "finish": {"targets": identities}},
                          dependencies={"finish": sorted(seals)})
        return "accepted"

    def _target(self, name):
        provider = self._targets[name]
        target = provider if isinstance(provider, EffectFences) else provider()
        if not isinstance(target, EffectFences):
            raise TypeError("cancellation_target_must_return_effect_fences")
        return target

    def _bound_target(self, name, identity):
        target = self._target(name)
        if target.identity != identity:
            raise ValueError("cancellation_destination_identity_changed")
        return target

    def _handle(self, lease):
        if lease.task_id == "finish":
            # Revalidate persisted bindings, including seals acknowledged before
            # restart. A remapped destination may never inherit another store's
            # acknowledgement. Re-sealing is idempotent and fail-closed.
            for name, identity in lease.payload["targets"].items():
                self._bound_target(name, identity).seal(lease.request_id)
            protect = self._protection(lease.request_id) if self._protection is not None else None
            outcome = self._origin.cancel(lease.request_id, self._task_id, protect=protect)
            if outcome == "terminal":
                # Restore a committed cancellation after its acknowledgement was
                # lost. Do not mistake an unrelated terminal task for cancelled.
                record = self._origin.read(lease.request_id)
                task = record["tasks"].get(self._task_id) if record is not None else None
                if task is not None and task.get("failure_code") == "request_cancelled":
                    outcome = "cancelled"
            return outcome
        name = lease.payload["destination"]
        if lease.task_id != "seal:" + name:
            raise ValueError("invalid_cancellation_task")
        target = self._bound_target(name, lease.payload["identity"])
        target.seal(lease.request_id)
        return {"sealed": True}

    def _failure(self, lease, error):
        # Availability/configuration failures cannot become successful partial
        # cancellation. Keep the durable intent recoverable without raw errors.
        return WorkFailure("cancellation_unavailable", min(
            self._max_retry_delay, self._retry_delay * 2 ** min(lease.attempt - 1, 10)))

    def wait(self, request_id, *, timeout: float):
        """Only returns after every seal and the origin outcome are durable."""
        record = self._work.wait(request_id, timeout=timeout)
        return record["tasks"]["finish"]["result"]

    def close(self, *, timeout: float = 30):
        self._work.close(timeout=timeout)

    async def astart(self):
        return await complete_sync_call(self.start)

    async def arequest(self, request_id):
        return await complete_sync_call(self.request, request_id)

    async def await_result(self, request_id, *, timeout: float):
        """Cancelling an observer cannot abandon a borrowed-store read thread."""
        return await complete_sync_call(self.wait, request_id, timeout=timeout)

    async def aclose(self, *, timeout: float = 30):
        await complete_sync_call(self.close, timeout=timeout)
