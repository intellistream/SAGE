"""
sage.platform.runtime.protocol - Runtime Backend Protocol Interface

Layer: L2 (sage-platform)

This module defines the **protocol contract** between SAGE L3 (sage-kernel)
and the underlying runtime backend (default: sageFlownet).

Design Rules
------------
- This module contains **only** ABC/Protocol-level declarations.
- Zero direct Flownet imports – this is the abstraction layer.
- All implementations live in ``adapters/`` submodule (e.g. ``flownet_adapter``).
- Per the migration boundary (intellistream/SAGE#1430), runtime core keeps its
  execution loop; SAGE owns the protocol *contract*.

Protocol Hierarchy
------------------
::

    RuntimeBackendProtocol          – top-level runtime backend
        .create(cls, ...)           → ActorHandleProtocol
        .submit(flow, ...)          → FlowRunHandleProtocol
        .stop()
        .node_info()                → NodeInfoProtocol

    ActorHandleProtocol             – handle to a remote/local actor
        .get_method(name)           → MethodRefProtocol
        .cancel()                   – cancel/terminate the actor

    MethodRefProtocol               – callable actor method reference
        .call(*args, **kwargs)      → result (blocking synchronous)
        .async_call(*args, **kwargs)→ MethodCallFuture (non-blocking)
        .cancel()                   → bool (cancel in-flight call)

    MethodCallFuture                – handle for an in-flight async call
        .result(timeout)            → result (blocking with optional timeout)
        .cancel()                   → bool (cancel)
        .done                       → bool (completion flag)

    FlowRunHandleProtocol           – handle to a submitted flow run
        .call(*args, **kwargs)      → result (blocking)
        .cancel()

    NodeInfoProtocol                – node metadata snapshot

Usage (from sage-kernel facade)
--------------------------------
::

    from sage.platform.runtime.protocol import RuntimeBackendProtocol
    from sage.platform.runtime.adapters.flownet_adapter import FlownetRuntimeAdapter

    backend: RuntimeBackendProtocol = FlownetRuntimeAdapter()
    actor = backend.create(MyActorClass)

    # Synchronous call (blocking)
    result = actor.get_method("process").call(payload)

    # Asynchronous call (non-blocking, returns a MethodCallFuture)
    future = actor.get_method("process").async_call(payload)
    result = future.result(timeout=30.0)

References
----------
- Migration boundary:      intellistream/SAGE#1430
- Facade API (Issue 3):    intellistream/SAGE#1432
- Runtime protocol (Issue 4): intellistream/SAGE#1433
- Actor ref interfaces (Issue 7): intellistream/SAGE#1436
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

__all__ = [
    "RuntimeBackendProtocol",
    "ActorHandleProtocol",
    "MethodRefProtocol",
    "MethodCallFuture",
    "FlowRunHandleProtocol",
    "NodeInfoProtocol",
]


# ---------------------------------------------------------------------------
# NodeInfoProtocol
# ---------------------------------------------------------------------------


class NodeInfoProtocol(ABC):
    """Snapshot of runtime node metadata.

    Used by SAGE scheduler/placer to make placement decisions without
    importing Flownet cluster internals directly.
    """

    @property
    @abstractmethod
    def node_id(self) -> str:
        """Unique identifier for this node."""

    @property
    @abstractmethod
    def address(self) -> str:
        """Network address of this node (``host:port``)."""

    @property
    @abstractmethod
    def is_schedulable(self) -> bool:
        """Whether this node accepts new compute tasks."""

    @property
    @abstractmethod
    def resource_summary(self) -> dict[str, Any]:
        """Arbitrary resource metadata (cpu/gpu/memory).

        Keys are strings; values are numbers or nested dicts.
        See ``sage.kernel.scheduler.node_selector.NodeResources`` for
        the canonical field names consumed by the scheduler.
        """


# ---------------------------------------------------------------------------
# Handle protocols
# ---------------------------------------------------------------------------


class MethodCallFuture(ABC):
    """Handle for an in-flight asynchronous actor method invocation.

    Returned by ``MethodRefProtocol.async_call()``.  Callers can either
    block for the result via ``.result()``, poll via ``.done``, or attempt
    early cancellation via ``.cancel()``.

    This is SAGE's backend-agnostic future contract.  Implementations
    (e.g. ``_FlownetMethodCallFuture``) back it with
    ``concurrent.futures.Future`` or a Flownet-native future.

    Example::

        future = actor.get_method("process").async_call(payload)
        # ... do other work ...
        result = future.result(timeout=30.0)
    """

    @abstractmethod
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

    @abstractmethod
    def cancel(self) -> bool:
        """Request cancellation of the in-flight call.

        Returns:
            ``True`` if the cancellation was accepted; ``False`` if the
            call had already completed or cancellation is not supported.
        """

    @property
    @abstractmethod
    def done(self) -> bool:
        """``True`` when the call has completed (successfully or with error)
        or has been cancelled."""


class MethodRefProtocol(ABC):
    """Protocol for a callable actor method reference.

    A ``MethodRefProtocol`` is obtained via
    ``ActorHandleProtocol.get_method(name)`` and represents a single method
    on a remote/local actor.

    Three invocation modes are provided:

    * ``call()``       – blocking synchronous invocation.
    * ``async_call()`` – non-blocking invocation returning a
                         ``MethodCallFuture``.
    * ``cancel()``     – best-effort cancellation of any in-flight call.

    The Flownet adapter implements all three by delegating to the sageFlownet
    ``ActorMethodRef``.  Backends that do not support async/cancel should
    raise ``NotImplementedError`` from those methods.
    """

    @abstractmethod
    def call(self, *args: Any, **kwargs: Any) -> Any:
        """Invoke the actor method synchronously and return its result.

        Args:
            *args:    Positional arguments forwarded to the actor method.
            **kwargs: Keyword arguments forwarded to the actor method.

        Returns:
            The return value of the actor method.

        Raises:
            RuntimeError: If the actor is no longer alive or the call fails.
        """

    @abstractmethod
    def async_call(self, *args: Any, **kwargs: Any) -> MethodCallFuture:
        """Invoke the actor method asynchronously, returning a future handle.

        The call is dispatched immediately; the caller can collect the result
        by calling ``future.result()`` when convenient.

        Args:
            *args:    Positional arguments forwarded to the actor method.
            **kwargs: Keyword arguments forwarded to the actor method.

        Returns:
            A ``MethodCallFuture`` whose ``.result()`` blocks for completion.

        Raises:
            RuntimeError: If the actor is no longer alive.
        """

    @abstractmethod
    def cancel(self) -> bool:
        """Request cancellation of any in-flight synchronous/async call.

        This is a best-effort hint to the backend.  If the call has already
        completed, or the backend does not support cancellation, ``False`` is
        returned rather than raising.

        Returns:
            ``True`` if the cancellation was accepted; ``False`` otherwise.
        """


class ActorHandleProtocol(ABC):
    """Protocol for a handle to a remote or local actor.

    An ``ActorHandleProtocol`` is returned by
    ``RuntimeBackendProtocol.create()`` and provides ``get_method()`` to
    obtain callable references to individual actor methods.

    Actor-level cancellation (``cancel()``) terminates the actor itself and
    all in-flight calls associated with it.
    """

    @abstractmethod
    def get_method(self, name: str) -> MethodRefProtocol:
        """Return a callable reference to the named actor method.

        Args:
            name: The method name as a string.

        Returns:
            A ``MethodRefProtocol`` whose ``.call()`` / ``.async_call()``
            dispatches the method.

        Raises:
            AttributeError: If the actor does not expose ``name``.
        """

    def cancel(self) -> bool:
        """Request actor-level cancellation (terminate the actor).

        This is an *optional* contract: backends that support actor teardown
        should override this method; the default no-op returns ``False``.

        Returns:
            ``True`` if the backend accepted the cancellation request.
        """
        return False


class FlowRunHandleProtocol(ABC):
    """Protocol for a handle to a submitted flow run.

    A ``FlowRunHandleProtocol`` is returned by
    ``RuntimeBackendProtocol.submit()`` and allows callers to:
    - Forward input payloads and collect outputs via ``.call()``.
    - Cancel an in-flight run via ``.cancel()``.
    """

    @abstractmethod
    def call(self, *args: Any, **kwargs: Any) -> Any:
        """Send a payload to the submitted flow and return its output.

        Args:
            *args:   Positional payload arguments forwarded to the flow.
            **kwargs: Keyword payload arguments.

        Returns:
            The output produced by the flow's terminal stage.

        Raises:
            RuntimeError: If the flow run is not active or call fails.
        """

    @abstractmethod
    def cancel(self) -> None:
        """Cancel the in-flight flow run.

        After ``cancel()`` the handle must not be called again.

        Raises:
            RuntimeError: If cancellation is not supported by the backend.
        """


# ---------------------------------------------------------------------------
# RuntimeBackendProtocol – top-level contract
# ---------------------------------------------------------------------------


class RuntimeBackendProtocol(ABC):
    """Protocol contract between SAGE kernel and the underlying runtime backend.

    This is the **single seam** that separates SAGE's logical execution model
    from the physical runtime (Flownet by default).  The kernel facade
    (``sage.kernel.facade``) uses this interface exclusively; it never imports
    Flownet internals directly.

    Lifecycle
    ---------
    1. ``start()``  – boot or connect to the runtime (idempotent).
    2. Normal operations: ``create``, ``submit``.
    3. ``stop()``   – graceful shutdown.

    All runtime operations are **fail-fast**: they raise ``RuntimeError``
    if the backend is not started, rather than silently degrading.
    """

    @abstractmethod
    def start(self, config: Any | None = None) -> None:
        """Boot or connect to the runtime backend.

        May be called multiple times; implementations must be idempotent.

        Args:
            config: Backend-specific configuration object (e.g.
                    ``FlownetConfig``).  Passing ``None`` selects defaults.

        Raises:
            RuntimeError: If the backend fails to start.
        """

    @abstractmethod
    def stop(self) -> None:
        """Gracefully shut down the runtime backend.

        After ``stop()`` all outstanding actor handles and flow run handles
        may become invalid.

        Raises:
            RuntimeError: If the backend fails to stop cleanly.
        """

    @abstractmethod
    def create(
        self,
        actor_class: type,
        /,
        *args: Any,
        actor_config: Any | None = None,
        **kwargs: Any,
    ) -> ActorHandleProtocol:
        """Create (instantiate) a remote or local actor.

        The placement policy (local vs. remote) is decided by the backend
        based on cluster state and any hints in ``actor_config``.

        Args:
            actor_class:  The class to instantiate as a stateful actor.
            *args:        Positional constructor arguments.
            actor_config: Optional placement/resource hint dict.
            **kwargs:     Keyword constructor arguments.

        Returns:
            An ``ActorHandleProtocol`` whose methods can be invoked via
            ``handle.get_method(name).call(...)``.

        Raises:
            RuntimeError: If the backend is not started.
            TypeError:    If ``actor_class`` is not a valid actor type.
        """

    @abstractmethod
    def submit(
        self,
        flow_obj: Any,
        *,
        ingress: Any | None = None,
        egress: Any | None = None,
        run_config: Any | None = None,
    ) -> FlowRunHandleProtocol:
        """Submit a flow for asynchronous execution.

        Args:
            flow_obj:   A flow descriptor (e.g. ``FlowDeclaration`` from
                        ``sage.kernel.flow``).  The backend resolves it to
                        an executable form.
            ingress:    Optional ingress channel descriptor.
            egress:     Optional egress channel descriptor.
            run_config: Optional per-run execution configuration.

        Returns:
            A ``FlowRunHandleProtocol`` that can be used to drive
            inputs/collect outputs.

        Raises:
            RuntimeError: If the backend is not started.
        """

    @abstractmethod
    def list_nodes(self) -> list[NodeInfoProtocol]:
        """Return metadata for all currently known cluster nodes.

        Returns:
            A (possibly empty) list of ``NodeInfoProtocol`` snapshots.
            The list reflects a point-in-time view; membership may change
            between calls in a distributed deployment.

        Raises:
            RuntimeError: If the backend is not started.
        """
