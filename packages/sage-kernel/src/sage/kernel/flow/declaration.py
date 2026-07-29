"""
sage.kernel.flow.declaration - SAGE L3 Flow Declaration Abstractions

Layer: L3 (sage-kernel DSL layer)
Dependencies: sage.common (L1) only — NO sage.platform, NO Flownet runtime imports.

This module is the **SAGE canonical owner** of compile-time flow topology declarations.
It defines the abstract contract for what a flow declaration *is* (structure, validation),
without any runtime execution semantics.

Key design decisions:
- ``FlowDeclaration`` is a pure data descriptor — it holds a reference to the user-provided
  flow function and its compile-time metadata. It has NO connection to Flownet runtime objects.
- ``FlowGraphValidator`` codifies declaration-time constraint rules independent of any
  runtime backend. New validators can be added here; the Flownet runtime must call them.
- ``FlowDeclarationError`` is the SAGE-owned error type for compile-time violations.

Migration context (intellistream/SAGE#1430, #1431):
  - These classes were previously implicit in sageFlownet/src/sage/flownet/compiler/flow_def.py.
  - SAGE now owns the **declaration surface**; Flownet continues to own execution semantics.
  - Flownet's FlowDef wraps / delegates to these abstractions at compile time.

No legacy runtime-oriented concepts are present here.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Declaration-time error type
# ---------------------------------------------------------------------------


class FlowDeclarationError(Exception):
    """Raised when a flow declaration violates structural constraints.

    This is a SAGE-owned, compile-time error and has no dependency on the
    Flownet runtime.  It should be raised during graph construction / validation,
    before any execution attempt.

    Examples of situations that raise ``FlowDeclarationError``:
    - A flow function returns an unsupported type.
    - A ``pipe()`` sub-flow has no return stream but downstream operators exist.
    - A ``FlowDeclaration`` is created with an invalid function signature.
    """


# ---------------------------------------------------------------------------
# Immutable compile-time metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FlowFunctionMeta:
    """Immutable metadata extracted from a flow function at declaration time.

    Attributes:
        name: Qualified name of the flow function (``__qualname__``).
        is_method: ``True`` when the function is decorated as a class method
            (i.e. it expects ``self`` as first argument before ``init_stream``).
        module: Module where the flow function is defined.
        annotations: Raw type annotations of the original function.
    """

    name: str
    is_method: bool
    module: str
    annotations: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_function(cls, func: Callable) -> FlowFunctionMeta:
        """Extract compile-time metadata from *func*."""
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        # A flow method has (self, init_stream, ...) signature
        is_method = len(params) >= 1 and params[0] == "self"
        return cls(
            name=getattr(func, "__qualname__", func.__name__),
            is_method=is_method,
            module=getattr(func, "__module__", "<unknown>"),
            annotations=dict(getattr(func, "__annotations__", {})),
        )


# ---------------------------------------------------------------------------
# Core declaration descriptor
# ---------------------------------------------------------------------------


class FlowDeclaration:
    """SAGE L3 compile-time descriptor for a flow program.

    ``FlowDeclaration`` is the **SAGE canonical representation** of a declared
    flow.  It is created by the ``@flow`` decorator and stores the user function
    plus its compile-time metadata.

    Design constraints (per migration boundary, intellistream/SAGE#1430):
    - This class has **no runtime dependency** — it does not import any Flownet
      runtime module at class definition time.
    - It does not execute user code.  Execution is delegated to the Flownet
      runtime adapter (``FlownetAdapter``) which wraps a ``FlowDeclaration``.
    - It is safe to import and instantiate in environments where Flownet is not
      installed (e.g. pure unit tests of declaration semantics).

    Typical lifecycle:
    1. User decorates a function/method with ``@flow`` → ``FlowDeclaration`` is
       created and returned (replacing the original function).
    2. When the Flownet runtime is configured, a ``FlownetAdapter`` wraps this
       declaration and provides execution semantics (``compile()``, ``call()``,
       ``submit()``, ``put()``, ``open()``).
    3. Users invoke the flow through the adapter (or through SAGE facade APIs).
    """

    def __init__(self, func: Callable, *, static: bool = False):
        """
        Args:
            func: The decorated flow function.  Must accept ``init_stream`` as
                  its first positional parameter (or second, if ``self`` is first
                  for a method flow).
            static: Internal flag; ``True`` when the flow is decorated at
                    module (static) level rather than as a class method.
        """
        if not callable(func):
            raise FlowDeclarationError(f"@flow expects a callable, got {type(func)!r}")
        self._func = func
        self._static = static
        self._meta = FlowFunctionMeta.from_function(func)
        # Preserve function identity attributes for introspection.
        self.__name__ = func.__name__
        self.__qualname__ = func.__qualname__
        self.__module__ = func.__module__
        self.__doc__ = func.__doc__
        self.__wrapped__ = func

    # ------------------------------------------------------------------
    # Public read-only accessors
    # ------------------------------------------------------------------

    @property
    def func(self) -> Callable:
        """The original flow function (un-decorated)."""
        return self._func

    @property
    def meta(self) -> FlowFunctionMeta:
        """Compile-time metadata for this flow declaration."""
        return self._meta

    @property
    def name(self) -> str:
        """Qualified name of the declared flow."""
        return self._meta.name

    @property
    def is_method(self) -> bool:
        """``True`` when this declaration was created from a class method."""
        return self._meta.is_method

    # ------------------------------------------------------------------
    # Descriptor protocol — allow @flow on class methods
    # ------------------------------------------------------------------

    def __get__(
        self, obj: Any, objtype: type | None = None
    ) -> FlowDeclaration | _BoundFlowDeclaration:
        """Return a bound view when accessed as an instance attribute."""
        if obj is None:
            return self
        return _BoundFlowDeclaration(self, obj)

    # ------------------------------------------------------------------
    # Runtime delegation (requires Flownet backend)
    # ------------------------------------------------------------------

    def _require_adapter(self) -> Any:
        """Return the Flownet runtime adapter for this declaration.

        This is a lazy import: it only pulls in Flownet when actually needed
        for execution.  Declaration-time operations (validation, metadata
        inspection) work without Flownet being installed.

        Raises:
            ImportError: If ``sageFlownet`` is not installed.
            RuntimeError: If the Flownet runtime has not been configured yet.
        """
        try:
            from sage.flownet.compiler.flow_def import FlowDef as _FlownetFlowDef
        except ImportError as exc:
            raise ImportError(
                "Executing a flow requires sageFlownet to be installed. "
                "Install it with: pip install isage-flownet\n"
                f"Original error: {exc}"
            ) from exc
        # Lazy-create the Flownet adapter; cache it on this declaration object
        # using a private attribute to avoid polluting the public interface.
        adapter_attr = "_flownet_adapter"
        adapter = getattr(self, adapter_attr, None)
        if adapter is None:
            adapter = _FlownetFlowDef(self._func, static=self._static)
            object.__setattr__(self, adapter_attr, adapter) if hasattr(
                self, "__slots__"
            ) else setattr(self, adapter_attr, adapter)
        return adapter

    def compile(self) -> Any:
        """Compile this flow declaration into a ``FlowTask`` (Flownet runtime).

        Requires sageFlownet to be installed.
        """
        return self._require_adapter().compile()

    def call(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the flow synchronously and return results (Flownet runtime)."""
        return self._require_adapter().call(*args, **kwargs)

    def submit(self, *args: Any, **kwargs: Any) -> Any:
        """Submit the flow for asynchronous execution (Flownet runtime)."""
        return self._require_adapter().submit(*args, **kwargs)

    def put(self, *args: Any, **kwargs: Any) -> None:
        """Fire-and-forget execution (Flownet runtime)."""
        self._require_adapter().put(*args, **kwargs)

    def open(self) -> Any:
        """Open a pipe for streaming I/O (Flownet runtime)."""
        return self._require_adapter().open()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.call(*args, **kwargs)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"FlowDeclaration(name={self.name!r}, "
            f"is_method={self.is_method}, "
            f"module={self._meta.module!r})"
        )


class _BoundFlowDeclaration:
    """A ``FlowDeclaration`` bound to a specific instance (class method case).

    This mirrors how Python's bound method works: when you access a flow
    method via ``instance.my_flow``, you get a ``_BoundFlowDeclaration``
    that pre-fills ``self`` when delegating to the Flownet adapter.
    """

    def __init__(self, declaration: FlowDeclaration, instance: Any):
        self._declaration = declaration
        self._instance = instance

    def _require_adapter(self) -> Any:
        adapter = self._declaration._require_adapter()
        # Return Flownet BoundFlow for this instance
        bound = adapter.__get__(self._instance, type(self._instance))
        return bound

    def compile(self) -> Any:
        return self._require_adapter().compile()

    def call(self, *args: Any, **kwargs: Any) -> Any:
        return self._require_adapter().call(*args, **kwargs)

    def submit(self, *args: Any, **kwargs: Any) -> Any:
        return self._require_adapter().submit(*args, **kwargs)

    def put(self, *args: Any, **kwargs: Any) -> None:
        self._require_adapter().put(*args, **kwargs)

    def open(self) -> Any:
        return self._require_adapter().open()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.call(*args, **kwargs)

    def __repr__(self) -> str:
        return (
            f"_BoundFlowDeclaration(declaration={self._declaration!r}, instance={self._instance!r})"
        )


# ---------------------------------------------------------------------------
# Declaration-time graph validator
# ---------------------------------------------------------------------------


class FlowGraphValidator:
    """Declaration-time structural validator for flow graphs.

    ``FlowGraphValidator`` is the SAGE-owned location for *compile-time*
    constraint rules.  It validates that a flow function declaration meets
    structural requirements **before** any execution is attempted.

    This validator operates purely on ``FlowDeclaration`` metadata and does
    not execute user code.  The Flownet runtime may call it during ``compile()``
    to enforce SAGE-level constraints in addition to its own checks.

    Usage::

        validator = FlowGraphValidator()
        validator.validate(my_flow_declaration)  # raises FlowDeclarationError on violation

    To add a project-specific rule, subclass and override ``_extra_rules``::

        class MyValidator(FlowGraphValidator):
            def _extra_rules(self, decl: FlowDeclaration) -> None:
                if not decl.name.startswith("my_prefix_"):
                    raise FlowDeclarationError("Flow name must start with my_prefix_")
    """

    def validate(self, declaration: FlowDeclaration) -> None:
        """Run all structural validators against *declaration*.

        Args:
            declaration: The ``FlowDeclaration`` to check.

        Raises:
            FlowDeclarationError: On the first validation failure encountered.
            TypeError: If *declaration* is not a ``FlowDeclaration`` instance.
        """
        if not isinstance(declaration, FlowDeclaration):
            raise TypeError(f"Expected FlowDeclaration, got {type(declaration)!r}")
        self._check_callable(declaration)
        self._check_init_stream_param(declaration)
        self._extra_rules(declaration)

    # ------------------------------------------------------------------
    # Built-in rules (call order matters — cheapest first)
    # ------------------------------------------------------------------

    @staticmethod
    def _check_callable(declaration: FlowDeclaration) -> None:
        if not callable(declaration.func):
            raise FlowDeclarationError(
                f"Flow function must be callable, got {type(declaration.func)!r}."
            )

    @staticmethod
    def _check_init_stream_param(declaration: FlowDeclaration) -> None:
        """Ensure the flow function has the required ``init_stream`` parameter."""
        sig = inspect.signature(declaration.func)
        params = list(sig.parameters.keys())
        # For method flows: (self, init_stream, ...)
        # For static flows: (init_stream, ...)
        expected_pos = 1 if declaration.is_method else 0
        if len(params) <= expected_pos:
            raise FlowDeclarationError(
                f"Flow function '{declaration.name}' must accept 'init_stream' as "
                f"{'second' if declaration.is_method else 'first'} positional parameter. "
                f"Got params: {params}"
            )

    def _extra_rules(self, declaration: FlowDeclaration) -> None:
        """Override in subclasses to add project-specific validation rules."""


# ---------------------------------------------------------------------------
# Public re-exports
# ---------------------------------------------------------------------------

__all__ = [
    "FlowDeclaration",
    "FlowFunctionMeta",
    "FlowGraphValidator",
    "FlowDeclarationError",
    "_BoundFlowDeclaration",
]
