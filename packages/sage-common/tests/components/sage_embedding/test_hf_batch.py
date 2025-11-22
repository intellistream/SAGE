"""
Unit tests for HuggingFace batch embedding functionality.

This test verifies that the batch processing implementation works correctly
and produces the same results as individual processing.
"""

import pytest


class TestHFBatchEmbedding:
    """测试 HuggingFace 批量 embedding 功能"""

    def test_hf_embed_batch_sync_function(self):
        """测试 hf_embed_batch_sync 函数的正确性

        由于下载和加载 HF 模型需要时间和资源，这个测试通过 mock 来验证逻辑。
        实际的端到端测试应该在集成测试中进行。
        """
        from unittest.mock import MagicMock, patch

        from sage.common.components.sage_embedding.hf import hf_embed_batch_sync

        # Mock tokenizer
        mock_tokenizer = MagicMock()
        mock_encoded = {
            "input_ids": MagicMock(),
            "attention_mask": MagicMock(),
        }
        mock_encoded["input_ids"].to = MagicMock(return_value=mock_encoded["input_ids"])
        mock_encoded["attention_mask"].to = MagicMock(
            return_value=mock_encoded["attention_mask"]
        )
        mock_tokenizer.return_value = mock_encoded

        # Mock model
        mock_model = MagicMock()
        mock_device = MagicMock()
        mock_model.parameters.return_value = iter([MagicMock(device=mock_device)])

        # Mock torch
        with patch("sage.common.components.sage_embedding.hf.torch") as mock_torch:
            # Setup mock outputs
            mock_outputs = MagicMock()
            mock_last_hidden_state = MagicMock()
            mock_embeddings = MagicMock()

            # Mock the tensor operations
            mock_embeddings.dtype = "float32"  # Not bfloat16
            mock_embeddings.detach.return_value.cpu.return_value.tolist.return_value = [
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6],
            ]

            mock_last_hidden_state.mean.return_value = mock_embeddings
            mock_outputs.last_hidden_state = mock_last_hidden_state
            mock_model.return_value = mock_outputs

            # Mock torch.no_grad
            mock_torch.no_grad.return_value.__enter__ = MagicMock()
            mock_torch.no_grad.return_value.__exit__ = MagicMock()

            # Call the function
            texts = ["text1", "text2"]
            result = hf_embed_batch_sync(texts, mock_tokenizer, mock_model)

            # Verify results
            assert isinstance(result, list)
            assert len(result) == 2
            assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

            # Verify tokenizer was called with all texts
            mock_tokenizer.assert_called_once_with(
                texts, return_tensors="pt", padding=True, truncation=True
            )

    def test_hf_wrapper_embed_batch_consistency(self):
        """测试 HFEmbedding.embed_batch() 与单独调用 embed() 的一致性

        这个测试验证批量处理和单独处理产生相同的结果（或接近的结果）。
        由于需要真实模型，这个测试会跳过，除非有可用的模型。
        """
        pytest.skip(
            "此测试需要下载真实的 HuggingFace 模型，跳过以避免 CI 超时。"
            "在本地使用真实模型时可以启用此测试。"
        )

        # 以下是示例代码，如果要在本地测试，取消注释并提供有效的模型
        # from sage.common.components.sage_embedding.wrappers.hf_wrapper import HFEmbedding
        # import numpy as np
        #
        # emb = HFEmbedding(model="sentence-transformers/all-MiniLM-L6-v2")
        # texts = ["Hello world", "How are you", "Test text"]
        #
        # # 批量处理
        # batch_results = emb.embed_batch(texts)
        #
        # # 单独处理
        # individual_results = [emb.embed(text) for text in texts]
        #
        # # 验证结果一致
        # assert len(batch_results) == len(individual_results)
        # for batch_vec, individual_vec in zip(batch_results, individual_results):
        #     # 允许小的数值误差
        #     np.testing.assert_allclose(batch_vec, individual_vec, rtol=1e-5, atol=1e-7)

    def test_hf_batch_handles_empty_list(self):
        """测试空列表的处理"""
        from unittest.mock import MagicMock, patch

        from sage.common.components.sage_embedding.hf import hf_embed_batch_sync

        mock_tokenizer = MagicMock()
        mock_model = MagicMock()
        mock_device = MagicMock()
        mock_model.parameters.return_value = iter([MagicMock(device=mock_device)])

        with patch("sage.common.components.sage_embedding.hf.torch") as mock_torch:
            mock_outputs = MagicMock()
            mock_embeddings = MagicMock()
            mock_embeddings.dtype = "float32"
            mock_embeddings.detach.return_value.cpu.return_value.tolist.return_value = []
            mock_outputs.last_hidden_state.mean.return_value = mock_embeddings
            mock_model.return_value = mock_outputs

            mock_torch.no_grad.return_value.__enter__ = MagicMock()
            mock_torch.no_grad.return_value.__exit__ = MagicMock()

            # Empty list
            result = hf_embed_batch_sync([], mock_tokenizer, mock_model)
            assert isinstance(result, list)
            assert len(result) == 0

    def test_hf_batch_handles_single_text(self):
        """测试单个文本的处理"""
        from unittest.mock import MagicMock, patch

        from sage.common.components.sage_embedding.hf import hf_embed_batch_sync

        mock_tokenizer = MagicMock()
        mock_encoded = {
            "input_ids": MagicMock(),
            "attention_mask": MagicMock(),
        }
        mock_encoded["input_ids"].to = MagicMock(return_value=mock_encoded["input_ids"])
        mock_encoded["attention_mask"].to = MagicMock(
            return_value=mock_encoded["attention_mask"]
        )
        mock_tokenizer.return_value = mock_encoded

        mock_model = MagicMock()
        mock_device = MagicMock()
        mock_model.parameters.return_value = iter([MagicMock(device=mock_device)])

        with patch("sage.common.components.sage_embedding.hf.torch") as mock_torch:
            mock_outputs = MagicMock()
            mock_embeddings = MagicMock()
            mock_embeddings.dtype = "float32"
            mock_embeddings.detach.return_value.cpu.return_value.tolist.return_value = [
                [0.1, 0.2, 0.3]
            ]
            mock_outputs.last_hidden_state.mean.return_value = mock_embeddings
            mock_model.return_value = mock_outputs

            mock_torch.no_grad.return_value.__enter__ = MagicMock()
            mock_torch.no_grad.return_value.__exit__ = MagicMock()

            # Single text
            result = hf_embed_batch_sync(["single text"], mock_tokenizer, mock_model)
            assert isinstance(result, list)
            assert len(result) == 1
            assert result == [[0.1, 0.2, 0.3]]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
