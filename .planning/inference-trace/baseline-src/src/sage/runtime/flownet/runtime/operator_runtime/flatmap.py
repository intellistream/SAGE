from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from typing import Any

from .errors import FlatMapContractError
from .models import _FlatMapContinuationState


class FlatMapContinuationRuntime:
    """
    Runtime-local continuation store for incremental `flatmap` iteration.

    The continuation state is intentionally in-memory and runtime-local:
    cursors only carry a session id; iterator objects are never serialized.
    """

    def __init__(
        self,
        *,
        run_coroutine: Callable[[Awaitable[Any]], Any] | None = None,
    ) -> None:
        self._sessions: dict[str, _FlatMapContinuationState] = {}
        self._session_nonce = 0
        self._run_coroutine = run_coroutine

    def allocate_session_id(
        self,
        *,
        event_group_id: str,
        event_chain_id: str,
        pc_node_id: str,
    ) -> str:
        self._session_nonce += 1
        return f"flatmap:{event_group_id}:{event_chain_id}:{pc_node_id}:{self._session_nonce}"

    def register_sync_iterator(
        self,
        *,
        session_id: str,
        iterator: Iterator[Any],
    ) -> None:
        self._register_session(
            session_id=session_id,
            state=_FlatMapContinuationState(mode="sync", iterator=iterator),
        )

    def register_async_iterator(
        self,
        *,
        session_id: str,
        iterator: AsyncIterator[Any],
    ) -> None:
        self._register_session(
            session_id=session_id,
            state=_FlatMapContinuationState(mode="async", iterator=iterator),
        )

    def advance_one(self, *, session_id: str) -> tuple[bool, Any | None]:
        state = self._sessions.get(session_id)
        if state is None:
            raise FlatMapContractError(f"flatmap_missing_continuation_session:{session_id}")

        if state.mode == "sync":
            iterator = state.iterator
            if not isinstance(iterator, Iterator):
                self._sessions.pop(session_id, None)
                raise FlatMapContractError(
                    f"flatmap_invalid_sync_iterator_session:{session_id}",
                )
            try:
                return True, next(iterator)
            except StopIteration:
                self._sessions.pop(session_id, None)
                return False, None
            except Exception:
                self._sessions.pop(session_id, None)
                raise

        iterator = state.iterator
        if not isinstance(iterator, AsyncIterator):
            self._sessions.pop(session_id, None)
            raise FlatMapContractError(
                f"flatmap_invalid_async_iterator_session:{session_id}",
            )
        awaitable = iterator.__anext__()
        try:
            value = self._run_awaitable_blocking(awaitable)
            return True, value
        except StopAsyncIteration:
            self._sessions.pop(session_id, None)
            return False, None
        except Exception:
            self._sessions.pop(session_id, None)
            raise

    def discard(self, *, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def _register_session(
        self,
        *,
        session_id: str,
        state: _FlatMapContinuationState,
    ) -> None:
        normalized_session_id = str(session_id or "").strip()
        if not normalized_session_id:
            raise FlatMapContractError("flatmap_session_id must be a non-empty string.")
        if normalized_session_id in self._sessions:
            raise FlatMapContractError(
                f"flatmap_duplicate_continuation_session:{normalized_session_id}",
            )
        self._sessions[normalized_session_id] = state

    def _run_awaitable_blocking(self, awaitable: Awaitable[Any]) -> Any:
        if self._run_coroutine is not None:
            return self._run_coroutine(_awaitable_to_coroutine(awaitable))
        try:
            import asyncio

            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        if running_loop is not None:
            raise FlatMapContractError(
                "flatmap_async_iterator_requires_runtime_coroutine_runner",
            )
        return asyncio.run(_awaitable_to_coroutine(awaitable))


async def _awaitable_to_coroutine(awaitable: Awaitable[Any]) -> Any:
    return await awaitable


__all__ = [
    "FlatMapContinuationRuntime",
]
