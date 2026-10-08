from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from concurrent.futures import Future


class LoopThread:
    """Dedicated event-loop thread used by v1 runtime host."""

    def __init__(self, name: str):
        normalized_name = str(name or "").strip()
        if not normalized_name:
            raise ValueError("name must be non-empty.")
        self._name = normalized_name
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._stop_lock = threading.Lock()
        self._stopped = False
        self._start()

    @property
    def name(self) -> str:
        return self._name

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            raise RuntimeError("loop not initialized")
        return self._loop

    @property
    def is_running(self) -> bool:
        return self._loop is not None and self._loop.is_running()

    def submit(self, coro: Coroutine) -> Future:
        if self._stopped:
            raise RuntimeError("loop_thread_stopped")
        if not asyncio.iscoroutine(coro):
            raise TypeError("submit(...) expects a coroutine object.")
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self, *, join: bool = True, join_timeout: float | None = 2.0) -> None:
        with self._stop_lock:
            if self._stopped:
                return
            self._stopped = True
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        if join and self._thread is not None:
            self._thread.join(join_timeout)

    def _start(self) -> None:
        def _run_loop() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            self._ready.set()
            try:
                loop.run_forever()
            finally:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.close()

        thread = threading.Thread(target=_run_loop, daemon=True, name=self._name)
        thread.start()
        self._ready.wait()
        self._thread = thread


__all__ = ["LoopThread"]
