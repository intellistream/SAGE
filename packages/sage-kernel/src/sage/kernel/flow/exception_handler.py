"""
sage.kernel.flow.exception_handler — SAGE L3 Flow Exception Handler API

Layer: L3 (sage-kernel, DSL / declaration layer)
Dependencies: sage.common (L1) only — NO sage.platform, NO Flownet import at module level.

This module is the **SAGE-owned declaration-side** of the exception handler
registration API.  It provides ``flow_exception_handler``, a context manager
that attaches an exception-handling actor method to a flow scope during
compilation.

The underlying mechanism (stack bookkeeping, runtime dispatch) is wired by the
Flownet backend.  This module only defines the *contract* and the
*compilation-time attachment hook*.

Migration context (intellistream/SAGE#1434):
  - Previously this API lived exclusively in
    ``sageFlownet/src/sage/flownet/api/flow_exception_handlers.py``.
  - SAGE now owns the public API surface; Flownet keeps the internal wiring.
  - The context variable ``_flowtask_ctx`` is lazily injected by Flownet when
    the runtime is initialised; SAGE only reads/writes through the public slot.

Usage
-----
::

    from sage.kernel.flow import flow
    from sage.kernel.flow.exception_handler import flow_exception_handler
    from sage.kernel.facade import create, run

    class MyErrorHandler:
        def handle(self, event):
            from sage.common.core.flow_exceptions import ExceptionDecision
            if "divide by zero" in event.message:
                return ExceptionDecision.fallback(value=0)
            return ExceptionDecision.abort()

    handler = create(MyErrorHandler)

    @flow
    def my_pipeline(init_stream):
        with flow_exception_handler(handler.handle):
            return init_stream.map(risky_actor.process)

    result = run(my_pipeline, payload)
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Optional

# Only import the abstract contract types from L1 — no runtime deps.
from sage.common.core.flow_exceptions import FlowDefinitionError

if TYPE_CHECKING:
    # MethodRefProtocol is the L2 typing for a callable actor-method reference.
    # Imported only for type-checkers; do NOT reference at runtime here.
    pass

__all__ = [
    "flow_exception_handler",
    "exception_handler",  # backwards-compatible alias
    "register_exception_handler_hook",
]


# ---------------------------------------------------------------------------
# Runtime injection slot
# ---------------------------------------------------------------------------
# Flownet sets this hook during FlowTask compilation so that the context
# manager can reach the active flowtask without importing Flownet directly.
# The hook signature must be:
#
#   _push_handler(handler: Any) -> None
#   _pop_handler() -> None
#
# Both callables are injected by the Flownet adapter at startup.

_PUSH_HANDLER: Optional[Any] = None
_POP_HANDLER: Optional[Any] = None


def register_exception_handler_hook(push: Any, pop: Any) -> None:
    """Register the runtime-backend hooks for handler stack management.

    Called once by the Flownet adapter (or test doubles) to wire the context
    manager to the live compilation state.  SAGE code never calls this
    directly — it is meant to be invoked from the ``flownet_adapter`` during
    backend initialisation.

    Args:
        push: A callable ``(handler) -> None`` that pushes a handler onto the
              active flowtask's exception handler stack.
        pop:  A callable ``() -> None`` that pops the most recently pushed
              handler from the active flowtask's exception handler stack.

    Raises:
        TypeError: If either argument is not callable.
    """
    global _PUSH_HANDLER, _POP_HANDLER
    if not callable(push):
        raise TypeError(f"push hook must be callable, got {type(push)!r}")
    if not callable(pop):
        raise TypeError(f"pop hook must be callable, got {type(pop)!r}")
    _PUSH_HANDLER = push
    _POP_HANDLER = pop


# ---------------------------------------------------------------------------
# Public API — context manager
# ---------------------------------------------------------------------------


def _resolve_handler(handler: Any) -> Any:
    """Validate that *handler* is an acceptable handler reference.

    Accepts any callable.  Raises ``FlowDefinitionError`` for ``None`` or
    clearly invalid types (non-callable, not a method reference).
    """
    if handler is None:
        raise FlowDefinitionError(
            "flow_exception_handler requires a non-None handler. "
            "Pass an actor method reference: actor.method"
        )
    # Accept any callable (ActorMethodRef is callable; plain functions are
    # allowed in tests / local mode).
    if not callable(handler):
        raise FlowDefinitionError(
            f"flow_exception_handler expects a callable (ActorMethodRef or function), "
            f"got {type(handler)!r}."
        )
    return handler


@contextmanager
def flow_exception_handler(handler: Any):
    """Register an exception handler for the enclosed flow scope (context manager).

    Must be used **inside** a ``@flow`` function during compilation.  The
    *handler* callable is invoked when an exception escapes an actor method
    in the enclosed datastream scope.

    The handler receives an ``ExceptionEvent`` and must return an
    ``ExceptionDecision`` (from ``sage.common.core.flow_exceptions``):

    - ``ExceptionDecision.propagate()`` — try the next outer handler.
    - ``ExceptionDecision.abort()`` — silently discard the failed payload.
    - ``ExceptionDecision.fallback(value=...)`` — replace with a default value.

    If all registered handlers propagate, or no handler is registered, the
    runtime sends a flow-error notification and raises ``FlowException`` at the
    call site.

    Args:
        handler: A callable that accepts ``ExceptionEvent`` and returns
            ``ExceptionDecision``.  Typically an actor method reference
            obtained via ``create(MyHandler).method``.

    Raises:
        FlowDefinitionError: If *handler* is ``None`` or not callable.
        RuntimeError: If called outside a flow compilation context (i.e. the
            runtime backend hook has not been registered yet).

    Example::

        @flow
        def my_pipeline(init_stream):
            with flow_exception_handler(error_actor.handle):
                return init_stream.map(risky_actor.process)
    """
    resolved = _resolve_handler(handler)

    if _PUSH_HANDLER is None or _POP_HANDLER is None:
        # Provide a clear error when the backend hasn't been initialised.
        # This can happen if ``flow_exception_handler`` is used in a pure
        # compilation context without a running Flownet backend.
        raise RuntimeError(
            "flow_exception_handler requires an active runtime backend. "
            "Make sure the Flownet adapter is initialised before compiling flows "
            "that use exception handlers.  (Hint: call sage.kernel.facade.run() or "
            "sage.kernel.facade.submit() to auto-initialise the backend.)"
        )

    _PUSH_HANDLER(resolved)
    try:
        yield
    finally:
        _POP_HANDLER()


# Backwards-compatible alias — mirrors the old sageFlownet public name.
exception_handler = flow_exception_handler
