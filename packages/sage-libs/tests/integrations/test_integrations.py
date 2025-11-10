"""
Unit tests for OpenAI and HuggingFace integrations
"""

from unittest.mock import MagicMock, patch

import pytest


class TestOpenAIIntegration:
    """Test OpenAI integration module"""

    @patch("openai.OpenAI")
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

    @patch("openai.OpenAI")
    def test_openai_generate(self, mock_openai_class):
        """Test OpenAI generate functionality"""
        from sage.libs.integrations.openai import OpenAIClient

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Test response"
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(
            model_name="gpt-4",
            base_url="http://test.com/v1",
            api_key="test_key",  # pragma: allowlist secret
        )
        messages = [{"role": "user", "content": "Hello"}]
        result = client.generate(messages)
        assert result == "Test response"

    @patch("openai.OpenAI")
    def test_openai_generate_with_dict_message(self, mock_openai_class):
        """Test OpenAI generate with single dict message"""
        from sage.libs.integrations.openai import OpenAIClient

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Test response"
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(
            model_name="gpt-4",
            base_url="http://test.com/v1",
            api_key="test_key",  # pragma: allowlist secret
        )
        message = {"role": "user", "content": "Hello"}
        result = client.generate(message)
        assert result == "Test response"

    @patch("openai.OpenAI")
    def test_openai_generate_error_handling(self, mock_openai_class):
        """Test OpenAI error handling"""
        from sage.libs.integrations.openai import OpenAIClient

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(
            model_name="gpt-4",
            base_url="http://test.com/v1",
            api_key="test_key",  # pragma: allowlist secret
        )

        with pytest.raises(RuntimeError, match="Response generation failed"):
            client.generate([{"role": "user", "content": "Hello"}])


class TestHuggingFaceIntegration:
    """Test HuggingFace integration module"""

    @patch("transformers.AutoTokenizer")
    @patch("transformers.AutoModelForCausalLM")
    def test_huggingface_client_creation(self, mock_model, mock_tokenizer):
        """Test HuggingFace client creation"""
        from sage.libs.integrations.huggingface import HFClient

        mock_tokenizer_instance = MagicMock()
        mock_tokenizer_instance.eos_token = "</s>"
        mock_tokenizer_instance.pad_token = None
        mock_model_instance = MagicMock()
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
        mock_model.from_pretrained.return_value = mock_model_instance

        client = HFClient(model_name="test-model")
        assert client is not None
        assert client.model_name == "test-model"

    @patch("transformers.AutoTokenizer")
    @patch("transformers.AutoModelForCausalLM")
    def test_huggingface_generate(self, mock_model, mock_tokenizer):
        """Test HuggingFace generation"""
        from sage.libs.integrations.huggingface import HFClient

        mock_tokenizer_instance = MagicMock()
        mock_tokenizer_instance.eos_token = "</s>"
        mock_tokenizer_instance.eos_token_id = 2
        mock_tokenizer_instance.pad_token = None
        mock_tokenizer_instance.return_value = {"input_ids": [[1, 2, 3]]}
        mock_tokenizer_instance.decode.return_value = "Generated text"

        mock_model_instance = MagicMock()
        mock_model_instance.generate.return_value = [[1, 2, 3, 4, 5]]

        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
        mock_model.from_pretrained.return_value = mock_model_instance

        client = HFClient(model_name="test-model", device="cpu")
        result = client.generate("Test prompt")
        assert result is not None

    @patch("transformers.AutoTokenizer")
    @patch("transformers.AutoModelForCausalLM")
    def test_huggingface_device_selection(self, mock_model, mock_tokenizer):
        """Test HuggingFace device selection"""
        from sage.libs.integrations.huggingface import HFClient

        mock_tokenizer_instance = MagicMock()
        mock_tokenizer_instance.eos_token = "</s>"
        mock_tokenizer_instance.pad_token = None
        mock_model_instance = MagicMock()
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
        mock_model.from_pretrained.return_value = mock_model_instance

        client = HFClient(model_name="test-model", device="cpu")
        assert client.device == "cpu"


class TestIntegrationErrorHandling:
    """Test error handling in integrations"""

    @patch("openai.OpenAI")
    def test_openai_api_error_handling(self, mock_openai_class):
        """Test OpenAI API error handling"""
        from sage.libs.integrations.openai import OpenAIClient

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(
            model_name="gpt-4",
            base_url="http://test.com/v1",
            api_key="test_key",  # pragma: allowlist secret
        )

        with pytest.raises(RuntimeError, match="Response generation failed"):
            client.generate([{"role": "user", "content": "Test"}])

    @patch("transformers.AutoTokenizer")
    @patch("transformers.AutoModelForCausalLM")
    def test_huggingface_model_not_found(self, mock_model, mock_tokenizer):
        """Test HuggingFace model not found error"""
        from sage.libs.integrations.huggingface import HFClient

        mock_model.from_pretrained.side_effect = Exception("Model not found")

        with pytest.raises(Exception, match="Model not found"):
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
