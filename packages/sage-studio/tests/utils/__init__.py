"""Tests for GPU check utility."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from sage.studio.utils.gpu_check import is_gpu_available


class TestIsGPUAvailable:
    """Test is_gpu_available function."""

    @patch("shutil.which")
    @patch("ctypes.util.find_library")
    @patch("subprocess.check_call")
    def test_gpu_available_all_checks_pass(self, mock_check_call, mock_find_library, mock_which):
        """Test when all GPU checks pass."""
        # Mock successful checks
        mock_which.return_value = "/usr/bin/nvidia-smi"
        mock_find_library.return_value = "/usr/lib/libcuda.so"
        mock_check_call.return_value = 0

        result = is_gpu_available()

        assert result is True
        mock_which.assert_called_once_with("nvidia-smi")
        mock_find_library.assert_called_once_with("cuda")
        mock_check_call.assert_called_once()

    @patch("shutil.which")
    def test_gpu_not_available_no_nvidia_smi(self, mock_which):
        """Test when nvidia-smi is not found."""
        mock_which.return_value = None

        result = is_gpu_available()

        assert result is False
        mock_which.assert_called_once_with("nvidia-smi")

    @patch("shutil.which")
    @patch("ctypes.util.find_library")
    def test_gpu_not_available_no_libcuda(self, mock_find_library, mock_which):
        """Test when libcuda.so is not found."""
        mock_which.return_value = "/usr/bin/nvidia-smi"
        mock_find_library.return_value = None

        result = is_gpu_available()

        assert result is False
        mock_which.assert_called_once_with("nvidia-smi")
        mock_find_library.assert_called_once_with("cuda")

    @patch("shutil.which")
    @patch("ctypes.util.find_library")
    @patch("subprocess.check_call")
    def test_gpu_not_available_nvidia_smi_fails(
        self, mock_check_call, mock_find_library, mock_which
    ):
        """Test when nvidia-smi command fails."""
        mock_which.return_value = "/usr/bin/nvidia-smi"
        mock_find_library.return_value = "/usr/lib/libcuda.so"
        mock_check_call.side_effect = subprocess.CalledProcessError(1, "nvidia-smi")

        result = is_gpu_available()

        assert result is False

    @patch("shutil.which")
    @patch("ctypes.util.find_library")
    @patch("subprocess.check_call")
    def test_gpu_not_available_os_error(self, mock_check_call, mock_find_library, mock_which):
        """Test when nvidia-smi raises OSError."""
        mock_which.return_value = "/usr/bin/nvidia-smi"
        mock_find_library.return_value = "/usr/lib/libcuda.so"
        mock_check_call.side_effect = OSError("Command not found")

        result = is_gpu_available()

        assert result is False

    @patch("shutil.which")
    @patch("ctypes.util.find_library")
    @patch("subprocess.check_call")
    def test_nvidia_smi_output_suppressed(self, mock_check_call, mock_find_library, mock_which):
        """Test that nvidia-smi output is suppressed."""
        mock_which.return_value = "/usr/bin/nvidia-smi"
        mock_find_library.return_value = "/usr/lib/libcuda.so"
        mock_check_call.return_value = 0

        is_gpu_available()

        # Verify that stdout and stderr are set to DEVNULL
        call_args = mock_check_call.call_args
        assert call_args is not None
        assert "stdout" in call_args.kwargs
        assert "stderr" in call_args.kwargs
        assert call_args.kwargs["stdout"] == subprocess.DEVNULL
        assert call_args.kwargs["stderr"] == subprocess.DEVNULL
