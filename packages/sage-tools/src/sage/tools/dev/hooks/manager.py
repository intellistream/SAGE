"""
Git Hooks Manager for SAGE Development.

Provides high-level management interface for Git hooks.
"""

from pathlib import Path

from .installer import HooksInstaller


class HooksManager:
    """Manager for SAGE Git hooks."""

    def __init__(self, root_dir: Path | None = None):
        """
        Initialize the hooks manager.

        Args:
            root_dir: Root directory of the SAGE project.
        """
        self.root_dir = root_dir
        self.installer = HooksInstaller(root_dir=root_dir)

    def install(self, quiet: bool = False) -> bool:
        """
        Install Git hooks.

        Args:
            quiet: If True, suppress non-error output.

        Returns:
            True if installation was successful, False otherwise.
        """
        self.installer.quiet = quiet
        return self.installer.install()

    def uninstall(self, quiet: bool = False) -> bool:
        """
        Uninstall Git hooks.

        Args:
            quiet: If True, suppress non-error output.

        Returns:
            True if uninstallation was successful, False otherwise.
        """
        self.installer.quiet = quiet
        return self.installer.uninstall()

    def status(self) -> dict:
        """
        Get the status of installed hooks.

        Returns:
            Dictionary with hook status information.
        """
        return self.installer.status()

    def print_status(self) -> None:
        """Print the status of installed hooks."""
        self.installer.print_status()
