"""Bounded, restartable dispatch of SAGE journal tasks.

The handler receives a TaskLease and must implement destination idempotency.
Only one thread may drive run_once/run for a dispatcher. Journal leases arbitrate
between multiple dispatchers. No request context or credentials are persisted.
An optional accept_task(task_id, payload) selector must be a fast, pure routing
decision returning bool. It is not authorization. It runs before lease claim;
unmatched tasks remain pending for their destination. Predicate errors fail the
supervisor rather than silently dropping work.

An optional completion_mutations(lease, result) prepares pure same-store
destination transforms for the journal's fenced completion transaction. It
must not perform external effects. Preparation/storage failures propagate;
the task is not acknowledged and can be recovered by its next lease owner.
"""

import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Event

from sage.runtime.work_journal import StaleTaskLeaseError, WorkJournal


@dataclass(frozen=True)
class WorkFailure:
    """Safe failure classification; None delay stops retries durably."""

    code: str
    retry_delay: float | None = None


class WorkDispatcher:
    def __init__(self, journal: WorkJournal, handler, *, max_workers: int = 2,
                 lease_seconds: float = 60, retry_delay: float = 5,
                 poll_interval: float = 1, page_size: int = 100, accept_task=None,
                 completion_mutations=None, failure_policy=None):
        if max_workers < 1 or page_size < 1:
            raise ValueError("dispatcher_bounds_must_be_positive")
        if accept_task is not None and not callable(accept_task):
            raise TypeError("task_selector_must_be_callable")
        if completion_mutations is not None and not callable(completion_mutations):
            raise TypeError("completion_mutations_must_be_callable")
        if failure_policy is not None and not callable(failure_policy):
            raise TypeError("failure_policy_must_be_callable")
        if (not all(math.isfinite(v) for v in (lease_seconds, retry_delay, poll_interval))
                or not 0 < poll_interval < lease_seconds / 3 or retry_delay < 0):
            raise ValueError("invalid_dispatcher_timing")
        self.journal = journal
        self.handler = handler
        self.accept_task = accept_task
        self.completion_mutations = completion_mutations
        self.failure_policy = failure_policy
        self.max_workers = max_workers
        self.lease_seconds = lease_seconds
        self.retry_delay = retry_delay
        self.poll_interval = poll_interval
        self.page_size = page_size
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="sage-work")
        self._active = {}
        self._cursor = 0
        self._closed = False
        self.completed = 0
        self.failed = 0
        self.lease_losses = 0
        self._lost = set()

    def run_once(self, *, admit: bool = True) -> int:
        """Maintain leases, acknowledge completed work, inspect one bounded page.

        Storage/fencing failures propagate to the supervisor; they are never
        interpreted as successful work. Handler failures persist a delayed retry.
        """
        if self._closed:
            raise RuntimeError("work_dispatcher_closed")
        for future, lease in list(self._active.items()):
            if future in self._lost:
                if future.done():
                    del self._active[future]
                    self._lost.remove(future)
                continue
            if not future.done():
                try:
                    self.journal.renew(lease, lease_seconds=self.lease_seconds)
                except StaleTaskLeaseError:
                    self.lease_losses += 1
                    self._lost.add(future)
                    raise
                continue
            failed = future.exception() is not None
            try:
                if failed:
                    if self.failure_policy is None:
                        self.journal.finish(lease, retry=True, retry_delay=self.retry_delay)
                    else:
                        decision = self.failure_policy(lease, future.exception())
                        if not isinstance(decision, WorkFailure):
                            raise TypeError("failure_policy_must_return_work_failure")
                        self.journal.fail(lease, code=decision.code, retry_delay=decision.retry_delay)
                else:
                    result = future.result()
                    mutations = (self.completion_mutations(lease, result)
                                 if self.completion_mutations is not None else None)
                    self.journal.finish(lease, result=result, mutations=mutations)
            except StaleTaskLeaseError:
                self.lease_losses += 1
                del self._active[future]
                raise
            del self._active[future]
            if failed:
                self.failed += 1
            else:
                self.completed += 1
        if not admit or len(self._active) >= self.max_workers:
            return 0
        rows, following = self.journal.records(cursor=self._cursor, limit=self.page_size)
        active_keys = {(lease.request_id, lease.task_id) for lease in self._active.values()}
        admitted = 0
        for row in rows:
            for task_id, task in row["value"]["tasks"].items():
                if len(self._active) >= self.max_workers:
                    # Revisit this page: unclaimed tasks must not be skipped.
                    return admitted
                if task["status"] in {"done", "failed", "blocked"} or (row["key"], task_id) in active_keys:
                    continue
                if any(row["value"]["tasks"][parent]["status"] != "done"
                       for parent in row["value"].get("dependencies", {}).get(task_id, [])):
                    continue  # claim() rechecks atomically; avoid writes for known blocked work.
                if self.accept_task is not None:
                    # Selection precedes lease acquisition. A worker must not
                    # claim/retry another destination's tasks just to route them.
                    # records() returns detached JSON; claim() returns the
                    # authoritative immutable payload even if selection mutates it.
                    accepted = self.accept_task(task_id, task["payload"])
                    if type(accepted) is not bool:
                        raise TypeError("task_selector_must_return_bool")
                    if not accepted:
                        continue
                lease = self.journal.claim(row["key"], task_id, lease_seconds=self.lease_seconds)
                if lease is None:
                    continue
                try:
                    future = self._pool.submit(self.handler, lease)
                except BaseException:
                    self.journal.finish(lease, retry=True, retry_delay=self.retry_delay)
                    raise
                self._active[future] = lease
                admitted += 1
        self._cursor = following or 0
        return admitted

    def run(self, stop: Event) -> None:
        """Run until stopped, then drain work while maintaining its leases.

        A supervisor must surface exceptions and arrange a restart. Running
        synchronous handlers cannot be forcibly stopped by this dispatcher.
        """
        while not stop.is_set() or self._active:
            self.run_once(admit=not stop.is_set())
            if stop.is_set():
                Event().wait(self.poll_interval)
            else:
                stop.wait(self.poll_interval)

    def close(self) -> None:
        """Close only after run has drained; never abandon active lease renewal."""
        if self._active:
            raise RuntimeError("work_dispatcher_not_drained")
        if not self._closed:
            self._closed = True
            self._pool.shutdown(wait=True)
