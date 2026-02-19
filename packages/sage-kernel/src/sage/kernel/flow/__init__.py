"""
sage.kernel.flow - SAGE L3 Flow Declaration Layer

Layer: L3 (sage-kernel, DSL / Interface)
Dependencies: sage.common (L1), sage.platform (L2) -- NO runtime core dependency allowed.

This sub-package is the **SAGE canonical owner** of application-level flow declaration
semantics, per the Flownet->SAGE migration boundary (intellistream/SAGE#1430, #1431).

What lives here (declaration / API / protocol abstraction):
  - ``@flow`` decorator entry point (``sage.kernel.flow.flow``)
  - ``FlowDeclaration`` - pure compile-time topology descriptor
  - ``FlowGraphValidator`` - declaration-time validation rules
  - ``FlowRef`` / ``FlowDSL`` - public typing contracts for flow composition
  - ``FlowDeclarationError`` - declaration-time exception type
  - ``flow_exception_handler`` - handler registration context manager (Issue #1434)
  - ``ExceptionDecision`` / ``ExceptionEvent`` - portable error contracts (Issue #1434)

What does NOT live here (runtime core, stays in Flownet):
  - Execution loop / request-advancing engine
  - Actor runtime lifecycle / dispatch implementation
  - Transport stack (TCP/UDS/SHM)
  - Cluster gossip / membership / node control internals

Migration reference:
  - Boundary doc: sage-docs/docs_src/concepts/architecture/design-decisions/flownet-migration-boundary.md
  - GitHub issues: intellistream/SAGE#1431, #1434
"""

# Re-export portable exception contract types from L1 for convenience.
# User code can import directly from sage.common.core.flow_exceptions or
# use these re-exports from sage.kernel.flow.
from sage.common.core.flow_exceptions import (
    ExceptionAction,
    ExceptionContext,
    ExceptionDecision,
    ExceptionEvent,
    FlowDefinitionError,
    FlowException,
)
from sage.kernel.flow.declaration import (
    FlowDeclaration,
    FlowDeclarationError,
    FlowGraphValidator,
)
from sage.kernel.flow.decorator import flow
from sage.kernel.flow.exception_handler import (
    exception_handler,
    flow_exception_handler,
    register_exception_handler_hook,
)

__all__ = [
    # Flow DSL
    "flow",
    "FlowDeclaration",
    "FlowGraphValidator",
    "FlowDeclarationError",
    # Exception handler API (Issue #1434)
    "flow_exception_handler",
    "exception_handler",
    "register_exception_handler_hook",
    # Portable exception contract types (re-exported from L1)
    "ExceptionAction",
    "ExceptionContext",
    "ExceptionEvent",
    "ExceptionDecision",
    "FlowException",
    "FlowDefinitionError",
]
