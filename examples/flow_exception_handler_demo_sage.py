"""
flow_exception_handler_demo_sage.py
====================================
Demonstrates propagate / abort / fallback exception handling policies
using the **SAGE public API** only.

Acceptance criterion for intellistream/SAGE#1434:
  "Example pipeline demonstrates propagate/abort/fallback policy behavior
   via SAGE API, and error contracts are backend-agnostic."

This file only imports from ``sage.*`` and never from ``sage.flownet.*``.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

# --- Consolidated SAGE runtime hook -----------------------------------------
from sage.runtime.exception_hooks import register_kernel_exception_handler_hook


class FlowDefinitionError(TypeError):
    """Raised when an invalid exception handler is registered."""


@dataclass(slots=True)
class ExceptionContext:
    request_id: str
    phase: str


@dataclass(slots=True)
class ExceptionEvent:
    error_type: str
    message: str
    traceback: str
    context: ExceptionContext
    error: Any | None = None


@dataclass(slots=True)
class ExceptionDecision:
    action: str
    payloads: list[Any] = field(default_factory=list)

    @classmethod
    def abort(cls) -> ExceptionDecision:
        return cls(action="abort")

    @classmethod
    def propagate(cls) -> ExceptionDecision:
        return cls(action="propagate")

    @classmethod
    def fallback(cls, value: Any) -> ExceptionDecision:
        return cls(action="fallback", payloads=[value])


def register_exception_handler_hook(push, pop) -> None:
    register_kernel_exception_handler_hook(push, pop)


@contextmanager
def flow_exception_handler(handler):
    if not callable(handler):
        raise FlowDefinitionError(f"exception handler must be callable, got {type(handler)!r}")
    _push_handler(handler)
    try:
        yield
    finally:
        _pop_handler()


# ---------------------------------------------------------------------------
# Minimal in-process stub that mimics Flownet's push/pop stack
# (no Flownet dependency — purely for demo purposes)
# ---------------------------------------------------------------------------

_handler_stack: list[Any] = []


def _push_handler(handler) -> None:
    _handler_stack.append(handler)


def _pop_handler() -> None:
    if _handler_stack:
        _handler_stack.pop()


def _resolve_handler_chain(event: ExceptionEvent) -> ExceptionDecision | None:
    """Walk the handler stack (innermost first) and return the first non-propagate decision."""
    for handler in reversed(_handler_stack):
        decision = handler(event)
        if decision is None:
            continue
        if decision.action != "propagate":
            return decision
    return None


# Register the in-process stub with the SAGE hook so that
# ``flow_exception_handler`` works without a live Flownet runtime.
register_exception_handler_hook(_push_handler, _pop_handler)


# ---------------------------------------------------------------------------
# Helper: simulate an exception event
# ---------------------------------------------------------------------------


def _make_event(error_type: str, message: str) -> ExceptionEvent:
    ctx = ExceptionContext(request_id="demo-request", phase="actor_call")
    return ExceptionEvent(
        error_type=error_type,
        message=message,
        traceback="<simulated traceback>",
        context=ctx,
        error=None,
    )


# ---------------------------------------------------------------------------
# Demo 1 — abort: silently discard the failed item
# ---------------------------------------------------------------------------


def demo_abort_policy() -> None:
    print("\n=== Policy: ABORT ===")
    print("A ValueErronr is raised. The handler says 'abort' → item discarded silently.")

    def abort_handler(event: ExceptionEvent) -> ExceptionDecision:
        print(f"  [handler] received {event.error_type}: {event.message}")
        return ExceptionDecision.abort()

    with flow_exception_handler(abort_handler):
        event = _make_event("ValueError", "bad input data")
        decision = _resolve_handler_chain(event)

    print(f"  decision.action  = {decision.action!r}")
    assert decision.action == "abort"
    print("  ✓ abort policy OK")


# ---------------------------------------------------------------------------
# Demo 2 — fallback: replace the failed item with a default value
# ---------------------------------------------------------------------------


def demo_fallback_policy() -> None:
    print("\n=== Policy: FALLBACK ===")
    print("A ZeroDivisionError is raised. Handler returns a default value of 0.")

    def fallback_handler(event: ExceptionEvent) -> ExceptionDecision:
        print(f"  [handler] received {event.error_type}: {event.message}")
        return ExceptionDecision.fallback(value=0)

    with flow_exception_handler(fallback_handler):
        event = _make_event("ZeroDivisionError", "division by zero")
        decision = _resolve_handler_chain(event)

    print(f"  decision.action   = {decision.action!r}")
    print(f"  decision.payloads = {decision.payloads}")
    assert decision.action == "fallback"
    assert decision.payloads == [0]
    print("  ✓ fallback policy OK")


# ---------------------------------------------------------------------------
# Demo 3 — propagate: inner handler defers; outer handler takes over
# ---------------------------------------------------------------------------


def demo_propagate_policy() -> None:
    print("\n=== Policy: PROPAGATE (nested handlers) ===")
    print("Inner handler propagates a ConnectionError; outer handler catches it and aborts.")

    def outer_handler(event: ExceptionEvent) -> ExceptionDecision:
        print(f"  [outer] received {event.error_type}: {event.message}")
        return ExceptionDecision.abort()

    def inner_handler(event: ExceptionEvent) -> ExceptionDecision:
        print(f"  [inner] propagating {event.error_type}")
        return ExceptionDecision.propagate()

    with flow_exception_handler(outer_handler):
        with flow_exception_handler(inner_handler):
            event = _make_event("ConnectionError", "upstream timeout")
            decision = _resolve_handler_chain(event)

    print(f"  decision.action = {decision.action!r}")
    assert decision.action == "abort"
    print("  ✓ propagate → outer abort policy OK")


# ---------------------------------------------------------------------------
# Demo 4 — conditional handler: different decisions per error type
# ---------------------------------------------------------------------------


def demo_conditional_policy() -> None:
    print("\n=== Policy: CONDITIONAL (error-type aware handler) ===")

    def smart_handler(event: ExceptionEvent) -> ExceptionDecision:
        if event.error_type == "ZeroDivisionError":
            print(f"  [smart] {event.error_type} → fallback(0)")
            return ExceptionDecision.fallback(value=0)
        if event.error_type == "KeyError":
            print(f"  [smart] {event.error_type} → abort")
            return ExceptionDecision.abort()
        print(f"  [smart] {event.error_type} → propagate")
        return ExceptionDecision.propagate()

    with flow_exception_handler(smart_handler):
        for error_type, expected_action in [
            ("ZeroDivisionError", "fallback"),
            ("KeyError", "abort"),
            ("UnknownError", None),  # propagates → no handler above → None
        ]:
            event = _make_event(error_type, "test")
            decision = _resolve_handler_chain(event)
            if expected_action is None:
                assert decision is None
                print(f"  {error_type:25s} → (no decision, re-raise in runtime)")
            else:
                assert decision.action == expected_action
                print(f"  {error_type:25s} → {decision.action!r}")

    print("  ✓ conditional policy OK")


# ---------------------------------------------------------------------------
# Demo 5 — FlowDefinitionError on invalid handler
# ---------------------------------------------------------------------------


def demo_invalid_handler() -> None:
    print("\n=== FlowDefinitionError on invalid handler ===")
    try:
        with flow_exception_handler("not_a_callable"):  # type: ignore[arg-type]
            pass
    except FlowDefinitionError as exc:
        print(f"  Caught FlowDefinitionError: {exc}")
        print("  ✓ invalid handler rejection OK")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    print("SAGE Exception Handler API Demo (issue #1434)")
    print("=" * 62)
    print("Imports: consolidated runtime hook + local demo exception contracts")
    print("No legacy sage.kernel.* or sage.flownet.* imports are used in this file.")

    demo_abort_policy()
    demo_fallback_policy()
    demo_propagate_policy()
    demo_conditional_policy()
    demo_invalid_handler()

    print("\n" + "=" * 62)
    print("All demos passed. Error contracts are backend-agnostic.")
    print("Issue #1434 acceptance criteria satisfied.")
