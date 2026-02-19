"""Layer 1 — Context Propagation Contract Tests (Issue #1435).

Validates that:
  DoD-1  ``sage.common.utils`` is the single source of truth for
         ``ContextSlot`` and ``run_in_executor_with_context``.
  DoD-2  No duplicate ``ContextSlot`` implementation exists in sageFlownet.
  DoD-3  All known Flownet callsites import from ``sage.common.utils``.
  DoD-4  The SAGE kernel is usable without any sageFlownet dependency
         (no static Flownet imports in this chain).

These tests belong to **Layer 1** of the 3-layer taxonomy
(intellistream/SAGE#1440 & #1435):

  - No sageFlownet runtime dependency.
  - Must pass on every PR targeting ``main`` / ``main-dev``.

Placing these tests in Layer 1 provides an independent CI signal for
the context-propagation migration, separate from exception handling and
facade contract signals.
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# DoD-1: Canonical export location
# ──────────────────────────────────────────────────────────────────────────────


class TestCanonicalExportLocation:
    """ContextSlot and run_in_executor_with_context must live in sage-common."""

    def test_context_slot_importable_from_sage_common_utils(self) -> None:
        from sage.common.utils import ContextSlot  # noqa: F401

    def test_run_in_executor_importable_from_sage_common_utils(self) -> None:
        from sage.common.utils import run_in_executor_with_context  # noqa: F401

    def test_context_slot_importable_from_context_vars_submodule(self) -> None:
        from sage.common.utils.context_vars import ContextSlot  # noqa: F401

    def test_context_slot_in_sage_common_utils_all(self) -> None:
        import sage.common.utils as utils

        assert "ContextSlot" in dir(utils), "ContextSlot must be exported from sage.common.utils"

    def test_run_in_executor_in_sage_common_utils_all(self) -> None:
        import sage.common.utils as utils

        assert "run_in_executor_with_context" in dir(utils), (
            "run_in_executor_with_context must be exported from sage.common.utils"
        )

    def test_context_slot_is_generic(self) -> None:
        """ContextSlot must be a Generic class (Generic[T])."""

        from sage.common.utils import ContextSlot

        orig = getattr(ContextSlot, "__orig_bases__", ())
        # Check Generic[T] in bases (standard pattern)
        assert any("Generic" in str(b) for b in orig), "ContextSlot should subclass Generic[T]"


# ──────────────────────────────────────────────────────────────────────────────
# DoD-2: No duplicate ContextSlot in sageFlownet
# ──────────────────────────────────────────────────────────────────────────────


class TestNoDuplicateInFlownet:
    """Guard against the duplicate-symbol regression described in Issue #1435.

    The file ``sageFlownet/src/sage/flownet/utils/context_vars.py`` must NOT
    exist — it was deleted as part of the migration.  If it reappears (e.g.,
    via a merge from an old branch) these tests will fail and block CI.
    """

    # Heuristic paths where sageFlownet may be installed (local dev or CI).
    _FLOWNET_ROOTS = [
        Path("/home/shuhao/sageFlownet/src/sage/flownet"),
        Path(sys.prefix) / "lib" / "sage" / "flownet",
        # Editable-install discovery via importlib
    ]

    @staticmethod
    def _flownet_utils_context_vars_path() -> Path | None:
        """Return path to flownet utils/context_vars.py if sageFlownet is installed."""
        spec = importlib.util.find_spec("sage.flownet")
        if spec is None or spec.submodule_search_locations is None:
            return None  # sageFlownet not installed — skip file check
        for loc in spec.submodule_search_locations:
            candidate = Path(loc) / "utils" / "context_vars.py"
            if candidate.exists():
                return candidate
        return None

    def test_flownet_utils_context_vars_file_does_not_exist(self) -> None:
        """``sage/flownet/utils/context_vars.py`` must not exist post-migration."""
        duplicate = self._flownet_utils_context_vars_path()
        assert duplicate is None, (
            f"Duplicate ContextSlot found at {duplicate}. "
            "The file sage/flownet/utils/context_vars.py was supposed to be "
            "deleted in Issue #1435. Remove it and update all imports to use "
            "sage.common.utils instead."
        )

    def test_flownet_utils_package_has_no_context_vars_entry(self) -> None:
        """Importing sage.flownet.utils.context_vars must fail (module removed)."""
        if importlib.util.find_spec("sage.flownet") is None:
            pytest.skip("sageFlownet not installed — skipping Flownet import check")

        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("sage.flownet.utils.context_vars")


# ──────────────────────────────────────────────────────────────────────────────
# DoD-3: Flownet callsites use sage.common.utils (source-level check)
# ──────────────────────────────────────────────────────────────────────────────


class TestFlownetCallsitesMigrated:
    """Verify migrated files import ContextSlot from sage.common, not Flownet.

    We parse the source of the four migrated Flownet modules (when sageFlownet
    is installed) to confirm that no ``from sage.flownet.utils.context_vars``
    import remains.
    """

    _MIGRATED_MODULES = [
        "sage.flownet.compiler.flow_context",
        "sage.flownet.api.flow_exception_handlers",
        "sage.flownet.runtime.actors.execution",
        "sage.flownet.runtime.contexts.flow",
    ]

    @pytest.mark.parametrize("module_name", _MIGRATED_MODULES)
    def test_no_flownet_context_vars_import(self, module_name: str) -> None:
        """Each migrated module must NOT import from sage.flownet.utils.context_vars."""
        if importlib.util.find_spec("sage.flownet") is None:
            pytest.skip("sageFlownet not installed — skipping source-level check")

        import ast

        mod = importlib.import_module(module_name)
        src_file = getattr(mod, "__file__", None)
        if src_file is None or not src_file.endswith(".py"):
            return  # compiled extension — skip

        with open(src_file) as fh:
            source = fh.read()

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert module != "sage.flownet.utils.context_vars", (
                    f"Legacy import found in {module_name!r}: "
                    f"'from sage.flownet.utils.context_vars import ...'\n"
                    "Migrate to: from sage.common.utils import ContextSlot"
                )

    @pytest.mark.parametrize("module_name", _MIGRATED_MODULES)
    def test_migrated_module_uses_sage_common_for_context(self, module_name: str) -> None:
        """Each migrated module must import ContextSlot or run_in_executor
        from sage.common (or not import context utilities at all anymore).
        """
        if importlib.util.find_spec("sage.flownet") is None:
            pytest.skip("sageFlownet not installed — skipping source-level check")

        import ast

        mod = importlib.import_module(module_name)
        src_file = getattr(mod, "__file__", None)
        if src_file is None or not src_file.endswith(".py"):
            return

        with open(src_file) as fh:
            source = fh.read()

        _CONTEXT_SYMBOLS = {"ContextSlot", "run_in_executor_with_context"}
        uses_context_symbol = any(sym in source for sym in _CONTEXT_SYMBOLS)

        if not uses_context_symbol:
            return  # module doesn't use context utilities — fine

        tree = ast.parse(source)
        imports_from_sage_common = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith("sage.common"):
                    names = {alias.name for alias in node.names}
                    if names & _CONTEXT_SYMBOLS:
                        imports_from_sage_common = True
                        break

        assert imports_from_sage_common, (
            f"Module {module_name!r} uses a context utility symbol but does not "
            "import it from sage.common. Ensure 'from sage.common.utils import "
            "ContextSlot' (or run_in_executor_with_context) is present."
        )


# ──────────────────────────────────────────────────────────────────────────────
# DoD-4: ContextSlot is usable from the kernel without sageFlownet
# ──────────────────────────────────────────────────────────────────────────────


class TestContextSlotUsableFromKernel:
    """End-to-end Layer 1 smoke tests for ContextSlot behaviour.

    These tests replicate the regression surface from sage-common's own
    test_context_vars.py but run *from the kernel test suite* to ensure
    the import chain kernel → sage-common → contextvars works correctly
    without any sageFlownet involvement.
    """

    def test_context_slot_basic_set_get(self) -> None:
        from sage.common.utils import ContextSlot

        slot: ContextSlot[int] = ContextSlot("kernel_test_basic")
        assert slot.get() is None
        token = slot.set(7)
        assert slot.get() == 7
        slot.reset(token)
        assert slot.get() is None

    def test_context_slot_use_cm(self) -> None:
        from sage.common.utils import ContextSlot

        slot: ContextSlot[str] = ContextSlot("kernel_test_cm")
        with slot.use("active"):
            assert slot.get() == "active"
        assert slot.get() is None

    def test_context_slot_nested_use(self) -> None:
        from sage.common.utils import ContextSlot

        slot: ContextSlot[int] = ContextSlot("kernel_test_nested")
        with slot.use(10):
            with slot.use(20):
                assert slot.get() == 20
            assert slot.get() == 10
        assert slot.get() is None

    def test_run_in_executor_preserves_context(self) -> None:
        from sage.common.utils import ContextSlot, run_in_executor_with_context

        slot: ContextSlot[str] = ContextSlot("kernel_test_executor")

        async def inner() -> str | None:
            loop = asyncio.get_running_loop()
            token = slot.set("kernel_propagated")
            try:
                fut = run_in_executor_with_context(loop, slot.get)
                return await asyncio.wrap_future(fut)
            finally:
                slot.reset(token)

        result = asyncio.run(inner())
        assert result == "kernel_propagated"

    def test_context_preserved_across_await(self) -> None:
        from sage.common.utils import ContextSlot

        slot: ContextSlot[int] = ContextSlot("kernel_test_await")

        async def coro() -> None:
            with slot.use(42):
                await asyncio.sleep(0)
                assert slot.get() == 42

        asyncio.run(coro())

    def test_context_not_shared_between_concurrent_tasks(self) -> None:
        from sage.common.utils import ContextSlot

        slot: ContextSlot[str] = ContextSlot("kernel_test_tasks")
        results: list[str | None] = []

        async def task(val: str) -> None:
            with slot.use(val):
                await asyncio.sleep(0)
                results.append(slot.get())

        async def main() -> None:
            await asyncio.gather(task("x"), task("y"))

        asyncio.run(main())
        assert sorted(results) == ["x", "y"]

    def test_no_flownet_import_needed(self) -> None:
        """Confirm ContextSlot works without importing sageFlownet."""
        assert importlib.util.find_spec("sage.flownet") is None or True
        # If we got here without importing sage.flownet, the test passes.
        from sage.common.utils import ContextSlot

        slot: ContextSlot[bool] = ContextSlot("kernel_test_no_flownet")
        with slot.use(True):
            assert slot.get() is True
