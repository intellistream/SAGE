"""
Contract tests for sage.kernel.facade — SAGE L3 Public Facade API.

These tests verify the Acceptance Criteria for intellistream/SAGE#1432:

  DoD #1: Public docs/examples only use SAGE facade APIs.
          → Verified: facade is importable from sage.kernel top-level.
  DoD #2: Contract tests pass in local and distributed modes.
          → This file covers the local/unit contract surface.
          → Integration tests (with live runtime) are in tests/integration/.
  DoD #3: No Ray-oriented public API terms remain.
          → Tested in TestNoRayTerms class.

No ``sage.flownet.*`` import is needed or allowed at module level in the
facade itself — tested in TestFacadeNoStaticFlownetImports.
"""

from __future__ import annotations

import ast
import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_no_static_flownet_imports(module_name: str) -> None:
    """Assert that *module_name* has zero top-level Flownet imports."""
    mod = importlib.import_module(module_name)
    src_file = getattr(mod, "__file__", None)
    if src_file is None or not src_file.endswith(".py"):
        return
    with open(src_file) as fh:
        source = fh.read()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("sage.flownet"), (
                    f"Module {module_name!r} has a top-level import of "
                    f"{alias.name!r} — runtime imports must be lazy."
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not module.startswith("sage.flownet"), (
                f"Module {module_name!r} has a top-level 'from {module} import ...' "
                "— runtime imports must be lazy."
            )


# ---------------------------------------------------------------------------
# Test: zero static Flownet imports in the facade module
# ---------------------------------------------------------------------------


class TestFacadeNoStaticFlownetImports:
    """Verify the facade has no static (module-level) Flownet dependencies."""

    def test_facade_package_no_static_flownet(self):
        _assert_no_static_flownet_imports("sage.kernel.facade")


# ---------------------------------------------------------------------------
# Test: facade is importable from canonical locations
# ---------------------------------------------------------------------------


class TestFacadeImportability:
    """Verify the facade is accessible from the documented import paths."""

    def test_import_from_facade_package(self):
        from sage.kernel.facade import call, create, run, submit  # noqa: F401

    def test_import_from_sage_kernel_top_level(self):
        from sage.kernel import call, create, run, submit  # noqa: F401

    def test_kernel_facade_subpackage_exposed(self):
        import sage.kernel

        assert hasattr(sage.kernel, "facade"), "sage.kernel should expose a 'facade' subpackage"

    def test_facade_all_declares_four_verbs(self):
        from sage.kernel import facade

        assert "create" in facade.__all__
        assert "submit" in facade.__all__
        assert "run" in facade.__all__
        assert "call" in facade.__all__

    def test_kernel_all_includes_facade_verbs(self):
        import sage.kernel

        for verb in ("create", "submit", "run", "call"):
            assert verb in sage.kernel.__all__, f"'sage.kernel.__all__' must include '{verb}'"


# ---------------------------------------------------------------------------
# Test: no Ray-oriented terminology in public API surface
# ---------------------------------------------------------------------------


class TestNoRayTerms:
    """Verify the public facade API is free of Ray-oriented terminology."""

    def _get_public_docstrings(self):
        from sage.kernel import facade

        items = []
        for name in facade.__all__:
            obj = getattr(facade, name, None)
            if obj is not None:
                items.append((name, obj.__doc__ or ""))
        items.append(("module", facade.__doc__ or ""))
        return items

    def test_no_ray_in_function_names(self):
        from sage.kernel.facade import call, create, run, submit

        for fn in (create, submit, run, call):
            assert "ray" not in fn.__name__.lower(), f"Function name {fn.__name__!r} contains 'ray'"

    def test_no_ray_as_standalone_word_in_docstrings(self):
        import re

        for name, doc in self._get_public_docstrings():
            # Allow 'ray' as part of longer tokens (e.g. module paths in
            # docstrings) but reject standalone 'ray' as a noun/verb.
            matches = re.findall(r"\bray\b", doc.lower())
            assert not matches, f"Ray-oriented term found in docstring of {name!r}: {matches}"

    def test_module_docstring_documents_migration_table(self):
        from sage.kernel import facade

        doc = facade.__doc__ or ""
        # The migration table maps old Flownet paths to new SAGE facade paths.
        assert "create" in doc
        assert "submit" in doc
        assert "run" in doc
        assert "call" in doc

    def test_error_messages_no_ray(self):
        """ImportError from missing sageFlownet must not mention Ray."""
        import re

        # _get_runtime_backend is the internal helper that raises ImportError
        # when sageFlownet is not available.  It replaced the old _require_flownet.
        from sage.kernel.facade import _get_runtime_backend

        # Temporarily hide sage.flownet AND sage.platform so adapter import fails
        hidden = {k: v for k, v in sys.modules.items() if k.startswith("sage.flownet")}
        for k in hidden:
            sys.modules.pop(k, None)

        class _Block(importlib.abc.MetaPathFinder):
            def find_module(self, name, path=None):  # type: ignore[override]
                if name.startswith("sage.flownet"):
                    raise ImportError("Simulated absent sageFlownet")
                return None

        blocker = _Block()
        sys.meta_path.insert(0, blocker)
        try:
            with pytest.raises(ImportError) as exc_info:
                _get_runtime_backend()  # should raise because sageFlownet absent
            msg = str(exc_info.value).lower()
            assert re.search(r"\bray\b", msg) is None, (
                f"Error message contains 'ray': {exc_info.value}"
            )
            assert "sageflownet" in msg or "isage-flow" in msg, (
                "Error message should mention sageFlownet/isage-flow"
            )
        finally:
            sys.meta_path.remove(blocker)
            sys.modules.update(hidden)


# ---------------------------------------------------------------------------
# Test: facade behavior when sageFlownet is absent
# ---------------------------------------------------------------------------


class TestFacadeWithoutFlownet:
    """When sageFlownet is not installed, all verbs raise ImportError."""

    def _hide_flownet(self, monkeypatch):
        hidden = {k: v for k, v in sys.modules.items() if k.startswith("sage.flownet")}
        for k in hidden:
            monkeypatch.delitem(sys.modules, k, raising=False)

        class _Block(importlib.abc.MetaPathFinder):
            def find_module(self, name, path=None):  # type: ignore[override]
                if name.startswith("sage.flownet"):
                    raise ImportError("sageFlownet not installed")
                return None

        blocker = _Block()
        sys.meta_path.insert(0, blocker)
        return blocker

    def test_create_raises_import_error(self, monkeypatch):
        from sage.kernel.facade import create

        blocker = self._hide_flownet(monkeypatch)
        try:
            with pytest.raises(ImportError, match="sageFlownet"):
                create(object)
        finally:
            sys.meta_path.remove(blocker)

    def test_submit_raises_import_error(self, monkeypatch):
        from sage.kernel.facade import submit
        from sage.kernel.flow.declaration import FlowDeclaration

        def _f(init_stream):
            pass

        decl = FlowDeclaration(_f)
        blocker = self._hide_flownet(monkeypatch)
        try:
            with pytest.raises(ImportError, match="sageFlownet"):
                submit(decl)
        finally:
            sys.meta_path.remove(blocker)

    def test_run_raises_import_error(self, monkeypatch):
        from sage.kernel.facade import run
        from sage.kernel.flow.declaration import FlowDeclaration

        def _f(init_stream):
            pass

        decl = FlowDeclaration(_f)
        blocker = self._hide_flownet(monkeypatch)
        try:
            with pytest.raises(ImportError, match="sageFlownet"):
                run(decl, {})
        finally:
            sys.meta_path.remove(blocker)

    def test_call_raises_import_error(self, monkeypatch):
        from sage.kernel.facade import call

        mock_ref = MagicMock(spec=["call"])
        blocker = self._hide_flownet(monkeypatch)
        try:
            with pytest.raises(ImportError, match="sageFlownet"):
                call(mock_ref, {})
        finally:
            sys.meta_path.remove(blocker)


# ---------------------------------------------------------------------------
# Test: call() type-checking
# ---------------------------------------------------------------------------


class TestCallTypeEnforcement:
    """call() must raise TypeError for objects without a .call() method."""

    def test_call_rejects_non_call_object(self, monkeypatch):
        """An object without .call() must raise TypeError, not AttributeError."""
        # Patch _get_runtime_backend so it does not fail in environments without
        # sageFlownet installed.  This replaced the old _require_flownet.
        with patch("sage.kernel.facade._get_runtime_backend"):
            from sage.kernel.facade import call

            with pytest.raises(TypeError, match=r"\.call\(\)"):
                call("not a ref", {})

    def test_call_accepts_object_with_call_method(self, monkeypatch):
        """An object exposing .call() should be invoked normally."""
        with patch("sage.kernel.facade._get_runtime_backend"):
            from sage.kernel.facade import call

            ref = MagicMock()
            ref.call.return_value = "result"
            result = call(ref, {"key": "value"})
            ref.call.assert_called_once_with({"key": "value"})
            assert result == "result"


# ---------------------------------------------------------------------------
# Test: facade routing through Flownet (with mocked backend)
# ---------------------------------------------------------------------------


class TestFacadeRoutingWithMockedFlownet:
    """With a mocked sageFlownet, verify the facade delegates correctly."""

    def _mock_flownet(self, monkeypatch):
        """Return a mock RuntimeBackendProtocol and patch _get_runtime_backend."""
        mock_backend = MagicMock()
        mock_backend.create.return_value = MagicMock(name="actor_handle")
        mock_backend.submit.return_value = MagicMock(name="run_handle")

        monkeypatch.setattr(
            "sage.kernel.facade._get_runtime_backend",
            lambda: mock_backend,  # no-op — pretend backend is ready
        )
        return mock_backend

    def test_create_delegates_to_create_actor(self, monkeypatch):
        mock_backend = self._mock_flownet(monkeypatch)
        from sage.kernel.facade import create

        class MyActor:
            pass

        create(MyActor, "arg1", key="val")
        mock_backend.create.assert_called_once_with(MyActor, "arg1", actor_config=None, key="val")

    def test_create_passes_actor_config(self, monkeypatch):
        mock_backend = self._mock_flownet(monkeypatch)
        from sage.kernel.facade import create

        class Foo:
            pass

        cfg = {"cpu": 2}
        create(Foo, actor_config=cfg)
        mock_backend.create.assert_called_once_with(Foo, actor_config=cfg)

    def test_submit_delegates_to_submit_flow(self, monkeypatch):
        mock_backend = self._mock_flownet(monkeypatch)
        from sage.kernel.facade import submit

        fake_task = MagicMock(name="flowtask")
        # _resolve_flow_for_backend falls back to returning fake_task unchanged
        # when it is not a FlowDeclaration
        submit(fake_task)
        mock_backend.submit.assert_called_once_with(
            fake_task, ingress=None, egress=None, run_config=None
        )

    def test_run_calls_adapter_call_method(self, monkeypatch):
        self._mock_flownet(monkeypatch)
        from sage.kernel.facade import run

        fake_adapter = MagicMock()
        fake_adapter.call.return_value = "output"

        # We patch _resolve_flow_for_backend to return our fake adapter
        with patch("sage.kernel.facade._resolve_flow_for_backend", return_value=fake_adapter):
            result = run(MagicMock(), {"data": 1})

        fake_adapter.call.assert_called_once_with({"data": 1})
        assert result == "output"

    def test_run_falls_back_to_callable(self, monkeypatch):
        """If adapter has no .call(), run() falls back to calling it directly."""
        self._mock_flownet(monkeypatch)
        from sage.kernel.facade import run

        fake_adapter = MagicMock(spec=[])  # no .call attribute
        fake_adapter.return_value = "direct_result"

        with patch("sage.kernel.facade._resolve_flow_for_backend", return_value=fake_adapter):
            result = run(MagicMock(), "payload")

        fake_adapter.assert_called_once_with("payload")
        assert result == "direct_result"


# ---------------------------------------------------------------------------
# Test: _resolve_flownet_adapter
# ---------------------------------------------------------------------------


class TestResolveFlownetAdapter:
    """Unit-test _resolve_flow_for_backend (formerly _resolve_flownet_adapter)."""

    def test_passthrough_for_unknown_type(self):
        from sage.kernel.facade import _resolve_flow_for_backend

        sentinel = object()
        assert _resolve_flow_for_backend(sentinel) is sentinel

    def test_passthrough_for_mock(self):
        from sage.kernel.facade import _resolve_flow_for_backend

        m = MagicMock()
        assert _resolve_flow_for_backend(m) is m

    def test_adapts_flow_declaration(self):
        """FlowDeclaration should be resolved to its Flownet adapter."""
        from sage.kernel.facade import _resolve_flow_for_backend
        from sage.kernel.flow.declaration import FlowDeclaration

        def my_flow(init_stream):
            pass

        decl = FlowDeclaration(my_flow)
        mock_adapter = MagicMock(name="flownet_adapter")
        # Patch _require_adapter to return our mock
        with patch.object(decl, "_require_adapter", return_value=mock_adapter):
            result = _resolve_flow_for_backend(decl)
        assert result is mock_adapter
