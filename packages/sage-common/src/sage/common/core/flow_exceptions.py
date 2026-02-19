"""
Flow Exception Contracts — SAGE L1 Portable Error Model

Layer: L1 (sage-common, Foundation)
Dependencies: Python stdlib only — NO Flownet, NO sage-platform, NO sage-kernel.

This module defines the **SAGE-owned, backend-agnostic** exception contract for
flow-level error handling.  It is the canonical source for all error-category
types and decision semantics shared between the SAGE declaration layer (L3)
and the Flownet runtime backend.

Migration context (intellistream/SAGE#1434, depends on #1430-#1433):
  - Previously ``ExceptionContext``, ``ExceptionEvent``, ``ExceptionDecision``,
    and ``FlowException`` lived in ``sageFlownet/src/sage/flownet/core/exceptions.py``
    and imported ``PayloadData`` from Flownet internals.
  - SAGE now owns the **contract layer**; Flownet keeps the execution wiring.
  - ``ExceptionDecision.payloads`` uses plain ``list[Any]`` to avoid importing
    Flownet's ``PayloadData`` at the contract level.  The Flownet adapter
    converts ``Any`` values to ``PayloadData`` internally.

Error classification model
--------------------------
``ExceptionAction`` represents the three first-class decisions a handler may
return:

propagate
    The handler has no opinion; try the next handler in the stack.  If all
    handlers propagate, the runtime sends a flow-error notification and re-raises
    the exception.

abort
    Silently discard the failed item; no further processing for this payload.

fallback
    Replace the failed payload with zero or more alternative payloads and
    continue processing downstream.

Usage (declaration side, no runtime import)
-------------------------------------------
::

    from sage.common.core.flow_exceptions import ExceptionDecision

    class MyErrorHandler:
        def handle(self, event):
            if event.error_type == "ValueError":
                return ExceptionDecision.fallback(value="default_value")
            return ExceptionDecision.propagate()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

__all__ = [
    "ExceptionAction",
    "ExceptionContext",
    "ExceptionEvent",
    "ExceptionDecision",
    "FlowException",
    "FlowDefinitionError",
]

# ---------------------------------------------------------------------------
# Error action literal type
# ---------------------------------------------------------------------------

ExceptionAction = Literal["propagate", "abort", "fallback"]
"""The three first-class exception handler decisions.

propagate
    Pass control to the next registered handler (or re-raise if none).

abort
    Discard the failed payload; stop processing this item silently.

fallback
    Replace the failed payload with zero or more alternative values and
    continue downstream processing.
"""


# ---------------------------------------------------------------------------
# Context and event descriptors (declaration-level data types)
# ---------------------------------------------------------------------------


@dataclass
class ExceptionContext:
    """Contextual metadata describing where and how an exception occurred.

    This is a **pure data type** — it holds only immutable execution-context
    fields and carries no runtime state.  Flownet populates these fields when
    constructing an ``ExceptionEvent`` during execution.

    Attributes:
        request_id: Unique identifier of the flow request that failed.
        phase: Execution phase label (e.g. ``"actor_call"``).
        actor_id: Optional actor identifier if the exception originated inside
            an actor call.
        method: Optional method name on the actor.
        address: Optional network address of the actor.
        transformation_id: Optional ID of the dataflow transformation node.
        payload_summary: Brief human-readable summary of the triggering payload
            (not the full payload, to stay backend-agnostic at L1).
        stack_depth: Depth of the flow stack frame at the time of the failure.
        metadata: Arbitrary string-keyed metadata for extensibility.
    """

    request_id: str
    phase: str
    actor_id: Optional[str] = None
    method: Optional[str] = None
    address: Optional[str] = None
    transformation_id: Optional[str] = None
    payload_summary: Optional[str] = None
    stack_depth: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExceptionEvent:
    """A snapshot of an exception during flow execution.

    Constructed by the runtime backend when an actor method raises; passed to
    registered exception handlers.

    Attributes:
        error_type: The class name of the original exception.
        message: Human-readable exception message.
        traceback: Full formatted traceback string.
        context: Execution context in which the exception occurred.
        error: The original ``BaseException`` object.  May be ``None`` when the
            event is deserialized across process boundaries.
    """

    error_type: str
    message: str
    traceback: str
    context: ExceptionContext
    error: Optional[BaseException] = None


# ---------------------------------------------------------------------------
# Handler decision type
# ---------------------------------------------------------------------------


@dataclass
class ExceptionDecision:
    """The decision returned by a flow exception handler.

    Create instances via the three static factory methods to ensure valid
    combinations of ``action`` and ``payloads``:

    .. code-block:: python

        # Discard the failed item silently
        ExceptionDecision.abort()

        # Continue to the next registered handler
        ExceptionDecision.propagate()

        # Replace the failed payload with a default value
        ExceptionDecision.fallback(value="default")

        # Replace the failed payload with nothing (empty stream item)
        ExceptionDecision.fallback()

    Attributes:
        action: One of ``"propagate"``, ``"abort"``, ``"fallback"``.
        payloads: For ``"fallback"`` actions only — zero or more replacement
            values.  Each element is forwarded to downstream operators as-is;
            the Flownet adapter wraps them in ``PayloadData`` internally.
            For non-fallback actions this field is ``None``.
        metadata: Arbitrary string-keyed metadata; the runtime may attach
            information such as ``retry_count``, ``handler_name``, etc.
    """

    action: ExceptionAction
    payloads: Optional[list[Any]] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience factory constructors
    # ------------------------------------------------------------------

    @staticmethod
    def abort(**metadata: Any) -> ExceptionDecision:
        """Create an *abort* decision — silently discard the failed payload."""
        return ExceptionDecision(action="abort", payloads=None, metadata=dict(metadata))

    @staticmethod
    def propagate(**metadata: Any) -> ExceptionDecision:
        """Create a *propagate* decision — defer to the next handler."""
        return ExceptionDecision(action="propagate", payloads=None, metadata=dict(metadata))

    @staticmethod
    def fallback(
        value: Optional[Any] = None,
        payloads: Optional[list[Any]] = None,
        **metadata: Any,
    ) -> ExceptionDecision:
        """Create a *fallback* decision — replace the failed payload.

        Args:
            value: A single replacement value.  Mutually exclusive with
                *payloads*.  Pass ``None`` (default) to produce an empty
                replacement (i.e. consume the item with no output).
            payloads: An explicit list of replacement values.  Use when you
                need to fan-out to multiple downstream items.
            **metadata: Arbitrary extra metadata attached to the decision.

        Returns:
            A ``ExceptionDecision`` with ``action="fallback"`` and the
            resolved replacement payloads.
        """
        if payloads is not None:
            resolved: list[Any] = payloads
        elif value is None:
            resolved = []
        else:
            resolved = [value]
        return ExceptionDecision(action="fallback", payloads=resolved, metadata=dict(metadata))


# ---------------------------------------------------------------------------
# SAGE-owned exception types
# ---------------------------------------------------------------------------


class FlowException(RuntimeError):
    """Raised by the runtime when an unhandled exception escapes a flow.

    This is the **application-facing** exception.  User code that calls
    ``run(my_pipeline, payload)`` will see a ``FlowException`` when the
    pipeline fails and no handler absorbed the error.

    Attributes:
        event: The ``ExceptionEvent`` that triggered this exception.
    """

    def __init__(self, event: ExceptionEvent) -> None:
        message = f"{event.error_type}: {event.message}"
        super().__init__(message)
        self.event = event


class FlowDefinitionError(RuntimeError):
    """Raised when a flow definition violates structural/return-sink semantics.

    This is a **declaration-time** error — it does not require a running
    runtime backend.

    Examples:
    - A ``@flow`` function does not return a ``DataStream``.
    - A handler is registered with an invalid type.
    """
