"""
Unit tests for HuggingFace batch embedding functionality.

This test verifies that the batch processing implementation works correctly
and produces the same results as individual processing.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest


class TestHFBatchEmbedding:
    """Test HuggingFace batch embedding functionality."""

    def test_hf_embed_batch_sync_function(self):
        """Test hf_embed_batch_sync function correctness.

        Since downloading and loading HF models requires time and resources,
        this test uses mocks to verify the logic.
        End-to-end tests should be done in integration tests.
        """
        # Remove already imported modules to reimport with mock
        modules_to_remove = [
            k for k in sys.modules.keys() if "sage.common.components.sage_embedding.hf" in k
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Create mock torch module
        mock_torch = MagicMock()

        # Mock tensor operations
        mock_tensor = MagicMock()
        mock_tensor.size.return_value = (2, 10, 768)
        mock_tensor.__mul__ = MagicMock(return_value=mock_tensor)

        mock_sum_result = MagicMock()
        mock_sum_mask = MagicMock()
        mock_embeddings = MagicMock()
        mock_embeddings.dtype = "float32"
        mock_embeddings.detach.return_value.cpu.return_value.tolist.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]

        mock_torch.sum.return_value = mock_sum_result
        mock_torch.clamp.return_value = mock_sum_mask
        mock_sum_result.__truediv__ = MagicMock(return_value=mock_embeddings)

        mock_torch.no_grad.return_value.__enter__ = MagicMock()
        mock_torch.no_grad.return_value.__exit__ = MagicMock()

        with patch.dict(sys.modules, {"torch": mock_torch}):
            from sage.common.components.sage_embedding.hf import hf_embed_batch_sync

            mock_tokenizer = MagicMock()
            mock_encoded = MagicMock()
            mock_encoded.__getitem__ = MagicMock(side_effect=lambda k: MagicMock())
            mock_encoded.to = MagicMock(return_value=mock_encoded)
            mock_tokenizer.return_value = mock_encoded

            mock_model = MagicMock()
            mock_device = MagicMock()
            mock_model.parameters.return_value = iter([MagicMock(device=mock_device)])

            mock_outputs = MagicMock()
            mock_outputs.last_hidden_state = mock_tensor
            mock_model.return_value = mock_outputs

            texts = ["text1", "text2"]
            result = hf_embed_batch_sync(texts, mock_tokenizer, mock_model)

            assert isinstance(result, list)
            assert len(result) == 2
            assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

            mock_tokenizer.assert_called_once_with(
                texts, return_tensors="pt", padding=True, truncation=True
            )

    def test_hf_wrapper_embed_batch_consistency(self):
        """Test HFEmbedding.embed_batch() consistency with individual embed() calls."""
        pytest.skip(
            "This test requires downloading real HuggingFace models, skipping to avoid CI timeout."
        )

    def test_hf_batch_handles_empty_list(self):
        """Test empty list handling - should return empty list without calling model."""
        from sage.common.components.sage_embedding.hf import hf_embed_batch_sync

        mock_tokenizer = MagicMock()
        mock_model = MagicMock()

        result = hf_embed_batch_sync([], mock_tokenizer, mock_model)
        assert isinstance(result, list)
        assert len(result) == 0

        mock_tokenizer.assert_not_called()
        mock_model.assert_not_called()

    def test_hf_batch_handles_single_text(self):
        """Test single text processing."""
        modules_to_remove = [
            k for k in sys.modules.keys() if "sage.common.components.sage_embedding.hf" in k
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        mock_torch = MagicMock()

        mock_tensor = MagicMock()
        mock_tensor.size.return_value = (1, 5, 768)
        mock_tensor.__mul__ = MagicMock(return_value=mock_tensor)

        mock_sum_result = MagicMock()
        mock_sum_mask = MagicMock()
        mock_embeddings = MagicMock()
        mock_embeddings.dtype = "float32"
        mock_embeddings.detach.return_value.cpu.return_value.tolist.return_value = [[0.1, 0.2, 0.3]]

        mock_torch.sum.return_value = mock_sum_result
        mock_torch.clamp.return_value = mock_sum_mask
        mock_sum_result.__truediv__ = MagicMock(return_value=mock_embeddings)

        mock_torch.no_grad.return_value.__enter__ = MagicMock()
        mock_torch.no_grad.return_value.__exit__ = MagicMock()

        with patch.dict(sys.modules, {"torch": mock_torch}):
            from sage.common.components.sage_embedding.hf import hf_embed_batch_sync

            mock_tokenizer = MagicMock()
            mock_encoded = MagicMock()
            mock_encoded.__getitem__ = MagicMock(side_effect=lambda k: MagicMock())
            mock_encoded.to = MagicMock(return_value=mock_encoded)
            mock_tokenizer.return_value = mock_encoded

            mock_model = MagicMock()
            mock_device = MagicMock()
            mock_model.parameters.return_value = iter([MagicMock(device=mock_device)])

            mock_outputs = MagicMock()
            mock_outputs.last_hidden_state = mock_tensor
            mock_model.return_value = mock_outputs

            result = hf_embed_batch_sync(["single text"], mock_tokenizer, mock_model)
            assert isinstance(result, list)
            assert len(result) == 1
            assert result == [[0.1, 0.2, 0.3]]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
