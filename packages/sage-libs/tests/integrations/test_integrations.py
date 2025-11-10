"""
Unit tests for OpenAI and HuggingFace integrations

These tests use mocking by default to avoid requiring real API keys.
For integration testing with real APIs, set environment variables:
- OPENAI_API_KEY
- HF_TOKEN
"""

from unittest.mock import MagicMock, patch

import pytest


class TestOpenAIIntegration:
    """Test OpenAI integration module"""

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_openai_client_creation(self, mock_openai_class):
        """Test OpenAI client creation"""
        from sage.libs.integrations.openai import OpenAIClient

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(
            model_name="gpt-4",
            base_url="http://test.com/v1",
            api_key="test_key",  # pragma: allowlist secret
        )
        assert client is not None
        assert client.model_name == "gpt-4"

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_openai_generate(self, mock_openai_class):
        """Test OpenAI generate functionality"""
        from sage.libs.integrations.openai import OpenAIClient

        # Create properly structured mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock the response structure
        mock_message = MagicMock()
        mock_message.content = "Test response"

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(
            model_name="gpt-4",
            base_url="http://test.com/v1",
            api_key="test_key",  # pragma: allowlist secret
        )
        messages = [{"role": "user", "content": "Hello"}]
        result = client.generate(messages)
        assert result == "Test response"

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_openai_generate_with_dict_message(self, mock_openai_class):
        """Test OpenAI generate with single dict message"""
        from sage.libs.integrations.openai import OpenAIClient

        # Create properly structured mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = "Test response"

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(
            model_name="gpt-4",
            base_url="http://test.com/v1",
            api_key="test_key",  # pragma: allowlist secret
        )
        message = {"role": "user", "content": "Hello"}
        result = client.generate(message)
        assert result == "Test response"

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_openai_generate_error_handling(self, mock_openai_class):
        """Test OpenAI error handling"""
        from sage.libs.integrations.openai import OpenAIClient

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Set side_effect on the create method
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        client = OpenAIClient(
            model_name="gpt-4",
            base_url="http://test.com/v1",
            api_key="test_key",  # pragma: allowlist secret
        )

        with pytest.raises(RuntimeError, match="Response generation failed"):
            client.generate([{"role": "user", "content": "Hello"}])


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

        # Mock tokenizer call to return proper dict
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

    @patch("sage.libs.integrations.openai.OpenAI")
    def test_openai_api_error_handling(self, mock_openai_class):
        """Test OpenAI API error handling"""
        from sage.libs.integrations.openai import OpenAIClient

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Set side_effect on the create method
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        client = OpenAIClient(
            model_name="gpt-4",
            base_url="http://test.com/v1",
            api_key="test_key",  # pragma: allowlist secret
        )

        # Should raise RuntimeError from the generate method's exception handling
        with pytest.raises(RuntimeError, match="Response generation failed"):
            client.generate([{"role": "user", "content": "Test"}])

    @patch("sage.libs.integrations.huggingface.AutoTokenizer.from_pretrained")
    @patch("sage.libs.integrations.huggingface.AutoModelForCausalLM.from_pretrained")
    def test_huggingface_model_not_found(
        self, mock_model_from_pretrained, mock_tokenizer_from_pretrained
    ):
        """Test HuggingFace model not found error"""
        from sage.libs.integrations.huggingface import HFClient

        # Mock the actual error message from HuggingFace
        error_msg = "nonexistent-model is not a local folder and is not a valid model identifier listed on 'https://huggingface.co/models'\nIf this is a private repository, make sure to pass a token having permission to this repo either by logging in with `hf auth login` or by passing `token=<your_token>`"
        mock_model_from_pretrained.side_effect = OSError(error_msg)

        with pytest.raises(
            OSError, match="is not a local folder and is not a valid model identifier"
        ):
            HFClient(model_name="nonexistent-model")


class TestModuleImports:
    """Test that integration modules can be imported"""

    def test_openai_module_import(self):
        """Test OpenAI module import"""
        from sage.libs.integrations import openai

        assert openai is not None
        assert hasattr(openai, "OpenAIClient")

    def test_huggingface_module_import(self):
        """Test HuggingFace module import"""
        from sage.libs.integrations import huggingface

        assert huggingface is not None
        assert hasattr(huggingface, "HFClient")


class TestIntegrationClasses:
    """Test that integration classes exist and can be instantiated"""

    @patch("openai.OpenAI")
    def test_openai_client_exists(self, mock_openai):
        """Test that OpenAIClient class exists"""
        from sage.libs.integrations.openai import OpenAIClient

        assert OpenAIClient is not None
        assert callable(OpenAIClient)

    @patch("transformers.AutoTokenizer")
    @patch("transformers.AutoModelForCausalLM")
    def test_hf_client_exists(self, mock_model, mock_tokenizer):
        """Test that HFClient class exists"""
        from sage.libs.integrations.huggingface import HFClient

        assert HFClient is not None
        assert callable(HFClient)
