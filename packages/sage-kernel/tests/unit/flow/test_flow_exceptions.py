"""
Unit tests for exception contract migration — intellistream/SAGE#1434

Verifies the Acceptance Criteria (DoD) for Issue #1434:

  1. Unified error category model in SAGE (L1 sage-common).
  2. SAGE declaration-layer exception handler APIs (L3 sage-kernel).
  3. Error contracts are backend-agnostic (no Flownet types at L1/L3).
  4. Example pipeline demonstrates propagate/abort/fallback via SAGE API.

No ``sage.flownet.*`` import is allowed in this test file (verify that
contracts are truly backend-agnostic at L1 and L3 declaration level).
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_no_flownet_toplevel(module_name: str) -> None:
    """Assert that *module_name* has zero top-level Flownet imports."""
    import ast

    mod = importlib.import_module(module_name)
    src_file = getattr(mod, "__file__", None)
    if not src_file or not src_file.endswith(".py"):
        return
    with open(src_file) as fh:
        source = fh.read()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("sage.flownet"), (
                    f"{module_name} has top-level import of {alias.name!r}"
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not module.startswith("sage.flownet"), (
                f"{module_name} has top-level 'from {module} import ...' — "
                "L1/L3 must not import Flownet at module level."
            )


# ===========================================================================
# DoD #1 — Unified error category model in SAGE (L1 sage-common)
# ===========================================================================


class TestL1FlowExceptionContracts:
    """Verify that all portable contract types live in sage.common (L1)."""

    def test_exception_action_importable_from_l1(self):
        from sage.common.core.flow_exceptions import ExceptionAction

        assert ExceptionAction is not None

    def test_exception_context_importable_from_l1(self):
        from sage.common.core.flow_exceptions import ExceptionContext

        ctx = ExceptionContext(request_id="r1", phase="test")
        assert ctx.request_id == "r1"
        assert ctx.payload_summary is None  # backend-agnostic field

    def test_exception_event_importable_from_l1(self):
        from sage.common.core.flow_exceptions import ExceptionContext, ExceptionEvent

        ctx = ExceptionContext(request_id="r1", phase="test")
        event = ExceptionEvent(
            error_type="ValueError",
            message="bad value",
            traceback="<tb>",
            context=ctx,
        )
        assert event.error_type == "ValueError"
        assert event.error is None

    def test_exception_decision_abort(self):
        from sage.common.core.flow_exceptions import ExceptionDecision

        d = ExceptionDecision.abort()
        assert d.action == "abort"
        assert d.payloads is None

    def test_exception_decision_propagate(self):
        from sage.common.core.flow_exceptions import ExceptionDecision

        d = ExceptionDecision.propagate()
        assert d.action == "propagate"
        assert d.payloads is None

    def test_exception_decision_fallback_with_value(self):
        from sage.common.core.flow_exceptions import ExceptionDecision

        d = ExceptionDecision.fallback(value="default")
        assert d.action == "fallback"
        assert d.payloads == ["default"]

    def test_exception_decision_fallback_empty(self):
        from sage.common.core.flow_exceptions import ExceptionDecision

        d = ExceptionDecision.fallback()
        assert d.action == "fallback"
        assert d.payloads == []

    def test_exception_decision_fallback_multi_payloads(self):
        from sage.common.core.flow_exceptions import ExceptionDecision

        d = ExceptionDecision.fallback(payloads=["a", "b", "c"])
        assert d.action == "fallback"
        assert d.payloads == ["a", "b", "c"]

    def test_flow_exception_wraps_event(self):
        from sage.common.core.flow_exceptions import (
            ExceptionContext,
            ExceptionEvent,
            FlowException,
        )

        ctx = ExceptionContext(request_id="req1", phase="actor_call")
        event = ExceptionEvent(
            error_type="ZeroDivisionError",
            message="division by zero",
            traceback="...",
            context=ctx,
        )
        exc = FlowException(event)
        assert "ZeroDivisionError" in str(exc)
        assert exc.event is event

    def test_flow_definition_error(self):
        from sage.common.core.flow_exceptions import FlowDefinitionError

        with pytest.raises(FlowDefinitionError, match="bad definition"):
            raise FlowDefinitionError("bad definition")

    def test_l1_module_no_flownet_toplevel_imports(self):
        """L1 contract module must have zero top-level Flownet imports."""
        _assert_no_flownet_toplevel("sage.common.core.flow_exceptions")

    def test_l1_contracts_also_exported_from_sage_common_core(self):
        """Verify sage.common.core re-exports the new types."""
        from sage.common.core import ExceptionDecision, ExceptionEvent, FlowException

        assert ExceptionDecision is not None
        assert ExceptionEvent is not None
        assert FlowException is not None


# ===========================================================================
# DoD #2 — SAGE declaration-layer exception handler API (L3 sage-kernel)
# ===========================================================================


class TestL3ExceptionHandlerAPI:
    """Verify sage.kernel.flow exports the handler registration API."""

    def test_flow_exception_handler_importable_from_kernel_flow(self):
        from sage.kernel.flow import flow_exception_handler

        assert callable(flow_exception_handler)

    def test_exception_handler_alias_importable(self):
        from sage.kernel.flow import exception_handler

        assert callable(exception_handler)

    def test_register_exception_handler_hook_importable(self):
        from sage.kernel.flow import register_exception_handler_hook

        assert callable(register_exception_handler_hook)

    def test_exception_decision_importable_from_kernel_flow(self):
        """ExceptionDecision should be re-exported from sage.kernel.flow."""
        from sage.kernel.flow import ExceptionDecision

        assert ExceptionDecision.abort().action == "abort"

    def test_flow_exception_importable_from_kernel_flow(self):
        from sage.kernel.flow import FlowException

        assert issubclass(FlowException, RuntimeError)

    def test_exception_handler_module_no_flownet_toplevel(self):
        """sage.kernel.flow.exception_handler must not import Flownet at top-level."""
        _assert_no_flownet_toplevel("sage.kernel.flow.exception_handler")

    def test_kernel_flow_init_no_flownet_toplevel(self):
        """sage.kernel.flow __init__ must not import Flownet at top-level."""
        _assert_no_flownet_toplevel("sage.kernel.flow")

    def test_register_hook_validates_callables(self):
        from sage.kernel.flow.exception_handler import register_exception_handler_hook

        with pytest.raises(TypeError):
            register_exception_handler_hook("not_callable", lambda: None)

        with pytest.raises(TypeError):
            register_exception_handler_hook(lambda: None, "not_callable")

    def test_flow_exception_handler_requires_callable(self):
        """flow_exception_handler must raise FlowDefinitionError for non-callables."""
        from sage.common.core.flow_exceptions import FlowDefinitionError
        from sage.kernel.flow import flow_exception_handler

        # Register a dummy hook so the context manager gets past the hook check.
        from sage.kernel.flow.exception_handler import register_exception_handler_hook

        pushed: list[Any] = []
        register_exception_handler_hook(pushed.append, lambda: pushed.pop() if pushed else None)

        with pytest.raises(FlowDefinitionError):
            with flow_exception_handler(None):  # None is not callable
                pass

    def test_flow_exception_handler_context_manager_push_pop(self):
        """flow_exception_handler pushes/pops via registered hooks."""
        from sage.kernel.flow import flow_exception_handler
        from sage.kernel.flow.exception_handler import register_exception_handler_hook

        pushed: list[Any] = []

        def _push(h):
            pushed.append(h)

        def _pop():
            if pushed:
                pushed.pop()

        register_exception_handler_hook(_push, _pop)

        def my_handler(event):
            from sage.common.core.flow_exceptions import ExceptionDecision

            return ExceptionDecision.abort()

        assert len(pushed) == 0
        with flow_exception_handler(my_handler):
            assert len(pushed) == 1
            assert pushed[0] is my_handler
        assert len(pushed) == 0  # popped on exit

    def test_flow_exception_handler_pops_on_exception(self):
        """flow_exception_handler must pop even if an exception occurs inside."""
        from sage.kernel.flow import flow_exception_handler
        from sage.kernel.flow.exception_handler import register_exception_handler_hook

        pushed: list[Any] = []
        register_exception_handler_hook(pushed.append, lambda: pushed.pop() if pushed else None)

        def dummy_handler(event):
            pass

        with pytest.raises(RuntimeError, match="inside"), flow_exception_handler(dummy_handler):
            raise RuntimeError("inside")

        assert len(pushed) == 0  # should have been popped by finally block

    def test_no_runtime_needed_for_import(self):
        """Importing the exception contract types must not require a runtime."""
        # If sage.flownet is not installed, L1 and L3 types must still be importable.
        # We force this check by ensuring the import succeeds in a cold state.
        from sage.common.core.flow_exceptions import ExceptionDecision, ExceptionEvent
        from sage.kernel.flow import (
            ExceptionDecision as KD,
        )
        from sage.kernel.flow import (
            ExceptionEvent as KE,
        )

        assert ExceptionDecision is KD
        assert ExceptionEvent is KE


# ===========================================================================
# DoD #3 — Error contracts are backend-agnostic
# ===========================================================================


class TestBackendAgnosticContracts:
    """Verify the contract types have no runtime-backend fields or imports."""

    def test_exception_context_has_no_payload_data_field(self):
        """L1 ExceptionContext must NOT have a 'payload' field of PayloadData type."""
        import dataclasses

        from sage.common.core.flow_exceptions import ExceptionContext

        field_names = {f.name for f in dataclasses.fields(ExceptionContext)}
        # Should have payload_summary (string), NOT payload (PayloadData)
        assert "payload_summary" in field_names
        assert "payload" not in field_names

    def test_exception_decision_payloads_is_list_any(self):
        """ExceptionDecision.payloads should be list[Any], not list[PayloadData]."""
        from sage.common.core.flow_exceptions import ExceptionDecision

        d = ExceptionDecision.fallback(value=42)
        assert isinstance(d.payloads, list)
        # Value stored as-is (not wrapped in PayloadData)
        assert d.payloads[0] == 42

    def test_exception_decision_accepts_arbitrary_fallback_values(self):
        """ExceptionDecision.fallback should accept any Python value."""
        from sage.common.core.flow_exceptions import ExceptionDecision

        for value in [None, 0, "str", [], {}, object()]:
            if value is None:
                d = ExceptionDecision.fallback()
                assert d.payloads == []
            else:
                d = ExceptionDecision.fallback(value=value)
                assert d.payloads[0] is value

    def test_flow_exception_contains_no_ray_terminology(self):
        """FlowException must not have Ray-style terminology."""
        from sage.common.core.flow_exceptions import FlowException

        assert "ray" not in FlowException.__name__.lower()
        assert "ray" not in (FlowException.__doc__ or "").lower()
        assert "ray" not in (FlowException.__module__ or "").lower()

    def test_exception_decision_no_ray_terminology(self):
        """ExceptionDecision must not have Ray-style terminology."""
        from sage.common.core.flow_exceptions import ExceptionDecision

        assert "ray" not in ExceptionDecision.__name__.lower()
        for method_name in ("abort", "propagate", "fallback"):
            method = getattr(ExceptionDecision, method_name)
            assert "ray" not in (method.__doc__ or "").lower()


# ===========================================================================
# DoD #4 — Demonstrate propagate/abort/fallback via SAGE API (contract test)
# ===========================================================================


class TestExceptionDecisionPatterns:
    """Demonstrate the three decision patterns work correctly end-to-end."""

    def _run_handler_chain(self, event, handlers):
        """Simulate the Flownet exception resolver handler chain using only SAGE types."""
        from sage.common.core.flow_exceptions import ExceptionDecision

        for handler in reversed(handlers):
            decision = handler(event)
            if decision is None:
                continue
            assert isinstance(decision, ExceptionDecision), (
                f"Handler must return ExceptionDecision, got {type(decision)}"
            )
            if decision.action != "propagate":
                return decision
        return None  # All propagated or no handlers

    def _make_event(self, error_type: str = "ValueError", message: str = "oops"):
        from sage.common.core.flow_exceptions import ExceptionContext, ExceptionEvent

        ctx = ExceptionContext(request_id="req-test", phase="test")
        return ExceptionEvent(
            error_type=error_type,
            message=message,
            traceback="<test>",
            context=ctx,
        )

    def test_abort_pattern(self):
        """Handler returns abort — failed item is silently discarded."""
        from sage.common.core.flow_exceptions import ExceptionDecision

        def handler(event):
            return ExceptionDecision.abort()

        event = self._make_event()
        decision = self._run_handler_chain(event, [handler])
        assert decision is not None
        assert decision.action == "abort"

    def test_fallback_pattern(self):
        """Handler returns fallback — item replaced with default value."""
        from sage.common.core.flow_exceptions import ExceptionDecision

        def handler(event):
            return ExceptionDecision.fallback(value="DEFAULT")

        event = self._make_event()
        decision = self._run_handler_chain(event, [handler])
        assert decision is not None
        assert decision.action == "fallback"
        assert decision.payloads == ["DEFAULT"]

    def test_propagate_pattern(self):
        """Handler propagates — falls through to outer handler."""
        from sage.common.core.flow_exceptions import ExceptionDecision

        inner_results = []

        def inner_handler(event):
            inner_results.append("inner_called")
            return ExceptionDecision.propagate()

        def outer_handler(event):
            return ExceptionDecision.fallback(value="outer_fallback")

        event = self._make_event()
        # outer_handler first in list (handlers are reversed in chain)
        decision = self._run_handler_chain(event, [outer_handler, inner_handler])
        assert "inner_called" in inner_results
        assert decision is not None
        assert decision.action == "fallback"
        assert decision.payloads == ["outer_fallback"]

    def test_all_propagate_returns_none(self):
        """If all handlers propagate, the chain returns None (runtime re-raises)."""
        from sage.common.core.flow_exceptions import ExceptionDecision

        def always_propagate(event):
            return ExceptionDecision.propagate()

        event = self._make_event()
        decision = self._run_handler_chain(event, [always_propagate, always_propagate])
        assert decision is None

    def test_empty_handler_stack_returns_none(self):
        """No registered handlers -> returns None."""
        event = self._make_event()
        decision = self._run_handler_chain(event, [])
        assert decision is None

    def test_conditional_handler_pattern(self):
        """Handler decides based on error type (real-world pattern)."""
        from sage.common.core.flow_exceptions import ExceptionDecision

        def smart_handler(event):
            if event.error_type == "ZeroDivisionError":
                return ExceptionDecision.fallback(value=0)
            if event.error_type == "ConnectionError":
                return ExceptionDecision.abort()
            return ExceptionDecision.propagate()

        # ZeroDivisionError -> fallback with 0
        event = self._make_event("ZeroDivisionError", "division by zero")
        d = self._run_handler_chain(event, [smart_handler])
        assert d.action == "fallback"
        assert d.payloads == [0]

        # ConnectionError -> abort
        event = self._make_event("ConnectionError", "timeout")
        d = self._run_handler_chain(event, [smart_handler])
        assert d.action == "abort"

        # Unknown error -> propagate -> None
        event = self._make_event("UnknownError", "???")
        d = self._run_handler_chain(event, [smart_handler])
        assert d is None
