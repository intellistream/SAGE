"""
sage.kernel.facade - SAGE L3 Public Facade API

Layer: L3 (sage-kernel facade layer)
Dependencies: sage.platform.runtime (L2 protocol) — Flownet imported lazily
              via the adapter in sage.platform.runtime.adapters.flownet_adapter.

Per the Flownet→SAGE migration boundaries:
- intellistream/SAGE#1432 (Issue 3): defines these four canonical verbs.
- intellistream/SAGE#1433 (Issue 4): all backend dispatching routes through
  the L2 ``RuntimeBackendProtocol``; no direct Flownet internal imports here.

This module is the **single stable user-facing entry point** for all SAGE
execution operations.  It ships with four canonical verbs:

    create(actor_class, ...)  – instantiate a remote/local actor
    submit(flow_or_decl, ...) – register and submit a flow for async execution
    run(flow_or_decl, ...)    – compile + execute a flow (blocking, returns result)
    call(flow_or_decl, ...)   – call a pre-submitted flow by reference (blocking)

Design rules
------------
- **No backend-specific terms** anywhere in this public API.
- All backend references (Flownet runtime) are **lazy** — routed through the
  L2 ``RuntimeBackendProtocol``/``FlownetRuntimeAdapter`` instead of calling
  Flownet internals directly.
- Signatures are stable contracts; internal routing to Flownet is an
  implementation detail encapsulated in the L2 adapter layer.
- Legacy ``LocalEnvironment.submit()`` / ``env.submit()`` path remains in
  ``sage.kernel.api`` for DataStream pipelines; *this* module serves the
  flow-program/actor pattern introduced by Issues #1431 and #1432.

Migration guide
---------------
+--------------------------------------------+------------------------------------------+
| Old path                                   | New path                                 |
+============================================+==========================================+
| ``from sage.flownet.api import create_actor``  | ``from sage.kernel.facade import create``|
| ``from sage.flownet.api import submit_flow``   | ``from sage.kernel.facade import submit``|
| ``flow_decl._require_adapter(); .call(...)``   | ``from sage.kernel.facade import run``   |
| ``flow_decl._require_adapter(); .submit(...)`` | ``from sage.kernel.facade import submit``|
+--------------------------------------------+------------------------------------------+

Example usage
-------------
::

    from sage.kernel.flow import flow
    from sage.kernel.facade import create, submit, run, call

    # 1. Declare a flow
    @flow
    def my_pipeline(init_stream):
        return init_stream.map(my_actor.process)

    # 2. Create an actor (actor lifecycle managed by runtime backend)
    my_actor = create(MyActorClass, config={"key": "value"})

    # 3. Run synchronously
    result = run(my_pipeline, payload)

    # 4. Submit asynchronously and call later
    run_handle = submit(my_pipeline)
    result = call(run_handle, payload)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sage.kernel.flow.declaration import FlowDeclaration, _BoundFlowDeclaration
    from sage.platform.runtime.protocol import (
        ActorHandleProtocol,
        FlowRunHandleProtocol,
        MethodCallFuture,
        MethodRefProtocol,
    )

__all__ = [
    "create",
    "submit",
    "run",
    "call",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_runtime_backend() -> Any:
    """Return the process-global ``FlownetRuntimeAdapter`` (L2 protocol impl).

    This is the **only** place in the facade that knows the backend is
    Flownet.  All other code interacts via ``RuntimeBackendProtocol``.

    Raises:
        ImportError: If sageFlownet is not installed.
    """
    try:
        from sage.platform.runtime.adapters.flownet_adapter import (  # lazy
            get_flownet_adapter,
        )

        return get_flownet_adapter()
    except ImportError as exc:
        raise ImportError(
            "SAGE facade operations require the sageFlownet runtime backend.\n"
            "Install it with:  pip install isage-flow\n"
            f"Original error: {exc}"
        ) from exc


def _resolve_flow_for_backend(flow_obj: Any) -> Any:
    """Resolve a SAGE ``FlowDeclaration`` to a backend-native flow object.

    Accepts:
    - A ``FlowDeclaration`` (SAGE L3 canonical descriptor).
    - A ``_BoundFlowDeclaration`` (descriptor accessed from an instance).
    - A raw Flownet ``FlowDef`` (legacy/interop path; passed through as-is).
    - Any other object (passed through unchanged).

    Returns the backend-native (Flownet) flow object ready for submission.
    """
    try:
        from sage.kernel.flow.declaration import (  # lazy
            FlowDeclaration,
            _BoundFlowDeclaration,
        )

        if isinstance(flow_obj, _BoundFlowDeclaration):
            return flow_obj._declaration._require_adapter()(flow_obj._instance)
        if isinstance(flow_obj, FlowDeclaration):
            return flow_obj._require_adapter()
    except ImportError:
        pass
    # Fall-through: assume flow_obj is already a backend-native object
    return flow_obj


# ---------------------------------------------------------------------------
# Public facade verbs
# ---------------------------------------------------------------------------


def create(
    actor_class: type,
    *args: Any,
    actor_config: Any | None = None,
    **kwargs: Any,
) -> ActorHandleProtocol:
    """Create a (remote/local) actor via the runtime backend.

    This is the SAGE canonical replacement for direct backend-specific actor
    creation calls.  The dispatch is routed through the L2
    ``RuntimeBackendProtocol`` so that the facade has no direct dependency on
    Flownet internals (intellistream/SAGE#1433).

    The returned handle supports both the canonical protocol API
    (``handle.get_method(name).call(...)``) and the attribute-shorthand
    (``handle.method_name.call(...)``), so existing code continues to work.

    Three invocation modes are available on the returned handle's method refs
    (``ActorHandleProtocol`` / ``MethodRefProtocol``, intellistream/SAGE#1436):

    * **Synchronous**: ``handle.get_method("process").call(payload)``
    * **Asynchronous**: ``future = handle.get_method("process").async_call(payload)``
      then ``result = future.result(timeout=30.0)``
    * **Cancel**: ``handle.get_method("process").cancel()`` or
      ``handle.cancel()`` for actor-level teardown.

    Args:
        actor_class:  The class to instantiate as a stateful actor.
        *args:        Positional construction arguments forwarded to
                      ``actor_class.__init__``.
        actor_config: Optional runtime configuration dict (placement hints,
                      resource requirements, etc.).
        **kwargs:     Keyword construction arguments forwarded to
                      ``actor_class.__init__``.

    Returns:
        An ``ActorHandleProtocol`` whose methods can be called via
        ``handle.method_name(...)`` or ``handle.get_method("method_name").call(...)``.

    Raises:
        ImportError: If the runtime backend (sageFlownet) is not installed.
        RuntimeError: If the runtime backend has not been initialised.

    Example::

        from sage.kernel.facade import create

        actor = create(MyWorker, num_threads=4)

        # Synchronous invocation
        result = actor.process.call(payload)

        # Asynchronous invocation (non-blocking)
        future = actor.process.async_call(payload)
        result = future.result(timeout=30.0)

        # Cancel actor
        actor.cancel()
    """
    backend = _get_runtime_backend()
    return backend.create(actor_class, *args, actor_config=actor_config, **kwargs)


def submit(
    flow_obj: Any,
    *,
    ingress: Any | None = None,
    egress: Any | None = None,
    run_config: Any | None = None,
) -> FlowRunHandleProtocol:
    """Submit a flow for asynchronous execution via the runtime backend.

    Accepts a ``FlowDeclaration`` (as created by ``@flow``), a
    ``_BoundFlowDeclaration`` (method flow accessed from an instance), or a
    backend-native flow object for interop.

    This call returns a run handle immediately without blocking.  Use
    :func:`call` to retrieve results from a submitted flow.

    The dispatch is routed through the L2 ``RuntimeBackendProtocol``
    (intellistream/SAGE#1433).

    Args:
        flow_obj:   A ``FlowDeclaration``, bound flow method, or backend-native
                    flow task object.
        ingress:    Optional ingress channel descriptor.
        egress:     Optional egress channel descriptor.
        run_config: Optional per-run execution configuration.

    Returns:
        A ``FlowRunHandleProtocol`` that can be used with :func:`call` to
        drive inputs/outputs after submission.

    Raises:
        ImportError: If the runtime backend (sageFlownet) is not installed.
        RuntimeError: If the runtime backend has not been initialised.

    Example::

        from sage.kernel.facade import submit, call

        run_ref = submit(my_pipeline)
        result = call(run_ref, my_payload)
    """
    backend = _get_runtime_backend()
    native_flow = _resolve_flow_for_backend(flow_obj)
    return backend.submit(native_flow, ingress=ingress, egress=egress, run_config=run_config)


def run(flow_obj: Any, *args: Any, **kwargs: Any) -> Any:
    """Compile and execute a flow synchronously, returning its result.

    This is the blocking ("fire-and-collect") execution path.  Under the hood
    it resolves the ``FlowDeclaration`` to a backend-native flow and invokes
    its ``.call()`` method, which compiles the flow, opens a pipe, enqueues
    the payload, and awaits the result.

    The dispatch is routed through the L2 ``RuntimeBackendProtocol``
    (intellistream/SAGE#1433).

    Args:
        flow_obj: A ``FlowDeclaration``, ``_BoundFlowDeclaration``, or a
                  backend-native flow object.
        *args:    Positional payload arguments forwarded to the flow.
        **kwargs: Keyword payload arguments forwarded to the flow.

    Returns:
        The result produced by the flow's output stage.

    Raises:
        ImportError: If the runtime backend (sageFlownet) is not installed.
        RuntimeError: If the runtime backend has not been initialised.

    Example::

        from sage.kernel.flow import flow
        from sage.kernel.facade import create, run

        @flow
        def pipeline(init_stream):
            return init_stream.map(worker.process)

        worker = create(MyWorker)
        result = run(pipeline, {"text": "hello"})
    """
    # Ensure backend is available (raises ImportError if not).
    _get_runtime_backend()
    native_flow = _resolve_flow_for_backend(flow_obj)
    # BoundFlow / FlowDef both expose .call(*args, **kwargs); so do
    # _FlownetFlowRunHandle wrappers returned from submit().
    if hasattr(native_flow, "call"):
        return native_flow.call(*args, **kwargs)
    # Fallback: treat as callable (e.g. a raw compiled FlowTask).
    return native_flow(*args, **kwargs)


def call(flow_ref: Any, *args: Any, **kwargs: Any) -> Any:
    """Call a previously submitted flow run handle, returning its output.

    :func:`call` is the blocking counterpart to :func:`submit`.  It forwards
    ``*args`` / ``**kwargs`` as the input payload to the run handle returned
    by :func:`submit`, blocks until a result is available, and returns it.

    For cases where both submission and collection happen in the same scope,
    prefer :func:`run` for simplicity (it is equivalent to
    ``call(submit(flow), ...)``).

    The dispatch is routed through the L2 ``RuntimeBackendProtocol``
    (intellistream/SAGE#1433).

    Args:
        flow_ref: A run handle returned by :func:`submit` (a
                  ``FlowRunHandleProtocol``), *or* any object exposing a
                  ``call()`` method (e.g. an ``ActorMethodRef``-style handle
                  from :func:`create`).
        *args:    Positional payload arguments.
        **kwargs: Keyword payload arguments.

    Returns:
        The result value produced by the referenced flow/actor method.

    Raises:
        ImportError: If the runtime backend (sageFlownet) is not installed.
        RuntimeError: If the runtime backend has not been initialised.
        TypeError: If ``flow_ref`` does not expose a ``call()`` interface.

    Example::

        from sage.kernel.facade import submit, call

        run_ref = submit(my_pipeline)
        # ... do other work ...
        result = call(run_ref, payload)
    """
    # Ensure backend is available (raises ImportError if not).
    _get_runtime_backend()
    if not hasattr(flow_ref, "call"):
        raise TypeError(
            f"'call' expects an object with a .call() method (e.g. a run handle "
            f"or method reference), got {type(flow_ref)!r}.\n"
            "Use 'run(flow, payload)' to compile-and-execute a FlowDeclaration."
        )
    return flow_ref.call(*args, **kwargs)
