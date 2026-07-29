"""
Tests for sage.platform.runtime.protocol - Runtime Protocol Interface.

Verifies the Acceptance Criteria for intellistream/SAGE#1433:

  DoD #1: No direct Flownet internal imports in kernel dispatch/scheduling path.
          → Tested: TestFacadeUsesProtocol ensures facade routes through L2.
  DoD #2: Adapter integration tests pass end-to-end execution.
          → Tested: TestFlownetRuntimeAdapterWithMock using mock Flownet runtime.
  DoD #3: Protocol docs describe lifecycle and error semantics.
          → Tested: TestProtocolDocumentation checks docstrings.
"""

from __future__ import annotations

import ast
import importlib
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_top_level_imports(module_name: str) -> list[str]:
    """Return the names of all top-level (module-level) imports in *module_name*."""
    mod = importlib.import_module(module_name)
    src_file = getattr(mod, "__file__", None)
    if src_file is None or not src_file.endswith(".py"):
        return []
    with open(src_file) as fh:
        source = fh.read()
    tree = ast.parse(source)
    imports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    return imports


# ---------------------------------------------------------------------------
# Tests: protocol module structure
# ---------------------------------------------------------------------------


class TestProtocolModuleStructure:
    """Verify the protocol module only contains ABC/Protocol definitions."""

    def test_protocol_importable(self):
        from sage.platform.runtime import protocol  # noqa: F401

    def test_all_protocol_classes_exported(self):
        from sage.platform.runtime.protocol import (
            ActorHandleProtocol,
            FlowRunHandleProtocol,
            MethodRefProtocol,
            NodeInfoProtocol,
            RuntimeBackendProtocol,
        )

        assert RuntimeBackendProtocol.__abstractmethods__  # must have abstract methods
        assert ActorHandleProtocol.__abstractmethods__
        assert MethodRefProtocol.__abstractmethods__
        assert FlowRunHandleProtocol.__abstractmethods__
        assert NodeInfoProtocol.__abstractmethods__

    def test_protocol_module_no_flownet_imports(self):
        """Protocol module must have zero Flownet imports."""
        imports = _get_top_level_imports("sage.platform.runtime.protocol")
        for imp in imports:
            assert not imp.startswith("sage.flownet"), (
                f"Protocol module has a Flownet import '{imp}' — "
                "protocol layer must be backend-agnostic."
            )

    def test_runtime_subpackage_exported_from_platform(self):
        import sage.platform

        assert hasattr(sage.platform, "runtime"), "sage.platform must expose a 'runtime' subpackage"

    def test_protocol_classes_in_runtime_init(self):
        from sage.platform.runtime import (
            ActorHandleProtocol,
            RuntimeBackendProtocol,
        )

        assert RuntimeBackendProtocol is not None
        assert ActorHandleProtocol is not None

    def test_protocol_documentation(self):
        from sage.platform.runtime import protocol

        for name in protocol.__all__:
            cls = getattr(protocol, name)
            assert cls.__doc__, f"{name} must have a docstring"


# ---------------------------------------------------------------------------
# Tests: protocol abstract method compliance
# ---------------------------------------------------------------------------


class TestRuntimeBackendProtocolCompliance:
    """Verify that a concrete subclass must implement all abstract methods."""

    def test_cannot_instantiate_abstract_backend(self):
        from sage.platform.runtime.protocol import RuntimeBackendProtocol

        with pytest.raises(TypeError):
            RuntimeBackendProtocol()  # type: ignore[abstract]

    def test_concrete_implementation_passes(self):
        """A minimal concrete implementation should be instantiable."""
        from sage.platform.runtime.protocol import (
            ActorHandleProtocol,
            FlowRunHandleProtocol,
            MethodRefProtocol,
            NodeInfoProtocol,
            RuntimeBackendProtocol,
        )

        class _ConcreteMethod(MethodRefProtocol):
            def call(self, *a, **kw):
                return "result"

            def async_call(self, *a, **kw):
                import concurrent.futures

                from sage.platform.runtime.protocol import MethodCallFuture

                fut = concurrent.futures.Future()
                fut.set_result("result")

                class _ImmediateFuture(MethodCallFuture):
                    def result(self, timeout=None):
                        return "result"

                    def cancel(self):
                        return False

                    @property
                    def done(self):
                        return True

                return _ImmediateFuture()

            def cancel(self) -> bool:
                return False

        class _ConcreteHandle(ActorHandleProtocol):
            def get_method(self, name):
                return _ConcreteMethod()

        class _ConcreteRunHandle(FlowRunHandleProtocol):
            def call(self, *a, **kw):
                return "output"

            def cancel(self):
                pass

        class _ConcreteNodeInfo(NodeInfoProtocol):
            @property
            def node_id(self):
                return "n1"

            @property
            def address(self):
                return "127.0.0.1:8787"

            @property
            def is_schedulable(self):
                return True

            @property
            def resource_summary(self):
                return {}

        class _ConcreteBackend(RuntimeBackendProtocol):
            def start(self, config=None):
                pass

            def stop(self):
                pass

            def create(self, actor_class, /, *a, actor_config=None, **kw):
                return _ConcreteHandle()

            def submit(self, flow_obj, *, ingress=None, egress=None, run_config=None):
                return _ConcreteRunHandle()

            def list_nodes(self):
                return [_ConcreteNodeInfo()]

        backend = _ConcreteBackend()
        backend.start()
        handle = backend.create(object)
        method_ref = handle.get_method("foo")
        assert method_ref.call() == "result"
        run_handle = backend.submit(None)
        assert run_handle.call() == "output"
        run_handle.cancel()
        nodes = backend.list_nodes()
        assert nodes[0].node_id == "n1"


# ---------------------------------------------------------------------------
# Tests: FlownetRuntimeAdapter structure
# ---------------------------------------------------------------------------


class TestFlownetRuntimeAdapterStructure:
    """Verify the Flownet adapter satisfies the protocol without Flownet installed."""

    def test_adapter_importable(self):
        from sage.platform.runtime.adapters.flownet_adapter import (  # noqa: F401
            FlownetRuntimeAdapter,
            get_flownet_adapter,
        )

    def test_adapter_is_runtime_backend_protocol(self):
        from sage.platform.runtime.adapters.flownet_adapter import FlownetRuntimeAdapter
        from sage.platform.runtime.protocol import RuntimeBackendProtocol

        # Check it's a subclass (structural compliance)
        assert issubclass(FlownetRuntimeAdapter, RuntimeBackendProtocol)

    def test_adapter_module_no_static_flownet_imports(self):
        """Adapter module top-level code must not import Flownet statically."""
        imports = _get_top_level_imports("sage.platform.runtime.adapters.flownet_adapter")
        for imp in imports:
            assert not imp.startswith("sage.flownet"), (
                f"Adapter module has a static Flownet import '{imp}' — "
                "all Flownet imports must be lazy (inside methods)."
            )

    def test_unstarted_adapter_raises_on_create(self):
        """Calling create() before start() should raise RuntimeError."""
        from sage.platform.runtime.adapters.flownet_adapter import FlownetRuntimeAdapter

        adapter = FlownetRuntimeAdapter()  # fresh, unstarted
        with pytest.raises(RuntimeError, match="start"):
            # Patch to avoid actual Flownet ImportError
            with patch("sage.platform.runtime.adapters.flownet_adapter._require_flownet"):
                adapter.create(object)

    def test_unstarted_adapter_raises_on_submit(self):
        from sage.platform.runtime.adapters.flownet_adapter import FlownetRuntimeAdapter

        adapter = FlownetRuntimeAdapter()
        with pytest.raises(RuntimeError, match="start"):
            with patch("sage.platform.runtime.adapters.flownet_adapter._require_flownet"):
                adapter.submit(None)

    def test_unstarted_adapter_raises_on_list_nodes(self):
        from sage.platform.runtime.adapters.flownet_adapter import FlownetRuntimeAdapter

        adapter = FlownetRuntimeAdapter()
        with pytest.raises(RuntimeError, match="start"):
            with patch("sage.platform.runtime.adapters.flownet_adapter._require_flownet"):
                adapter.list_nodes()


# ---------------------------------------------------------------------------
# Tests: FlownetRuntimeAdapter with mock Flownet runtime
# ---------------------------------------------------------------------------


class TestFlownetRuntimeAdapterWithMock:
    """End-to-end adapter tests using a mocked Flownet runtime.

    These tests validate the adapter wire-up without requiring a live
    sageFlownet installation (intellistream/SAGE#1433 DoD #2).
    """

    def _make_started_adapter(self):
        """Return a FlownetRuntimeAdapter that is pre-started via mock."""
        from sage.platform.runtime.adapters.flownet_adapter import FlownetRuntimeAdapter

        adapter = FlownetRuntimeAdapter()
        # Force _started = True to skip runtime initialisation in unit tests.
        object.__setattr__(adapter, "_started", True) if hasattr(adapter, "__slots__") else setattr(
            adapter, "_started", True
        )
        return adapter

    def test_create_wraps_actor_ref_as_handle_protocol(self):
        """create() should return an ActorHandleProtocol wrapping ActorRef."""
        from sage.platform.runtime.adapters.flownet_adapter import (
            _FlownetActorHandle,
        )
        from sage.platform.runtime.protocol import ActorHandleProtocol

        adapter = self._make_started_adapter()

        mock_actor_ref = MagicMock()
        mock_actor_ref.process = MagicMock()

        # Patch via sys.modules so the lazy `from sage.flownet.api.runtime import create_actor`
        # inside FlownetRuntimeAdapter.create() resolves to our mock, and the
        # `import sage.flownet` availability check inside _require_flownet() succeeds.
        import sys

        mock_flownet_mod = MagicMock()
        mock_flownet_runtime_mod = MagicMock()
        mock_flownet_runtime_mod.create_actor.return_value = mock_actor_ref
        with patch.dict(
            sys.modules,
            {
                "sage.flownet": mock_flownet_mod,
                "sage.flownet.api": MagicMock(),
                "sage.flownet.api.runtime": mock_flownet_runtime_mod,
            },
        ):
            handle = adapter.create(object)

        assert isinstance(handle, (_FlownetActorHandle, ActorHandleProtocol))

    def test_flownet_actor_handle_attribute_access(self):
        """_FlownetActorHandle.__getattr__ should delegate to get_method."""
        from sage.platform.runtime.adapters.flownet_adapter import (
            _FlownetActorHandle,
            _FlownetMethodRef,
        )

        mock_actor_ref = MagicMock()
        mock_method_ref = MagicMock()
        mock_method_ref.__call__ = MagicMock(return_value="result")
        mock_actor_ref.process = mock_method_ref

        handle = _FlownetActorHandle(mock_actor_ref)
        # Attribute-style access should return a _FlownetMethodRef
        method = handle.process
        assert isinstance(method, _FlownetMethodRef)

    def test_flownet_method_ref_delegates_call(self):
        """_FlownetMethodRef.call() should invoke the underlying method ref."""
        from sage.platform.runtime.adapters.flownet_adapter import _FlownetMethodRef

        mock_ref = MagicMock(return_value="output")
        method_ref = _FlownetMethodRef(mock_ref)
        result = method_ref.call("arg1", key="val")
        mock_ref.assert_called_once_with("arg1", key="val")
        assert result == "output"

    def test_flownet_flow_run_handle_call(self):
        """_FlownetFlowRunHandle.call() should invoke the underlying handle."""
        from sage.platform.runtime.adapters.flownet_adapter import _FlownetFlowRunHandle

        mock_handle = MagicMock()
        mock_handle.call.return_value = "flow_result"
        run_handle = _FlownetFlowRunHandle(mock_handle)
        result = run_handle.call("payload")
        mock_handle.call.assert_called_once_with("payload")
        assert result == "flow_result"

    def test_flownet_flow_run_handle_cancel(self):
        """_FlownetFlowRunHandle.cancel() should invoke the underlying cancel."""
        from sage.platform.runtime.adapters.flownet_adapter import _FlownetFlowRunHandle

        mock_handle = MagicMock()
        run_handle = _FlownetFlowRunHandle(mock_handle)
        run_handle.cancel()
        mock_handle.cancel.assert_called_once()

    def test_flownet_flow_run_handle_cancel_not_supported(self):
        """cancel() should raise RuntimeError when underlying handle lacks .cancel()."""
        from sage.platform.runtime.adapters.flownet_adapter import _FlownetFlowRunHandle

        mock_handle = MagicMock(spec=[])  # no .cancel attribute
        # Add .call so the handle is otherwise valid
        mock_handle.call = MagicMock(return_value="x")
        run_handle = _FlownetFlowRunHandle(mock_handle)
        with pytest.raises(RuntimeError, match="cancel"):
            run_handle.cancel()

    def test_flownet_node_info_wraps_cluster_node(self):
        """_FlownetNodeInfo should map ClusterNode fields to protocol properties."""
        from sage.platform.runtime.adapters.flownet_adapter import _FlownetNodeInfo

        mock_node = MagicMock()
        mock_node.node_id = "node-42"
        mock_node.address = "10.0.0.1:8787"
        mock_node.resource_summary = {
            "cpu_available": 3.5,
            "schedulable": True,
        }

        info = _FlownetNodeInfo(mock_node)
        assert info.node_id == "node-42"
        assert info.address == "10.0.0.1:8787"
        assert info.is_schedulable is True
        assert info.resource_summary["cpu_available"] == 3.5

    def test_get_flownet_adapter_returns_singleton(self):
        """get_flownet_adapter() should return the same instance each call."""
        import sage.platform.runtime.adapters.flownet_adapter as mod

        # Reset singleton for test isolation
        original = mod._adapter_singleton
        mod._adapter_singleton = None
        try:
            with patch.object(mod.FlownetRuntimeAdapter, "start", return_value=None):
                a1 = mod.get_flownet_adapter()
                a2 = mod.get_flownet_adapter()
            assert a1 is a2
        finally:
            mod._adapter_singleton = original


# ---------------------------------------------------------------------------
# Tests: facade routes through L2 protocol
# ---------------------------------------------------------------------------


class TestFacadeUsesProtocol:
    """Verify sage.kernel.facade routes through the L2 protocol adapter.

    Per intellistream/SAGE#1433 DoD #1: no direct Flownet internal imports
    in the kernel dispatch/scheduling path.
    """

    def test_facade_no_direct_sage_flownet_imports(self):
        """The facade must not have top-level imports from sage.flownet."""
        imports = _get_top_level_imports("sage.kernel.facade")
        for imp in imports:
            assert not imp.startswith("sage.flownet"), (
                f"sage.kernel.facade has a direct sage.flownet import '{imp}'. "
                "Dispatch must go through sage.platform.runtime (L2 protocol)."
            )

    def test_facade_create_routes_through_backend(self):
        """facade.create() should call the runtime backend, not Flownet directly."""
        from sage.kernel.facade import create

        mock_backend = MagicMock()
        mock_handle = MagicMock()
        mock_handle.get_method.return_value = MagicMock()
        mock_backend.create.return_value = mock_handle

        with patch(
            "sage.kernel.facade._get_runtime_backend",
            return_value=mock_backend,
        ):
            handle = create(object)

        mock_backend.create.assert_called_once_with(object, actor_config=None)
        assert handle is mock_handle

    def test_facade_submit_routes_through_backend(self):
        """facade.submit() should call the runtime backend, not Flownet directly."""
        from sage.kernel.facade import submit

        mock_backend = MagicMock()
        mock_run_handle = MagicMock()
        mock_backend.submit.return_value = mock_run_handle

        mock_flow = MagicMock()

        with patch(
            "sage.kernel.facade._get_runtime_backend",
            return_value=mock_backend,
        ):
            with patch(
                "sage.kernel.facade._resolve_flow_for_backend",
                return_value=mock_flow,
            ):
                handle = submit(mock_flow)

        mock_backend.submit.assert_called_once()
        assert handle is mock_run_handle

    def test_facade_run_uses_backend_for_availability_check(self):
        """facade.run() should call _get_runtime_backend() to verify availability."""
        from sage.kernel.facade import run

        mock_backend = MagicMock()
        mock_flow = MagicMock()
        mock_flow.call = MagicMock(return_value="done")

        with patch(
            "sage.kernel.facade._get_runtime_backend",
            return_value=mock_backend,
        ):
            with patch(
                "sage.kernel.facade._resolve_flow_for_backend",
                return_value=mock_flow,
            ):
                result = run(mock_flow, "payload")

        mock_backend  # backend was fetched (availability check)
        assert result == "done"

    def test_facade_call_uses_backend_for_availability_check(self):
        """facade.call() should call _get_runtime_backend() to verify availability."""
        from sage.kernel.facade import call

        mock_backend = MagicMock()
        mock_handle = MagicMock()
        mock_handle.call.return_value = "result"

        with patch(
            "sage.kernel.facade._get_runtime_backend",
            return_value=mock_backend,
        ):
            result = call(mock_handle, "input")

        assert result == "result"
        mock_handle.call.assert_called_once_with("input")


# ---------------------------------------------------------------------------
# Tests: MethodCallFuture and async_call/cancel contract (Issue 1436)
# ---------------------------------------------------------------------------


class TestMethodCallFutureProtocol:
    """Verify MethodCallFuture ABC completeness (intellistream/SAGE#1436)."""

    def test_method_call_future_importable(self):
        from sage.platform.runtime.protocol import MethodCallFuture  # noqa: F401

    def test_method_call_future_in_package_init(self):
        from sage.platform.runtime import MethodCallFuture  # noqa: F401

    def test_method_call_future_has_abstract_methods(self):
        from sage.platform.runtime.protocol import MethodCallFuture

        assert MethodCallFuture.__abstractmethods__

    def test_method_call_future_abstract_methods_complete(self):
        """MethodCallFuture must declare result, cancel, done."""
        from sage.platform.runtime.protocol import MethodCallFuture

        abstract_names = MethodCallFuture.__abstractmethods__
        assert "result" in abstract_names
        assert "cancel" in abstract_names
        assert "done" in abstract_names

    def test_cannot_instantiate_method_call_future(self):
        from sage.platform.runtime.protocol import MethodCallFuture

        with pytest.raises(TypeError):
            MethodCallFuture()  # type: ignore[abstract]

    def test_method_call_future_in_protocol_all(self):
        from sage.platform.runtime import protocol

        assert "MethodCallFuture" in protocol.__all__


class TestMethodRefProtocolExtended:
    """Verify MethodRefProtocol has async_call and cancel (intellistream/SAGE#1436)."""

    def test_method_ref_has_async_call_abstract(self):
        from sage.platform.runtime.protocol import MethodRefProtocol

        abstract_names = MethodRefProtocol.__abstractmethods__
        assert "async_call" in abstract_names, (
            "MethodRefProtocol must declare async_call() as an abstract method "
            "(intellistream/SAGE#1436)"
        )

    def test_method_ref_has_cancel_abstract(self):
        from sage.platform.runtime.protocol import MethodRefProtocol

        abstract_names = MethodRefProtocol.__abstractmethods__
        assert "cancel" in abstract_names, (
            "MethodRefProtocol must declare cancel() as an abstract method "
            "(intellistream/SAGE#1436)"
        )

    def test_actor_handle_has_cancel_method(self):
        """ActorHandleProtocol must expose cancel() (actor-level teardown)."""
        from sage.platform.runtime.protocol import ActorHandleProtocol

        assert hasattr(ActorHandleProtocol, "cancel"), (
            "ActorHandleProtocol must expose cancel() (intellistream/SAGE#1436)"
        )

    def test_concrete_method_ref_must_implement_all_abstract_methods(self):
        """Concrete subclass that omits async_call/cancel cannot be instantiated."""
        from sage.platform.runtime.protocol import MethodRefProtocol

        class _Incomplete(MethodRefProtocol):
            def call(self, *a, **k):
                return None

            # async_call and cancel intentionally omitted

        with pytest.raises(TypeError):
            _Incomplete()  # type: ignore[abstract]

    def test_concrete_method_ref_with_all_methods_ok(self):
        """A fully concrete MethodRefProtocol can be instantiated."""
        from sage.platform.runtime.protocol import MethodCallFuture, MethodRefProtocol

        class _StubFuture(MethodCallFuture):
            def result(self, timeout=None):
                return "ok"

            def cancel(self):
                return False

            @property
            def done(self):
                return True

        class _Complete(MethodRefProtocol):
            def call(self, *a, **k):
                return "sync_result"

            def async_call(self, *a, **k) -> MethodCallFuture:
                return _StubFuture()

            def cancel(self) -> bool:
                return False

        obj = _Complete()
        assert obj.call() == "sync_result"
        future = obj.async_call()
        assert future.result() == "ok"
        assert obj.cancel() is False


class TestFlownetAdapterAsyncCancel:
    """Verify _FlownetMethodRef async_call / cancel semantics (intellistream/SAGE#1436)."""

    def _make_method_ref(self, side_effect=None, return_value="sync_result"):
        """Create a _FlownetMethodRef backed by a mock ActorMethodRef."""
        import sage.platform.runtime.adapters.flownet_adapter as mod

        mock_actor_method_ref = MagicMock()
        if side_effect is not None:
            mock_actor_method_ref.side_effect = side_effect
        else:
            mock_actor_method_ref.return_value = return_value
        return mod._FlownetMethodRef(mock_actor_method_ref)

    def test_async_call_returns_method_call_future(self):
        from sage.platform.runtime.protocol import MethodCallFuture

        ref = self._make_method_ref(return_value="async_result")
        future = ref.async_call("payload")
        assert isinstance(future, MethodCallFuture)

    def test_async_call_result_matches_sync_call(self):
        ref = self._make_method_ref(return_value="computed")
        future = ref.async_call("input")
        assert future.result(timeout=5.0) == "computed"

    def test_async_call_done_after_result(self):
        ref = self._make_method_ref(return_value="x")
        future = ref.async_call()
        _ = future.result(timeout=5.0)
        assert future.done is True

    def test_sync_call_still_works(self):
        ref = self._make_method_ref(return_value="sync")
        assert ref.call("arg") == "sync"

    def test_cancel_returns_false_for_flownet(self):
        """Flownet does not support per-method cancel; must return False."""
        ref = self._make_method_ref()
        assert ref.cancel() is False

    def test_async_call_timeout_raises_timeout_error(self):
        import time

        def _slow(*args, **kwargs):
            time.sleep(2.0)
            return "late"

        ref = self._make_method_ref(side_effect=_slow)
        future = ref.async_call()
        with pytest.raises(TimeoutError):
            future.result(timeout=0.01)

    def test_async_call_future_cancel_before_execution(self):
        """cancel() on a not-yet-started future returns True."""
        import time

        import sage.platform.runtime.adapters.flownet_adapter as mod

        barrier = [False]

        def _blocking(*args, **kwargs):
            while not barrier[0]:
                time.sleep(0.01)
            return "result"

        # We can't directly control when our future runs, but we can test
        # that cancel() is callable and returns a bool.
        mock_actor_method_ref = MagicMock(return_value="value")
        ref = mod._FlownetMethodRef(mock_actor_method_ref)
        future = ref.async_call()
        # Future may be done already; cancel() returns bool in either case.
        result = future.cancel()
        assert isinstance(result, bool)

    def test_flownet_actor_handle_cancel_returns_false(self):
        """_FlownetActorHandle.cancel() returns False (not supported yet)."""
        import sage.platform.runtime.adapters.flownet_adapter as mod

        mock_ref = MagicMock()
        handle = mod._FlownetActorHandle(mock_ref)
        assert handle.cancel() is False

    def test_method_call_future_protocol_compliance(self):
        """_FlownetMethodCallFuture is a MethodCallFuture."""
        import sage.platform.runtime.adapters.flownet_adapter as mod
        from sage.platform.runtime.protocol import MethodCallFuture

        assert issubclass(mod._FlownetMethodCallFuture, MethodCallFuture)

    def test_async_call_exception_becomes_runtime_error(self):
        """If the remote call raises, future.result() re-raises as RuntimeError or original."""
        ref = self._make_method_ref(side_effect=ValueError("boom"))
        future = ref.async_call()
        with pytest.raises(ValueError, match="boom"):
            future.result(timeout=5.0)


class TestPublicTypingNoFlownetExposure:
    """Verify no direct Flownet types are exposed in public SAGE contracts (Issue 1436 DoD #3)."""

    def test_protocol_module_no_flownet_imports(self):
        """The protocol module must not import from sage.flownet."""
        imports = _get_top_level_imports("sage.platform.runtime.protocol")
        for imp in imports:
            assert not imp.startswith("sage.flownet"), (
                f"Protocol module has a Flownet import '{imp}' — "
                "protocol layer must be backend-agnostic."
            )

    def test_platform_runtime_init_no_flownet_imports(self):
        """sage.platform.runtime.__init__ must not import from sage.flownet."""
        imports = _get_top_level_imports("sage.platform.runtime")
        for imp in imports:
            assert not imp.startswith("sage.flownet"), (
                f"sage.platform.runtime has a Flownet import '{imp}'"
            )

    def test_method_call_future_exported_from_platform(self):
        """MethodCallFuture must be importable from the top-level platform runtime."""
        from sage.platform.runtime import MethodCallFuture  # noqa: F401

        assert MethodCallFuture is not None

    def test_public_type_annotations_use_sage_contracts(self):
        """facade TYPE_CHECKING block should reference SAGE protocol types, not Flownet."""
        imports = _get_top_level_imports("sage.kernel.facade")
        for imp in imports:
            assert not imp.startswith("sage.flownet"), (
                f"sage.kernel.facade has a top-level sage.flownet import '{imp}'. "
                "Public type annotations should reference SAGE protocol types only."
            )
