"""Cooperative request cancellation shared by SAGE runtimes and operators."""

from contextlib import contextmanager
from contextvars import ContextVar
from threading import Event
from time import monotonic


class RequestCancelledError(RuntimeError):
    pass


class RequestCancellation:
    def __init__(self, *, parent: "RequestCancellation | None" = None,
                 deadline_at: float | None = None):
        self._event = Event()
        self._parent = parent
        self._deadline_at = deadline_at

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return (
            self._event.is_set()
            or (self._deadline_at is not None and monotonic() >= self._deadline_at)
            or (self._parent is not None and self._parent.cancelled)
        )

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise RequestCancelledError("sage_request_cancelled")


_current: ContextVar[RequestCancellation | None] = ContextVar("sage_cancellation", default=None)


def child_request_cancellation(*, deadline_at: float | None = None) -> RequestCancellation:
    """Create a request token linked to the current scope, without upward cancellation."""
    return RequestCancellation(parent=_current.get(), deadline_at=deadline_at)


@contextmanager
def bind_request_cancellation(cancellation: RequestCancellation):
    token = _current.set(cancellation)
    try:
        yield cancellation
    finally:
        _current.reset(token)


def raise_if_request_cancelled() -> None:
    cancellation = _current.get()
    if cancellation is not None:
        cancellation.raise_if_cancelled()
