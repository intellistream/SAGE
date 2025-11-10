"""
Unit tests for LongRefiner class
"""

from unittest.mock import MagicMock, patch

import pytest
import torch

# Check if vllm is available
pytest.importorskip("vllm", reason="vllm is required for LongRefiner tests")


class TestLongRefinerInit:
    """Test LongRefiner initialization"""

    @patch("sage.libs.context.compression.algorithms.long_refiner_impl.refiner.LLM")
    @patch("sage.libs.context.compression.algorithms.long_refiner_impl.refiner.AutoTokenizer")
    @patch(
        "sage.libs.context.compression.algorithms.long_refiner_impl.refiner.AutoModelForSequenceClassification"
    )
    def test_init_with_defaults(self, mock_score_model, mock_tokenizer, mock_llm):
        """Test initialization with default parameters"""
        from sage.libs.context.compression.algorithms.long_refiner_impl.refiner import LongRefiner

        # Mock the models
        mock_llm_instance = MagicMock()
        mock_llm.return_value = mock_llm_instance
        mock_tokenizer_instance = MagicMock()
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
        mock_score_model_instance = MagicMock()
        mock_score_model.from_pretrained.return_value = mock_score_model_instance

        # Test initialization
        refiner = LongRefiner(
            base_model_path="test/model",
            query_analysis_module_lora_path="test/lora1",
            doc_structuring_module_lora_path="test/lora2",
            global_selection_module_lora_path="test/lora3",
        )

        assert refiner.gpu_device == 0
        assert refiner.score_gpu_device == 0
        assert refiner.model == mock_llm_instance
        mock_llm.assert_called_once()

    @patch("sage.libs.context.compression.algorithms.long_refiner_impl.refiner.LLM")
    @patch("sage.libs.context.compression.algorithms.long_refiner_impl.refiner.AutoTokenizer")
    @patch(
        "sage.libs.context.compression.algorithms.long_refiner_impl.refiner.AutoModelForSequenceClassification"
    )
    def test_init_with_custom_gpu(self, mock_score_model, mock_tokenizer, mock_llm):
        """Test initialization with custom GPU settings"""
        from sage.libs.context.compression.algorithms.long_refiner_impl.refiner import LongRefiner

        mock_llm.return_value = MagicMock()
        mock_tokenizer.from_pretrained.return_value = MagicMock()
        mock_score_model.from_pretrained.return_value = MagicMock()

        refiner = LongRefiner(
            base_model_path="test/model",
            query_analysis_module_lora_path="test/lora1",
            doc_structuring_module_lora_path="test/lora2",
            global_selection_module_lora_path="test/lora3",
            gpu_device=1,
            score_gpu_device=2,
        )

        assert refiner.gpu_device == 1
        assert refiner.score_gpu_device == 2


class TestLongRefinerScoring:
    """Test LongRefiner scoring methods"""

    def test_cal_score_bm25(self):
        """Test BM25 scoring"""
        from sage.libs.context.compression.algorithms.long_refiner_impl.refiner import LongRefiner

        with patch.object(LongRefiner, "__init__", lambda x: None):
            refiner = LongRefiner()
            refiner.score_model_name = "bm25"

            all_pairs = [
                ("what is python", "Python is a programming language"),
                ("what is python", "Python is a snake"),
                ("what is java", "Java is a programming language"),
            ]

            scores = refiner._cal_score_bm25(all_pairs)
            assert len(scores) == 3
            assert all(isinstance(s, (int, float)) for s in scores)

    @patch("torch.no_grad")
    @patch("torch.cuda.is_available", return_value=False)
    def test_cal_score_reranker(self, mock_cuda, mock_no_grad):
        """Test reranker scoring"""
        from sage.libs.context.compression.algorithms.long_refiner_impl.refiner import LongRefiner

        with patch.object(LongRefiner, "__init__", lambda x: None):
            refiner = LongRefiner()
            refiner.score_model_name = "bge-reranker-v2-m3"
            refiner.score_gpu_device = 0

            # Mock tokenizer and model
            mock_tokenizer = MagicMock()
            mock_model = MagicMock()

            # Setup mock returns
            mock_inputs = {"input_ids": torch.tensor([[1, 2, 3]])}
            mock_tokenizer.return_value = mock_inputs

            # Mock the to() method to return the tensor itself (no GPU transfer)
            for key in mock_inputs:
                mock_inputs[key].to = MagicMock(return_value=mock_inputs[key])

            mock_output = MagicMock()
            mock_output.logits = torch.tensor([[0.5]])
            mock_model.return_value = mock_output

            refiner.score_tokenizer = mock_tokenizer
            refiner.score_model = mock_model

            all_pairs = [("query", "document")]
            scores = refiner._cal_score_reranker(all_pairs)

            assert len(scores) == 1
            assert isinstance(scores[0], (int, float))

    @patch("torch.no_grad")
    @patch("torch.cuda.is_available", return_value=False)
    def test_cal_score_sbert(self, mock_cuda, mock_no_grad):
        """Test SBERT scoring"""
        from sage.libs.context.compression.algorithms.long_refiner_impl.refiner import LongRefiner

        with patch.object(LongRefiner, "__init__", lambda x: None):
            refiner = LongRefiner()
            refiner.score_model_name = "sentence-transformers/all-MiniLM-L6-v2"
            refiner.score_gpu_device = 0

            # Mock tokenizer and model
            mock_tokenizer = MagicMock()
            mock_model = MagicMock()

            # Setup mock returns
            mock_inputs = {
                "input_ids": torch.tensor([[1, 2, 3]]),
                "attention_mask": torch.tensor([[1, 1, 1]]),
            }
            mock_tokenizer.return_value = mock_inputs

            # Mock the to() method to return the tensor itself (no GPU transfer)
            for key in mock_inputs:
                mock_inputs[key].to = MagicMock(return_value=mock_inputs[key])

            mock_output = MagicMock()
            mock_output.last_hidden_state = torch.randn(1, 3, 384)
            mock_output.pooler_output = torch.randn(1, 384)
            mock_model.return_value = mock_output

            refiner.score_tokenizer = mock_tokenizer
            refiner.score_model = mock_model

            all_pairs = [("query", "document")]
            scores = refiner._cal_score_sbert(all_pairs)

            assert len(scores) == 1
            assert isinstance(scores[0], (int, float))


class TestLongRefinerLoadModel:
    """Test model loading methods"""

    @patch("sage.libs.context.compression.algorithms.long_refiner_impl.refiner.AutoTokenizer")
    def test_load_score_model_bm25(self, mock_tokenizer):
        """Test loading BM25 scorer"""
        from sage.libs.context.compression.algorithms.long_refiner_impl.refiner import LongRefiner

        with patch.object(LongRefiner, "__init__", lambda x: None):
            refiner = LongRefiner()
            refiner._load_score_model("bm25", "", 0)

            assert refiner.score_model is None
            assert refiner.score_tokenizer is None
            assert refiner.local_score_func == refiner._cal_score_bm25

    @patch(
        "sage.libs.context.compression.algorithms.long_refiner_impl.refiner.AutoModelForSequenceClassification"
    )
    @patch("sage.libs.context.compression.algorithms.long_refiner_impl.refiner.AutoTokenizer")
    def test_load_score_model_reranker(self, mock_tokenizer, mock_model):
        """Test loading reranker model"""
        from sage.libs.context.compression.algorithms.long_refiner_impl.refiner import LongRefiner

        mock_model_instance = MagicMock()
        mock_model.from_pretrained.return_value = mock_model_instance
        mock_tokenizer_instance = MagicMock()
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance

        with patch.object(LongRefiner, "__init__", lambda x: None):
            refiner = LongRefiner()
            refiner._load_score_model("bge-reranker-v2-m3", "test/model", 0)

            assert refiner.score_model == mock_model_instance
            assert refiner.score_tokenizer == mock_tokenizer_instance

    @patch("sage.libs.context.compression.algorithms.long_refiner_impl.refiner.AutoModel")
    @patch("sage.libs.context.compression.algorithms.long_refiner_impl.refiner.AutoTokenizer")
    def test_load_score_model_sbert(self, mock_tokenizer, mock_model):
        """Test loading SBERT model"""
        from sage.libs.context.compression.algorithms.long_refiner_impl.refiner import LongRefiner

        mock_model_instance = MagicMock()
        mock_model.from_pretrained.return_value = mock_model_instance
        mock_tokenizer_instance = MagicMock()
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance

        with patch.object(LongRefiner, "__init__", lambda x: None):
            refiner = LongRefiner()
            refiner._load_score_model("sentence-transformers/all-MiniLM-L6-v2", "test/model", 0)

            assert refiner.score_model == mock_model_instance
            assert refiner.score_tokenizer == mock_tokenizer_instance
