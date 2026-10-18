"""Independent, fail-closed dependency verification on the native work engine.

A fresh verifier binds a dependency to this process's current probe. Historical
success never unlocks a new binding. Probes are read-only, bounded synchronous
calls; keep credentials in the closure, never in names, results or exceptions
intended for storage. This module persists only generated binding IDs and fixed
status codes. It borrows storage and must drain before that storage is closed.
"""

from __future__ import annotations

import math
import threading
from uuid import uuid4

from sage.runtime.work_dispatcher import WorkFailure
from sage.runtime.work_journal import WorkJournal
from sage.runtime.work_service import WorkService


class DependencyRejected(RuntimeError):
    """Explicit permanent rejection; its message is never persisted."""


class DependencyVerifier:
    """One authoritative binding per dependency name in the supplied store.

    ``start`` commits pending state without waiting for network I/O. Exactly True
    verifies; False or DependencyRejected rejects permanently for this binding.
    Other exceptions retry through WorkService with bounded exponential delay.
    Their messages, types and probe responses are not journaled. A replacement
    must create a fresh verifier, capturing immutable configuration in its probe.
    Multiple replicas needing independent readiness must use distinct names.
    """

    def __init__(self, store, *, name: str, probe, retry_delay: float = 1,
                 max_retry_delay: float = 60, poll_interval: float = 0.05):
        if not isinstance(name, str) or not name or name != name.strip():
            raise ValueError("dependency_name_required")
        if not callable(probe):
            raise TypeError("dependency_probe_required")
        if (not all(math.isfinite(v) for v in (retry_delay, max_retry_delay))
                or not 0 < retry_delay <= max_retry_delay):
            raise ValueError("invalid_dependency_retry_timing")
        self._store = store
        self._probe = probe
        self._binding = uuid4().hex
        self._slot = ("sage-dependency-verifier-v1", name, "current")
        previous = store.peek(self._slot)
        self._previous = previous["binding"] if previous is not None else None
        self._retry_delay = retry_delay
        self._max_retry_delay = max_retry_delay
        self._lock = threading.RLock()
        self._started = False
        self._closing = False
        self.journal = WorkJournal(store, namespace="sage-dependency-verifier-v1:" + name)
        self._work = WorkService(self.journal, self._verify, max_workers=1,
                                 poll_interval=poll_interval,
                                 accept_task=lambda task, payload: payload == self._binding,
                                 completion_mutations=self._complete,
                                 failure_policy=self._failure)

    def _current(self):
        return self._store.peek(self._slot)

    def status(self):
        """Sanitized readiness, never an exception, credential or binding ID."""
        with self._lock:
            if self._closing:
                return {"state": "closed"}
            current = self._current()
            if current is None or current["binding"] != self._binding:
                return {"state": "superseded" if self._started else "not_started"}
            return {"state": current["state"]}

    def ready(self):
        return self.status()["state"] == "verified"

    def work_status(self):
        """Supervisor lifecycle is independent of a committed verification."""
        return self._work.status()

    def _register(self, current):
        if current is not None and current["binding"] == self._binding:
            return current  # Lost admission acknowledgement must not reset success.
        actual = current["binding"] if current is not None else None
        if actual != self._previous:
            raise RuntimeError("dependency_binding_superseded")
        return {"binding": self._binding, "state": "pending"}

    def start(self):
        with self._lock:
            if self._closing:
                raise RuntimeError("dependency_verifier_closing")
            if self._started:
                return self
            self.journal.commit(self._binding, result=None,
                                tasks={"verify": self._binding},
                                mutations={self._slot: self._register})
            # Retain audit records, but retire obsolete pending leases. Cancellation
            # protects the authoritative binding inside its own transaction, so an
            # overlapping newer startup cannot have its task cancelled by us.
            cursor = None
            while True:
                rows, cursor = self.journal.active_records(after_key=cursor)
                for row in rows:
                    key = row["key"]
                    if key != self._binding:
                        self.journal.cancel(key, "verify", protect={
                            self._slot: lambda value, key=key: (
                                value is not None and value["binding"] == key),
                        })
                if cursor is None:
                    break
            self._work.start()
            self._started = True
        return self

    def _verify(self, lease):
        current = self._current()
        if current is None or current["binding"] != self._binding:
            return "superseded"
        try:
            accepted = self._probe()
        except DependencyRejected:
            return "rejected"
        return "verified" if accepted is True else "rejected"

    def _complete(self, lease, result):
        def publish(current):
            if current is not None and current["binding"] == self._binding:
                return {**current, "state": result}
            return current
        return {self._slot: publish}

    def _failure(self, lease, error):
        return WorkFailure("dependency_unavailable", min(
            self._max_retry_delay, self._retry_delay * 2 ** min(lease.attempt - 1, 10)))

    def close(self, *, timeout: float = 30):
        with self._lock:
            self._closing = True
        self._work.close(timeout=timeout)
