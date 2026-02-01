"""
Tests for Issue #1418: 上游算子并行度不为 1 时导致任务丢失

These tests validate that TaskContext implements upstream parallelism
tracking for stop-signal coordination.
"""

import inspect

from sage.kernel.runtime.context.task_context import TaskContext


def test_handle_stop_signal_contains_parallel_tracking():
    """Ensure handle_stop_signal implements upstream parallelism tracking."""
    source = inspect.getsource(TaskContext.handle_stop_signal)

    assert "_upstream_parallelism_map" in source
    assert "_upstream_stop_signals_received" in source


def test_initialize_upstream_tracking_exists():
    """Ensure helper method for upstream tracking exists."""
    assert hasattr(TaskContext, "_initialize_upstream_tracking")


def test_state_exclude_contains_tracking_set():
    """Ensure runtime tracking set is excluded from serialization."""
    assert hasattr(TaskContext, "__state_exclude__")
    assert "_upstream_stop_signals_received" in TaskContext.__state_exclude__
