"""Managed lifecycle for a SAGE durable journal and bounded dispatcher.

Owns the dispatch thread, not the injected state backend. On restart a new
service recovers the same journal; it never re-runs an upstream producer.
Synchronous handlers must terminate cooperatively. A close timeout does not
abandon their leases or pretend that shutdown has finished.
"""

from __future__ import annotations

import math
import threading
import time

from sage.runtime.work_dispatcher import WorkDispatcher
from sage.runtime.work_journal import WorkJournal


class WorkWaitTimeoutError(TimeoutError):
    """Observer deadline, distinct from a backend storage timeout."""


class WorkFailedError(RuntimeError):
    """Durable terminal failure; successful completion was not observed."""


class WorkService:
    def __init__(self, journal: WorkJournal, handler, **dispatcher_options):
        self.journal = journal
        self._dispatcher = WorkDispatcher(journal, handler, **dispatcher_options)
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._stopped = threading.Event()
        self._thread = None
        self._error = None
        self._closing = False
        self._closed = False
        self._retiring = False
        self._on_drained = None

    def _check_available(self):
        if self._error is not None:
            raise RuntimeError("work_service_failed") from self._error
        if self._closing or self._closed:
            raise RuntimeError("work_service_closing")

    def start(self):
        with self._lock:
            self._check_available()
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name="sage-work-service", daemon=True)
                self._thread.start()
        return self

    def _run(self):
        try:
            self._dispatcher.run(self._stop)
        except BaseException as exc:
            with self._lock:
                self._error = exc
        finally:
            with self._lock:
                try:
                    if self._retiring:
                        self._finish_retirement()
                except BaseException as exc:
                    self._error = exc
                finally:
                    self._stopped.set()

    def retire(self, on_drained):
        """Stop admission without joining; release resources after safe drain.

        Suitable for an owner's finalizer, including one invoked by a handler.
        The callback runs exactly once after dispatcher shutdown, never while
        handlers or journal acknowledgements still require its resources. It
        must only release resources (not wait for this service). Dispatch/drain
        failure retains resources and is reported by close/wait. Queued work
        stays durable for a replacement service. Retirement is one-shot.
        """
        if not callable(on_drained):
            raise TypeError("retirement_callback_must_be_callable")
        with self._lock:
            if self._retiring:
                raise RuntimeError("work_service_already_retiring")
            self._retiring = True
            self._on_drained = on_drained
            self._closing = True
            self._stop.set()
            if self._thread is None or self._stopped.is_set():
                self._finish_retirement()

    def _finish_retirement(self):
        # WorkDispatcher refuses shutdown if a failed supervisor still owns
        # active work. Do not close storage in that case.
        if self._error is not None:
            raise RuntimeError("work_service_failed") from self._error
        self._dispatcher.close()
        callback, self._on_drained = self._on_drained, None
        if callback is not None:
            callback()
        self._closed = True

    def commit(self, request_id, *, result, tasks, mutations=None, dependencies=None):
        """Admit one atomic journal/destination commit before starting dispatch.

        The admission lock also serializes shutdown against the transaction.
        A failure never starts a fresh dispatcher. A lost acknowledgement may
        still have committed; replay safely or recover the journal on restart.
        Existing workers can observe committed intents, never partial writes.
        """
        with self._lock:
            self._check_available()
            committed = self.journal.commit(request_id, result=result, tasks=tasks,
                                            mutations=mutations, dependencies=dependencies)
            self.start()
            return committed

    def wait(self, request_id, *, timeout: float):
        """Return a detached completed record, or raise without cancelling work."""
        if not math.isfinite(timeout) or timeout < 0:
            raise ValueError("invalid_work_wait_timeout")
        deadline = time.monotonic() + timeout
        while True:
            record = self.journal.read(request_id)
            if record is None:
                raise KeyError("journal_request_not_found")
            if any(task["status"] in {"failed", "blocked"} for task in record["tasks"].values()):
                raise WorkFailedError("work_request_failed")
            if all(task["status"] == "done" for task in record["tasks"].values()):
                return record
            with self._lock:
                if self._error is not None:
                    raise RuntimeError("work_service_failed") from self._error
                if self._stopped.is_set():
                    raise RuntimeError("work_service_stopped_with_pending_work")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise WorkWaitTimeoutError("work_result_wait_timeout")
            self._stopped.wait(min(remaining, self._dispatcher.poll_interval))

    def close(self, *, timeout: float = 30):
        if not math.isfinite(timeout) or timeout < 0:
            raise ValueError("invalid_work_close_timeout")
        with self._lock:
            if self._closed:
                return
            self._closing = True
            self._stop.set()
            thread = self._thread
        if thread is not None:
            if thread is threading.current_thread():
                raise RuntimeError("work_service_cannot_join_itself")
            thread.join(timeout)
            if thread.is_alive():
                raise TimeoutError("work_service_drain_timeout")
        else:
            self._stopped.set()
        with self._lock:
            self._dispatcher.close()
            self._closed = True
            if self._error is not None:
                raise RuntimeError("work_service_failed") from self._error
