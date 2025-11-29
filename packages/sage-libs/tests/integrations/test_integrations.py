"""
Unit tests for HuggingFace integration

These tests use mocking by default to avoid requiring real API keys.
For integration testing with real APIs, set environment variable:
- HF_TOKEN

Note:
    OpenAIClient has been removed. OpenAI functionality is now provided by
    sage.common.components.sage_llm.UnifiedInferenceClient (L1).
"""

from unittest.mock import MagicMock, patch

import pytest


class TestHuggingFaceIntegration:
    """Test HuggingFace integration module"""

    @patch("sage.libs.integrations.huggingface.AutoTokenizer.from_pretrained")
    @patch("sage.libs.integrations.huggingface.AutoModelForCausalLM.from_pretrained")
    def test_huggingface_client_creation(
        self, mock_model_from_pretrained, mock_tokenizer_from_pretrained
    ):
        """Test HuggingFace client creation"""
        from sage.libs.integrations.huggingface import HFClient

        mock_tokenizer_instance = MagicMock()
        mock_tokenizer_instance.eos_token = "</s>"
        mock_tokenizer_instance.pad_token = None
        mock_model_instance = MagicMock()

        mock_tokenizer_from_pretrained.return_value = mock_tokenizer_instance
        mock_model_from_pretrained.return_value = mock_model_instance

        client = HFClient(model_name="test-model", device="cpu")
        assert client is not None
        assert client.model_name == "test-model"

    @patch("sage.libs.integrations.huggingface.AutoTokenizer.from_pretrained")
    @patch("sage.libs.integrations.huggingface.AutoModelForCausalLM.from_pretrained")
    def test_huggingface_generate(self, mock_model_from_pretrained, mock_tokenizer_from_pretrained):
        """Test HuggingFace generation"""
        import torch

        from sage.libs.integrations.huggingface import HFClient

        mock_tokenizer_instance = MagicMock()
        mock_tokenizer_instance.eos_token = "</s>"
        mock_tokenizer_instance.eos_token_id = 2
        mock_tokenizer_instance.pad_token = None

        mock_input_dict = MagicMock()
        mock_input_dict.to.return_value = {"input_ids": torch.tensor([[1, 2, 3]])}
        mock_tokenizer_instance.return_value = mock_input_dict
        mock_tokenizer_instance.decode.return_value = "Generated text"

        mock_model_instance = MagicMock()
        mock_model_instance.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])

        mock_tokenizer_from_pretrained.return_value = mock_tokenizer_instance
        mock_model_from_pretrained.return_value = mock_model_instance

        client = HFClient(model_name="test-model", device="cpu")
        result = client.generate("Test prompt")
        assert result is not None

    @patch("sage.libs.integrations.huggingface.AutoTokenizer.from_pretrained")
    @patch("sage.libs.integrations.huggingface.AutoModelForCausalLM.from_pretrained")
    def test_huggingface_device_selection(
        self, mock_model_from_pretrained, mock_tokenizer_from_pretrained
    ):
        """Test HuggingFace device selection"""
        from sage.libs.integrations.huggingface import HFClient

        mock_tokenizer_instance = MagicMock()
        mock_tokenizer_instance.eos_token = "</s>"
        mock_tokenizer_instance.pad_token = None
        mock_model_instance = MagicMock()

        mock_tokenizer_from_pretrained.return_value = mock_tokenizer_instance
        mock_model_from_pretrained.return_value = mock_model_instance

        client = HFClient(model_name="test-model", device="cpu")
        assert client.device == "cpu"


class TestIntegrationErrorHandling:
    """Test error handling in integrations"""

    @patch("sage.libs.integrations.huggingface.AutoTokenizer.from_pretrained")
    @patch("sage.libs.integrations.huggingface.AutoModelForCausalLM.from_pretrained")
    def test_huggingface_model_not_found(
        self, mock_model_from_pretrained, mock_tokenizer_from_pretrained
    ):
        """Test HuggingFace model not found error"""
        from sage.libs.integrations.huggingface import HFClient

        error_msg = "nonexistent-model is not a local folder and is not a valid model identifier"
        mock_model_from_pretrained.side_effect = OSError(error_msg)

        with pytest.raises(OSError, match="is not a local folder"):
            HFClient(model_name="nonexistent-model")


class TestModuleImports:
    """Test that integration modules can be imported"""

    def test_huggingface_module_import(self):
        """Test HuggingFace module import"""
        from sage.libs.integrations import huggingface

        assert huggingface is not None
        assert hasattr(huggingface, "HFClient")


class TestIntegrationClasses:
    """Test that integration classes exist and can be instantiated"""

    @patch("transformers.AutoTokenizer")
    @patch("transformers.AutoModelForCausalLM")
    def test_hf_client_exists(self, mock_model, mock_tokenizer):
        """Test that HFClient class exists"""
        from sage.libs.integrations.huggingface import HFClient

        assert HFClient is not None
        assert callable(HFClient)
