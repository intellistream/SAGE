"""
sage.kernel.flow.pipeline_compiler - Pipeline DAG → Actor DAG compiler.

Layer: L3 (sage-kernel)
Dependencies: sage.platform (L2, via ``get_flownet_adapter``), sage.common (L1).

This module translates a SAGE declarative pipeline (a list of
``BaseTransformation`` nodes built via ``env.from_source().map().sink()``)
into a sageFlownet Actor DAG for distributed execution.

Terminology
-----------
Pipeline DAG
    The linear (or branching) list of ``BaseTransformation`` objects stored in
    ``BaseEnvironment.pipeline``.

Actor DAG
    A set of sageFlownet actors plus a Flownet ``@flow`` function that wires
    them via ``DataStream`` edges.

Compilation
-----------
``PipelineCompiler.compile(pipeline, adapter)`` returns a
``CompiledActorGraph``.  The caller then invokes
``CompiledActorGraph.submit(autostop=…)`` to start execution.

Two execution modes:

Batch mode (``autostop=True``)
    1. The source function is drained synchronously to collect all items.
    2. A *batch flow* (which starts with a ``flatmap(identity)`` that unpacks
       the collected list) is submitted via ``flow_def.submit(items).wait()``.
    3. ``submit()`` blocks until the sink has consumed every item.

Streaming mode (``autostop=False``)
    1. A *streaming flow* processes one item per ``pipe.write()`` call.
    2. ``pipe = flow_def.open()`` opens a ``FlowPipe``.
    3. The source function is run in a background ``threading.Thread`` that
       calls ``pipe.write(item)`` for each produced item.
    4. ``submit()`` returns a ``_StreamingFlowHandle`` immediately.

Boundary rule (intellistream/SAGE#1442 DoD)
    All ``sage.flownet.*`` imports are **lazy** and **confined to this
    module**.  ``FlownetEnvironment`` and every other caller accesses Flownet
    only through the L2 ``FlownetRuntimeAdapter`` or through the high-level
    ``CompiledActorGraph`` interface returned by this compiler.

References
----------
- Actor DAG specification: intellistream/SAGE#1442
- L2 adapter:              sage.platform.runtime.adapters.flownet_adapter
- Migration boundary:      intellistream/SAGE#1430
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sage.kernel.api.transformation.base_transformation import BaseTransformation
    from sage.platform.runtime.protocol import ActorHandleProtocol, RuntimeBackendProtocol

logger = logging.getLogger(__name__)

__all__ = [
    "PipelineCompiler",
    "CompiledActorGraph",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TRANSFORMATION_MAP: dict[str, tuple[str, str]] | None = None
"""Lazy cache: ``{transformation_class_name: (wrapper_class_name, op_type)}``."""


def _require_flownet(where: str) -> None:
    """Raise a clear error when sageFlownet is not installed."""
    try:
        import sage.flownet  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            f"PipelineCompiler.{where}() requires sageFlownet to be installed.\n"
            "Install it with:  pip install isage-flow\n"
            f"Original error: {exc}"
        ) from exc


# Stable op-type constants used inside the compiled flow closure.
_OP_MAP: str = "map"
_OP_FLATMAP: str = "flatmap"
_OP_FILTER: str = "filter"
_OP_SINK: str = "sink"


def _classify(t: BaseTransformation) -> tuple[type, str, str]:
    """Return ``(WrapperClass, op_type_str, method_name)`` for *t*.

    Imports are deferred so this file can be imported without Flownet.
    """
    from sage.kernel.api.transformation.filter_transformation import FilterTransformation
    from sage.kernel.api.transformation.flatmap_transformation import FlatMapTransformation
    from sage.kernel.api.transformation.map_transformation import MapTransformation
    from sage.kernel.api.transformation.sink_transformation import SinkTransformation
    from sage.kernel.api.transformation.source_transformation import SourceTransformation
    from sage.kernel.flow.actor_wrappers import (
        FilterActorWrapper,
        FlatMapActorWrapper,
        MapActorWrapper,
        ServiceActorWrapper,
        SinkActorWrapper,
        SourceActorWrapper,
    )

    if isinstance(t, SourceTransformation):
        return (SourceActorWrapper, "source", "run")
    if isinstance(t, MapTransformation):
        return (MapActorWrapper, _OP_MAP, "process")
    if isinstance(t, FlatMapTransformation):
        return (FlatMapActorWrapper, _OP_FLATMAP, "process")
    if isinstance(t, FilterTransformation):
        return (FilterActorWrapper, _OP_FILTER, "accepts")
    if isinstance(t, SinkTransformation):
        return (SinkActorWrapper, _OP_SINK, "consume")
    # Fall back to generic service wrapper
    return (ServiceActorWrapper, _OP_MAP, "process")


# ---------------------------------------------------------------------------
# Streaming handle
# ---------------------------------------------------------------------------


class _StreamingFlowHandle:
    """Returned by ``CompiledActorGraph.submit(autostop=False)``.

    Callers can use ``stop()`` to request graceful shutdown of the source
    background thread and the underlying Flownet flow.
    """

    def __init__(
        self,
        flow_pipe: Any,
        source_thread: threading.Thread | None,
        *,
        stop_event: threading.Event,
    ) -> None:
        self._pipe = flow_pipe
        self._thread = source_thread
        self._stop_event = stop_event

    def stop(self, timeout: float = 30.0) -> None:
        """Signal the source thread to stop and wait for it to join."""
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        # Best-effort close of the pipe
        close_fn = getattr(self._pipe, "close", None) or getattr(self._pipe, "drain", None)
        if callable(close_fn):
            try:
                close_fn()
            except Exception:  # noqa: BLE001
                pass

    @property
    def is_running(self) -> bool:
        """``True`` while the source thread is still alive."""
        return self._thread is not None and self._thread.is_alive()


# ---------------------------------------------------------------------------
# CompiledActorGraph
# ---------------------------------------------------------------------------


@dataclass
class CompiledActorGraph:
    """The compiled result of ``PipelineCompiler.compile()``.

    Holds all Flownet-specific objects (actor handles and flow definitions)
    produced during compilation.  The only public entry point is ``submit()``.

    Attributes:
        streaming_flow:     Flownet ``FlowDef`` for one-item-per-call mode.
        batch_flow:         Flownet ``FlowDef`` that starts with a
                            ``flatmap(identity)`` to unpack a list of items.
        source_transformation:  The ``SourceTransformation`` node, or ``None``
                                if the pipeline has no source.
        actor_handles:      Protocol-wrapped Flownet actor handles for the
                            non-source stages (in pipeline order).
        adapter:            The ``RuntimeBackendProtocol`` adapter used to
                            create the actors and submit flows.
    """

    streaming_flow: Any
    batch_flow: Any | None
    source_transformation: Any | None
    actor_handles: list[Any] = field(default_factory=list)
    adapter: Any = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, autostop: bool = False) -> Any:
        """Execute the compiled pipeline.

        Args:
            autostop: When ``True``, collect all source items, submit the
                      batch flow, and **block** until every item has been
                      processed by the sink.  When ``False``, open a
                      streaming ``FlowPipe``, start the source in a
                      background thread, and return a
                      ``_StreamingFlowHandle`` immediately.

        Returns:
            * ``None`` when ``autostop=True`` (completes synchronously).
            * A ``_StreamingFlowHandle`` when ``autostop=False``.
        """
        if autostop:
            return self._submit_batch()
        return self._submit_streaming()

    # ------------------------------------------------------------------
    # Batch execution
    # ------------------------------------------------------------------

    def _collect_source_items(self) -> list[Any]:
        """Drain the source function to completion and return all items."""
        t = self.source_transformation
        if t is None:
            return []

        from sage.kernel.runtime.communication.packet import StopSignal

        fn = t.function_class(*t.function_args, **t.function_kwargs)
        items: list[Any] = []
        while True:
            item = fn.execute()
            if isinstance(item, StopSignal) or item is None:
                break
            items.append(item)

        logger.debug(
            "Source '%s' drained: %d items collected.",
            t.function_class.__name__,
            len(items),
        )
        return items

    def _submit_batch(self) -> None:
        """Collect source items and submit to batch flow; block until done."""
        if self.batch_flow is None:
            raise RuntimeError(
                "CompiledActorGraph.submit(autostop=True) requires a batch_flow, "
                "but none was compiled.  Ensure the pipeline has a SourceTransformation."
            )

        items = self._collect_source_items()
        if not items:
            logger.info("Source produced no items; batch pipeline skipped.")
            return None

        logger.info("Submitting batch of %d items to Flownet pipeline.", len(items))
        handle = self.batch_flow.submit(items)
        # wait() returns True when all items have been processed
        success = handle.wait(timeout=3600.0)  # 1-hour safety timeout
        if not success:
            logger.warning("Batch pipeline timed out waiting for all items to be processed.")
        return None

    # ------------------------------------------------------------------
    # Streaming execution
    # ------------------------------------------------------------------

    def _submit_streaming(self) -> _StreamingFlowHandle:
        """Open a FlowPipe and drive the source from a background thread."""
        pipe = self.streaming_flow.open()
        stop_event = threading.Event()
        source_thread: threading.Thread | None = None

        if self.source_transformation is not None:
            source_thread = threading.Thread(
                target=self._run_source_thread,
                args=(pipe, stop_event),
                daemon=True,
                name=f"sage-source-{self.source_transformation.basename}",
            )
            source_thread.start()

        return _StreamingFlowHandle(pipe, source_thread, stop_event=stop_event)

    def _run_source_thread(
        self,
        pipe: Any,
        stop_event: threading.Event,
    ) -> None:
        """Background thread: poll source function and write to *pipe*."""
        from sage.kernel.runtime.communication.packet import StopSignal

        t = self.source_transformation
        fn = t.function_class(*t.function_args, **t.function_kwargs)

        try:
            while not stop_event.is_set():
                item = fn.execute()
                if isinstance(item, StopSignal) or item is None:
                    break
                pipe.write(item)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Source function '%s' raised an exception in streaming mode.",
                t.function_class.__name__,
            )
        finally:
            logger.debug("Source thread for '%s' exiting.", t.function_class.__name__)


# ---------------------------------------------------------------------------
# PipelineCompiler
# ---------------------------------------------------------------------------


class PipelineCompiler:
    """Compiles a SAGE ``BaseTransformation`` list into a ``CompiledActorGraph``.

    Usage::

        from sage.platform.runtime.adapters.flownet_adapter import get_flownet_adapter
        from sage.kernel.flow.pipeline_compiler import PipelineCompiler

        adapter = get_flownet_adapter()
        graph = PipelineCompiler().compile(env.pipeline, adapter)
        graph.submit(autostop=True)

    sageFlownet requirement
    -----------------------
    This method imports ``sage.flownet.*`` lazily.  If sageFlownet is not
    installed, a clear ``ImportError`` is raised at call-time.
    """

    def compile(
        self,
        pipeline: list[BaseTransformation],
        adapter: RuntimeBackendProtocol,
    ) -> CompiledActorGraph:
        """Compile *pipeline* into a ``CompiledActorGraph`` using *adapter*.

        Args:
            pipeline: The ordered list of ``BaseTransformation`` objects built
                      by the ``BaseEnvironment`` DSL.
            adapter:  A started ``RuntimeBackendProtocol`` implementation
                      (typically ``FlownetRuntimeAdapter``) used to create
                      remote actors.

        Returns:
            A ``CompiledActorGraph`` ready to be submitted.

        Raises:
            ImportError:  If sageFlownet is not installed.
            ValueError:   If the pipeline is empty or otherwise malformed.
        """
        _require_flownet("compile")

        if not pipeline:
            raise ValueError(
                "PipelineCompiler.compile() received an empty pipeline.  "
                "Build a pipeline with env.from_source(...).map(...).sink(...) "
                "before calling env.submit()."
            )

        # ------------------------------------------------------------------
        # Step 1: Classify & partition transformations
        # ------------------------------------------------------------------
        source_trans: Any | None = None
        proc_transformations: list[Any] = []

        for t in pipeline:
            wrapper_cls, op_type, _ = _classify(t)
            if op_type == "source":
                if source_trans is not None:
                    raise ValueError(
                        "PipelineCompiler found more than one SourceTransformation in the "
                        "pipeline.  Only a single source is supported per compilation unit."
                    )
                source_trans = t
            else:
                proc_transformations.append(t)

        # ------------------------------------------------------------------
        # Step 2: Create Flownet actors for non-source stages
        # ------------------------------------------------------------------
        actor_handles: list[ActorHandleProtocol] = []
        # stage_info: list of (op_type_str, raw_actor_ref, method_name)
        stage_info: list[tuple[str, Any, str]] = []

        for t in proc_transformations:
            wrapper_cls, op_type, method_name = _classify(t)
            handle = adapter.create(
                wrapper_cls,
                t.function_class,
                *t.function_args,
                **t.function_kwargs,
            )
            actor_handles.append(handle)
            raw_ref = handle._raw_ref  # type: ignore[attr-defined]  # Flownet ActorRef
            stage_info.append((op_type, raw_ref, method_name))

            logger.debug(
                "Created actor %s → %s.%s()",
                t.basename,
                wrapper_cls.__name__,
                method_name,
            )

        # ------------------------------------------------------------------
        # Step 3: Build Flownet flow functions (lazy sage.flownet imports)
        # ------------------------------------------------------------------
        streaming_flow = self._build_streaming_flow(stage_info)
        batch_flow = self._build_batch_flow(stage_info) if source_trans is not None else None

        return CompiledActorGraph(
            streaming_flow=streaming_flow,
            batch_flow=batch_flow,
            source_transformation=source_trans,
            actor_handles=actor_handles,
            adapter=adapter,
        )

    # ------------------------------------------------------------------
    # Flow-building helpers (sage.flownet imports are confined here)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_streaming_flow(
        stage_info: list[tuple[str, Any, str]],
    ) -> Any:
        """Build a Flownet flow that processes **one item per invocation**.

        The generated ``@flow`` function chains the actor stages in order.
        Each ``pipe.write(item)`` call delivers a single SAGE data element.
        """
        import sage.flownet  # lazy – confined to PipelineCompiler (Issue #1442 DoD)

        # Capture stage_info in the closure
        _stages = stage_info

        def _streaming_pipeline(init_stream):  # type: ignore[return]
            stream = init_stream
            for op_type, raw_ref, method_name in _stages:
                method_ref = getattr(raw_ref, method_name)
                if op_type == _OP_SINK:
                    stream.write(method_ref)
                    return None  # terminal sink – no return stream
                elif op_type == _OP_FLATMAP:
                    stream = stream.flatmap(method_ref)
                elif op_type == _OP_FILTER:
                    stream = stream.filter(method_ref)
                else:  # map or generic
                    stream = stream.map(method_ref)
            return stream  # no explicit sink – return the tail stream

        return sage.flownet.flow(_streaming_pipeline)

    @staticmethod
    def _build_batch_flow(
        stage_info: list[tuple[str, Any, str]],
    ) -> Any:
        """Build a Flownet flow that processes **a list of items per invocation**.

        The first operation is a ``flatmap(identity_op)`` that unpacks the
        list into individual stream elements, followed by the same chain as
        the streaming flow.  This enables efficient batch submission via::

            flow_def.submit(all_items).wait(timeout)
        """
        import sage.flownet  # lazy – confined to PipelineCompiler (Issue #1442 DoD)
        from sage.flownet.api.stateless_op import stateless_op  # lazy

        # stateless identity function: receives the full list, returns it
        # so flatmap expands it into individual stream elements.
        _identity_op = stateless_op(lambda items: items, name="sage_batch_unpack")
        _stages = stage_info

        def _batch_pipeline(init_stream):  # type: ignore[return]
            # Unpack the submitted list into individual stream elements
            stream = init_stream.flatmap(_identity_op)

            for op_type, raw_ref, method_name in _stages:
                method_ref = getattr(raw_ref, method_name)
                if op_type == _OP_SINK:
                    stream.write(method_ref)
                    return None  # terminal sink
                elif op_type == _OP_FLATMAP:
                    stream = stream.flatmap(method_ref)
                elif op_type == _OP_FILTER:
                    stream = stream.filter(method_ref)
                else:
                    stream = stream.map(method_ref)
            return stream

        return sage.flownet.flow(_batch_pipeline)
