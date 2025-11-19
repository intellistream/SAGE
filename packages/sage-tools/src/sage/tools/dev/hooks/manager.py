"""
Git Hooks Manager for SAGE Development.

Provides high-level management interface for Git hooks.
"""

from pathlib import Path

from .installer import HooksInstaller


class HooksManager:
    """Manager for SAGE Git hooks."""

    def __init__(
        self,
        root_dir: Path | None = None,
        mode: str = HooksInstaller.LIGHTWEIGHT,
    ):
        """
        Initialize the hooks manager.

        Args:
            root_dir: Root directory of the SAGE project.
            mode: Installation mode ("lightweight" or "full").
        """
        self.root_dir = root_dir
        self.mode = mode

    def _create_installer(self, quiet: bool = False) -> HooksInstaller:
        return HooksInstaller(root_dir=self.root_dir, quiet=quiet, mode=self.mode)

    def install(self, quiet: bool = False) -> bool:
        """
        Install Git hooks.

        Args:
            quiet: If True, suppress non-error output.

        Returns:
            True if installation was successful, False otherwise.
        """
        installer = self._create_installer(quiet=quiet)
        return installer.install()

    def uninstall(self, quiet: bool = False) -> bool:
        """
        Uninstall Git hooks.

        Args:
            quiet: If True, suppress non-error output.

        Returns:
            True if uninstallation was successful, False otherwise.
        """
        installer = self._create_installer(quiet=quiet)
        return installer.uninstall()

    def status(self) -> dict:
        """
        Get the status of installed hooks.

        Returns:
            Dictionary with hook status information.
        """
        installer = self._create_installer(quiet=True)
        return installer.status()

    def print_status(self) -> None:
        """Print the status of installed hooks."""
        installer = self._create_installer(quiet=True)
        installer.print_status()
