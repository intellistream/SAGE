"""
Context propagation migration contract tests — intellistream/SAGE#1435.

Layer 1 of the 3-layer test taxonomy — intellistream/SAGE#1440.

DoD coverage (Issue #1435 Acceptance Criteria)
===============================================
AC-1: Single implementation source.
      → ContextSlot and run_in_executor_with_context live ONLY in sage-common.
      → The canonical import path is ``sage.common.utils`` (L1 package).
AC-2: No duplicate context-slot utility remains across repos.
      → sage-kernel and sage-platform must NOT define their own ContextSlot.
AC-3: Tests validate context preservation in async and executor paths.
      → Functional tests live in packages/sage-common/tests/unit/utils/test_context_vars.py
        This file covers the *boundary / migration contract* side.

These tests run at Layer 1 (no sageFlownet required) and are included in the
``test-layer-declaration`` CI job defined in
``.github/workflows/ci-flownet-layer-tests.yml``.
"""

from __future__ import annotations

import importlib
import importlib.util
import pathlib

# ===========================================================================
# AC-1: Canonical import location (sage.common.utils — the single L1 home)
# ===========================================================================


class TestCanonicalImportLocation:
    """ContextSlot and run_in_executor_with_context must be importable from the
    single canonical location: ``sage.common.utils`` (L1 package)."""

    def test_context_slot_importable_from_sage_common_utils(self):
        from sage.common.utils import ContextSlot  # noqa: F401

        assert ContextSlot is not None

    def test_run_in_executor_importable_from_sage_common_utils(self):
        from sage.common.utils import run_in_executor_with_context  # noqa: F401

        assert run_in_executor_with_context is not None

    def test_context_slot_importable_via_direct_module(self):
        """The implementation module itself is importable."""
        from sage.common.utils.context_vars import ContextSlot  # noqa: F401

        assert ContextSlot is not None

    def test_run_in_executor_importable_via_direct_module(self):
        from sage.common.utils.context_vars import run_in_executor_with_context  # noqa: F401

        assert run_in_executor_with_context is not None

    def test_context_slot_source_is_context_vars_module(self):
        """The ContextSlot class must be *defined* in context_vars, not re-exported
        from a Flownet or kernel module."""
        from sage.common.utils import ContextSlot

        assert ContextSlot.__module__ == "sage.common.utils.context_vars", (
            f"ContextSlot.__module__ is {ContextSlot.__module__!r}; "
            "expected 'sage.common.utils.context_vars' — single-source-of-truth "
            "contract violated (intellistream/SAGE#1435)."
        )

    def test_sage_common_utils_all_exports_context_apis(self):
        """sage.common.utils.__all__ must explicitly list both context utilities."""
        from sage.common.utils import __all__ as utils_all

        assert "ContextSlot" in utils_all, (
            "'ContextSlot' not in sage.common.utils.__all__ — "
            "canonical exports are missing (intellistream/SAGE#1435)."
        )
        assert "run_in_executor_with_context" in utils_all, (
            "'run_in_executor_with_context' not in sage.common.utils.__all__ — "
            "canonical exports are missing (intellistream/SAGE#1435)."
        )


# ===========================================================================
# AC-2: No duplicate definitions in SAGE kernel or platform packages
# ===========================================================================


class TestNoDuplicateAcrossLayers:
    """Verify that no SAGE layer above L1 defines its own ContextSlot or
    run_in_executor_with_context, ensuring there is a single source of truth.

    Checks are AST/source-level to catch copy-paste duplicates that might
    otherwise pass import-time tests.
    """

    @staticmethod
    def _package_search_root(dotted_name: str) -> pathlib.Path:
        """Return the package directory for a (possibly namespace) package.

        Namespace packages return ``None`` for ``spec.__file__`` but have
        ``spec.submodule_search_locations`` set.
        """
        import pathlib

        spec = importlib.util.find_spec(dotted_name)
        assert spec is not None, f"Package {dotted_name!r} not found"
        if spec.origin:
            # Regular package: __init__.py lives here
            return pathlib.Path(spec.origin).parent
        # Namespace package: use first search location
        locations = list(spec.submodule_search_locations)
        assert locations, f"Package {dotted_name!r} has no search locations"
        return pathlib.Path(locations[0])

    def _collect_defined_names(self, package_root: pathlib.Path) -> set[str]:
        """Return the set of all top-level class and function names *defined*
        (not merely imported) across all .py files under *package_root*."""
        import ast

        defined: set[str] = set()
        for py_file in package_root.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError:
                continue
            for node in tree.body:
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    defined.add(node.name)
        return defined

    def test_sage_kernel_has_no_own_context_slot(self):
        root = self._package_search_root("sage.kernel")
        names = self._collect_defined_names(root)
        assert "ContextSlot" not in names, (
            "sage.kernel defines its own 'ContextSlot' — this is a duplicate of "
            "sage.common.utils.context_vars.ContextSlot (intellistream/SAGE#1435)."
        )

    def test_sage_platform_has_no_own_context_slot(self):
        root = self._package_search_root("sage.platform")
        names = self._collect_defined_names(root)
        assert "ContextSlot" not in names, (
            "sage.platform defines its own 'ContextSlot' — this is a duplicate of "
            "sage.common.utils.context_vars.ContextSlot (intellistream/SAGE#1435)."
        )

    def test_sage_kernel_has_no_own_run_in_executor_with_context(self):
        root = self._package_search_root("sage.kernel")
        names = self._collect_defined_names(root)
        assert "run_in_executor_with_context" not in names, (
            "sage.kernel defines its own 'run_in_executor_with_context' — "
            "duplicate of sage.common utility (intellistream/SAGE#1435)."
        )


# ===========================================================================
# AC-3: No Ray-oriented terminology in the context propagation API
# ===========================================================================


class TestNoRayTerminologyInContextAPI:
    """Verify the context propagation API carries no Ray-oriented naming."""

    def test_context_slot_has_no_ray_in_name(self):
        from sage.common.utils import ContextSlot

        assert "ray" not in ContextSlot.__name__.lower()

    def test_run_in_executor_has_no_ray_in_name(self):
        from sage.common.utils import run_in_executor_with_context

        assert "ray" not in run_in_executor_with_context.__name__.lower()

    def test_context_vars_module_no_ray_imports(self):
        """sage.common.utils.context_vars must not import from Ray."""
        import ast

        spec = importlib.util.find_spec("sage.common.utils.context_vars")
        assert spec is not None and spec.origin
        with open(spec.origin) as fh:
            source = fh.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("ray"), (
                        f"context_vars imports {alias.name!r} — no Ray in L1 utility."
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not module.startswith("ray"), (
                    f"context_vars has 'from {module} import ...' — no Ray in L1 utility."
                )
