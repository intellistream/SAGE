"""
sage.platform.runtime.adapters.flownet_adapter - Flownet Runtime Adapter

Layer: L2 (sage-platform)

This module provides ``FlownetRuntimeAdapter`` – the concrete implementation of
``RuntimeBackendProtocol`` that delegates to sageFlownet (``sage.flownet``).

Architecture
------------
- All imports of ``sage.flownet.*`` are **lazy** (inside methods / inner
  functions).  This guarantees that importing *this* module does not fail
  when sageFlownet is not installed.
- The adapter wraps Flownet's concrete objects in thin protocol-conforming
  wrappers (``_FlownetActorHandle``, ``_FlownetMethodRef``,
  ``_FlownetMethodCallFuture``, ``_FlownetFlowRunHandle``,
  ``_FlownetNodeInfo``) so that sage-kernel code only operates against the
  L2 protocol types.

Usage
-----
::

    from sage.platform.runtime.adapters.flownet_adapter import (
        FlownetRuntimeAdapter,
        get_flownet_adapter,   # singleton accessor
    )

    backend = get_flownet_adapter()   # returns cached singleton
    actor = backend.create(MyActorClass)

    # Synchronous call
    result = actor.get_method("process").call(payload)

    # Asynchronous call
    future = actor.get_method("process").async_call(payload)
    result = future.result(timeout=30.0)

Per the migration boundary (intellistream/SAGE#1430):
- SAGE calls only ``RuntimeBackendProtocol`` methods.
- This adapter (not sage-kernel internals) owns the Flownet glue.
- If sageFlownet is replaced, only this adapter needs to change.

References
----------
- Protocol definition:       ``sage.platform.runtime.protocol``
- Migration boundary:         intellistream/SAGE#1430
- Runtime protocol (Issue 4): intellistream/SAGE#1433
- Actor ref interfaces (Issue 7): intellistream/SAGE#1436
"""

from __future__ import annotations

import concurrent.futures
from threading import Lock
from typing import Any

from sage.platform.runtime.protocol import (
    ActorHandleProtocol,
    FlowRunHandleProtocol,
    MethodCallFuture,
    MethodRefProtocol,
    NodeInfoProtocol,
    RuntimeBackendProtocol,
)

__all__ = [
    "FlownetRuntimeAdapter",
    "get_flownet_adapter",
]


# ---------------------------------------------------------------------------
# Internal helper: ensure sageFlownet is present
# ---------------------------------------------------------------------------


def _require_flownet(operation: str) -> None:
    """Raise a clear ImportError when sageFlownet is not installed."""
    try:
        import sage.flownet  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            f"FlownetRuntimeAdapter.{operation}() requires the sageFlownet "
            "runtime to be installed.\n"
            "Install it with:  pip install isage-flow\n"
            f"Original error: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Thread pool for async_call dispatch
# ---------------------------------------------------------------------------

# A module-level executor is used to back `async_call()`.  It is created
# lazily on first use and shared across all _FlownetMethodRef instances so
# that we don't spawn an unbounded number of threads.
_async_executor: concurrent.futures.ThreadPoolExecutor | None = None
_async_executor_lock: Lock = Lock()


def _get_async_executor() -> concurrent.futures.ThreadPoolExecutor:
    global _async_executor
    with _async_executor_lock:
        if _async_executor is None:
            _async_executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=32,
                thread_name_prefix="sage_actor_async",
            )
        return _async_executor


# ---------------------------------------------------------------------------
# MethodCallFuture implementation
# ---------------------------------------------------------------------------


class _FlownetMethodCallFuture(MethodCallFuture):
    """Backs ``MethodCallFuture`` with a ``concurrent.futures.Future``.

    Created by ``_FlownetMethodRef.async_call()`` and returned to the caller.
    The underlying ``concurrent.futures.Future`` runs the synchronous
    ``ActorMethodRef.__call__`` on the shared thread-pool executor.
    """

    __slots__ = ("_fut",)

    def __init__(self, fut: concurrent.futures.Future[Any]) -> None:  # type: ignore[type-arg]
        self._fut = fut

    def result(self, timeout: float | None = None) -> Any:
        """Block until the call completes and return its result.

        Args:
            timeout: Maximum seconds to wait.  ``None`` means wait forever.

        Returns:
            The return value of the remote actor method.

        Raises:
            TimeoutError:  If ``timeout`` is exceeded before completion.
            RuntimeError:  If the call failed or was cancelled.
        """
        try:
            return self._fut.result(timeout=timeout)
        except concurrent.futures.TimeoutError as exc:
            raise TimeoutError(f"Actor method call did not complete within {timeout}s.") from exc
        except concurrent.futures.CancelledError as exc:
            raise RuntimeError("Actor method call was cancelled.") from exc

    def cancel(self) -> bool:
        """Request cancellation of the pending async call.

        Returns ``True`` if the future was not yet executing and cancellation
        succeeded; ``False`` if it was already running or completed.
        """
        return self._fut.cancel()

    @property
    def done(self) -> bool:
        """``True`` when the call has finished or been cancelled."""
        return self._fut.done()


# ---------------------------------------------------------------------------
# Thin protocol wrappers
# ---------------------------------------------------------------------------


class _FlownetMethodRef(MethodRefProtocol):
    """Wraps a Flownet ``ActorMethodRef`` as a ``MethodRefProtocol``.

    Implements all three invocation modes:
    - ``call()``        – delegates directly to ``ActorMethodRef.__call__``.
    - ``async_call()``  – submits ``call()`` to the shared thread-pool
                          executor and returns a ``_FlownetMethodCallFuture``.
    - ``cancel()``      – best-effort; returns ``False`` because Flownet's
                          current actor call model (request/response via
                          queues) does not expose per-call cancellation at the
                          Python API level.  Override when Flownet adds native
                          cancel support.
    """

    __slots__ = ("_ref",)

    def __init__(self, method_ref: Any) -> None:
        self._ref = method_ref

    def call(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to Flownet ``ActorMethodRef.__call__`` (blocking)."""
        return self._ref(*args, **kwargs)

    def async_call(self, *args: Any, **kwargs: Any) -> MethodCallFuture:
        """Dispatch the call on the shared thread-pool executor (non-blocking).

        Returns a ``_FlownetMethodCallFuture`` that wraps the submitted
        ``concurrent.futures.Future``.
        """
        executor = _get_async_executor()
        fut = executor.submit(self._ref, *args, **kwargs)
        return _FlownetMethodCallFuture(fut)

    def cancel(self) -> bool:
        """Best-effort cancellation.

        Flownet's current queue-based actor dispatch does not expose a
        per-call cancel primitive, so this always returns ``False``.  Callers
        wishing to cancel pending work should use
        ``MethodCallFuture.cancel()`` instead (which works for calls that are
        still queued in the thread-pool before execution begins).
        """
        return False


class _FlownetActorHandle(ActorHandleProtocol):
    """Wraps a Flownet ``ActorRef`` as an ``ActorHandleProtocol``.

    Supports attribute-style method access (``handle.method_name``) as a
    convenience shorthand for ``handle.get_method("method_name")``.  This
    maintains backward compatibility with code written against the raw
    Flownet ``ActorRef`` API (``actor.process.call(payload)``).

    Actor-level cancellation (``cancel()``) is a best-effort operation.
    Flownet's current actor model does not expose a hard-stop API for
    individual actors, so ``cancel()`` always returns ``False`` unless
    Flownet adds native support.
    """

    # Use a class-level set to avoid recursion when __getattr__ is called
    # for slots/dunder attributes.
    _RESERVED_ATTRS: frozenset[str] = frozenset({"_ref", "get_method", "_raw_ref", "cancel"})

    def __init__(self, actor_ref: Any) -> None:
        object.__setattr__(self, "_ref", actor_ref)

    def get_method(self, name: str) -> MethodRefProtocol:
        """Return ``_FlownetMethodRef`` for the named actor method.

        Delegates to ``ActorRef.__getattr__`` which produces an
        ``ActorMethodRef``.
        """
        method_ref = getattr(self._ref, name)
        return _FlownetMethodRef(method_ref)

    def cancel(self) -> bool:
        """Best-effort actor-level cancellation.

        Flownet's current runtime does not expose a per-actor terminate
        primitive at the Python API level, so this always returns ``False``.
        When Flownet adds native actor cancel support, update this method.

        Returns:
            ``False`` (not supported by the current Flownet backend).
        """
        return False

    def __getattr__(self, name: str) -> MethodRefProtocol:
        """Attribute-style shorthand: ``handle.method_name`` → ``get_method(name)``.

        This allows existing code written against raw ``ActorRef`` objects to
        continue working without modification::

            actor = create(MyClass)
            result = actor.process.call(payload)   # backwards-compatible
            result = actor.get_method("process").call(payload)  # explicit form
        """
        if name.startswith("_"):
            raise AttributeError(name)
        return self.get_method(name)

    @property
    def _raw_ref(self) -> Any:
        """Expose the raw Flownet ActorRef for interop with legacy code."""
        return self._ref


class _FlownetFlowRunHandle(FlowRunHandleProtocol):
    """Wraps a Flownet flow run handle as a ``FlowRunHandleProtocol``.

    The Flownet API currently returns a ``FlowPipe``-like object or a
    ``BoundFlow`` / ``FlowDef`` that exposes ``.call()``.  We wrap whichever
    object ``submit_flow`` returns.
    """

    __slots__ = ("_handle",)

    def __init__(self, handle: Any) -> None:
        self._handle = handle

    def call(self, *args: Any, **kwargs: Any) -> Any:
        """Forward call to the Flownet flow run handle."""
        if not hasattr(self._handle, "call"):
            raise TypeError(
                f"Flownet flow run handle {type(self._handle)!r} does not "
                "expose a .call() method.  Expected a FlowPipe or BoundFlow."
            )
        return self._handle.call(*args, **kwargs)

    def cancel(self) -> None:
        """Cancel the in-flight flow run if supported by Flownet."""
        cancel_fn = getattr(self._handle, "cancel", None)
        if cancel_fn is None:
            raise RuntimeError(
                "The Flownet flow run handle does not support cancel().  "
                "Upgrade sageFlownet or use a FlowPipe-based run handle."
            )
        cancel_fn()

    @property
    def _raw_handle(self) -> Any:
        """Expose the raw Flownet handle for interop with legacy code."""
        return self._handle


class _FlownetNodeInfo(NodeInfoProtocol):
    """Wraps a Flownet ``ClusterNode`` as a ``NodeInfoProtocol``."""

    __slots__ = ("_node",)

    def __init__(self, cluster_node: Any) -> None:
        self._node = cluster_node

    @property
    def node_id(self) -> str:
        return str(getattr(self._node, "node_id", "unknown"))

    @property
    def address(self) -> str:
        return str(getattr(self._node, "address", "0.0.0.0"))

    @property
    def is_schedulable(self) -> bool:
        # ClusterNode may expose a schedulable flag or resource_summary key.
        rs: dict[str, Any] = getattr(self._node, "resource_summary", {}) or {}
        schedulable = rs.get("schedulable", None)
        if schedulable is not None:
            return bool(schedulable)
        # Fallback: node is schedulable if it has any available CPU.
        try:
            return float(rs.get("cpu_available", 0)) > 0
        except (TypeError, ValueError):
            return True

    @property
    def resource_summary(self) -> dict[str, Any]:
        raw = getattr(self._node, "resource_summary", None)
        return dict(raw) if isinstance(raw, dict) else {}


# ---------------------------------------------------------------------------
# FlownetRuntimeAdapter - main adapter class
# ---------------------------------------------------------------------------


class FlownetRuntimeAdapter(RuntimeBackendProtocol):
    """Adapter that satisfies ``RuntimeBackendProtocol`` using sageFlownet.

    All Flownet-internal imports are **lazy** (deferred to first use) so that
    this class can be imported even when sageFlownet is not installed.  An
    ``ImportError`` is raised at call-time with a user-friendly message.

    Thread Safety
    -------------
    ``start()`` is idempotent and protected by a lock; it is safe to call
    from multiple threads.  Operations after ``stop()`` raise ``RuntimeError``.
    """

    def __init__(self) -> None:
        self._started: bool = False
        self._lock: Lock = Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, config: Any | None = None) -> None:
        """Boot or attach to the sageFlownet runtime (idempotent).

        If already started, this is a no-op.  If ``config`` is provided,
        it is passed to ``sage.flownet.runtime.runtime.get_runtime()``
        as configuration.

        Args:
            config: A ``FlownetConfig`` or ``RuntimeConfigInput`` dict, or
                    ``None`` to use environment/default settings.
        """
        with self._lock:
            if self._started:
                return
            _require_flownet("start")
            from sage.flownet.runtime.runtime import (  # lazy  # noqa: F401
                get_runtime,
            )

            if config is not None:
                get_runtime(config)
            else:
                get_runtime()

            # Register Flownet's exception handler push/pop hooks with the
            # SAGE L3 flow_exception_handler API so that the context manager
            # in sage.kernel.flow can manipulate the Flownet flowtask stack.
            # (intellistream/SAGE#1434 -- Exception API migration)
            from sage.flownet.api.flow_exception_handlers import (  # lazy
                register_flownet_exception_hooks,
            )

            register_flownet_exception_hooks()

            self._started = True

    def stop(self) -> None:
        """Gracefully shut down the sageFlownet runtime.

        After ``stop()`` this adapter can be re-started with ``start()``.
        """
        _require_flownet("stop")
        from sage.flownet.runtime.runtime import get_runtime  # lazy

        try:
            runtime = get_runtime()
            runtime.stop()
        finally:
            with self._lock:
                self._started = False

    def _assert_started(self, operation: str) -> None:
        if not self._started:
            raise RuntimeError(
                f"FlownetRuntimeAdapter.{operation}() called before start(). "
                "Call start() first or use get_flownet_adapter() which starts "
                "automatically."
            )

    # ------------------------------------------------------------------
    # Actor management
    # ------------------------------------------------------------------

    def create(
        self,
        actor_class: type,
        /,
        *args: Any,
        actor_config: Any | None = None,
        **kwargs: Any,
    ) -> ActorHandleProtocol:
        """Create a remote/local actor via sageFlownet and return a wrapped handle."""
        self._assert_started("create")
        _require_flownet("create")
        from sage.flownet.api.runtime import create_actor  # lazy

        raw_ref = create_actor(actor_class, *args, actor_config=actor_config, **kwargs)
        return _FlownetActorHandle(raw_ref)

    # ------------------------------------------------------------------
    # Flow submission
    # ------------------------------------------------------------------

    def submit(
        self,
        flow_obj: Any,
        *,
        ingress: Any | None = None,
        egress: Any | None = None,
        run_config: Any | None = None,
    ) -> FlowRunHandleProtocol:
        """Submit a flow for async execution and return a wrapped run handle."""
        self._assert_started("submit")
        _require_flownet("submit")
        from sage.flownet.api.runtime import submit_flow  # lazy

        raw_handle = submit_flow(flow_obj, ingress=ingress, egress=egress, run_config=run_config)
        return _FlownetFlowRunHandle(raw_handle)

    # ------------------------------------------------------------------
    # Node information
    # ------------------------------------------------------------------

    def list_nodes(self) -> list[NodeInfoProtocol]:
        """Return wrapped node snapshots from the Flownet ClusterView."""
        self._assert_started("list_nodes")
        _require_flownet("list_nodes")
        from sage.flownet.runtime.runtime import get_runtime  # lazy

        runtime = get_runtime()
        cluster_view = getattr(runtime, "cluster_view", None)
        if cluster_view is None:
            # Local-only runtime may not have a cluster view
            return []
        list_nodes_fn = getattr(cluster_view, "list_nodes", None)
        if not callable(list_nodes_fn):
            return []
        return [_FlownetNodeInfo(n) for n in list_nodes_fn()]


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_adapter_singleton: FlownetRuntimeAdapter | None = None
_adapter_lock: Lock = Lock()


def get_flownet_adapter(*, auto_start: bool = True) -> FlownetRuntimeAdapter:
    """Return the process-global ``FlownetRuntimeAdapter`` singleton.

    Args:
        auto_start: If ``True`` (default), automatically calls
                    :meth:`~FlownetRuntimeAdapter.start` the first time this
                    function is called.  Set to ``False`` to obtain the
                    unstarted adapter for testing.

    Returns:
        The singleton ``FlownetRuntimeAdapter`` instance.
    """
    global _adapter_singleton
    with _adapter_lock:
        if _adapter_singleton is None:
            _adapter_singleton = FlownetRuntimeAdapter()
        if auto_start and not _adapter_singleton._started:
            _adapter_singleton.start()
        return _adapter_singleton
