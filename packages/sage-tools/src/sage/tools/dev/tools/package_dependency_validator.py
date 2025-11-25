"""
Package Dependency Validator

Validates SAGE package dependency separation rules in pyproject.toml files.

Rules:
1. Non-meta packages should NOT have isage-* dependencies in [project.dependencies]
2. Packages should use sage-deps for internal SAGE dependencies (except L1 and meta-package)
3. The sage meta-package should reference other packages using [sage-deps] in extras

Migrated from tools/scripts/verify_dependency_separation.sh
"""

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback


@dataclass
class ValidationIssue:
    """Represents a validation issue found in a package."""

    package: str
    severity: str  # "error" or "warning"
    message: str
    details: str = ""


class PackageDependencyValidator:
    """Validates SAGE package dependency separation rules."""

    # Packages that don't need sage-deps
    NO_SAGE_DEPS_REQUIRED = {"sage-common", "sage-cli", "sage"}

    def __init__(self, project_root: Path | str):
        """Initialize validator with project root."""
        self.project_root = Path(project_root)
        self.packages_dir = self.project_root / "packages"

    def validate_all_packages(self) -> tuple[list[ValidationIssue], bool]:
        """
        Validate all packages for dependency separation compliance.

        Returns:
            tuple: (list of issues, overall_pass)
        """
        issues: list[ValidationIssue] = []

        if not self.packages_dir.exists():
            issues.append(
                ValidationIssue(
                    package="project",
                    severity="error",
                    message="packages/ directory not found",
                )
            )
            return issues, False

        # Find all package directories
        for package_dir in sorted(self.packages_dir.iterdir()):
            if not package_dir.is_dir():
                continue

            pyproject_file = package_dir / "pyproject.toml"
            if not pyproject_file.exists():
                continue

            package_name = package_dir.name
            package_issues = self._validate_package(package_name, pyproject_file)
            issues.extend(package_issues)

        # Determine overall pass/fail
        has_errors = any(issue.severity == "error" for issue in issues)
        return issues, not has_errors

    def _validate_package(self, package_name: str, pyproject_file: Path) -> list[ValidationIssue]:
        """Validate a single package's pyproject.toml file."""
        issues: list[ValidationIssue] = []

        try:
            with open(pyproject_file, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            issues.append(
                ValidationIssue(
                    package=package_name,
                    severity="error",
                    message=f"Failed to parse pyproject.toml: {e}",
                )
            )
            return issues

        # Skip if not a project section
        if "project" not in data:
            return issues

        # Rule 1: Check for isage-* in dependencies (except meta-package)
        if package_name != "sage":
            isage_deps = self._find_isage_dependencies(data)
            if isage_deps:
                issues.append(
                    ValidationIssue(
                        package=package_name,
                        severity="error",
                        message="contains isage-* dependencies in [project.dependencies]",
                        details="\n".join(f"  - {dep}" for dep in isage_deps),
                    )
                )

        # Rule 2: Check for sage-deps (except for packages that don't need it)
        if package_name not in self.NO_SAGE_DEPS_REQUIRED:
            if not self._has_sage_deps(data):
                issues.append(
                    ValidationIssue(
                        package=package_name,
                        severity="error",
                        message="missing sage-deps configuration",
                        details="Package should define sage-deps for internal SAGE dependencies",
                    )
                )

        # Rule 3: For sage meta-package, check extras use [sage-deps]
        if package_name == "sage":
            extra_issues = self._validate_meta_package_extras(data)
            issues.extend(extra_issues)

        return issues

    def _find_isage_dependencies(self, data: dict) -> list[str]:
        """Find all isage-* dependencies in [project.dependencies]."""
        isage_deps = []

        if "project" in data and "dependencies" in data["project"]:
            for dep in data["project"]["dependencies"]:
                if isinstance(dep, str) and "isage-" in dep.lower():
                    isage_deps.append(dep.strip())

        return isage_deps

    def _has_sage_deps(self, data: dict) -> bool:
        """Check if package defines sage-deps."""
        if "project" not in data:
            return False

        if "optional-dependencies" not in data["project"]:
            return False

        return "sage-deps" in data["project"]["optional-dependencies"]

    def _validate_meta_package_extras(self, data: dict) -> list[ValidationIssue]:
        """Validate that sage meta-package extras use [sage-deps]."""
        issues: list[ValidationIssue] = []

        if "project" not in data or "optional-dependencies" not in data["project"]:
            return issues

        extras = data["project"]["optional-dependencies"]

        # Check if standard extras reference [sage-deps]
        expected_with_sage_deps = ["standard", "full"]

        for extra_name in expected_with_sage_deps:
            if extra_name not in extras:
                continue

            deps = extras[extra_name]
            # Check if any dependency uses [sage-deps] notation
            has_sage_deps_ref = any(
                "[sage-deps]" in str(dep) for dep in deps if isinstance(dep, str)
            )

            if not has_sage_deps_ref:
                issues.append(
                    ValidationIssue(
                        package="sage",
                        severity="warning",
                        message=f"extra '{extra_name}' may not reference [sage-deps]",
                        details="Expected dependencies to use isage-*[sage-deps] notation",
                    )
                )

        return issues

    def print_results(self, issues: list[ValidationIssue], passed: bool) -> None:
        """Print validation results in a formatted way."""
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()

        if not issues:
            console.print(
                Panel(
                    "[green]✅ All packages pass dependency separation validation![/green]",
                    title="Dependency Validation",
                    border_style="green",
                )
            )
            return

        # Create table for issues
        table = Table(title="Dependency Validation Issues", show_header=True, header_style="bold")
        table.add_column("Package", style="cyan")
        table.add_column("Severity", style="yellow")
        table.add_column("Issue")

        for issue in issues:
            severity_color = "red" if issue.severity == "error" else "yellow"
            severity_text = f"[{severity_color}]{issue.severity.upper()}[/{severity_color}]"

            message = issue.message
            if issue.details:
                message += f"\n{issue.details}"

            table.add_row(issue.package, severity_text, message)

        console.print(table)

        # Print summary
        error_count = sum(1 for issue in issues if issue.severity == "error")
        warning_count = sum(1 for issue in issues if issue.severity == "warning")

        if passed:
            console.print(f"\n[yellow]⚠️  Found {warning_count} warning(s), but no errors[/yellow]")
        else:
            console.print(
                f"\n[red]❌ Found {error_count} error(s) and {warning_count} warning(s)[/red]"
            )
