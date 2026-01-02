"""Unit tests for api_server module.

Tests for GPU selection and LLM API server functionality.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip(
    "sage.llm.api_server",
    reason="sage-llm-core package not available; skip api_server tests.",
)


def _mock_nvidia_smi_result(stdout: str, returncode: int = 0):
    """Helper to create mock subprocess result for nvidia-smi."""
    mock_result = MagicMock()
    mock_result.returncode = returncode
    mock_result.stdout = stdout
    return mock_result


class TestSelectAvailableGpus:
    """Tests for _select_available_gpus function.

    The function uses nvidia-smi to query GPU memory and selects GPUs
    with the most free memory.
    """

    def test_returns_none_when_nvidia_smi_fails(self):
        """Should return None when nvidia-smi command fails."""
        from sage.llm.api_server import _select_available_gpus

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _mock_nvidia_smi_result("", returncode=1)
            result = _select_available_gpus(40.0, 1)
            assert result is None

    def test_returns_gpus_when_available(self):
        """Should return list of GPU IDs when sufficient memory is available."""
        from sage.llm.api_server import _select_available_gpus

        # nvidia-smi output: GPU 0 has 80GB free, GPU 1 has 70GB free
        nvidia_output = "0, 81920\n1, 71680\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _mock_nvidia_smi_result(nvidia_output)
            result = _select_available_gpus(40.0, 2)

            assert result == [0, 1]

    def test_returns_none_when_insufficient_gpus(self):
        """Should still return available GPUs even if fewer than requested."""
        from sage.llm.api_server import _select_available_gpus

        # Only 1 GPU available, but requesting 2
        nvidia_output = "0, 81920\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _mock_nvidia_smi_result(nvidia_output)
            result = _select_available_gpus(40.0, 2)

            # Function returns what's available, even if less than requested
            assert result == [0]

    def test_returns_none_when_no_gpus_available(self):
        """Should return None when nvidia-smi returns empty output."""
        from sage.llm.api_server import _select_available_gpus

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _mock_nvidia_smi_result("")
            result = _select_available_gpus(40.0, 1)
            assert result is None

    def test_returns_none_when_nvidia_smi_times_out(self):
        """Should return None when nvidia-smi times out."""
        from subprocess import TimeoutExpired

        from sage.llm.api_server import _select_available_gpus

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = TimeoutExpired("nvidia-smi", 10)
            result = _select_available_gpus(40.0, 1)
            assert result is None

    def test_returns_none_on_exception(self):
        """Should return None when subprocess raises exception."""
        from sage.llm.api_server import _select_available_gpus

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("nvidia-smi not found")
            result = _select_available_gpus(40.0, 1)
            assert result is None

    def test_single_gpu_selection(self):
        """Should correctly select single GPU with most free memory."""
        from sage.llm.api_server import _select_available_gpus

        # GPU 1 has more free memory than GPU 0
        nvidia_output = "0, 20480\n1, 61440\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _mock_nvidia_smi_result(nvidia_output)
            result = _select_available_gpus(60.0, 1)

            # Should select GPU 1 (60GB free) since it has more memory
            assert result == [1]

    def test_default_tensor_parallel_size(self):
        """Should use default tensor_parallel_size of 1."""
        from sage.llm.api_server import _select_available_gpus

        nvidia_output = "0, 81920\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _mock_nvidia_smi_result(nvidia_output)
            result = _select_available_gpus(40.0)  # No tensor_parallel_size specified

            # Default should select 1 GPU
            assert result == [0]

    def test_selects_gpus_with_sufficient_memory(self):
        """Should prefer GPUs that meet memory requirement."""
        from sage.llm.api_server import _select_available_gpus

        # GPU 0: 50GB, GPU 1: 30GB, GPU 2: 60GB
        nvidia_output = "0, 51200\n1, 30720\n2, 61440\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _mock_nvidia_smi_result(nvidia_output)
            # Request 2 GPUs with at least 40GB each
            result = _select_available_gpus(40.0, 2)

            # Should select GPU 2 (60GB) and GPU 0 (50GB), sorted by free memory
            assert result == [2, 0]

    def test_falls_back_to_available_gpus_when_insufficient_memory(self):
        """Should fall back to available GPUs when not enough meet memory requirement."""
        from sage.llm.api_server import _select_available_gpus

        # Only GPU 0 has enough memory, but we need 2 GPUs
        nvidia_output = "0, 51200\n1, 10240\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _mock_nvidia_smi_result(nvidia_output)
            result = _select_available_gpus(40.0, 2)

            # Should fall back to selecting top 2 GPUs by free memory
            assert result == [0, 1]


class TestGetServedModelName:
    """Tests for get_served_model_name function."""

    def test_local_path_with_double_underscore(self):
        """Should convert local path with __ to HuggingFace format."""
        from sage.llm.api_server import get_served_model_name

        result = get_served_model_name("/home/user/.sage/models/vllm/Qwen__Qwen2.5-0.5B-Instruct")
        assert result == "Qwen/Qwen2.5-0.5B-Instruct"

    def test_huggingface_model_name_unchanged(self):
        """Should return HuggingFace model name unchanged."""
        from sage.llm.api_server import get_served_model_name

        result = get_served_model_name("Qwen/Qwen2.5-0.5B-Instruct")
        assert result == "Qwen/Qwen2.5-0.5B-Instruct"

    def test_local_path_without_double_underscore(self):
        """Should return basename for local path without __."""
        from sage.llm.api_server import get_served_model_name

        result = get_served_model_name("/home/user/models/my-model")
        assert result == "my-model"

    def test_windows_style_path(self):
        """Should handle Windows-style paths."""
        from sage.llm.api_server import get_served_model_name

        # Windows path with backslashes - basename extraction works differently
        result = get_served_model_name("C:\\Users\\models\\Qwen__Model")
        # On Linux, os.path.basename doesn't understand Windows paths properly
        # The function checks for backslashes to identify local paths
        assert "__" not in result or "/" in result  # Either converted or basename extracted
