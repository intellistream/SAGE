"""SAGE Output Path Configuration

Layer: L1 (Foundation - Common Configuration)

This module provides a centralized configuration system for all output paths in SAGE.
All intermediate results, logs, outputs, and temporary files should use this system
to ensure consistent placement.

Supports both development environments and pip-installed environments:
- Development: Uses project_root/.sage/
- Pip-installed: Uses ~/.sage/

Architecture:
    This is a L1 foundation component providing configuration management.
    It does not contain business logic, only path and environment management.
"""

import os
import shutil
from functools import lru_cache
from pathlib import Path


def find_sage_project_root(
    start_path: str | Path | None = None,
) -> Path | None:
    """
    Find SAGE project root directory by looking for characteristic files/directories.

    Args:
        start_path: Starting path for search. If None, uses current working directory.

    Returns:
        Optional[Path]: Project root path if found, None otherwise
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path)

    current = start_path.resolve()

    # Look for SAGE project markers
    while True:
        # Check for specific SAGE project markers
        if any(
            (current / marker).exists()
            for marker in [
                "packages/sage-kernel",
                "packages/sage-common",
                "_version.py",
                "quickstart.sh",
                "packages",
                "scripts",
                "examples",
            ]
        ):
            # Additional check for packages/sage structure
            if (current / "packages" / "sage").exists() or (
                current / "packages" / "sage-common"
            ).exists():
                return current

        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    return None


def get_appropriate_sage_dir(project_root: str | Path | None = None) -> Path:
    """
    Get the appropriate SAGE directory based on environment.

    Priority:
    1. Environment variable SAGE_OUTPUT_DIR
    2. If in development environment: project_root/.sage/
    3. Otherwise: ~/.sage/

    Args:
        project_root: Explicit project root. If None, auto-detect.

    Returns:
        Path: SAGE directory path
    """
    # 1. Check environment variable
    env_dir = os.environ.get("SAGE_OUTPUT_DIR")
    if env_dir:
        sage_dir = Path(env_dir)
        sage_dir.mkdir(parents=True, exist_ok=True)
        return sage_dir

    # 2. Use explicit project root if provided
    if project_root:
        project_root = Path(project_root).resolve()
        sage_dir = project_root / ".sage"
    else:
        # 3. Auto-detect: development vs pip-installed
        detected_root = find_sage_project_root()
        if detected_root:
            # Development environment
            sage_dir = detected_root / ".sage"
        else:
            # Pip-installed or other environment
            sage_dir = Path.home() / ".sage"

    # Ensure directory exists
    sage_dir.mkdir(parents=True, exist_ok=True)
    return sage_dir


class SageOutputPaths:
    """Centralized configuration for SAGE output paths."""

    def __init__(self, project_root: str | Path | None = None):
        """
        Initialize SAGE output paths.

        Args:
            project_root: Project root directory. If None, will auto-detect environment.
        """
        # Use the new intelligent path detection
        self.sage_dir = get_appropriate_sage_dir(project_root)

        # Set project root and environment type
        self.project_root: Path | None
        if project_root:
            self.project_root = Path(project_root).resolve()
            self.is_pip_environment = False  # Explicit project root means dev environment
        else:
            detected_root = find_sage_project_root()
            if detected_root:
                self.project_root = detected_root
                self.is_pip_environment = False  # Found project root means dev environment
            else:
                self.project_root = None
                self.is_pip_environment = True  # No project root means pip-installed

        # Ensure .sage directory and subdirectories exist
        self._ensure_sage_structure()

    def _ensure_sage_structure(self):
        """Ensure .sage directory and required subdirectories exist."""
        # Standard subdirectories in .sage
        subdirs = [
            "logs",
            "output",
            "temp",
            "cache",
            "reports",
            "coverage",
            "test_logs",
            "experiments",
            "issues",
            "states",  # For .sage_states data (rag components state)
            "benchmarks",  # For pytest-benchmark results
            "studio",  # For Angular Studio build outputs
        ]

        # Ensure subdirectories exist
        for subdir in subdirs:
            (self.sage_dir / subdir).mkdir(exist_ok=True)

    @property
    def logs_dir(self) -> Path:
        """Get the logs directory."""
        return self.sage_dir / "logs"

    @property
    def output_dir(self) -> Path:
        """Get the output directory."""
        return self.sage_dir / "output"

    @property
    def temp_dir(self) -> Path:
        """Get the temporary files directory."""
        return self.sage_dir / "temp"

    @property
    def cache_dir(self) -> Path:
        """Get the cache directory."""
        return self.sage_dir / "cache"

    @property
    def reports_dir(self) -> Path:
        """Get the reports directory."""
        return self.sage_dir / "reports"

    @property
    def coverage_dir(self) -> Path:
        """Get the coverage directory."""
        return self.sage_dir / "coverage"

    @property
    def test_logs_dir(self) -> Path:
        """Get the test logs directory."""
        return self.sage_dir / "test_logs"

    @property
    def experiments_dir(self) -> Path:
        """Get the experiments directory."""
        return self.sage_dir / "experiments"

    @property
    def issues_dir(self) -> Path:
        """Get the issues directory."""
        return self.sage_dir / "issues"

    @property
    def states_dir(self) -> Path:
        """Get the states directory (for .sage_states data)."""
        return self.sage_dir / "states"

    @property
    def benchmarks_dir(self) -> Path:
        """Get the benchmarks directory (for pytest-benchmark results)."""
        return self.sage_dir / "benchmarks"

    @property
    def studio_dir(self) -> Path:
        """Get the studio directory (for Angular Studio files)."""
        return self.sage_dir / "studio"

    @property
    def studio_dist_dir(self) -> Path:
        """Get the studio dist directory (for Angular Studio build outputs)."""
        return self.studio_dir / "dist"

    def get_test_env_dir(self, test_name: str = "test_env") -> Path:
        """
        Get a test environment directory path.

        Args:
            test_name: Name of the test environment

        Returns:
            Path to test environment directory in .sage/temp/
        """
        test_dir = self.temp_dir / test_name
        test_dir.mkdir(parents=True, exist_ok=True)
        return test_dir

    def get_test_context_dir(self, context_name: str = "test_context") -> Path:
        """
        Get a test context directory path.

        Args:
            context_name: Name of the test context

        Returns:
            Path to test context directory in .sage/temp/
        """
        context_dir = self.temp_dir / context_name
        context_dir.mkdir(parents=True, exist_ok=True)
        return context_dir

    def get_ray_temp_dir(self) -> Path:
        """Get Ray temporary files directory."""
        ray_dir = self.temp_dir / "ray"
        ray_dir.mkdir(parents=True, exist_ok=True)
        return ray_dir

    def setup_environment_variables(self):
        """Set up environment variables for SAGE and other tools."""
        # Core SAGE paths
        os.environ["SAGE_OUTPUT_DIR"] = str(self.sage_dir)
        os.environ["SAGE_HOME"] = str(self.sage_dir)
        os.environ["SAGE_LOGS_DIR"] = str(self.logs_dir)
        os.environ["SAGE_TEMP_DIR"] = str(self.temp_dir)

        # Ray-specific environment
        ray_temp_dir = self.get_ray_temp_dir()
        os.environ["RAY_TMPDIR"] = str(ray_temp_dir)

        return {
            "sage_dir": self.sage_dir,
            "logs_dir": self.logs_dir,
            "temp_dir": self.temp_dir,
            "ray_temp_dir": ray_temp_dir,
        }

    def get_log_file(self, name: str, subdir: str | None = None) -> Path:
        """
        Get a log file path.

        Args:
            name: Log file name
            subdir: Optional subdirectory within logs

        Returns:
            Path to log file
        """
        if subdir:
            log_dir = self.logs_dir / subdir
            log_dir.mkdir(exist_ok=True)
            return log_dir / name
        return self.logs_dir / name

    def get_output_file(self, name: str, subdir: str | None = None) -> Path:
        """
        Get an output file path.

        Args:
            name: Output file name
            subdir: Optional subdirectory within output

        Returns:
            Path to output file
        """
        if subdir:
            output_dir = self.output_dir / subdir
            output_dir.mkdir(parents=True, exist_ok=True)
            return output_dir / name
        return self.output_dir / name

    def get_temp_file(self, name: str, subdir: str | None = None) -> Path:
        """
        Get a temporary file path.

        Args:
            name: Temp file name
            subdir: Optional subdirectory within temp

        Returns:
            Path to temp file
        """
        if subdir:
            temp_dir = self.temp_dir / subdir
            temp_dir.mkdir(parents=True, exist_ok=True)
            return temp_dir / name
        return self.temp_dir / name

    def get_cache_file(self, name: str, subdir: str | None = None) -> Path:
        """
        Get a cache file path.

        Args:
            name: Cache file name
            subdir: Optional subdirectory within cache

        Returns:
            Path to cache file
        """
        if subdir:
            cache_dir = self.cache_dir / subdir
            cache_dir.mkdir(parents=True, exist_ok=True)
            return cache_dir / name
        return self.cache_dir / name

    def migrate_existing_outputs(self):
        """
        Migrate existing output files from project root to .sage directory.

        This method will move files from:
        - logs/ -> .sage/logs/
        - output/ -> .sage/output/
        """
        # Skip migration if project_root is None or same as sage_dir parent
        if self.project_root is None or not self.project_root.exists():
            return

        migrations = [
            (self.project_root / "logs", self.logs_dir),
            (self.project_root / "output", self.output_dir),
        ]

        for src, dst in migrations:
            if src.exists() and src != dst:
                print(f"Migrating {src} -> {dst}")

                # Ensure destination directory exists
                dst.mkdir(parents=True, exist_ok=True)

                # Move all files and subdirectories
                for item in src.iterdir():
                    dst_item = dst / item.name
                    if item.is_dir():
                        if dst_item.exists():
                            # Merge directories
                            shutil.copytree(item, dst_item, dirs_exist_ok=True)
                            shutil.rmtree(item)
                        else:
                            shutil.move(str(item), str(dst_item))
                    else:
                        if dst_item.exists():
                            # Backup existing file
                            backup_name = f"{dst_item.name}.backup"
                            dst_item.rename(dst_item.parent / backup_name)
                        shutil.move(str(item), str(dst_item))

                # Remove empty source directory
                try:
                    src.rmdir()
                except OSError:
                    print(f"Warning: Could not remove {src} (not empty)")


# Global cached instance (use normalized project_root key to avoid unexpected
# cache behavior when Path/str objects differ between callers). We expose
# `cache_clear` on the public `get_sage_paths` so tests that call
# `get_sage_paths.cache_clear()` continue to work.
@lru_cache(maxsize=8)
def _get_sage_paths_cached(project_root_key: str | None) -> SageOutputPaths:
    """Internal cached constructor keyed by normalized project_root string."""
    if project_root_key is None:
        return SageOutputPaths(None)
    return SageOutputPaths(Path(project_root_key))


def get_sage_paths(project_root: str | Path | None = None) -> SageOutputPaths:
    """Get the global SAGE output paths instance.

    This wrapper normalizes the project_root to an absolute string and uses
    the internal cached function. Tests expect a `cache_clear` attribute on
    `get_sage_paths`; attach it from the cached function.
    """
    project_root_key = None if project_root is None else str(Path(project_root).resolve())
    return _get_sage_paths_cached(project_root_key)


# Expose cache_clear on the public function for backward compatibility
get_sage_paths.cache_clear = _get_sage_paths_cached.cache_clear


# Convenience functions for backward compatibility and ease of use
def get_logs_dir(project_root: str | Path | None = None) -> Path:
    """Get the logs directory."""
    return get_sage_paths(project_root).logs_dir


def get_output_dir(project_root: str | Path | None = None) -> Path:
    """Get the output directory."""
    return get_sage_paths(project_root).output_dir


def get_temp_dir(project_root: str | Path | None = None) -> Path:
    """Get the temp directory."""
    return get_sage_paths(project_root).temp_dir


def get_cache_dir(project_root: str | Path | None = None) -> Path:
    """Get the cache directory."""
    return get_sage_paths(project_root).cache_dir


def get_reports_dir(project_root: str | Path | None = None) -> Path:
    """Get the reports directory."""
    return get_sage_paths(project_root).reports_dir


def get_coverage_dir(project_root: str | Path | None = None) -> Path:
    """Get the coverage directory."""
    return get_sage_paths(project_root).coverage_dir


def get_benchmarks_dir(project_root: str | Path | None = None) -> Path:
    """Get the benchmarks directory."""
    return get_sage_paths(project_root).benchmarks_dir


def get_ray_temp_dir(project_root: str | Path | None = None) -> Path:
    """Get Ray temporary files directory."""
    return get_sage_paths(project_root).get_ray_temp_dir()


def setup_sage_environment(project_root: str | Path | None = None) -> dict:
    """Set up SAGE environment variables and return directory paths."""
    return get_sage_paths(project_root).setup_environment_variables()


# Main initialization function
def initialize_sage_paths(
    project_root: str | Path | None = None,
) -> "SageOutputPaths":
    """
    Initialize SAGE paths and set up environment.

    This is the main entry point for path initialization.
    It creates all necessary directories and sets up environment variables.

    Args:
        project_root: Optional project root path. If None, auto-detected.

    Returns:
        SageOutputPaths instance with all paths configured.
    """
    paths = get_sage_paths(project_root)
    paths.setup_environment_variables()
    return paths


def get_log_file(
    name: str,
    subdir: str | None = None,
    project_root: str | Path | None = None,
) -> Path:
    """Get a log file path."""
    return get_sage_paths(project_root).get_log_file(name, subdir)


def get_output_file(
    name: str,
    subdir: str | None = None,
    project_root: str | Path | None = None,
) -> Path:
    """Get an output file path."""
    return get_sage_paths(project_root).get_output_file(name, subdir)


def get_states_dir(project_root: str | Path | None = None) -> Path:
    """Get the states directory."""
    return get_sage_paths(project_root).states_dir


def get_states_file(
    name: str,
    subdir: str | None = None,
    project_root: str | Path | None = None,
) -> Path:
    """Get a states file path."""
    sage_paths = get_sage_paths(project_root)
    if subdir:
        states_dir = sage_paths.states_dir / subdir
        states_dir.mkdir(parents=True, exist_ok=True)
        return states_dir / name
    return sage_paths.states_dir / name


def migrate_existing_outputs(project_root: str | Path | None = None):
    """Migrate existing outputs to .sage directory."""
    get_sage_paths(project_root).migrate_existing_outputs()


# Testing utilities
def get_test_env_dir(test_name: str = "test_env", project_root: str | Path | None = None) -> Path:
    """Get a test environment directory path in .sage/temp/."""
    return get_sage_paths(project_root).get_test_env_dir(test_name)


def get_test_context_dir(
    context_name: str = "test_context", project_root: str | Path | None = None
) -> Path:
    """Get a test context directory path in .sage/temp/."""
    return get_sage_paths(project_root).get_test_context_dir(context_name)


def get_test_temp_dir(temp_name: str, project_root: str | Path | None = None) -> Path:
    """Get a temporary directory for testing in .sage/temp/."""
    sage_paths = get_sage_paths(project_root)
    temp_dir = sage_paths.temp_dir / temp_name
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir
