from contextvars import ContextVar
from threading import Event

import pytest

from sage.runtime.read_tool_deadline import ReadToolDeadlineExceeded, ReadToolExecutor


def test_blocked_read_times_out_but_retains_capacity_until_cleanup_and_discards_late_result():
    executor = ReadToolExecutor(capacity=1)
    started, release = Event(), Event()

    def blocked():
        started.set()
        release.wait(2)
        return "late evidence must not be delivered"

    try:
        with pytest.raises(ReadToolDeadlineExceeded):
            executor.call(blocked, timeout=0.02)
        assert started.is_set()
        with pytest.raises(RuntimeError, match="capacity_exhausted"):
            executor.call(lambda: "not admitted", timeout=1)
    finally:
        release.set()
        executor.close()


def test_request_context_is_propagated_without_leaking_between_calls():
    executor = ReadToolExecutor(capacity=1)
    scope = ContextVar("read-test-scope", default="unassigned")
    try:
        token = scope.set("request-one")
        assert executor.call(scope.get, timeout=1) == "request-one"
        scope.reset(token)
        assert executor.call(scope.get, timeout=1) == "unassigned"
    finally:
        executor.close()
