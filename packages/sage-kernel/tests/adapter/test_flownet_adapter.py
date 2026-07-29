"""
Adapter integration tests: SAGE L3 → L2 → sageFlownet boundary.

Layer 3 of the 3-layer test taxonomy — intellistream/SAGE#1440.

DoD coverage
============
Issue 1440 acceptance criteria:
  AC-1: Each layer has independent CI signal.
        → This file is the Layer 3 test suite; CI runs it as a separate job.
  AC-2: Boundary regressions are detectable via contract tests.
        → TestAdapterProtocolConformance validates the structural contract.
  AC-3: Test docs explain where to add future tests.
        → See docs_src/developers/test-taxonomy.md in sage-docs.

Also covers Issue 1433 (Runtime Protocol Interface) integration path:
  DoD: No direct Flownet-internal imports from SAGE kernel dispatch path.
  DoD: Adapter integration tests validate end-to-end execution.

When sageFlownet is not installed, tests that need a live runtime are
automatically skipped via the ``requires_sageflownet`` marker.  The
structural / contract tests run regardless.
"""

from __future__ import annotations

import importlib
import sys

import pytest

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_SAGEFLOWNET_AVAILABLE = importlib.util.find_spec("sage.flownet") is not None


def _skip_if_no_flownet(test_fn=None):
    """Decorator: skip test when sageFlownet is not available."""
    marker = pytest.mark.skipif(
        not _SAGEFLOWNET_AVAILABLE,
        reason="sageFlownet (isage-flow) is not installed — skipping live adapter test",
    )
    if test_fn is not None:
        return marker(test_fn)
    return marker


# ===========================================================================
# Suite 1: Structural protocol conformance (no live runtime required)
# ===========================================================================


class TestAdapterProtocolConformance:
    """Verify that FlownetRuntimeAdapter structurally conforms to
    RuntimeBackendProtocol WITHOUT requiring a live sageFlownet runtime.

    These tests are the primary boundary regression guard: if someone changes
    the RuntimeBackendProtocol abstract surface (Issue #1433 contract) without
    updating the adapter, these tests will fail.

    They run on every PR independent of sageFlownet availability.
    """

    def test_adapter_is_subclass_of_runtime_backend_protocol(self):
        """FlownetRuntimeAdapter must be a subclass of RuntimeBackendProtocol."""
        from sage.platform.runtime.adapters.flownet_adapter import FlownetRuntimeAdapter
        from sage.platform.runtime.protocol import RuntimeBackendProtocol

        assert issubclass(FlownetRuntimeAdapter, RuntimeBackendProtocol), (
            "FlownetRuntimeAdapter must subclass RuntimeBackendProtocol — "
            "boundary regression detected (intellistream/SAGE#1433)."
        )

    def test_adapter_implements_all_abstract_methods(self):
        """FlownetRuntimeAdapter must implement every abstract method declared
        in RuntimeBackendProtocol so that it can be instantiated."""
        from sage.platform.runtime.adapters.flownet_adapter import FlownetRuntimeAdapter
        from sage.platform.runtime.protocol import RuntimeBackendProtocol

        # Collect abstract methods declared by the protocol
        abstract_methods = {
            name
            for name, obj in vars(RuntimeBackendProtocol).items()
            if getattr(obj, "__isabstractmethod__", False)
        }

        # Verify each is overridden by the adapter
        for method_name in abstract_methods:
            assert hasattr(FlownetRuntimeAdapter, method_name), (
                f"FlownetRuntimeAdapter is missing abstract method {method_name!r} "
                f"from RuntimeBackendProtocol."
            )
            impl = getattr(FlownetRuntimeAdapter, method_name)
            assert not getattr(impl, "__isabstractmethod__", False), (
                f"FlownetRuntimeAdapter.{method_name}() is still abstract — "
                "concrete implementation is required."
            )

    def test_protocol_wrapper_hierarchy_is_complete(self):
        """Inner protocol wrappers must subclass the appropriate protocol ABCs."""
        from sage.platform.runtime.adapters.flownet_adapter import (
            _FlownetActorHandle,
            _FlownetFlowRunHandle,
            _FlownetMethodCallFuture,
            _FlownetMethodRef,
            _FlownetNodeInfo,
        )
        from sage.platform.runtime.protocol import (
            ActorHandleProtocol,
            FlowRunHandleProtocol,
            MethodCallFuture,
            MethodRefProtocol,
            NodeInfoProtocol,
        )

        assert issubclass(_FlownetMethodCallFuture, MethodCallFuture), (
            "_FlownetMethodCallFuture must subclass MethodCallFuture (Issue #1433)."
        )
        assert issubclass(_FlownetMethodRef, MethodRefProtocol), (
            "_FlownetMethodRef must subclass MethodRefProtocol (Issue #1433)."
        )
        assert issubclass(_FlownetActorHandle, ActorHandleProtocol), (
            "_FlownetActorHandle must subclass ActorHandleProtocol (Issue #1433)."
        )
        assert issubclass(_FlownetFlowRunHandle, FlowRunHandleProtocol), (
            "_FlownetFlowRunHandle must subclass FlowRunHandleProtocol (Issue #1433)."
        )
        assert issubclass(_FlownetNodeInfo, NodeInfoProtocol), (
            "_FlownetNodeInfo must subclass NodeInfoProtocol (Issue #1433)."
        )

    def test_adapter_module_has_no_sage_kernel_imports(self):
        """The adapter must NOT import sage.kernel — preventing reverse coupling.

        Adapters are in L2 (sage-platform); they must not depend on L3 (sage-kernel).
        """
        import ast
        import importlib.util

        spec = importlib.util.find_spec("sage.platform.runtime.adapters.flownet_adapter")
        assert spec is not None and spec.origin, (
            "Could not locate sage.platform.runtime.adapters.flownet_adapter source."
        )
        with open(spec.origin) as fh:
            source = fh.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("sage.kernel"), (
                        f"Adapter imports sage.kernel.{alias.name!r} — "
                        "this creates an upward L2→L3 dependency violation."
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not module.startswith("sage.kernel"), (
                    f"Adapter has 'from {module} import ...' — "
                    "this creates an upward L2→L3 dependency violation."
                )

    def test_protocol_module_has_no_flownet_imports(self):
        """sage.platform.runtime.protocol must have zero sage.flownet imports.

        The protocol is the pure abstraction; the adapter is the Flownet glue.
        """
        import ast
        import importlib.util

        spec = importlib.util.find_spec("sage.platform.runtime.protocol")
        assert spec is not None and spec.origin
        with open(spec.origin) as fh:
            source = fh.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("sage.flownet"), (
                        f"Protocol module imports {alias.name!r} — "
                        "protocols must be backend-agnostic (Issue #1433)."
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not module.startswith("sage.flownet"), (
                    f"Protocol module has 'from {module} import ...' — "
                    "protocols must be backend-agnostic (Issue #1433)."
                )

    def test_get_flownet_adapter_factory_exists(self):
        """get_flownet_adapter() must be importable and callable."""
        from sage.platform.runtime.adapters.flownet_adapter import get_flownet_adapter

        assert callable(get_flownet_adapter)

    def test_adapter_exposes_expected_public_api(self):
        """FlownetRuntimeAdapter must expose __all__ with the correct symbols."""
        from sage.platform.runtime.adapters import flownet_adapter

        assert hasattr(flownet_adapter, "__all__")
        assert "FlownetRuntimeAdapter" in flownet_adapter.__all__
        assert "get_flownet_adapter" in flownet_adapter.__all__


# ===========================================================================
# Suite 2: Error message contracts (no live runtime required)
# ===========================================================================


class TestAdapterErrorMessages:
    """Verify that ImportError messages from the adapter follow the contract:
    - Must NOT mention 'ray' as a standalone term.
    - Must reference sageFlownet or isage-flow.

    This is the adapter-layer gating for the same check done in
    TestNoRayTerms in test_facade_api.py (Issue #1432 DoD).
    """

    def test_require_flownet_error_message_format(self):
        """_require_flownet raises ImportError with correct message format."""
        import re

        from sage.platform.runtime.adapters.flownet_adapter import _require_flownet

        # Patch sage.flownet to be missing
        hidden = {}
        for k in list(sys.modules):
            if k == "sage.flownet" or k.startswith("sage.flownet."):
                hidden[k] = sys.modules.pop(k)

        # Block import
        class _FlownetBlocker(importlib.abc.MetaPathFinder):
            def find_module(self, name, path=None):  # type: ignore[override]
                if name == "sage.flownet" or name.startswith("sage.flownet."):
                    raise ImportError("Simulated absent sageFlownet")
                return None

        blocker = _FlownetBlocker()
        sys.meta_path.insert(0, blocker)
        try:
            with pytest.raises(ImportError) as exc_info:
                _require_flownet("test_op")
            msg = str(exc_info.value).lower()
            # Must not mention 'ray' as noun
            assert re.search(r"\bray\b", msg) is None, (
                f"Error message contains 'ray': {exc_info.value!r}"
            )
            # Must reference sageFlownet or the PyPI package name
            assert "sageflownet" in msg or "isage-flow" in msg, (
                f"Error message must reference sageFlownet or isage-flow: {exc_info.value!r}"
            )
        finally:
            sys.meta_path.remove(blocker)
            sys.modules.update(hidden)


# ===========================================================================
# Suite 3: Live runtime end-to-end (skipped when sageFlownet absent)
# ===========================================================================


class TestAdapterLiveExecution:
    """End-to-end tests that require a live sageFlownet runtime.

    Skipped automatically when sageFlownet (isage-flow) is not installed.
    These validate that the SAGE facade → L2 protocol → Flownet bridge
    processes a simple flow execution correctly.
    """

    @_skip_if_no_flownet()
    def test_get_flownet_adapter_returns_singleton(self):
        """get_flownet_adapter() must return the same instance on repeated calls."""
        from sage.platform.runtime.adapters.flownet_adapter import get_flownet_adapter

        a1 = get_flownet_adapter()
        a2 = get_flownet_adapter()
        assert a1 is a2, "get_flownet_adapter() must return a singleton"

    @_skip_if_no_flownet()
    def test_adapter_can_be_instantiated(self):
        """FlownetRuntimeAdapter can be instantiated without errors."""
        from sage.platform.runtime.adapters.flownet_adapter import FlownetRuntimeAdapter

        adapter = FlownetRuntimeAdapter()
        assert adapter is not None

    @_skip_if_no_flownet()
    def test_facade_create_routes_through_protocol(self):
        """sage.kernel.facade.create() must not call Flownet internals directly.

        It must route through RuntimeBackendProtocol.create() on the adapter,
        which is the sole boundary point per Issue #1433.
        """
        from unittest.mock import MagicMock, patch

        from sage.platform.runtime.adapters.flownet_adapter import get_flownet_adapter

        adapter = get_flownet_adapter()

        class _DummyWorker:
            def process(self, x):
                return x

        mock_handle = MagicMock()
        with patch.object(adapter, "create", return_value=mock_handle) as mock_create:
            from sage.kernel.facade import create

            result = create(_DummyWorker)
            mock_create.assert_called_once()
            assert result is mock_handle, (
                "facade.create() must return the handle produced by the adapter "
                "(no direct Flownet bypass)."
            )

    @_skip_if_no_flownet()
    def test_flow_declaration_require_adapter_returns_flownet_object(self):
        """FlowDeclaration._require_adapter() must produce a backend-native
        (Flownet) Flow object when sageFlownet is available.

        This validates the SAGE L3 → L2 bridge (Issue #1432 / #1433 integration
        DoD: 'Adapter integration tests validate end-to-end execution').
        """
        from sage.kernel.flow.declaration import FlowDeclaration

        def my_test_flow(init_stream):
            return init_stream

        decl = FlowDeclaration(my_test_flow)
        # _require_adapter() is the L3 bridge to the Flownet FlowDef
        flownet_obj = decl._require_adapter()
        assert flownet_obj is not None, (
            "FlowDeclaration._require_adapter() must return a backend-native "
            "object when sageFlownet is installed."
        )
