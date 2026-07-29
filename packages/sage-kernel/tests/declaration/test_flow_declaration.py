"""
Unit tests for sage.kernel.flow — SAGE L3 Flow Declaration Layer.

These tests intentionally avoid importing any Flownet runtime modules.
They verify the Acceptance Criteria for intellistream/SAGE#1431:

  DoD #1: Declaration layer unit tests run without runtime-core dependency.
  DoD #2: Public declaration APIs contain no Ray-style concepts.
  DoD #3: SAGE declaration APIs are documented as canonical.

No ``sage.flownet.*`` import is allowed in this test file.
"""

import importlib
import sys

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _no_flownet_imports(module_name: str) -> None:
    """Assert that *module_name* does not have module-level Flownet imports.

    Only top-level (module-scope) imports are checked.  Lazy imports inside
    function/method bodies are explicitly allowed and expected.
    """
    mod = importlib.import_module(module_name)
    src_file = getattr(mod, "__file__", None)
    if src_file is None or not src_file.endswith(".py"):
        return
    with open(src_file) as fh:
        source = fh.read()
    import ast

    tree = ast.parse(source)
    # Only iterate over **top-level** nodes in the module body, not recursively
    # into function/class bodies, so lazy imports inside methods are allowed.
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("sage.flownet"), (
                    f"Module {module_name!r} has a top-level import of "
                    f"{alias.name!r} — runtime imports must be lazy (inside functions)."
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not module.startswith("sage.flownet"), (
                f"Module {module_name!r} has a top-level 'from {module} import ...' — "
                "runtime imports must be lazy (inside functions)."
            )


# ---------------------------------------------------------------------------
# Test: no static Flownet imports at module level
# ---------------------------------------------------------------------------


class TestNoStaticFlownetImports:
    """Verify the declaration modules have zero static Flownet dependencies."""

    def test_declaration_module_no_static_flownet(self):
        _no_flownet_imports("sage.kernel.flow.declaration")

    def test_decorator_module_no_static_flownet(self):
        _no_flownet_imports("sage.kernel.flow.decorator")

    def test_flow_package_no_static_flownet(self):
        _no_flownet_imports("sage.kernel.flow")


# ---------------------------------------------------------------------------
# Test: FlowDeclarationError
# ---------------------------------------------------------------------------


class TestFlowDeclarationError:
    def test_is_exception(self):
        from sage.kernel.flow import FlowDeclarationError

        assert issubclass(FlowDeclarationError, Exception)

    def test_can_be_raised_and_caught(self):
        from sage.kernel.flow import FlowDeclarationError

        with pytest.raises(FlowDeclarationError, match="test error"):
            raise FlowDeclarationError("test error")

    def test_no_ray_concepts_in_name(self):
        """Verify no Ray-style terminology is present in the error class."""
        from sage.kernel.flow import FlowDeclarationError

        assert "ray" not in FlowDeclarationError.__name__.lower()
        assert "ray" not in (FlowDeclarationError.__doc__ or "").lower()


# ---------------------------------------------------------------------------
# Test: FlowFunctionMeta
# ---------------------------------------------------------------------------


class TestFlowFunctionMeta:
    def test_from_static_function(self):
        from sage.kernel.flow.declaration import FlowFunctionMeta

        def my_flow(init_stream):
            pass

        meta = FlowFunctionMeta.from_function(my_flow)
        # meta.name is __qualname__ which includes the enclosing class/function scope
        assert meta.name.endswith("my_flow")
        assert meta.is_method is False
        assert meta.module == __name__

    def test_from_method_function(self):
        from sage.kernel.flow.declaration import FlowFunctionMeta

        def my_method(self, init_stream):
            pass

        meta = FlowFunctionMeta.from_function(my_method)
        assert meta.is_method is True

    def test_frozen_dataclass(self):
        from sage.kernel.flow.declaration import FlowFunctionMeta

        def f(init_stream):
            pass

        meta = FlowFunctionMeta.from_function(f)
        with pytest.raises((AttributeError, TypeError)):
            meta.name = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Test: FlowDeclaration
# ---------------------------------------------------------------------------


class TestFlowDeclaration:
    def test_basic_creation(self):
        from sage.kernel.flow.declaration import FlowDeclaration

        def my_flow(init_stream):
            pass

        decl = FlowDeclaration(my_flow)
        # decl.name is __qualname__ which may include enclosing scope prefix
        assert decl.name.endswith("my_flow")
        assert decl.__name__ == "my_flow"  # __name__ is always the unqualified name
        assert decl.is_method is False
        assert decl.func is my_flow

    def test_method_detection(self):
        from sage.kernel.flow.declaration import FlowDeclaration

        def handle(self, init_stream):
            pass

        decl = FlowDeclaration(handle)
        assert decl.is_method is True

    def test_preserves_identity_attributes(self):
        from sage.kernel.flow.declaration import FlowDeclaration

        def documented_flow(init_stream):
            """My flow docs."""

        decl = FlowDeclaration(documented_flow)
        assert decl.__name__ == "documented_flow"
        assert decl.__doc__ == "My flow docs."
        assert decl.__wrapped__ is documented_flow

    def test_rejects_non_callable(self):
        from sage.kernel.flow.declaration import FlowDeclaration, FlowDeclarationError

        with pytest.raises(FlowDeclarationError):
            FlowDeclaration("not a function")  # type: ignore[arg-type]

    def test_repr_has_no_ray_concepts(self):
        from sage.kernel.flow.declaration import FlowDeclaration

        def my_simple_func(init_stream):
            pass

        decl = FlowDeclaration(my_simple_func)
        r = repr(decl)
        # The repr should contain FlowDeclaration but must not mention ray as a
        # standalone concept.  We check it doesn't appear as a word boundary
        # to avoid false positives from unrelated substrings (e.g. module paths).
        import re

        assert not re.search(r"\bray\b", r.lower()), f"Ray-style concept found in repr: {r!r}"
        assert "FlowDeclaration" in r

    def test_descriptor_returns_bound_on_instance(self):
        from sage.kernel.flow.declaration import FlowDeclaration, _BoundFlowDeclaration

        def handle(self, init_stream):
            pass

        class MyClass:
            method = FlowDeclaration(handle)

        obj = MyClass()
        bound = obj.method
        assert isinstance(bound, _BoundFlowDeclaration)

    def test_descriptor_returns_declaration_on_class(self):
        from sage.kernel.flow.declaration import FlowDeclaration

        def handle(self, init_stream):
            pass

        class MyClass:
            method = FlowDeclaration(handle)

        assert isinstance(MyClass.method, FlowDeclaration)

    def test_execution_requires_flownet_raises_import_error_when_absent(self, monkeypatch):
        """When sageFlownet is not installed, calling a flow raises ImportError."""
        from sage.kernel.flow.declaration import FlowDeclaration

        def my_flow(init_stream):
            pass

        decl = FlowDeclaration(my_flow)

        # Temporarily hide sage.flownet from the import system
        # Remove any already-imported sage.flownet modules
        hidden = {k: v for k, v in sys.modules.items() if k.startswith("sage.flownet")}
        for k in hidden:
            sys.modules.pop(k, None)

        # Also block further imports
        class _BlockFlownet(importlib.abc.MetaPathFinder):
            def find_module(self, name, path=None):  # type: ignore[override]
                if name.startswith("sage.flownet"):
                    raise ImportError("Simulated missing sageFlownet")
                return None

        blocker = _BlockFlownet()
        sys.meta_path.insert(0, blocker)
        # Clear cached adapter
        if hasattr(decl, "_flownet_adapter"):
            del decl._flownet_adapter

        try:
            with pytest.raises(ImportError, match="sageFlownet"):
                decl.compile()
        finally:
            sys.meta_path.remove(blocker)
            # Restore hidden modules
            sys.modules.update(hidden)


# ---------------------------------------------------------------------------
# Test: FlowGraphValidator
# ---------------------------------------------------------------------------


class TestFlowGraphValidator:
    def test_valid_static_flow(self):
        from sage.kernel.flow.declaration import FlowDeclaration, FlowGraphValidator

        def my_flow(init_stream):
            pass

        decl = FlowDeclaration(my_flow)
        validator = FlowGraphValidator()
        validator.validate(decl)  # should not raise

    def test_valid_method_flow(self):
        from sage.kernel.flow.declaration import FlowDeclaration, FlowGraphValidator

        def handle(self, init_stream):
            pass

        decl = FlowDeclaration(handle)
        validator = FlowGraphValidator()
        validator.validate(decl)  # should not raise

    def test_invalid_missing_init_stream(self):
        """A flow function with no parameters should fail validation."""
        from sage.kernel.flow.declaration import (
            FlowDeclaration,
            FlowDeclarationError,
            FlowGraphValidator,
        )

        # Bypass decorator validation to test validator directly
        def bad_flow():  # missing init_stream
            pass

        # Manually bypass FlowGraphValidator in FlowDeclaration constructor
        # by patching to avoid validation during construction
        class BypassDeclaration(FlowDeclaration):
            def __init__(self, func):
                # Call object.__init__ to skip FlowDeclaration's validation
                object.__init__(self)
                self._func = func
                self._static = True
                from sage.kernel.flow.declaration import FlowFunctionMeta

                self._meta = FlowFunctionMeta.from_function(func)
                self.__name__ = func.__name__
                self.__qualname__ = func.__qualname__
                self.__module__ = func.__module__
                self.__doc__ = func.__doc__
                self.__wrapped__ = func

        decl = BypassDeclaration(bad_flow)
        validator = FlowGraphValidator()
        with pytest.raises(FlowDeclarationError, match="init_stream"):
            validator.validate(decl)

    def test_rejects_non_declaration(self):
        from sage.kernel.flow.declaration import FlowGraphValidator

        validator = FlowGraphValidator()
        with pytest.raises(TypeError):
            validator.validate("not a declaration")  # type: ignore[arg-type]

    def test_extra_rules_subclass(self):
        """Subclassing allows adding custom project-specific rules."""
        from sage.kernel.flow.declaration import (
            FlowDeclaration,
            FlowDeclarationError,
            FlowGraphValidator,
        )

        class StrictValidator(FlowGraphValidator):
            def _extra_rules(self, decl: FlowDeclaration) -> None:
                # Use __name__ (unqualified) rather than qualname which may include
                # the test class/method prefix in the function name.
                if not decl.__name__.startswith("allowed_"):
                    raise FlowDeclarationError(
                        f"Flow name must start with 'allowed_', got {decl.__name__!r}"
                    )

        def allowed_flow(init_stream):
            pass

        def forbidden_flow(init_stream):
            pass

        ok_decl = FlowDeclaration(allowed_flow)
        bad_decl = FlowDeclaration(forbidden_flow)
        v = StrictValidator()
        v.validate(ok_decl)  # OK
        with pytest.raises(FlowDeclarationError, match="allowed_"):
            v.validate(bad_decl)


# ---------------------------------------------------------------------------
# Test: @flow decorator
# ---------------------------------------------------------------------------


class TestFlowDecorator:
    def test_bare_decorator_returns_declaration(self):
        from sage.kernel.flow import FlowDeclaration
        from sage.kernel.flow.decorator import flow

        @flow
        def my_flow(init_stream):
            pass

        assert isinstance(my_flow, FlowDeclaration)

    def test_parameterised_decorator_returns_declaration(self):
        from sage.kernel.flow import FlowDeclaration
        from sage.kernel.flow.decorator import flow

        @flow(static=True)
        def my_flow(init_stream):
            pass

        assert isinstance(my_flow, FlowDeclaration)

    def test_method_decoration(self):
        from sage.kernel.flow import FlowDeclaration
        from sage.kernel.flow.decorator import flow

        class MyService:
            @flow
            def handle(self, init_stream):
                pass

        assert isinstance(MyService.handle, FlowDeclaration)
        assert MyService.handle.is_method

    def test_decorator_runs_validation_eagerly(self):
        """@flow should raise FlowDeclarationError at decoration time for invalid functions."""
        from sage.kernel.flow import FlowDeclarationError
        from sage.kernel.flow.decorator import flow

        with pytest.raises(FlowDeclarationError):

            @flow
            def bad():  # missing init_stream → validation error
                pass

    def test_no_ray_terminology_in_module(self):
        """The decorator module must not contain Ray-style public names."""
        import sage.kernel.flow.decorator as dmod

        public_names = [name for name in dir(dmod) if not name.startswith("_")]
        for name in public_names:
            assert "ray" not in name.lower(), (
                f"Ray-style name {name!r} found in sage.kernel.flow.decorator"
            )

    def test_package_level_import(self):
        """``from sage.kernel.flow import flow`` must work."""
        from sage.kernel.flow import flow  # noqa: F401

        assert callable(flow)

    def test_kernel_package_exports(self):
        """sage.kernel must expose FlowDeclaration and FlowDeclarationError."""
        import sage.kernel as kernel

        assert hasattr(kernel, "FlowDeclaration")
        assert hasattr(kernel, "FlowDeclarationError")
        assert hasattr(kernel, "FlowGraphValidator")
