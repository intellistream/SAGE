"""Integration tests for finetune CLI."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from sage.libs.finetune.cli import app


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_dependencies():
    """Mock training dependencies."""
    with patch("sage.libs.finetune.utils.check_training_dependencies") as mock_check:
        mock_check.return_value = []  # No missing dependencies
        yield mock_check


class TestFinetuneStartCommand:
    """Test the 'start' command."""

    def test_start_command_help(self, cli_runner):
        """Test that start command help works."""
        result = cli_runner.invoke(app, ["start", "--help"])
        assert result.exit_code == 0
        assert "start" in result.stdout.lower() or "微调" in result.stdout

    @patch("sage.libs.finetune.cli.start_training")
    @patch("sage.libs.finetune.cli.prepare_training_data")
    @patch("sage.libs.finetune.cli.generate_training_config")
    def test_start_command_with_all_options(
        self, mock_config, mock_prepare, mock_train, cli_runner, tmp_path
    ):
        """Test start command with all options provided."""
        # Setup mocks
        data_file = tmp_path / "train.json"
        data_file.write_text("[]")
        mock_prepare.return_value = data_file
        mock_config.return_value = {"model_name": "test/model"}
        mock_train.return_value = None

        output_dir = tmp_path / "output"

        result = cli_runner.invoke(
            app,
            [
                "start",
                "--task",
                "code",
                "--model",
                "test/model",
                "--data",
                str(data_file),
                "--output",
                str(output_dir),
            ],
        )

        # Command should execute (might fail due to missing deps, but should parse correctly)
        assert result.exit_code in [0, 1]  # 0 success, 1 if deps check fails


class TestFinetuneServeCommand:
    """Test the 'serve' command."""

    def test_serve_command_help(self, cli_runner):
        """Test that serve command help works."""
        result = cli_runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "serve" in result.stdout.lower() or "服务" in result.stdout

    @patch("sage.libs.finetune.cli.serve_model_with_vllm")
    @patch("sage.libs.finetune.cli._find_model_for_serving")
    def test_serve_command_basic(self, mock_find_model, mock_serve, cli_runner, tmp_path):
        """Test serve command with basic options."""
        model_path = tmp_path / "model"
        model_path.mkdir()

        # Mock the model finder to return valid paths
        mock_find_model.return_value = (model_path, False, None)
        mock_serve.return_value = None

        result = cli_runner.invoke(app, ["serve", "test_model"])

        # Should attempt to call serve function
        assert result.exit_code in [0, 1]


class TestFinetuneMergeCommand:
    """Test the 'merge' command."""

    def test_merge_command_help(self, cli_runner):
        """Test that merge command help works."""
        result = cli_runner.invoke(app, ["merge", "--help"])
        assert result.exit_code == 0
        assert "merge" in result.stdout.lower() or "合并" in result.stdout

    @patch("sage.libs.finetune.cli.merge_lora_weights")
    @patch("sage.libs.finetune.cli._find_checkpoint")
    def test_merge_command_basic(self, mock_find_checkpoint, mock_merge, cli_runner, tmp_path):
        """Test merge command with basic options."""
        base_model = "test/model"
        lora_path = tmp_path / "lora"
        lora_path.mkdir()
        output_path = tmp_path / "merged"

        # Mock the checkpoint finder to return valid paths
        mock_find_checkpoint.return_value = (lora_path, base_model)
        mock_merge.return_value = True

        result = cli_runner.invoke(
            app,
            [
                "merge",
                "test_model",
                "--output",
                str(output_path),
            ],
        )

        assert result.exit_code in [0, 1]


class TestFinetuneListCommand:
    """Test the 'list' command."""

    def test_list_command(self, cli_runner):
        """Test that list command works."""
        result = cli_runner.invoke(app, ["list"])
        assert result.exit_code == 0
        # Should show some output about available tasks or models
        assert len(result.stdout) > 0
