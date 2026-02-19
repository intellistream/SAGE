"""
Integration tests for FlownetEnvironment end-to-end execution.

Layer 3 of the 3-layer test taxonomy — intellistream/SAGE#1440.

When sageFlownet is not installed every test in
``TestFlownetEnvironmentLive`` is automatically skipped.  The structural
contract tests (``TestFlownetEnvironmentCompilerContract``) run regardless.
"""

from __future__ import annotations

import importlib
import queue
import time

import pytest

# ---------------------------------------------------------------------------
# Availability guard
# ---------------------------------------------------------------------------

_SAGEFLOWNET_AVAILABLE = importlib.util.find_spec("sage.flownet") is not None


def _skip_if_no_flownet(fn=None):
    marker = pytest.mark.skipif(
        not _SAGEFLOWNET_AVAILABLE,
        reason="sageFlownet (isage-flow) not installed — skipping live test",
    )
    return marker(fn) if fn is not None else marker


# ---------------------------------------------------------------------------
# Shared test functions
# ---------------------------------------------------------------------------


def _build_numbers_pipeline(env, numbers: list[int], out_q: queue.Queue):
    """
    Attach a simple source→map→sink pipeline to *env*.

    Source emits integers from *numbers*.
    Map multiplies each by 2.
    Sink puts results into *out_q*.
    """
    from sage.common.core.functions import MapFunction, SinkFunction, SourceFunction

    class NumberSource(SourceFunction):
        def __init__(self):
            self._items = iter(numbers)

        def execute(self, trigger=None):
            return next(self._items, None)

    class DoubleMap(MapFunction):
        def execute(self, item):
            return item * 2

    class QueueSink(SinkFunction):
        def __init__(self, q: queue.Queue):
            self._q = q

        def execute(self, item):
            self._q.put(item)

    env.from_source(NumberSource).map(DoubleMap).sink(QueueSink, out_q)


# ===========================================================================
# Suite 1: Compiler contract (no live runtime needed)
# ===========================================================================


class TestFlownetEnvironmentCompilerContract:
    """Structural checks that exercise PipelineCompiler via mocks."""

    def test_compiler_produces_compiled_actor_graph(self):
        from unittest.mock import MagicMock, patch

        from sage.kernel.api.flownet_environment import FlownetEnvironment
        from sage.kernel.flow.pipeline_compiler import CompiledActorGraph

        env = FlownetEnvironment()
        env.pipeline = [MagicMock()]  # At least one stage

        mock_compiled = MagicMock(spec=CompiledActorGraph)
        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = mock_compiled
        mock_adapter = MagicMock()

        with (
            patch(
                "sage.kernel.flow.pipeline_compiler.PipelineCompiler",
                return_value=mock_compiler,
            ),
            patch(
                "sage.platform.runtime.adapters.flownet_adapter.get_flownet_adapter",
                return_value=mock_adapter,
            ),
        ):
            env.submit(autostop=True)

        assert env._compiled_graph is mock_compiled

    def test_streaming_handle_stored_on_autostop_false(self):
        from unittest.mock import MagicMock, patch

        from sage.kernel.api.flownet_environment import FlownetEnvironment
        from sage.kernel.flow.pipeline_compiler import _StreamingFlowHandle

        env = FlownetEnvironment()
        env.pipeline = [MagicMock()]

        mock_handle = MagicMock(spec=_StreamingFlowHandle)
        mock_handle.is_running = True

        mock_compiled = MagicMock()
        mock_compiled.submit.return_value = mock_handle

        mock_compiler = MagicMock()
        mock_compiler.compile.return_value = mock_compiled

        mock_adapter = MagicMock()

        with (
            patch(
                "sage.kernel.flow.pipeline_compiler.PipelineCompiler",
                return_value=mock_compiler,
            ),
            patch(
                "sage.platform.runtime.adapters.flownet_adapter.get_flownet_adapter",
                return_value=mock_adapter,
            ),
        ):
            handle = env.submit(autostop=False)

        assert handle is mock_handle
        assert env._streaming_handle is mock_handle
        assert env.is_running is True

    def test_flow_module_exports_pipeline_compiler(self):
        from sage.kernel.flow import CompiledActorGraph, PipelineCompiler

        assert PipelineCompiler is not None
        assert CompiledActorGraph is not None


# ===========================================================================
# Suite 2: Actor-wrapper unit execution (no live Flownet runtime)
# ===========================================================================


class TestActorWrappers:
    """Run actor wrappers standalone to verify the bridging logic."""

    def test_map_actor_wrapper_doubles(self):
        from sage.common.core.functions import MapFunction
        from sage.kernel.flow.actor_wrappers import MapActorWrapper

        class Double(MapFunction):
            def execute(self, item):
                return item * 2

        wrapper = MapActorWrapper(Double)
        assert wrapper.process(5) == 10

    def test_filter_actor_wrapper_even(self):
        from sage.common.core.functions import FilterFunction
        from sage.kernel.flow.actor_wrappers import FilterActorWrapper

        class IsEven(FilterFunction):
            def execute(self, item):
                return item % 2 == 0

        wrapper = FilterActorWrapper(IsEven)
        assert wrapper.accepts(4) is True
        assert wrapper.accepts(3) is False

    def test_sink_actor_wrapper_captures(self):
        from sage.common.core.functions import SinkFunction
        from sage.kernel.flow.actor_wrappers import SinkActorWrapper

        collected = []

        class CaptureSink(SinkFunction):
            def execute(self, item):
                collected.append(item)

        wrapper = SinkActorWrapper(CaptureSink)
        wrapper.consume("hello")
        assert collected == ["hello"]

    def test_flatmap_actor_wrapper_expand(self):
        from sage.common.core.functions import FlatMapFunction
        from sage.kernel.flow.actor_wrappers import FlatMapActorWrapper

        class Expand(FlatMapFunction):
            def execute(self, item):
                return [item, item * 2]

        wrapper = FlatMapActorWrapper(Expand)
        result = wrapper.process(3)
        assert result == [3, 6]

    def test_source_actor_wrapper_emits(self):
        from sage.common.core.functions import SourceFunction
        from sage.kernel.flow.actor_wrappers import SourceActorWrapper

        class Counter(SourceFunction):
            def __init__(self):
                self._n = 0

            def execute(self, trigger=None):
                self._n += 1
                return self._n if self._n <= 3 else None

        wrapper = SourceActorWrapper(Counter)
        assert wrapper.run() == 1
        assert wrapper.run() == 2
        assert wrapper.run() == 3
        assert wrapper.run() is None


# ===========================================================================
# Suite 3: Live Flownet end-to-end (skipped when sageFlownet not installed)
# ===========================================================================


@_skip_if_no_flownet
class TestFlownetEnvironmentLive:
    """
    End-to-end execution through the real sageFlownet runtime.

    Requirements
    ------------
    * ``isage-flow`` (sageFlownet) must be installed.
    * Tests run in the CI ``flownet`` job (Layer 3), not in the fast-unit job.
    """

    def test_batch_pipeline_source_map_sink(self):
        """from_source → map → sink executes with autostop=True."""
        import queue

        from sage.kernel.api import FlownetEnvironment

        out = queue.Queue()
        numbers = [1, 2, 3, 4, 5]

        env = FlownetEnvironment(name="e2e_batch")
        _build_numbers_pipeline(env, numbers, out)

        env.submit(autostop=True)

        results = []
        while not out.empty():
            results.append(out.get_nowait())

        assert sorted(results) == [n * 2 for n in numbers], (
            f"Expected {[n * 2 for n in numbers]} (sorted), got {sorted(results)}"
        )

    def test_streaming_pipeline_can_be_stopped(self):
        """from_source → map → sink with autostop=False returns a stoppable handle."""
        import queue

        from sage.kernel.api import FlownetEnvironment

        out = queue.Queue()
        numbers = list(range(100))

        env = FlownetEnvironment(name="e2e_stream")
        _build_numbers_pipeline(env, numbers, out)

        _handle = env.submit(autostop=False)
        assert env.is_running is True

        # Give the streaming pipeline some time to process a few items.
        time.sleep(0.5)
        env.stop()

        assert env.is_running is False

    def test_context_manager_closes_on_exit(self):
        """Context manager stops the pipeline when the block exits."""
        import queue

        from sage.kernel.api import FlownetEnvironment

        out = queue.Queue()
        numbers = [10, 20]

        with FlownetEnvironment(name="e2e_ctx") as env:
            _build_numbers_pipeline(env, numbers, out)
            env.submit(autostop=True)

        # No assertion needed — if this completes without exception the test passes.
        assert env._compiled_graph is None  # close() resets this
