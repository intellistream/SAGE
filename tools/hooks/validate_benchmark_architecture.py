#!/usr/bin/env python3
"""
Pre-commit hook to validate SAGE benchmark architecture compliance.

This hook ensures that all benchmarks follow the unified CLI architecture:
- All benchmarks must be registered under `sage bench` command
- Benchmark directories should follow naming convention: benchmark_<name>/
- Each benchmark should have a CLI entry point or placeholder

Usage:
    As a pre-commit hook (configured in tools/pre-commit-config.yaml)
    Or run manually: python tools/hooks/validate_benchmark_architecture.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


class BenchmarkArchitectureValidator:
    """Validator for SAGE benchmark architecture compliance."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.benchmark_root = (
            repo_root / "packages" / "sage-benchmark" / "src" / "sage" / "benchmark"
        )
        self.bench_cli_path = (
            repo_root
            / "packages"
            / "sage-cli"
            / "src"
            / "sage"
            / "cli"
            / "commands"
            / "apps"
            / "bench.py"
        )
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_all(self) -> bool:
        """Run all validations. Returns True if all checks pass."""
        if not self.benchmark_root.exists():
            print(f"⚠️  Benchmark root not found: {self.benchmark_root}")
            return True

        print("🔍 Validating SAGE Benchmark Architecture...")

        self.discover_benchmarks()
        self.check_cli_registration()

        return self.report_results()

    def discover_benchmarks(self) -> list[str]:
        """Discover all benchmark_* directories."""
        self.benchmarks: dict[str, Path] = {}

        for item in self.benchmark_root.iterdir():
            if item.is_dir() and item.name.startswith("benchmark_"):
                benchmark_name = item.name.replace("benchmark_", "")
                self.benchmarks[benchmark_name] = item

        print(
            f"   Found {len(self.benchmarks)} benchmark(s): {', '.join(sorted(self.benchmarks.keys()))}"
        )
        return list(self.benchmarks.keys())

    def check_cli_registration(self):
        """Check if benchmarks are registered in sage bench CLI."""
        if not self.bench_cli_path.exists():
            self.errors.append(f"❌ Bench CLI file not found: {self.bench_cli_path}")
            return

        # Read the CLI file content
        cli_content = self.bench_cli_path.read_text()

        # Known registered benchmarks (parse from CLI)
        registered = self._parse_registered_benchmarks(cli_content)
        print(f"   Registered in CLI: {', '.join(sorted(registered)) if registered else '(none)'}")

        # Check each discovered benchmark
        for benchmark_name, benchmark_path in self.benchmarks.items():
            if benchmark_name not in registered:
                # Check if there's a CLI module in the benchmark
                has_cli = self._has_cli_module(benchmark_path)

                if has_cli:
                    self.warnings.append(
                        f"⚠️  Benchmark '{benchmark_name}' has CLI module but NOT registered in `sage bench`.\n"
                        f"      Location: {benchmark_path.relative_to(self.repo_root)}\n"
                        f"      Action: Add to packages/sage-cli/src/sage/cli/commands/apps/bench.py\n"
                        f"      Example:\n"
                        f"        from sage.benchmark.benchmark_{benchmark_name}.cli import create_app\n"
                        f'        app.add_typer(create_app(), name="{benchmark_name}")'
                    )
                else:
                    self.warnings.append(
                        f"⚠️  Benchmark '{benchmark_name}' is NOT registered in `sage bench` CLI.\n"
                        f"      Location: {benchmark_path.relative_to(self.repo_root)}\n"
                        f"      Consider: Creating a CLI module (cli.py) and registering it."
                    )

    def _parse_registered_benchmarks(self, cli_content: str) -> set[str]:
        """Parse CLI file to find registered benchmarks."""
        registered = set()

        # Pattern 1: app.add_typer(..., name="xxx")
        # Match both direct typer apps and imported ones
        add_typer_pattern = r'app\.add_typer\s*\([^)]*name\s*=\s*["\']([^"\']+)["\']'
        for match in re.finditer(add_typer_pattern, cli_content):
            name = match.group(1)
            # Normalize names (e.g., "control-plane" -> "control_plane")
            normalized = name.replace("-", "_")
            registered.add(normalized)

        # Pattern 2: Import from benchmark_xxx modules
        import_pattern = r"from\s+sage\.benchmark\.benchmark_(\w+)"
        for match in re.finditer(import_pattern, cli_content):
            registered.add(match.group(1))

        # Pattern 3: Check for agent/paper subcommands (special case)
        # agent_app contains paper1, paper2 etc which map to benchmark_agent
        if "agent_app" in cli_content and "benchmark_agent" in cli_content:
            registered.add("agent")

        return registered

    def _has_cli_module(self, benchmark_path: Path) -> bool:
        """Check if a benchmark has a CLI module."""
        cli_file = benchmark_path / "cli.py"
        if cli_file.exists():
            # Check if it has create_app or typer.Typer
            content = cli_file.read_text()
            return "typer" in content.lower() or "create_app" in content

        # Also check __main__.py
        main_file = benchmark_path / "__main__.py"
        if main_file.exists():
            content = main_file.read_text()
            return "typer" in content.lower()

        return False

    def report_results(self) -> bool:
        """Report validation results. Returns True if no errors."""
        if not self.errors and not self.warnings:
            print("✅ All benchmark architecture checks passed.")
            return True

        if self.warnings:
            print(f"\n⚠️  Found {len(self.warnings)} warning(s):")
            for warning in self.warnings:
                print(f"\n{warning}")

        if self.errors:
            print(f"\n❌ Found {len(self.errors)} error(s):")
            for error in self.errors:
                print(f"  {error}")
            return False

        print("\n" + "=" * 60)
        print("📋 Benchmark Architecture Guidelines:")
        print("=" * 60)
        print("""
All benchmarks should be accessible via `sage bench <name>` command.

Required structure for a benchmark:
  packages/sage-benchmark/src/sage/benchmark/benchmark_<name>/
  ├── __init__.py
  ├── cli.py              # CLI entry point with create_app() function
  └── ...

Registration in bench.py:
  from sage.benchmark.benchmark_<name>.cli import create_app
  app.add_typer(create_app(), name="<name>", rich_help_panel="Benchmarks")

See existing benchmarks (agent, control-plane) for examples.
""")
        print("=" * 60)

        # Warnings don't cause failure, just inform
        print("\n✅ No errors found (only warnings)")
        return True


def find_repo_root() -> Path:
    """Find repository root by looking for .git directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return Path.cwd()


def main():
    """Main entry point for the validation hook."""
    repo_root = find_repo_root()
    validator = BenchmarkArchitectureValidator(repo_root)

    success = validator.validate_all()
    # Always exit 0 for warnings (don't block commits)
    # Only exit 1 for actual errors
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
