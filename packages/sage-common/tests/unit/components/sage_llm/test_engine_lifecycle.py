# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Unit tests for EngineLifecycleManager.

Tests engine lifecycle management using mocked subprocess calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sage.common.components.sage_llm.sageLLM.control_plane.engine_lifecycle import (
    EngineLifecycleManager,
    EngineProcessInfo,
    EngineRuntime,
    EngineStatus,
)


class TestEngineStatus:
    """Tests for EngineStatus enum."""

    def test_status_values(self):
        """Test all status enum values exist."""
        assert EngineStatus.STARTING == "STARTING"
        assert EngineStatus.RUNNING == "RUNNING"
        assert EngineStatus.STOPPING == "STOPPING"
        assert EngineStatus.STOPPED == "STOPPED"
        assert EngineStatus.FAILED == "FAILED"


class TestEngineRuntime:
    """Tests for EngineRuntime enum."""

    def test_runtime_values(self):
        """Test runtime enum values."""
        assert EngineRuntime.LLM == "llm"
        assert EngineRuntime.EMBEDDING == "embedding"


class TestEngineProcessInfo:
    """Tests for EngineProcessInfo dataclass."""

    def test_default_values(self):
        """Test default values for EngineProcessInfo."""
        info = EngineProcessInfo(
            engine_id="test-engine-123",
            model_id="Qwen/Qwen2.5-7B",
            port=8001,
            gpu_ids=[0],
            pid=12345,
            command=["python", "-m", "vllm.entrypoints.openai.api_server"],
            env_overrides={"CUDA_VISIBLE_DEVICES": "0"},
        )

        assert info.engine_id == "test-engine-123"
        assert info.model_id == "Qwen/Qwen2.5-7B"
        assert info.port == 8001
        assert info.gpu_ids == [0]
        assert info.pid == 12345
        assert info.runtime == EngineRuntime.LLM
        assert info.status == EngineStatus.STARTING
        assert info.stopped_at is None
        assert info.last_exit_code is None
        assert info.last_error is None


class TestEngineLifecycleManager:
    """Tests for EngineLifecycleManager."""

    def test_init_defaults(self):
        """Test initialization with default values."""
        manager = EngineLifecycleManager()

        assert manager.host == "0.0.0.0"
        assert manager.stop_timeout == 20.0
        assert len(manager._engines) == 0

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        manager = EngineLifecycleManager(
            python_executable="/usr/bin/python3",
            host="127.0.0.1",
            stop_timeout=30.0,
        )

        assert manager.python_executable == "/usr/bin/python3"
        assert manager.host == "127.0.0.1"
        assert manager.stop_timeout == 30.0

    @patch("subprocess.Popen")
    def test_spawn_llm_engine(self, mock_popen):
        """Test spawning an LLM engine."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        manager = EngineLifecycleManager()

        with patch.object(manager, "_reserve_port", return_value=8001):
            engine_id = manager.spawn_engine(
                model_id="Qwen/Qwen2.5-7B-Instruct",
                gpu_ids=[0],
                port=8001,
                tensor_parallel_size=1,
                engine_kind=EngineRuntime.LLM,
            )

        assert engine_id.startswith("engine-")
        assert engine_id in manager._engines
        assert manager._engines[engine_id].port == 8001
        assert manager._engines[engine_id].runtime == EngineRuntime.LLM

        # Verify command includes vllm
        call_args = mock_popen.call_args
        command = call_args[0][0]
        assert any("vllm" in arg for arg in command)

    @patch("subprocess.Popen")
    def test_spawn_embedding_engine_with_gpu(self, mock_popen):
        """Test spawning an Embedding engine with GPU."""
        mock_process = MagicMock()
        mock_process.pid = 12346
        mock_popen.return_value = mock_process

        manager = EngineLifecycleManager()

        with patch.object(manager, "_reserve_port", return_value=8090):
            engine_id = manager.spawn_engine(
                model_id="BAAI/bge-m3",
                gpu_ids=[0],  # Has GPU
                port=8090,
                engine_kind=EngineRuntime.EMBEDDING,
            )

        assert engine_id in manager._engines
        assert manager._engines[engine_id].runtime == EngineRuntime.EMBEDDING

        # Verify command includes --device cuda
        call_args = mock_popen.call_args
        command = call_args[0][0]
        assert "--device" in command
        device_idx = command.index("--device")
        assert command[device_idx + 1] == "cuda"

    @patch("subprocess.Popen")
    def test_spawn_embedding_engine_without_gpu(self, mock_popen):
        """Test spawning an Embedding engine without GPU."""
        mock_process = MagicMock()
        mock_process.pid = 12347
        mock_popen.return_value = mock_process

        manager = EngineLifecycleManager()

        with patch.object(manager, "_reserve_port", return_value=8090):
            _engine_id = manager.spawn_engine(
                model_id="BAAI/bge-m3",
                gpu_ids=[],  # No GPU
                port=8090,
                engine_kind=EngineRuntime.EMBEDDING,
            )

        # Verify command includes --device cpu
        call_args = mock_popen.call_args
        command = call_args[0][0]
        assert "--device" in command
        device_idx = command.index("--device")
        assert command[device_idx + 1] == "cpu"

    def test_list_engines_empty(self):
        """Test listing engines when none exist."""
        manager = EngineLifecycleManager()
        engines = manager.list_engines()
        assert engines == []

    @patch("subprocess.Popen")
    def test_list_engines(self, mock_popen):
        """Test listing engines after spawning."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        manager = EngineLifecycleManager()

        with patch.object(manager, "_reserve_port", return_value=8001):
            with patch.object(manager, "_get_process", return_value=None):
                engine_id = manager.spawn_engine(
                    model_id="test-model",
                    gpu_ids=[0],
                    port=8001,
                    engine_kind=EngineRuntime.LLM,
                )

        engines = manager.list_engines()
        assert len(engines) == 1
        assert engines[0]["engine_id"] == engine_id

    @patch("subprocess.Popen")
    def test_get_engine_status(self, mock_popen):
        """Test getting status of a specific engine."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        manager = EngineLifecycleManager()

        with patch.object(manager, "_reserve_port", return_value=8001):
            with patch.object(manager, "_get_process", return_value=None):
                engine_id = manager.spawn_engine(
                    model_id="test-model",
                    gpu_ids=[0],
                    port=8001,
                    engine_kind=EngineRuntime.LLM,
                )

        status = manager.get_engine_status(engine_id)
        assert status["engine_id"] == engine_id
        assert status["model_id"] == "test-model"
        assert status["port"] == 8001

    def test_get_engine_status_not_found(self):
        """Test getting status of non-existent engine."""
        manager = EngineLifecycleManager()

        with pytest.raises(KeyError, match="not found"):
            manager.get_engine_status("nonexistent-engine")

    @patch("subprocess.Popen")
    def test_stop_engine(self, mock_popen):
        """Test stopping an engine."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        manager = EngineLifecycleManager()

        with patch.object(manager, "_reserve_port", return_value=8001):
            engine_id = manager.spawn_engine(
                model_id="test-model",
                gpu_ids=[0],
                port=8001,
                engine_kind=EngineRuntime.LLM,
            )

        # Mock the process retrieval and termination
        mock_psutil_process = MagicMock()
        mock_psutil_process.is_running.return_value = True

        with patch.object(manager, "_get_process", return_value=mock_psutil_process):
            with patch.object(manager, "_terminate_process", return_value=True):
                result = manager.stop_engine(engine_id)

        assert result is True
        assert manager._engines[engine_id].status == EngineStatus.STOPPED

    def test_stop_nonexistent_engine(self):
        """Test stopping a non-existent engine."""
        manager = EngineLifecycleManager()
        result = manager.stop_engine("nonexistent-engine")
        assert result is False

    def test_build_llm_command(self):
        """Test building LLM engine command."""
        manager = EngineLifecycleManager()
        command = manager._build_llm_command(
            model_id="Qwen/Qwen2.5-7B",
            port=8001,
            tensor_parallel_size=2,
            pipeline_parallel_size=1,
            extra_args=["--max-model-len", "4096"],
        )

        assert manager.python_executable in command[0]
        assert "-m" in command
        assert "vllm.entrypoints.openai.api_server" in command
        assert "--model" in command
        assert "Qwen/Qwen2.5-7B" in command
        assert "--port" in command
        assert "8001" in command
        assert "--tensor-parallel-size" in command
        assert "2" in command
        assert "--max-model-len" in command
        assert "4096" in command

    def test_build_embedding_command_with_gpu(self):
        """Test building Embedding engine command with GPU."""
        manager = EngineLifecycleManager()
        command = manager._build_embedding_command(
            model_id="BAAI/bge-m3",
            port=8090,
            extra_args=[],
            gpu_ids=[0],
        )

        assert manager.python_executable in command[0]
        assert "sage.common.components.sage_embedding.embedding_server" in command
        assert "--model" in command
        assert "BAAI/bge-m3" in command
        assert "--device" in command
        assert "cuda" in command

    def test_build_embedding_command_without_gpu(self):
        """Test building Embedding engine command without GPU."""
        manager = EngineLifecycleManager()
        command = manager._build_embedding_command(
            model_id="BAAI/bge-m3",
            port=8090,
            extra_args=[],
            gpu_ids=[],
        )

        assert "--device" in command
        assert "cpu" in command

    def test_build_environment_with_gpus(self):
        """Test building environment with GPU IDs."""
        manager = EngineLifecycleManager()
        env = manager._build_environment([0, 1])

        assert "CUDA_VISIBLE_DEVICES" in env
        assert env["CUDA_VISIBLE_DEVICES"] == "0,1"

    def test_build_environment_without_gpus(self):
        """Test building environment without GPU IDs."""
        manager = EngineLifecycleManager()

        # First set an env var, then check it's removed
        import os

        original_env = os.environ.get("CUDA_VISIBLE_DEVICES")
        os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
        try:
            env = manager._build_environment([])
            assert "CUDA_VISIBLE_DEVICES" not in env
        finally:
            if original_env is not None:
                os.environ["CUDA_VISIBLE_DEVICES"] = original_env
            else:
                os.environ.pop("CUDA_VISIBLE_DEVICES", None)


class TestEngineLifecycleManagerHealthCheck:
    """Tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_unknown_engine(self):
        """Test health check for unknown engine returns False."""
        manager = EngineLifecycleManager()
        result = await manager.health_check("nonexistent-engine")
        assert result is False

    @pytest.mark.asyncio
    @patch("subprocess.Popen")
    async def test_health_check_stopped_engine(self, mock_popen):
        """Test health check for stopped engine returns False."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        manager = EngineLifecycleManager()

        with patch.object(manager, "_reserve_port", return_value=8001):
            engine_id = manager.spawn_engine(
                model_id="test-model",
                gpu_ids=[0],
                port=8001,
                engine_kind=EngineRuntime.LLM,
            )

        # Set engine to STOPPED
        manager._engines[engine_id].status = EngineStatus.STOPPED

        result = await manager.health_check(engine_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_all_empty(self):
        """Test health check all when no engines exist."""
        manager = EngineLifecycleManager()
        result = await manager.health_check_all()
        assert result == {}
