from __future__ import annotations

import asyncio
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class _PendingReply:
    loop: asyncio.AbstractEventLoop
    future: asyncio.Future[Any]


class V1ReplyTracker:
    """Tracks pending request futures keyed by outbound msg_id."""

    def __init__(self) -> None:
        self._pending: dict[str, _PendingReply] = {}
        self._lock = Lock()

    def register(self, msg_id: str) -> asyncio.Future[Any]:
        normalized = _normalize_non_empty(msg_id, field_name="msg_id")
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        with self._lock:
            if normalized in self._pending:
                raise ValueError(f"reply_tracker_duplicate_msg_id:{normalized}")
            self._pending[normalized] = _PendingReply(loop=loop, future=future)
        return future

    def complete(self, *, reply_to_msg_id: str, value: Any) -> bool:
        pending = self._pop(reply_to_msg_id)
        if pending is None:
            return False
        return self._schedule_future_result(pending, value=value)

    def fail(self, *, reply_to_msg_id: str, exc: BaseException) -> bool:
        pending = self._pop(reply_to_msg_id)
        if pending is None:
            return False
        return self._schedule_future_exception(pending, exc=exc)

    def cancel(self, msg_id: str) -> bool:
        pending = self._pop(msg_id)
        if pending is None:
            return False
        return self._schedule_future_cancel(pending)

    def cancel_all(self) -> int:
        with self._lock:
            pendings = list(self._pending.values())
            self._pending.clear()
        cancelled = 0
        for pending in pendings:
            if self._schedule_future_cancel(pending):
                cancelled += 1
        return cancelled

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def _pop(self, msg_id: str) -> _PendingReply | None:
        normalized = _normalize_non_empty(msg_id, field_name="msg_id")
        with self._lock:
            return self._pending.pop(normalized, None)

    @staticmethod
    def _schedule_future_result(pending: _PendingReply, *, value: Any) -> bool:
        def _set_result() -> None:
            if pending.future.done():
                return
            pending.future.set_result(value)

        return V1ReplyTracker._schedule_on_loop(pending.loop, _set_result)

    @staticmethod
    def _schedule_future_exception(pending: _PendingReply, *, exc: BaseException) -> bool:
        def _set_exception() -> None:
            if pending.future.done():
                return
            pending.future.set_exception(exc)

        return V1ReplyTracker._schedule_on_loop(pending.loop, _set_exception)

    @staticmethod
    def _schedule_future_cancel(pending: _PendingReply) -> bool:
        def _cancel() -> None:
            if pending.future.done():
                return
            pending.future.cancel()

        return V1ReplyTracker._schedule_on_loop(pending.loop, _cancel)

    @staticmethod
    def _schedule_on_loop(
        loop: asyncio.AbstractEventLoop,
        callback: Any,
    ) -> bool:
        if loop.is_closed():
            return False
        try:
            loop.call_soon_threadsafe(callback)
        except RuntimeError:
            return False
        return True


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


__all__ = ["V1ReplyTracker"]
