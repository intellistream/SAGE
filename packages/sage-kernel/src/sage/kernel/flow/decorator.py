"""
sage.kernel.flow.decorator - @flow decorator (SAGE canonical entry point)

Layer: L3 (sage-kernel DSL layer)
Dependencies: sage.kernel.flow.declaration — NO runtime imports.

This module provides the ``@flow`` decorator, which is the **SAGE-canonical**
entry point for declaring flow programs.  It replaces the Flownet-internal
``sage.flownet.api.flow()`` as the public user-facing API.

Migration context (intellistream/SAGE#1431):
  Prior to this migration, users imported ``@flow`` from ``sage.flownet.api``.
  After this migration the canonical import is::

      from sage.kernel.flow import flow   # SAGE L3 canonical
      # or equivalently:
      from sage.kernel.flow.decorator import flow

  The Flownet package continues to expose ``sage.flownet.api.flow`` for its own
  internal use, but that path is **not** the public user-facing API.

Usage examples::

    # Static (module-level) flow
    from sage.kernel.flow import flow

    @flow
    def my_pipeline(init_stream):
        return init_stream.map(my_actor.process)

    result = my_pipeline.call(payload)

    # Class-method flow
    class MyService:
        @flow
        def handle(self, init_stream):
            return init_stream.map(self.actor.process)

    svc = MyService()
    results = svc.handle.call(payload)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, overload

from sage.kernel.flow.declaration import FlowDeclaration

# ---------------------------------------------------------------------------
# @flow decorator
# ---------------------------------------------------------------------------


@overload
def flow(func: Callable) -> FlowDeclaration: ...


@overload
def flow(*, static: bool = True) -> Callable[[Callable], FlowDeclaration]: ...


def flow(func: Callable | None = None, *, static: bool = True) -> Any:
    """SAGE L3 ``@flow`` decorator — declares a function as a flow program.

    The decorator wraps the target function in a ``FlowDeclaration``, which
    is the SAGE-owned compile-time descriptor for a flow program.  Actual
    execution is delegated to the Flownet runtime backend.

    Can be used in two forms:

    **Bare decorator**::

        @flow
        def my_pipeline(init_stream):
            return init_stream.map(actor.process)

    **Parameterised decorator** (reserved for future options)::

        @flow(static=True)
        def my_pipeline(init_stream):
            ...

    Args:
        func:   The flow function to wrap.  If ``None``, returns a partial
                decorator (parameterised form).
        static: Internal hint; ``True`` for module-level (static) flows.
                Class methods set this implicitly.  You should not normally
                need to set this explicitly.

    Returns:
        A ``FlowDeclaration`` instance that:
        - Can be called directly (``my_pipeline(payload)``) to execute via Flownet.
        - Exposes ``compile()``, ``call()``, ``submit()``, ``put()``, ``open()``
          methods that delegate to Flownet at runtime.
        - Works as a Python descriptor so ``@flow`` works on class methods.

    Raises:
        FlowDeclarationError: If the decorated function violates declaration rules.

    Declaration-time validation is performed eagerly (at decoration time), so
    structural errors are caught as early as possible.
    """
    from sage.kernel.flow.declaration import FlowGraphValidator

    def _make_declaration(fn: Callable) -> FlowDeclaration:
        decl = FlowDeclaration(fn, static=static)
        # Run declaration-time validation immediately so errors surface at
        # decoration time rather than at first execution.
        FlowGraphValidator().validate(decl)
        return decl

    if func is not None:
        # Bare @flow usage
        return _make_declaration(func)

    # Parameterised @flow(...) usage
    def decorator(fn: Callable) -> FlowDeclaration:
        return _make_declaration(fn)

    return decorator


__all__ = ["flow"]
