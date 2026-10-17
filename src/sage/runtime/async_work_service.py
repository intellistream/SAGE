"""Async callers and handlers over the existing durable WorkService.

The creating event loop owns handler execution and must remain alive until
aclose finishes. The existing dispatcher alone owns leases, retries, bounds and
acknowledgements. Cancelling an observer never cancels admitted work. Storage
is borrowed; close this service before closing its state or async clients.
"""

from __future__ import annotations

import asyncio
import contextvars
import inspect
import math

from sage.runtime.work_service import WorkService, WorkWaitTimeoutError

_HANDLER_SERVICE = contextvars.ContextVar("sage_async_work_handler", default=None)


class AsyncWorkService:
    def __init__(self, journal, handler, **dispatcher_options):
        if not (inspect.iscoroutinefunction(handler)
                or (callable(handler) and inspect.iscoroutinefunction(handler.__call__))):
            raise TypeError("async_work_handler_required")
        self._loop = asyncio.get_running_loop()
        self.journal = journal
        self._handler = handler
        self._poll_interval = dispatcher_options.get("poll_interval", 1)
        self._service = WorkService(journal, self._invoke, **dispatcher_options)

    def _check_loop(self):
        if asyncio.get_running_loop() is not self._loop:
            raise RuntimeError("async_work_service_loop_mismatch")

    def _check_observer(self):
        self._check_loop()
        if _HANDLER_SERVICE.get() is self:
            raise RuntimeError("async_work_handler_cannot_wait_or_close_own_service")

    async def _execute(self, lease):
        token = _HANDLER_SERVICE.set(self)
        try:
            return await self._handler(lease)
        finally:
            _HANDLER_SERVICE.reset(token)

    def _invoke(self, lease):
        coroutine = self._execute(lease)
        try:
            future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        except BaseException:
            coroutine.close()
            raise
        return future.result()

    async def _offload(self, function, *args, **kwargs):
        self._check_loop()
        operation = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
        cancelled = False
        while not operation.done():
            try:
                await asyncio.shield(operation)
            except asyncio.CancelledError:
                # Cancelling the waiter cannot stop a transaction or close
                # thread. Retain ownership through repeated cancellations.
                cancelled = True
        result = operation.result()  # Surface actual storage/drain failures.
        if cancelled:
            raise asyncio.CancelledError
        return result

    async def start(self):
        await self._offload(self._service.start)
        return self

    async def commit(self, request_id, *, result, tasks, mutations=None, dependencies=None, settled=None):
        return await self._offload(self._service.commit, request_id,
                                   result=result, tasks=tasks, mutations=mutations, dependencies=dependencies,
                                   settled=settled)

    async def wait(self, request_id, *, timeout):
        self._check_observer()
        if not math.isfinite(timeout) or timeout < 0:
            raise ValueError("invalid_work_wait_timeout")
        deadline = self._loop.time() + timeout
        while True:
            try:
                return await self._offload(self._service.wait, request_id, timeout=0)
            except WorkWaitTimeoutError:
                remaining = deadline - self._loop.time()
                if remaining <= 0:
                    raise WorkWaitTimeoutError("work_result_wait_timeout") from None
                await asyncio.sleep(min(remaining, self._poll_interval))

    async def aclose(self, *, timeout=30):
        self._check_observer()
        await self._offload(self._service.close, timeout=timeout)
