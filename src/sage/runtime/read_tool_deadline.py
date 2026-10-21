"""Bound caller latency for read-only ports, including blocking DNS adapters.

Python cannot kill a blocked resolver thread. Limit outstanding calls, retain
ownership until cleanup and discard late results; never claim cancellation ack.
Do not use this executor for writes, payments or externally mutating tools.
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from contextvars import copy_context
from threading import BoundedSemaphore


class ReadToolDeadlineExceeded(TimeoutError):
    pass


class ReadToolExecutor:
    def __init__(self, capacity=4):
        self._slots = BoundedSemaphore(capacity)
        self._pool = ThreadPoolExecutor(max_workers=capacity, thread_name_prefix="sage-read-tool")

    def call(self, operation, *, timeout):
        if not self._slots.acquire(blocking=False):
            raise RuntimeError("read_tool_capacity_exhausted")
        context = copy_context()

        def run():
            try:
                return context.run(operation)
            finally:
                self._slots.release()

        try:
            future = self._pool.submit(run)
        except BaseException:
            self._slots.release()
            raise
        future.add_done_callback(
            lambda result: self._slots.release() if result.cancelled() else None
        )
        try:
            return future.result(timeout=max(0, timeout))
        except TimeoutError as error:
            if future.done():
                raise
            future.cancel()
            raise ReadToolDeadlineExceeded(
                "read_tool_deadline_exceeded_cleanup_may_be_pending"
            ) from error

    def close(self):
        self._pool.shutdown(wait=True, cancel_futures=True)


read_tool_executor = ReadToolExecutor()
