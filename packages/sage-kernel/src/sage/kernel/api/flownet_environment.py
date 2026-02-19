"""
FlownetEnvironment - Distributed execution environment backed by sageFlownet.

Layer: L3 (sage-kernel)
Dependencies: sage.platform (L2 adapter facade), sage.kernel.flow (L3 compiler)

Design principles
-----------------
* Zero direct ``sage.flownet.*`` imports here — all Flownet coupling is isolated
  inside ``sage.kernel.flow.pipeline_compiler.PipelineCompiler``.
* Identical user-facing API to ``LocalEnvironment``: only the class name changes.
* ``submit(autostop=False)`` delegates to the compiled actor graph:
    - ``autostop=True``  → blocking batch execution, returns when sink has
      processed every item emitted by the source.
    - ``autostop=False`` → non-blocking streaming execution, returns a
      ``_StreamingFlowHandle`` that the caller can ``stop()``.

Usage example
-------------
    from sage.kernel.api import FlownetEnvironment
    from my_functions import MySource, MyMap, MySink

    env = FlownetEnvironment("my_pipeline")
    env.from_source(MySource).map(MyMap).sink(MySink)
    env.submit(autostop=True)   # blocks until done
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sage.kernel.api.base_environment import BaseEnvironment

if TYPE_CHECKING:
    from sage.kernel.flow.pipeline_compiler import CompiledActorGraph, _StreamingFlowHandle


class FlownetEnvironment(BaseEnvironment):
    """Distributed stream-processing environment backed by the sageFlownet runtime.

    The environment compiles the declarative pipeline (the list of
    :class:`~sage.kernel.api.transformation.base_transformation.BaseTransformation`
    objects that ``from_source`` / ``map`` / ``filter`` / ``sink`` calls
    accumulate in ``self.pipeline``) into a Flownet Actor DAG at submission
    time via :class:`~sage.kernel.flow.pipeline_compiler.PipelineCompiler`.

    Parameters
    ----------
    name:
        Human-readable identifier for this environment instance.
    config:
        Optional key/value configuration dict.  The same keys honoured by
        ``BaseEnvironment`` apply (``engine_host``, ``engine_port``, …).
    scheduler:
        Scheduler instance or name string ("fifo", "load_aware").  Forwarded
        to ``BaseEnvironment.__init__``.
    placement_policy:
        Optional placement-policy string or object passed to the Flownet
        adapter so that actors can be assigned to specific cluster nodes.
        Currently informational; reserved for future runtime scheduling.
    enable_monitoring:
        Forward to ``BaseEnvironment`` monitoring toggle.
    """

    def __init__(
        self,
        name: str = "flownet_environment",
        config: dict | None = None,
        scheduler=None,
        placement_policy: str | None = None,
        enable_monitoring: bool = False,
    ) -> None:
        super().__init__(
            name,
            config,
            platform="flownet",
            scheduler=scheduler,
            enable_monitoring=enable_monitoring,
        )
        self._placement_policy: str | None = placement_policy
        # Set after a successful compile+submit cycle.
        self._compiled_graph: CompiledActorGraph | None = None
        # Non-None only when autostop=False (streaming mode).
        self._streaming_handle: _StreamingFlowHandle | None = None

    # ------------------------------------------------------------------
    # Core execution interface (satisfies BaseEnvironment.submit abstract)
    # ------------------------------------------------------------------

    def submit(self, autostop: bool = False) -> Any:
        """Compile the pipeline and start execution.

        Parameters
        ----------
        autostop:
            * ``True``  — block until all source items have been processed by
              the sink, then return ``None``.
            * ``False`` — start a background streaming execution immediately
              and return a :class:`~sage.kernel.flow.pipeline_compiler._StreamingFlowHandle`
              that exposes ``.stop()`` and ``.is_running``.

        Returns
        -------
        None or _StreamingFlowHandle
        """
        # Lazy import — keeps FlownetEnvironment free of sage.flownet coupling.
        from sage.kernel.flow.pipeline_compiler import PipelineCompiler
        from sage.platform.runtime.adapters.flownet_adapter import get_flownet_adapter

        adapter = get_flownet_adapter()
        compiler = PipelineCompiler()

        self.logger.info(
            f"[FlownetEnvironment:{self.name}] Compiling pipeline with "
            f"{len(self.pipeline)} stage(s)…"
        )
        self._compiled_graph = compiler.compile(self.pipeline, adapter)

        self.logger.info(
            f"[FlownetEnvironment:{self.name}] Submitting "
            f"({'batch/autostop' if autostop else 'streaming'})…"
        )
        result = self._compiled_graph.submit(autostop=autostop)

        if not autostop:
            # result is a _StreamingFlowHandle
            self._streaming_handle = result

        return result

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Stop an active streaming execution.

        Safe to call even if the pipeline is not running; a warning is logged
        instead of raising an exception.
        """
        if self._streaming_handle is not None:
            self.logger.info(f"[FlownetEnvironment:{self.name}] Stopping streaming pipeline…")
            self._streaming_handle.stop()
            self._streaming_handle = None
        else:
            self.logger.warning(
                f"[FlownetEnvironment:{self.name}] stop() called but no active "
                "streaming handle found — nothing to stop."
            )

    def close(self) -> None:
        """Stop any running pipeline and release resources."""
        self.stop()
        self._compiled_graph = None
        self.logger.info(f"[FlownetEnvironment:{self.name}] Closed.")

    def health_check(self) -> list[dict[str, Any]]:
        """Return node-health information from the Flownet adapter.

        Returns
        -------
        list[dict]
            Each dict has at minimum ``{"node_id": str, "status": str}``.
            Returns an empty list when the adapter is unavailable.
        """
        try:
            from sage.platform.runtime.adapters.flownet_adapter import get_flownet_adapter

            adapter = get_flownet_adapter()
            return adapter.list_nodes()
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(f"[FlownetEnvironment:{self.name}] health_check failed: {exc}")
            return []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """``True`` when a streaming pipeline is currently active."""
        if self._streaming_handle is None:
            return False
        return self._streaming_handle.is_running

    @property
    def placement_policy(self) -> str | None:
        """Placement policy hint passed to the Flownet scheduler."""
        return self._placement_policy

    @placement_policy.setter
    def placement_policy(self, value: str | None) -> None:
        self._placement_policy = value

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        state = "running" if self.is_running else "idle"
        return (
            f"FlownetEnvironment(name={self.name!r}, stages={len(self.pipeline)}, state={state!r})"
        )

    def __enter__(self) -> FlownetEnvironment:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
