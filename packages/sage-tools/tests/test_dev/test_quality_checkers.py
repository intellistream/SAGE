"""
Tests for quality checker CLI commands.

Tests the new sage dev check-* commands:
- check-architecture
- check-devnotes
- check-readme
- check-all
"""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from sage.tools.cli.commands.dev.main import app

runner = CliRunner()


class TestArchitectureChecker:
    """Tests for sage dev check-architecture command."""

    def test_check_architecture_help(self):
        """Test that help text is displayed."""
        result = runner.invoke(app, ["check-architecture", "--help"])
        assert result.exit_code == 0
        assert "架构合规性" in result.stdout or "architecture" in result.stdout.lower()

    def test_check_architecture_project_not_found(self):
        """Test behavior when project root doesn't exist."""
        result = runner.invoke(
            app, ["check-architecture", "--project-root", "/nonexistent/path"]
        )
        assert result.exit_code == 1
        assert "不存在" in result.stdout or "exist" in result.stdout.lower()

    @pytest.mark.skipif(
        not Path(".").resolve().name == "SAGE",
        reason="Only run in SAGE project root",
    )
    def test_check_architecture_basic(self):
        """Test basic architecture check (may fail, but shouldn't crash)."""
        result = runner.invoke(app, ["check-architecture", "--changed-only"])
        # Command should run without crashing
        assert "架构" in result.stdout or "architecture" in result.stdout.lower()


class TestDevNotesChecker:
    """Tests for sage dev check-devnotes command."""

    def test_check_devnotes_help(self):
        """Test that help text is displayed."""
        result = runner.invoke(app, ["check-devnotes", "--help"])
        assert result.exit_code == 0
        assert "dev-notes" in result.stdout.lower() or "文档" in result.stdout

    def test_check_devnotes_project_not_found(self):
        """Test behavior when project root doesn't exist."""
        result = runner.invoke(
            app, ["check-devnotes", "--project-root", "/nonexistent/path"]
        )
        assert result.exit_code == 1

    @pytest.mark.skipif(
        not Path(".").resolve().name == "SAGE",
        reason="Only run in SAGE project root",
    )
    def test_check_devnotes_structure(self):
        """Test directory structure check."""
        result = runner.invoke(app, ["check-devnotes", "--check-structure"])
        # Command should run
        assert "文档" in result.stdout or "devnotes" in result.stdout.lower()


class TestPackageREADMEChecker:
    """Tests for sage dev check-readme command."""

    def test_check_readme_help(self):
        """Test that help text is displayed."""
        result = runner.invoke(app, ["check-readme", "--help"])
        assert result.exit_code == 0
        assert "readme" in result.stdout.lower()

    def test_check_readme_project_not_found(self):
        """Test behavior when project root doesn't exist."""
        result = runner.invoke(
            app, ["check-readme", "--project-root", "/nonexistent/path"]
        )
        assert result.exit_code == 1

    @pytest.mark.skipif(
        not Path(".").resolve().name == "SAGE",
        reason="Only run in SAGE project root",
    )
    def test_check_readme_basic(self):
        """Test basic README check."""
        result = runner.invoke(app, ["check-readme"])
        # Command should run
        assert "readme" in result.stdout.lower() or "质量" in result.stdout


class TestCheckAll:
    """Tests for sage dev check-all convenience command."""

    def test_check_all_help(self):
        """Test that help text is displayed."""
        result = runner.invoke(app, ["check-all", "--help"])
        assert result.exit_code == 0
        assert "所有" in result.stdout or "all" in result.stdout.lower()

    def test_check_all_project_not_found(self):
        """Test behavior when project root doesn't exist."""
        result = runner.invoke(app, ["check-all", "--project-root", "/nonexistent/path"])
        assert result.exit_code == 1

    @pytest.mark.skipif(
        not Path(".").resolve().name == "SAGE",
        reason="Only run in SAGE project root",
    )
    def test_check_all_continue_on_error(self):
        """Test that --continue-on-error runs all checks."""
        result = runner.invoke(
            app, ["check-all", "--changed-only", "--continue-on-error"]
        )
        # All three checks should be mentioned
        assert "架构" in result.stdout or "architecture" in result.stdout.lower()
        assert "文档" in result.stdout or "devnotes" in result.stdout.lower()
        assert "readme" in result.stdout.lower()

    @pytest.mark.skipif(
        not Path(".").resolve().name == "SAGE",
        reason="Only run in SAGE project root",
    )
    def test_check_all_shows_summary(self):
        """Test that summary is shown."""
        result = runner.invoke(app, ["check-all", "--changed-only", "--continue-on-error"])
        # Should show summary
        assert "汇总" in result.stdout or "summary" in result.stdout.lower()


class TestQualityIntegration:
    """Tests for integration with sage dev quality command."""

    def test_quality_with_architecture_option(self):
        """Test quality command with --architecture option."""
        result = runner.invoke(app, ["quality", "--help"])
        assert result.exit_code == 0
        # Help should mention architecture option
        assert "--architecture" in result.stdout or "--no-architecture" in result.stdout

    def test_quality_with_devnotes_option(self):
        """Test quality command with --devnotes option."""
        result = runner.invoke(app, ["quality", "--help"])
        assert result.exit_code == 0
        # Help should mention devnotes option
        assert "--devnotes" in result.stdout or "--no-devnotes" in result.stdout

    def test_quality_with_readme_option(self):
        """Test quality command with --readme option."""
        result = runner.invoke(app, ["quality", "--help"])
        assert result.exit_code == 0
        # Help should mention readme option
        assert "--readme" in result.stdout


# Smoke tests for checker classes
class TestCheckerClasses:
    """Basic smoke tests for the checker classes themselves."""

    def test_architecture_checker_import(self):
        """Test that ArchitectureChecker can be imported."""
        from sage.tools.dev.tools.architecture_checker import ArchitectureChecker

        assert ArchitectureChecker is not None

    def test_devnotes_checker_import(self):
        """Test that DevNotesChecker can be imported."""
        from sage.tools.dev.tools.devnotes_checker import DevNotesChecker

        assert DevNotesChecker is not None

    def test_package_readme_checker_import(self):
        """Test that PackageREADMEChecker can be imported."""
        from sage.tools.dev.tools.package_readme_checker import PackageREADMEChecker

        assert PackageREADMEChecker is not None

    @pytest.mark.skipif(
        not Path(".").resolve().name == "SAGE",
        reason="Only run in SAGE project root",
    )
    def test_architecture_checker_instantiation(self):
        """Test that ArchitectureChecker can be instantiated."""
        from sage.tools.dev.tools.architecture_checker import ArchitectureChecker

        checker = ArchitectureChecker(root_dir=".")
        assert checker is not None

    @pytest.mark.skipif(
        not Path(".").resolve().name == "SAGE",
        reason="Only run in SAGE project root",
    )
    def test_devnotes_checker_instantiation(self):
        """Test that DevNotesChecker can be instantiated."""
        from sage.tools.dev.tools.devnotes_checker import DevNotesChecker

        checker = DevNotesChecker(root_dir=".")
        assert checker is not None

    @pytest.mark.skipif(
        not Path(".").resolve().name == "SAGE",
        reason="Only run in SAGE project root",
    )
    def test_package_readme_checker_instantiation(self):
        """Test that PackageREADMEChecker can be instantiated."""
        from sage.tools.dev.tools.package_readme_checker import PackageREADMEChecker

        checker = PackageREADMEChecker(root_dir=".")
        assert checker is not None
