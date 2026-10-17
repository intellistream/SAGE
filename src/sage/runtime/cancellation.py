"""Cooperative request cancellation shared by SAGE runtimes and operators."""

from contextlib import contextmanager
from contextvars import ContextVar
from threading import Event


class RequestCancelledError(RuntimeError):
    pass


class RequestCancellation:
    def __init__(self):
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise RequestCancelledError("sage_request_cancelled")


_current: ContextVar[RequestCancellation | None] = ContextVar("sage_cancellation", default=None)


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
