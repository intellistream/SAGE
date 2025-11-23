"""Aggregate runner for SAGE CLI command tests."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from rich.console import Console
from rich.table import Table

THIS_DIR = Path(__file__).resolve().parent
SUITE_PACKAGE = "sage_cli_suite"

try:  # pragma: no cover - import fallback for direct execution
    from .helpers import CLIRunSummary, CLITestCase, run_cases
except ImportError:  # pragma: no cover
    if __package__ in (None, ""):
        sys.path.insert(0, str(THIS_DIR))
        from helpers import CLIRunSummary  # type: ignore[no-redef]
        from helpers import (
            CLITestCase,
            run_cases,
        )
    else:  # pragma: no cover
        raise
SUITE_FILES: Sequence[str] = (
    "version_suite.py",
    "config_suite.py",
    "llm_suite.py",
    "doctor_suite.py",
    "dev_suite.py",
    "extensions_suite.py",
    # studio_suite.py moved to sage-studio package
    "job_suite.py",
    "jobmanager_suite.py",
    "worker_suite.py",
    "cluster_suite.py",
    "head_suite.py",
)

console = Console()


@dataclass
class CLITestRun:
    cases: list[CLITestCase]
    summary: CLIRunSummary

    @property
    def success(self) -> bool:
        return self.summary.success


def _ensure_package_namespace() -> None:
    if SUITE_PACKAGE not in sys.modules:
        package_module = ModuleType(SUITE_PACKAGE)
        package_module.__path__ = [str(THIS_DIR)]  # type: ignore[attr-defined]
        sys.modules[SUITE_PACKAGE] = package_module

    helpers_module = sys.modules.get(f"{SUITE_PACKAGE}.helpers")
    if helpers_module is None:
        base_helpers = sys.modules.get("helpers")
        if base_helpers is not None:
            sys.modules[f"{SUITE_PACKAGE}.helpers"] = base_helpers


def _load_module_from_path(path: Path) -> ModuleType:
    _ensure_package_namespace()
    module_name = f"{SUITE_PACKAGE}.{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = SUITE_PACKAGE
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def _load_modules() -> tuple[list[ModuleType], list[CLITestCase]]:
    modules: list[ModuleType] = []
    cases: list[CLITestCase] = []

    for filename in SUITE_FILES:
        path = THIS_DIR / filename
        module = _load_module_from_path(path)
        modules.append(module)
        if hasattr(module, "collect_cases"):
            module_cases = list(module.collect_cases())  # type: ignore[attr-defined]
            cases.extend(module_cases)

    return modules, cases


def run_all_cli_tests(*, quiet: bool = False) -> CLITestRun:
    modules, cases = _load_modules()

    summary = run_cases(cases)

    for module in modules:
        cleanup = getattr(module, "cleanup", None)
        if callable(cleanup):
            cleanup()

    if not quiet:
        _render_summary(summary)

    return CLITestRun(cases=cases, summary=summary)


def _render_summary(summary: CLIRunSummary) -> None:
    table = Table(title="SAGE CLI Test Summary")
    table.add_column("Case", style="cyan")
    table.add_column("Exit Code", justify="right")
    table.add_column("Status", style="green")

    for result in summary.results:
        status = "PASS" if result.ok else "FAIL"
        style = "green" if result.ok else "red"
        table.add_row(result.case.name, str(result.exit_code), f"[{style}]{status}[/{style}]")

    console.print(table)

    if summary.failures:
        console.print("[red]❌ CLI tests failed. Detailed outputs:[/red]")
        for failure in summary.failures:
            console.print(f"\n[red]Case:[/red] {failure.case.name}")
            if failure.exception:
                console.print(f"[red]Exception:[/red] {failure.exception!r}")
            if failure.stdout:
                console.print("[yellow]stdout:[/yellow]")
                console.print(failure.stdout)
            if failure.stderr:
                console.print("[yellow]stderr:[/yellow]")
                console.print(failure.stderr)
    else:
        console.print("[green]✅ All CLI tests passed[/green]")


def main(argv: Iterable[str] | None = None) -> int:
    run = run_all_cli_tests(quiet=False)
    return 0 if run.success else 1


if __name__ == "__main__":
    sys.exit(main())
