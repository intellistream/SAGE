"""Aggregate runner for SAGE CLI command tests."""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from rich.console import Console
from rich.table import Table

from .helpers import CLIRunSummary, CLITestCase, run_cases

TEST_MODULES = [
    "sage.tools.tests.test_cli.version_suite",
    "sage.tools.tests.test_cli.config_suite",
    "sage.tools.tests.test_cli.llm_suite",
    "sage.tools.tests.test_cli.doctor_suite",
    "sage.tools.tests.test_cli.dev_suite",
    "sage.tools.tests.test_cli.extensions_suite",
    "sage.tools.tests.test_cli.studio_suite",
    "sage.tools.tests.test_cli.job_suite",
    "sage.tools.tests.test_cli.jobmanager_suite",
    "sage.tools.tests.test_cli.worker_suite",
    "sage.tools.tests.test_cli.cluster_suite",
    "sage.tools.tests.test_cli.head_suite",
]

console = Console()


@dataclass
class CLITestRun:
    cases: List[CLITestCase]
    summary: CLIRunSummary

    @property
    def success(self) -> bool:
        return self.summary.success


def _load_modules() -> Tuple[List[object], List[CLITestCase]]:
    modules: List[object] = []
    cases: List[CLITestCase] = []

    for module_name in TEST_MODULES:
        module = importlib.import_module(module_name)
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
