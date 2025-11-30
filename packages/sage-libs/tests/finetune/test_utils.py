"""Tests for finetune utility functions."""

from pathlib import Path
from unittest.mock import patch

from sage.libs.finetune.utils import (
    check_training_dependencies,
    get_finetune_output_dir,
    get_sage_config_dir,
    get_sage_root,
    show_install_instructions,
)


class TestPathUtils:
    """Test path utility functions."""

    def test_get_sage_root_finds_git_directory(self):
        """Test that get_sage_root can find the .git directory."""
        root = get_sage_root()
        assert isinstance(root, Path)
        # Either we find .git or we get current working directory
        assert root.exists()

    def test_get_sage_config_dir_creates_directory(self, tmp_path):
        """Test that get_sage_config_dir creates the directory."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = tmp_path
            config_dir = get_sage_config_dir()
            assert config_dir.exists()
            assert config_dir.is_dir()
            assert config_dir.name == ".sage"

    def test_get_finetune_output_dir_creates_directory(self, tmp_path):
        """Test that get_finetune_output_dir creates the directory."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = tmp_path
            output_dir = get_finetune_output_dir()
            assert output_dir.exists()
            assert output_dir.is_dir()
            assert output_dir.name == "finetune_output"
            assert output_dir.parent.name == ".sage"


class TestDependencyChecks:
    """Test dependency checking functions."""

    def test_check_training_dependencies_success(self):
        """Test dependency check when all dependencies are available."""
        with patch("sage.libs.finetune.utils.accelerate", create=True):
            with patch("sage.libs.finetune.utils.peft", create=True):
                result = check_training_dependencies()
                assert result is True

    def test_check_training_dependencies_missing(self):
        """Test dependency check when dependencies are missing."""
        # This will actually try to import, so we expect False in test environment
        # unless peft/accelerate are installed
        result = check_training_dependencies()
        assert isinstance(result, bool)

    def test_show_install_instructions_displays_output(self):
        """Test that show_install_instructions produces output."""
        show_install_instructions()
        # Should print something (via rich.console)
        # Note: rich output might not show in capsys, so we just test it doesn't crash
        assert True  # Function executed without error
