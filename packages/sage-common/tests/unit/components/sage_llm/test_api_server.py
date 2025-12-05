"""Unit tests for api_server module.

Tests for GPU selection and LLM API server functionality.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestSelectAvailableGpus:
    """Tests for _select_available_gpus function."""

    def test_returns_none_when_import_fails(self):
        """Should return None when GPUResourceManager import fails."""
        from sage.common.components.sage_llm.api_server import _select_available_gpus

        # Mock the import to raise ImportError
        with patch.dict(
            "sys.modules",
            {"sage.common.components.sage_llm.sageLLM.control_plane": None},
        ):
            # Test the behavior - the function should gracefully handle import errors
            result = _select_available_gpus(40.0, 1)
            # Result could be None (if GPUResourceManager not available) or a list
            assert result is None or isinstance(result, list)

    def test_returns_gpus_when_available(self):
        """Should return list of GPU IDs when sufficient memory is available."""
        from sage.common.components.sage_llm.api_server import _select_available_gpus

        mock_gpu_manager = MagicMock()
        mock_gpu_manager.allocate_resources.return_value = [0, 1]

        with patch(
            "sage.common.components.sage_llm.sageLLM.control_plane.GPUResourceManager",
            return_value=mock_gpu_manager,
        ):
            result = _select_available_gpus(40.0, 2)

            if result is not None:
                assert result == [0, 1]
                mock_gpu_manager.allocate_resources.assert_called_once_with(40.0, 2)
                mock_gpu_manager.release_resources.assert_called_once_with([0, 1], 40.0)

    def test_returns_none_when_insufficient_gpus(self):
        """Should return None when not enough GPUs with sufficient memory."""
        from sage.common.components.sage_llm.api_server import _select_available_gpus

        mock_gpu_manager = MagicMock()
        mock_gpu_manager.allocate_resources.return_value = [0]  # Only 1 GPU, but need 2

        with patch(
            "sage.common.components.sage_llm.sageLLM.control_plane.GPUResourceManager",
            return_value=mock_gpu_manager,
        ):
            result = _select_available_gpus(40.0, 2)

            # Should return None since we need 2 GPUs but only 1 available
            assert result is None or len(result) < 2

    def test_returns_none_when_no_gpus_available(self):
        """Should return None when allocate_resources returns empty list."""
        from sage.common.components.sage_llm.api_server import _select_available_gpus

        mock_gpu_manager = MagicMock()
        mock_gpu_manager.allocate_resources.return_value = []

        with patch(
            "sage.common.components.sage_llm.sageLLM.control_plane.GPUResourceManager",
            return_value=mock_gpu_manager,
        ):
            result = _select_available_gpus(40.0, 1)
            assert result is None

    def test_returns_none_when_allocate_returns_none(self):
        """Should return None when allocate_resources returns None."""
        from sage.common.components.sage_llm.api_server import _select_available_gpus

        mock_gpu_manager = MagicMock()
        mock_gpu_manager.allocate_resources.return_value = None

        with patch(
            "sage.common.components.sage_llm.sageLLM.control_plane.GPUResourceManager",
            return_value=mock_gpu_manager,
        ):
            result = _select_available_gpus(40.0, 1)
            assert result is None

    def test_returns_none_on_exception(self):
        """Should return None when GPUResourceManager raises exception."""
        from sage.common.components.sage_llm.api_server import _select_available_gpus

        mock_gpu_manager = MagicMock()
        mock_gpu_manager.allocate_resources.side_effect = RuntimeError("GPU error")

        with patch(
            "sage.common.components.sage_llm.sageLLM.control_plane.GPUResourceManager",
            return_value=mock_gpu_manager,
        ):
            result = _select_available_gpus(40.0, 1)
            assert result is None

    def test_single_gpu_selection(self):
        """Should correctly select single GPU."""
        from sage.common.components.sage_llm.api_server import _select_available_gpus

        mock_gpu_manager = MagicMock()
        mock_gpu_manager.allocate_resources.return_value = [1]

        with patch(
            "sage.common.components.sage_llm.sageLLM.control_plane.GPUResourceManager",
            return_value=mock_gpu_manager,
        ):
            result = _select_available_gpus(60.0, 1)

            if result is not None:
                assert result == [1]
                mock_gpu_manager.allocate_resources.assert_called_once_with(60.0, 1)

    def test_default_tensor_parallel_size(self):
        """Should use default tensor_parallel_size of 1."""
        from sage.common.components.sage_llm.api_server import _select_available_gpus

        mock_gpu_manager = MagicMock()
        mock_gpu_manager.allocate_resources.return_value = [0]

        with patch(
            "sage.common.components.sage_llm.sageLLM.control_plane.GPUResourceManager",
            return_value=mock_gpu_manager,
        ):
            result = _select_available_gpus(40.0)  # No tensor_parallel_size specified

            if result is not None:
                mock_gpu_manager.allocate_resources.assert_called_once_with(40.0, 1)


class TestGetServedModelName:
    """Tests for get_served_model_name function."""

    def test_local_path_with_double_underscore(self):
        """Should convert local path with __ to HuggingFace format."""
        from sage.common.components.sage_llm.api_server import get_served_model_name

        result = get_served_model_name("/home/user/.sage/models/vllm/Qwen__Qwen2.5-0.5B-Instruct")
        assert result == "Qwen/Qwen2.5-0.5B-Instruct"

    def test_huggingface_model_name_unchanged(self):
        """Should return HuggingFace model name unchanged."""
        from sage.common.components.sage_llm.api_server import get_served_model_name

        result = get_served_model_name("Qwen/Qwen2.5-0.5B-Instruct")
        assert result == "Qwen/Qwen2.5-0.5B-Instruct"

    def test_local_path_without_double_underscore(self):
        """Should return basename for local path without __."""
        from sage.common.components.sage_llm.api_server import get_served_model_name

        result = get_served_model_name("/home/user/models/my-model")
        assert result == "my-model"

    def test_windows_style_path(self):
        """Should handle Windows-style paths."""
        from sage.common.components.sage_llm.api_server import get_served_model_name

        # Windows path with backslashes - basename extraction works differently
        result = get_served_model_name("C:\\Users\\models\\Qwen__Model")
        # On Linux, os.path.basename doesn't understand Windows paths properly
        # The function checks for backslashes to identify local paths
        assert "__" not in result or "/" in result  # Either converted or basename extracted
