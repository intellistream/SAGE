"""
sage.kernel.flow.actor_wrappers - Flownet actor wrappers for SAGE pipeline stages.

Layer: L3 (sage-kernel)

These plain Python classes bridge SAGE's ``BaseFunction`` / ``BaseTransformation``
model to the sageFlownet actor execution model.

Each wrapper holds an instance of the user's function class and exposes a
stable method name that ``PipelineCompiler`` wires into the Flownet
``DataStream`` graph::

    MapActorWrapper.process(item)       → used by DataStream.map()
    FlatMapActorWrapper.process(item)   → used by DataStream.flatmap()
    FilterActorWrapper.accepts(item)    → used by DataStream.filter()
    SinkActorWrapper.consume(item)      → used by DataStream.write()
    SourceActorWrapper.run(trigger)     → used by source background thread
    ServiceActorWrapper.process(item)   → used by DataStream.map() (generic)

Architecture note (intellistream/SAGE#1442):
- These classes have **no sageFlownet imports**.
- They are instantiated by ``PipelineCompiler.compile()`` via the L2
  ``FlownetRuntimeAdapter.create()`` API.
- All Flownet-specific wiring lives in ``pipeline_compiler.py``.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "SourceActorWrapper",
    "MapActorWrapper",
    "FlatMapActorWrapper",
    "FilterActorWrapper",
    "SinkActorWrapper",
    "ServiceActorWrapper",
]


class SourceActorWrapper:
    """Wraps a SAGE ``SourceFunction`` for use as a Flownet actor.

    In *batch* mode the compiler collects source items directly (no Flownet
    actor is created); the wrapper exists for *streaming* mode where the
    source is driven from a background thread via a ``FlowPipe``.
    """

    def __init__(self, fn_class: type, *fn_args: Any, **fn_kwargs: Any) -> None:
        self._fn = fn_class(*fn_args, **fn_kwargs)

    def run(self, trigger: Any = None) -> Any:
        """Execute the source function once and return its output.

        Args:
            trigger: Ignored for source actors; present for API uniformity.

        Returns:
            The item produced by this invocation of the source function,
            or a ``StopSignal`` to indicate end-of-stream.
        """
        return self._fn.execute(trigger)


class MapActorWrapper:
    """Wraps a SAGE ``MapFunction`` for use as a Flownet actor."""

    def __init__(self, fn_class: type, *fn_args: Any, **fn_kwargs: Any) -> None:
        self._fn = fn_class(*fn_args, **fn_kwargs)

    def process(self, item: Any) -> Any:
        """Apply the map function to *item* and return the transformed result."""
        return self._fn.execute(item)


class FlatMapActorWrapper:
    """Wraps a SAGE ``FlatMapFunction`` for use as a Flownet actor.

    The Flownet ``flatmap`` operator calls this method and expects an iterable
    return value; each element of the iterable becomes a separate downstream
    stream element.

    Handles both SAGE ``FlatMapFunction`` output conventions:

    * **Pattern 1** – the function calls ``self.collect(item)`` on its
      injected ``Collector``; the collected list is returned.
    * **Pattern 2** – the function returns an iterable directly.
    """

    def __init__(self, fn_class: type, *fn_args: Any, **fn_kwargs: Any) -> None:
        self._fn = fn_class(*fn_args, **fn_kwargs)

    def process(self, item: Any) -> list[Any]:
        """Apply the flatmap function to *item* and return a list of results."""
        from sage.common.core.functions.flatmap_collector import Collector

        collector = Collector()
        if hasattr(self._fn, "insert_collector"):
            self._fn.insert_collector(collector)

        result = self._fn.execute(item)

        if result is not None:
            # Pattern 2: function returned an iterable
            return list(result)

        # Pattern 1: function used self.collect()
        return collector.get_collected_data()


class FilterActorWrapper:
    """Wraps a SAGE ``FilterFunction`` for use as a Flownet actor.

    The Flownet ``filter`` operator calls the method and passes the item
    downstream only when the return value is truthy.
    """

    def __init__(self, fn_class: type, *fn_args: Any, **fn_kwargs: Any) -> None:
        self._fn = fn_class(*fn_args, **fn_kwargs)

    def accepts(self, item: Any) -> bool:
        """Return ``True`` if *item* should pass through the filter."""
        return bool(self._fn.execute(item))


class SinkActorWrapper:
    """Wraps a SAGE ``SinkFunction`` for use as a Flownet actor.

    The Flownet ``DataStream.write()`` operator calls the method for each
    stream element as a terminal side-effect.
    """

    def __init__(self, fn_class: type, *fn_args: Any, **fn_kwargs: Any) -> None:
        self._fn = fn_class(*fn_args, **fn_kwargs)

    def consume(self, item: Any) -> None:
        """Forward *item* to the underlying sink function."""
        self._fn.execute(item)


class ServiceActorWrapper:
    """Generic actor wrapper for SAGE service-role transformations.

    Used when a transformation does not fall into the canonical
    source / map / filter / flatmap / sink categories.  Delegates to the
    function's ``execute()`` method, exposing a ``process()`` actor method
    for use in ``DataStream.map()``.
    """

    def __init__(self, fn_class: type, *fn_args: Any, **fn_kwargs: Any) -> None:
        self._fn = fn_class(*fn_args, **fn_kwargs)

    def process(self, item: Any) -> Any:
        """Delegate processing to the underlying function's ``execute()``."""
        return self._fn.execute(item)
