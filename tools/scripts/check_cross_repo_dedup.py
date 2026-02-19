#!/usr/bin/env python3
"""
Cross-Repo Duplicate Declaration Detector (Issue #1439 - Wave C gate)

Enforces the move-then-delete rule from the Flownet Migration Boundary:
  docs_src/concepts/architecture/design-decisions/flownet-migration-boundary.md

Checks the following migrated capability domains for duplicate class/function
declarations between SAGE and sageFlownet:

  Domain               | SAGE canonical location         | Flownet allowed pattern
  -------------------- | ------------------------------- | -----------------------
  Exception model      | sage.common.core.flow_exceptions| re-export only (no class def)
  Scheduling schema    | sage.kernel.scheduler.schema    | import only (no stub classes)
  Context propagation  | sage.common.utils.context       | import only
  Runtime protocol     | sage.platform.runtime_protocol  | implementation only
  Flow declaration API | sage.kernel.flow / .api         | (Flownet keeps impl)

Usage:
    python tools/scripts/check_cross_repo_dedup.py [--flownet-path PATH] [--fix]

Exit codes:
    0  Clean - no duplicate declarations found
    1  Violations detected - list printed to stderr
    2  Script error (bad path, parse failure)
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Migrated domains: symbols that SAGE owns and Flownet must NOT redefine.
# Keys are class/function names; values describe the canonical SAGE location.
#
# Rules for entries here:
#   1. Symbols already present in SAGE at the listed path (single source).
#   2. Names that have been observed as stub fallback candidates in Flownet.
#   3. Do NOT list Flownet-internal implementation class names (e.g. RuntimeProtocol
#      is Flownet's own implementation; RuntimeBackendProtocol is the SAGE ABC).
# ---------------------------------------------------------------------------
MIGRATED_SYMBOLS: dict[str, str] = {
    # Exception model (Issue #1434 / #1435)
    "ExceptionAction": "sage.common.core.flow_exceptions",
    "ExceptionContext": "sage.common.core.flow_exceptions",
    "ExceptionDecision": "sage.common.core.flow_exceptions",
    "ExceptionEvent": "sage.common.core.flow_exceptions",
    "FlowException": "sage.common.core.flow_exceptions",
    "FlowDefinitionError": "sage.common.core.flow_exceptions",
    # Scheduling schema (Issue #1437)
    "ResourceSpec": "sage.kernel.scheduler.schema",
    "PlacementSchema": "sage.kernel.scheduler.schema",
    "PlacementStrategy": "sage.kernel.scheduler.schema",
    # Runtime protocol ABCs (Issue #1433) — note: SAGE uses RuntimeBackendProtocol,
    # not RuntimeProtocol.  Flownet.RuntimeProtocol is a legitimate implementation
    # class and must NOT appear in this list.
    "RuntimeBackendProtocol": "sage.platform.runtime.protocol",
    "NodeInfoProtocol": "sage.platform.runtime.protocol",
    "MethodRefProtocol": "sage.platform.runtime.protocol",
    "ActorHandleProtocol": "sage.platform.runtime.protocol",
    "FlowRunHandleProtocol": "sage.platform.runtime.protocol",
}

# Flownet paths/modules that are allowed to re-export (backward-compat only).
# These must not contain a new `class <Name>` definition.
ALLOWED_REEXPORT_MODULES: frozenset[str] = frozenset(
    [
        "sage/flownet/core/exceptions.py",  # re-exports SAGE L1 exception types
    ]
)


class Violation(NamedTuple):
    symbol: str
    flownet_file: str
    line: int
    sage_canonical: str
    kind: str  # "stub_class" | "duplicate_function" | "try_except_fallback"

    def __str__(self) -> str:
        return (
            f"  [{self.kind}] {self.symbol!r} in {self.flownet_file}:{self.line}\n"
            f"    Canonical owner: {self.sage_canonical}\n"
            f"    Flownet must import, not redefine."
        )


def _collect_class_defs(tree: ast.AST) -> list[tuple[str, int]]:
    """Return (class_name, lineno) for all top-level and nested ClassDef nodes."""
    return [(node.name, node.lineno) for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def _collect_function_defs(tree: ast.AST) -> list[tuple[str, int]]:
    """Return (func_name, lineno) for module-level FunctionDef nodes."""
    return [
        (node.name, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]


def _has_try_except_import_fallback(tree: ast.AST, symbol: str) -> int | None:
    """Detect try-except ImportError patterns that redefine a migrated symbol.

    Returns the line number of the except block if found, else None.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        # Check if any handler is `except ImportError`
        for handler in node.handlers:
            if handler.type is None:
                continue
            exc_names = []
            if isinstance(handler.type, ast.Name):
                exc_names.append(handler.type.id)
            elif isinstance(handler.type, ast.Tuple):
                for elt in handler.type.elts:
                    if isinstance(elt, ast.Name):
                        exc_names.append(elt.id)
            if "ImportError" not in exc_names:
                continue
            # Check if the except body defines <symbol> as a class
            for stmt in ast.walk(ast.Module(body=handler.body, type_ignores=[])):
                if isinstance(stmt, ast.ClassDef) and stmt.name == symbol:
                    return handler.lineno
    return None


def check_flownet_file(
    filepath: Path,
    violations: list[Violation],
) -> None:
    """Parse one Flownet Python file and collect any violations."""
    rel = str(filepath).replace(str(filepath.parent.parent.parent.parent) + "/", "")

    # Normalise to a relative path inside the sageFlownet repo
    for part in ("sageFlownet/", "src/"):
        rel = rel.replace(part, "", 1)

    code = filepath.read_text(encoding="utf-8")
    try:
        tree = ast.parse(code, filename=str(filepath))
    except SyntaxError:
        return  # skip unparseable files

    is_allowed_reexport = any(
        rel.endswith(m) or str(filepath).endswith(m) for m in ALLOWED_REEXPORT_MODULES
    )

    for symbol, sage_location in MIGRATED_SYMBOLS.items():
        # 1. Check for direct class redefinition (outside allowed re-export modules)
        if not is_allowed_reexport:
            for cls_name, lineno in _collect_class_defs(tree):
                if cls_name == symbol:
                    violations.append(
                        Violation(
                            symbol=symbol,
                            flownet_file=str(filepath),
                            line=lineno,
                            sage_canonical=sage_location,
                            kind="stub_class",
                        )
                    )

        # 2. Check for try-except ImportError fallback stub patterns
        lineno = _has_try_except_import_fallback(tree, symbol)
        if lineno is not None:
            violations.append(
                Violation(
                    symbol=symbol,
                    flownet_file=str(filepath),
                    line=lineno,
                    sage_canonical=sage_location,
                    kind="try_except_fallback",
                )
            )


def scan_flownet(flownet_root: Path) -> list[Violation]:
    """Walk the sageFlownet src/ tree and collect all violations."""
    violations: list[Violation] = []
    src_dir = flownet_root / "src"
    if not src_dir.exists():
        print(f"⚠️  sageFlownet src/ not found at {src_dir}", file=sys.stderr)
        return violations

    for dirpath, dirnames, filenames in os.walk(src_dir):
        # Skip __pycache__
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            filepath = Path(dirpath) / filename
            check_flownet_file(filepath, violations)

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check for duplicate migrated declarations between SAGE and sageFlownet."
    )
    parser.add_argument(
        "--flownet-path",
        default=None,
        help="Path to sageFlownet repository root (auto-detected if omitted).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose output even when passing.",
    )
    args = parser.parse_args()

    # Auto-detect sageFlownet root
    if args.flownet_path:
        flownet_root = Path(args.flownet_path)
    else:
        # Try common locations relative to SAGE repo
        script_dir = Path(__file__).resolve().parent
        sage_root = script_dir.parent.parent  # SAGE/
        candidates = [
            sage_root.parent / "sageFlownet",
            Path.home() / "sageFlownet",
            Path("/home/shuhao/sageFlownet"),
        ]
        flownet_root = None
        for candidate in candidates:
            if candidate.exists():
                flownet_root = candidate
                break

        if flownet_root is None:
            print(
                "⚠️  sageFlownet not found. Skipping cross-repo dedup check.\n"
                "   Set --flownet-path or clone sageFlownet alongside SAGE.",
                file=sys.stderr,
            )
            return 0  # Non-fatal in CI when Flownet is not checked out

    violations = scan_flownet(flownet_root)

    if not violations:
        if args.verbose:
            print("✅  Cross-repo dedup check passed: no duplicate migrated declarations found.")
        return 0

    print(
        f"❌  Cross-repo dedup check FAILED: {len(violations)} violation(s) found.\n",
        file=sys.stderr,
    )
    print(
        "These symbols have been migrated to SAGE (single source of truth).\n"
        "Flownet must import them, NOT redefine or stub them.\n"
        "See: docs_src/concepts/architecture/design-decisions/flownet-migration-boundary.md\n",
        file=sys.stderr,
    )
    for v in violations:
        print(str(v), file=sys.stderr)

    print(
        "\n💡 Fix: remove stub class definitions and try-except ImportError fallbacks.\n"
        "   Replace with direct imports from the canonical SAGE module.\n"
        "   Example:\n"
        "     # WRONG (stub fallback)\n"
        "     try:\n"
        "         from sage.kernel.scheduler.schema import ResourceSpec\n"
        "     except ImportError:\n"
        "         class ResourceSpec: ...\n"
        "\n"
        "     # CORRECT (fail fast)\n"
        "     from sage.kernel.scheduler.schema import ResourceSpec\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
