"""
Package Dependency Validator Tests

Tests for the PackageDependencyValidator ensuring strict isage-* dependency rules.
"""

import tempfile
from pathlib import Path

import pytest

from sage.tools.dev.tools.package_dependency_validator import (
    PackageDependencyValidator,
)


@pytest.fixture
def temp_packages_dir():
    """Create a temporary packages directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        packages_dir = Path(tmpdir) / "packages"
        packages_dir.mkdir()
        yield Path(tmpdir)


def create_pyproject(package_dir: Path, content: str) -> Path:
    """Helper to create a pyproject.toml file."""
    package_dir.mkdir(exist_ok=True)
    pyproject = package_dir / "pyproject.toml"
    pyproject.write_text(content)
    return pyproject


@pytest.mark.unit
class TestPackageDependencyValidator:
    """Tests for PackageDependencyValidator."""

    def test_isage_in_dependencies_is_error(self, temp_packages_dir):
        """Test that isage-* in [project.dependencies] is always an error for non-meta packages."""
        # Create a package with isage-common in dependencies
        pkg_dir = temp_packages_dir / "packages" / "sage-tools"
        create_pyproject(
            pkg_dir,
            """
[project]
name = "isage-tools"
dependencies = [
    "isage-common>=0.1.0",
    "typer>=0.9.0",
]

[project.optional-dependencies]
sage-deps = []
""",
        )

        validator = PackageDependencyValidator(temp_packages_dir)
        issues, passed = validator.validate_all_packages()

        # Should fail with an error (not a warning)
        assert not passed
        assert len(issues) >= 1

        # Find the isage-* dependency issue
        isage_issue = next(
            (i for i in issues if "isage-*" in i.message or "isage-common" in i.details),
            None,
        )
        assert isage_issue is not None
        assert isage_issue.severity == "error"
        assert isage_issue.package == "sage-tools"

    def test_sage_tools_with_isage_common_is_error(self, temp_packages_dir):
        """Test that sage-tools with isage-common in dependencies fails as error (no exception)."""
        # Create sage-tools package with isage-common in dependencies
        pkg_dir = temp_packages_dir / "packages" / "sage-tools"
        create_pyproject(
            pkg_dir,
            """
[project]
name = "isage-tools"
dependencies = [
    "isage-common>=0.1.0",
]

[project.optional-dependencies]
sage-deps = []
""",
        )

        validator = PackageDependencyValidator(temp_packages_dir)
        issues, passed = validator.validate_all_packages()

        # The old behavior would pass this as a warning
        # The new behavior should fail with an error
        assert not passed

        # Find the error issue
        error_issues = [i for i in issues if i.severity == "error"]
        assert len(error_issues) >= 1

        # The error should be about isage-* in dependencies
        isage_error = next(
            (i for i in error_issues if "isage-*" in i.message),
            None,
        )
        assert isage_error is not None
        assert isage_error.package == "sage-tools"

    def test_isage_in_sage_deps_is_allowed(self, temp_packages_dir):
        """Test that isage-* in sage-deps optional dependency is allowed."""
        # Create a package with isage-common only in sage-deps
        pkg_dir = temp_packages_dir / "packages" / "sage-tools"
        create_pyproject(
            pkg_dir,
            """
[project]
name = "isage-tools"
dependencies = [
    "typer>=0.9.0",
]

[project.optional-dependencies]
sage-deps = [
    "isage-common>=0.1.0",
]
""",
        )

        validator = PackageDependencyValidator(temp_packages_dir)
        issues, passed = validator.validate_all_packages()

        # Should pass without isage-* dependency errors
        isage_issues = [i for i in issues if "isage-*" in i.message and i.severity == "error"]
        assert len(isage_issues) == 0

    def test_meta_package_allowed_isage_deps(self, temp_packages_dir):
        """Test that sage meta-package is allowed to have isage-* in dependencies."""
        # Create the sage meta-package with isage-* dependencies
        pkg_dir = temp_packages_dir / "packages" / "sage"
        create_pyproject(
            pkg_dir,
            """
[project]
name = "isage"
dependencies = [
    "isage-common>=0.1.0",
    "isage-kernel>=0.1.0",
]

[project.optional-dependencies]
standard = [
    "isage-apps[sage-deps]>=0.1.0",
]
full = [
    "isage-studio[sage-deps]>=0.1.0",
]
""",
        )

        validator = PackageDependencyValidator(temp_packages_dir)
        issues, passed = validator.validate_all_packages()

        # Should not have isage-* dependency errors for the meta-package
        meta_package_errors = [i for i in issues if i.package == "sage" and "isage-*" in i.message]
        assert len(meta_package_errors) == 0

    def test_missing_sage_deps_is_error(self, temp_packages_dir):
        """Test that non-L1 packages without sage-deps are flagged."""
        # Create a package without sage-deps
        pkg_dir = temp_packages_dir / "packages" / "sage-kernel"
        create_pyproject(
            pkg_dir,
            """
[project]
name = "isage-kernel"
dependencies = [
    "numpy>=1.24.0",
]

[project.optional-dependencies]
dev = []
""",
        )

        validator = PackageDependencyValidator(temp_packages_dir)
        issues, passed = validator.validate_all_packages()

        # Should have missing sage-deps error
        sage_deps_issues = [i for i in issues if "sage-deps" in i.message]
        assert len(sage_deps_issues) >= 1
        assert sage_deps_issues[0].severity == "error"

    def test_l1_package_no_sage_deps_required(self, temp_packages_dir):
        """Test that L1 packages (sage-common) don't require sage-deps."""
        # Create sage-common without sage-deps
        pkg_dir = temp_packages_dir / "packages" / "sage-common"
        create_pyproject(
            pkg_dir,
            """
[project]
name = "isage-common"
dependencies = [
    "pyyaml>=6.0",
]
""",
        )

        validator = PackageDependencyValidator(temp_packages_dir)
        issues, passed = validator.validate_all_packages()

        # Should not have sage-deps missing error for sage-common
        common_issues = [
            i for i in issues if i.package == "sage-common" and "sage-deps" in i.message
        ]
        assert len(common_issues) == 0

    def test_multiple_isage_deps_all_reported(self, temp_packages_dir):
        """Test that all isage-* dependencies in [project.dependencies] are reported."""
        # Create a package with multiple isage-* dependencies
        pkg_dir = temp_packages_dir / "packages" / "sage-middleware"
        create_pyproject(
            pkg_dir,
            """
[project]
name = "isage-middleware"
dependencies = [
    "isage-common>=0.1.0",
    "isage-kernel>=0.1.0",
    "isage-libs>=0.1.0",
]

[project.optional-dependencies]
sage-deps = []
""",
        )

        validator = PackageDependencyValidator(temp_packages_dir)
        issues, passed = validator.validate_all_packages()

        # Should fail
        assert not passed

        # Find the middleware issue
        middleware_issue = next(
            (i for i in issues if i.package == "sage-middleware" and "isage-*" in i.message),
            None,
        )
        assert middleware_issue is not None
        assert middleware_issue.severity == "error"

        # All three dependencies should be in the details
        assert "isage-common" in middleware_issue.details
        assert "isage-kernel" in middleware_issue.details
        assert "isage-libs" in middleware_issue.details
