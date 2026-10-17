"""Bounded, runtime-owned coordination of independent cursor waves.

This pool must not share actor worker lanes: cursor execution waits for actors.
"""

from concurrent.futures import ThreadPoolExecutor, wait
from contextvars import ContextVar, copy_context
from threading import BoundedSemaphore, Lock

from sage.runtime.cancellation import raise_if_request_cancelled


_active_scheduler: ContextVar[object | None] = ContextVar("sage_branch_scheduler", default=None)


class BranchScheduler:
    def __init__(self, *, max_workers: int, max_inflight_waves: int = 16):
        if max_workers < 1 or max_inflight_waves < 1:
            raise ValueError("branch scheduler limits must be positive")
        self.max_workers = max_workers
        self._slots = BoundedSemaphore(max_inflight_waves)
        self._lock = Lock()
        self._closed = False
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="sage-flow-branch"
        )

    def run(self, function, items):
        raise_if_request_cancelled()
        if len(items) > self.max_workers:
            raise ValueError("branch_wave_exceeds_worker_limit")
        if _active_scheduler.get() is self:
            raise RuntimeError("branch_scheduler_reentrant_wait")
        if not self._slots.acquire(blocking=False):
            raise RuntimeError("branch_scheduler_overloaded")
        futures = []
        try:
            # Admit each wave atomically so requests cannot interleave partial
            # waves and deadlock actors waiting for their sibling branch.
            with self._lock:
                if self._closed:
                    raise RuntimeError("branch_scheduler_closed")
                for item in items:
                    futures.append(self._executor.submit(
                        copy_context().run, self._invoke, function, item
                    ))
            results = [future.result() for future in futures]
            raise_if_request_cancelled()
            return results
        finally:
            # Cancellation of queued work is not cancellation of running work.
            # Never release admission or report completion while siblings run.
            wait(futures)
            self._slots.release()

    def _invoke(self, function, item):
        token = _active_scheduler.set(self)
        try:
            raise_if_request_cancelled()
            return function(item)
        finally:
            _active_scheduler.reset(token)

    def close(self, *, wait: bool = True, cancel_futures: bool = False):
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)
