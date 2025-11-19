"""
Tests for Git Hooks Installer and Manager.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from sage.tools.dev.hooks import HooksInstaller, HooksManager


class TestHooksInstaller:
    """Test HooksInstaller class."""

    def test_init_with_root_dir(self, tmp_path: Path) -> None:
        """Test installer initialization with explicit root directory."""
        installer = HooksInstaller(root_dir=tmp_path, quiet=True)
        assert installer.root_dir == tmp_path
        assert installer.quiet is True
        assert installer.install_mode == HooksInstaller.LIGHTWEIGHT

    def test_init_invalid_mode_falls_back(self, tmp_path: Path) -> None:
        """Installer should fall back to lightweight mode for invalid input."""
        installer = HooksInstaller(root_dir=tmp_path, quiet=True, mode="invalid")
        assert installer.install_mode == HooksInstaller.LIGHTWEIGHT

    def test_init_auto_detect_git_root(self, tmp_path: Path) -> None:
        """Test installer auto-detects git root."""
        # Create a fake git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=str(tmp_path), returncode=0)
            installer = HooksInstaller(quiet=True)
            assert installer.root_dir == tmp_path

    def test_check_git_repo_success(self, tmp_path: Path) -> None:
        """Test checking for git repository (success case)."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        installer = HooksInstaller(root_dir=tmp_path, quiet=True)
        assert installer._check_git_repo() is True

    def test_check_git_repo_failure(self, tmp_path: Path) -> None:
        """Test checking for git repository (failure case)."""
        # No .git directory
        installer = HooksInstaller(root_dir=tmp_path, quiet=True)
        assert installer._check_git_repo() is False

    def test_backup_existing_hook(self, tmp_path: Path) -> None:
        """Test backing up existing hook."""
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        pre_commit = hooks_dir / "pre-commit"
        pre_commit.write_text("old hook content")

        installer = HooksInstaller(root_dir=tmp_path, quiet=True)
        installer._backup_existing_hook(pre_commit)

        # Original should be renamed
        assert not pre_commit.exists()
        # Backup should exist
        backups = list(hooks_dir.glob("pre-commit.backup.*"))
        assert len(backups) == 1
        assert backups[0].read_text() == "old hook content"

    def test_install_pre_commit_hook_success(self, tmp_path: Path) -> None:
        """Test installing pre-commit hook successfully."""
        # Setup
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir()

        # Create a fake template
        installer = HooksInstaller(root_dir=tmp_path, quiet=True)
        templates_dir = Path(installer.templates_dir)
        templates_dir.mkdir(parents=True, exist_ok=True)
        template_file = templates_dir / "pre-commit"
        template_file.write_text("#!/bin/bash\necho test")

        # Install
        result = installer._install_pre_commit_hook()

        # Verify
        assert result is True
        installed_hook = hooks_dir / "pre-commit"
        assert installed_hook.exists()
        assert installed_hook.read_text() == "#!/bin/bash\necho test"
        # Check it's executable
        assert installed_hook.stat().st_mode & 0o111  # Has execute permission

    def test_install_pre_commit_hook_no_template(self, tmp_path: Path) -> None:
        """Test installing pre-commit hook when template doesn't exist."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir()

        # Mock the templates_dir to point to a non-existent location
        installer = HooksInstaller(root_dir=tmp_path, quiet=True)
        installer.templates_dir = tmp_path / "non_existent_templates"

        result = installer._install_pre_commit_hook()

        assert result is False

    @patch("subprocess.run")
    def test_install_pre_commit_framework_success(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Test installing pre-commit framework successfully."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        config_file = tmp_path / "tools" / "pre-commit-config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.touch()

        # Mock pre-commit command exists and succeeds
        mock_run.return_value = Mock(returncode=0)

        installer = HooksInstaller(root_dir=tmp_path, quiet=True)
        result = installer._install_pre_commit_framework()

        assert result is True
        assert mock_run.call_count == 2  # version check + install

    @patch("subprocess.run")
    def test_install_pre_commit_framework_not_installed(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Test when pre-commit framework is not installed."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Mock pre-commit command not found
        mock_run.side_effect = FileNotFoundError()

        installer = HooksInstaller(root_dir=tmp_path, quiet=True)
        result = installer._install_pre_commit_framework()

        assert result is False

    @patch("subprocess.run")
    def test_test_architecture_checker_available(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test checking if architecture checker is available."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Mock sage-dev command available
        mock_run.return_value = Mock(returncode=0)

        installer = HooksInstaller(root_dir=tmp_path, quiet=True)
        result = installer._test_architecture_checker()

        assert result is True

    def test_status_not_in_git_repo(self, tmp_path: Path) -> None:
        """Test status when not in a git repository."""
        installer = HooksInstaller(root_dir=tmp_path, quiet=True)
        status = installer.status()

        assert status["git_repo"] is False
        assert status["pre_commit_hook_installed"] is False

    def test_status_in_git_repo_with_hook(self, tmp_path: Path) -> None:
        """Test status when in git repo with hook installed."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir()
        pre_commit = hooks_dir / "pre-commit"
        pre_commit.touch()

        installer = HooksInstaller(root_dir=tmp_path, quiet=True)
        status = installer.status()

        assert status["git_repo"] is True
        assert status["pre_commit_hook_installed"] is True

    def test_uninstall_success(self, tmp_path: Path) -> None:
        """Test uninstalling hooks successfully."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir()
        pre_commit = hooks_dir / "pre-commit"
        pre_commit.touch()

        installer = HooksInstaller(root_dir=tmp_path, quiet=True)
        result = installer.uninstall()

        assert result is True
        assert not pre_commit.exists()

    def test_uninstall_hook_not_exists(self, tmp_path: Path) -> None:
        """Test uninstalling when hook doesn't exist."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        installer = HooksInstaller(root_dir=tmp_path, quiet=True)
        result = installer.uninstall()

        # Should still return True (successful operation)
        assert result is True


class TestHooksManager:
    """Test HooksManager class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test manager initialization."""
        manager = HooksManager(root_dir=tmp_path, mode="full")
        assert manager.root_dir == tmp_path
        assert manager.mode == "full"

    @patch("sage.tools.dev.hooks.manager.HooksInstaller")
    def test_install(self, mock_installer_cls: MagicMock, tmp_path: Path) -> None:
        """Test install method delegates to installer."""
        mock_installer = mock_installer_cls.return_value
        mock_installer.install.return_value = True

        manager = HooksManager(root_dir=tmp_path, mode="lightweight")
        result = manager.install(quiet=True)

        assert result is True
        mock_installer_cls.assert_called_once_with(
            root_dir=tmp_path,
            quiet=True,
            mode="lightweight",
        )
        mock_installer.install.assert_called_once_with()

    @patch("sage.tools.dev.hooks.manager.HooksInstaller")
    def test_uninstall(self, mock_installer_cls: MagicMock, tmp_path: Path) -> None:
        """Test uninstall method delegates to installer."""
        mock_installer = mock_installer_cls.return_value
        mock_installer.uninstall.return_value = True

        manager = HooksManager(root_dir=tmp_path)
        result = manager.uninstall(quiet=True)

        assert result is True
        mock_installer_cls.assert_called_once_with(
            root_dir=tmp_path,
            quiet=True,
            mode="lightweight",
        )
        mock_installer.uninstall.assert_called_once_with()

    @patch("sage.tools.dev.hooks.manager.HooksInstaller")
    def test_status(self, mock_installer_cls: MagicMock, tmp_path: Path) -> None:
        """Test status method delegates to installer."""
        expected_status = {"git_repo": True, "pre_commit_hook_installed": True}
        mock_installer = mock_installer_cls.return_value
        mock_installer.status.return_value = expected_status

        manager = HooksManager(root_dir=tmp_path, mode="full")
        result = manager.status()

        assert result == expected_status
        mock_installer_cls.assert_called_once_with(
            root_dir=tmp_path,
            quiet=True,
            mode="full",
        )
        mock_installer.status.assert_called_once_with()


class TestHooksIntegration:
    """Integration tests for hooks functionality."""

    def test_full_install_uninstall_cycle(self, tmp_path: Path) -> None:
        """Test full install and uninstall cycle."""
        # Setup git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir()

        # Create template
        installer = HooksInstaller(root_dir=tmp_path, quiet=True)
        templates_dir = Path(installer.templates_dir)
        templates_dir.mkdir(parents=True, exist_ok=True)
        template_file = templates_dir / "pre-commit"
        template_file.write_text("#!/bin/bash\necho test")

        # Create config file for pre-commit framework
        config_dir = tmp_path / "tools"
        config_dir.mkdir()
        config_file = config_dir / "pre-commit-config.yaml"
        config_file.write_text("repos: []")

        # Install
        manager = HooksManager(root_dir=tmp_path)
        install_result = manager.install(quiet=True)
        assert install_result is True

        # Check status
        status = manager.status()
        assert status["git_repo"] is True
        assert status["pre_commit_hook_installed"] is True

        # Uninstall
        uninstall_result = manager.uninstall(quiet=True)
        assert uninstall_result is True

        # Check status after uninstall
        status_after = manager.status()
        assert status_after["git_repo"] is True
        assert status_after["pre_commit_hook_installed"] is False
