"""Unit tests for embedding CLI command behaviors."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from sage.cli.commands.apps.embedding import app
from sage.common.config.ports import SagePorts

runner = CliRunner()


class TestEmbeddingCLI:
    """Tests for embedding command group."""

    def test_start_help(self) -> None:
        """Start command help should expose runtime options."""
        result = runner.invoke(app, ["start", "--help"])
        assert result.exit_code == 0
        assert "启动 Embedding 服务器" in result.stdout
        assert "--port" in result.stdout
        assert str(SagePorts.EMBEDDING_DEFAULT) in result.stdout

    @patch("sage.cli.commands.apps.embedding.find_spec")
    def test_start_missing_embedding_module(self, mock_find_spec: MagicMock) -> None:
        """Start should fail fast when embedding server module is unavailable."""
        mock_find_spec.return_value = None
        result = runner.invoke(app, ["start"])
        assert result.exit_code == 1
        assert "未找到 embedding_server 模块" in result.stdout

    @patch("sage.cli.commands.apps.embedding.find_spec")
    @patch("sage.cli.commands.apps.embedding.subprocess.run")
    def test_start_invokes_module_run(
        self,
        mock_run: MagicMock,
        mock_find_spec: MagicMock,
    ) -> None:
        """Start should run embedding server with python -m module invocation."""
        mock_find_spec.return_value = object()
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(app, ["start", "--port", "8091", "--device", "cpu"])
        assert result.exit_code == 0

        called_cmd = mock_run.call_args.args[0]
        assert "python" in Path(called_cmd[0]).name
        assert called_cmd[1:3] == ["-m", "sage.common.components.sage_embedding.embedding_server"]
        assert "--port" in called_cmd
        assert "8091" in called_cmd
