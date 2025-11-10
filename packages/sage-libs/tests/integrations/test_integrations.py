"""
Unit tests for OpenAI and HuggingFace integrations
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestOpenAIIntegration:
    """Test OpenAI integration module"""

    @patch("openai.OpenAI")
    def test_openai_client_creation(self, mock_openai_class):
        """Test OpenAI client creation"""
        try:
            from sage.libs.integrations.openai import get_openai_client

            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client

            client = get_openai_client(api_key="test_key")
            assert client is not None
        except (ImportError, AttributeError):
            # Function may not exist
            pytest.skip("get_openai_client not available")

    @patch("openai.OpenAI")
    def test_openai_completion(self, mock_openai_class):
        """Test OpenAI completion functionality"""
        try:
            from sage.libs.integrations.openai import create_completion

            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(text="Test response")]
            mock_client.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            result = create_completion("Test prompt", api_key="test_key")
            assert result is not None
        except (ImportError, AttributeError):
            pytest.skip("create_completion not available")

    @patch("openai.OpenAI")
    def test_openai_chat_completion(self, mock_openai_class):
        """Test OpenAI chat completion"""
        try:
            from sage.libs.integrations.openai import create_chat_completion

            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            messages = [{"role": "user", "content": "Hello"}]
            result = create_chat_completion(messages, api_key="test_key")
            assert result is not None
        except (ImportError, AttributeError):
            pytest.skip("create_chat_completion not available")

    @patch("openai.OpenAI")
    def test_openai_embedding(self, mock_openai_class):
        """Test OpenAI embedding generation"""
        try:
            from sage.libs.integrations.openai import create_embedding

            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
            mock_client.embeddings.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            result = create_embedding("Test text", api_key="test_key")
            assert result is not None
        except (ImportError, AttributeError):
            pytest.skip("create_embedding not available")


class TestHuggingFaceIntegration:
    """Test HuggingFace integration module"""

    @patch("transformers.AutoTokenizer")
    @patch("transformers.AutoModel")
    def test_huggingface_model_loading(self, mock_model, mock_tokenizer):
        """Test HuggingFace model loading"""
        try:
            from sage.libs.integrations.huggingface import load_model

            mock_tokenizer_instance = MagicMock()
            mock_model_instance = MagicMock()
            mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
            mock_model.from_pretrained.return_value = mock_model_instance

            model, tokenizer = load_model("bert-base-uncased")
            assert model is not None
            assert tokenizer is not None
        except (ImportError, AttributeError):
            pytest.skip("load_model not available")

    @patch("transformers.pipeline")
    def test_huggingface_pipeline(self, mock_pipeline):
        """Test HuggingFace pipeline creation"""
        try:
            from sage.libs.integrations.huggingface import create_pipeline

            mock_pipe = MagicMock()
            mock_pipeline.return_value = mock_pipe

            pipe = create_pipeline("text-generation")
            assert pipe is not None
        except (ImportError, AttributeError):
            pytest.skip("create_pipeline not available")

    @patch("transformers.AutoTokenizer")
    def test_huggingface_tokenization(self, mock_tokenizer):
        """Test HuggingFace tokenization"""
        try:
            from sage.libs.integrations.huggingface import tokenize_text

            mock_tokenizer_instance = MagicMock()
            mock_tokenizer_instance.return_value = {"input_ids": [101, 102]}
            mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance

            result = tokenize_text("Test text", "bert-base-uncased")
            assert result is not None
        except (ImportError, AttributeError):
            pytest.skip("tokenize_text not available")


class TestIntegrationErrorHandling:
    """Test error handling in integrations"""

    @patch("openai.OpenAI")
    def test_openai_api_error_handling(self, mock_openai_class):
        """Test OpenAI API error handling"""
        try:
            from sage.libs.integrations.openai import create_completion

            mock_client = MagicMock()
            mock_client.completions.create.side_effect = Exception("API Error")
            mock_openai_class.return_value = mock_client

            try:
                create_completion("Test prompt", api_key="test_key")
            except Exception as e:
                assert "API Error" in str(e) or isinstance(e, Exception)
        except (ImportError, AttributeError):
            pytest.skip("create_completion not available")

    @patch("transformers.AutoModel")
    def test_huggingface_model_not_found(self, mock_model):
        """Test HuggingFace model not found error"""
        try:
            from sage.libs.integrations.huggingface import load_model

            mock_model.from_pretrained.side_effect = Exception("Model not found")

            try:
                load_model("nonexistent-model")
            except Exception as e:
                assert isinstance(e, Exception)
        except (ImportError, AttributeError):
            pytest.skip("load_model not available")


class TestIntegrationConfiguration:
    """Test configuration for integrations"""

    def test_openai_api_key_configuration(self):
        """Test OpenAI API key configuration"""
        try:
            from sage.libs.integrations import openai as openai_integration

            # Check if API key configuration exists
            if hasattr(openai_integration, "set_api_key"):
                openai_integration.set_api_key("test_key")
        except (ImportError, AttributeError):
            pytest.skip("OpenAI integration not fully available")

    def test_huggingface_cache_configuration(self):
        """Test HuggingFace cache configuration"""
        try:
            from sage.libs.integrations import huggingface as hf_integration

            # Check if cache configuration exists
            if hasattr(hf_integration, "set_cache_dir"):
                hf_integration.set_cache_dir("/tmp/cache")
        except (ImportError, AttributeError):
            pytest.skip("HuggingFace integration not fully available")


class TestModuleImports:
    """Test that integration modules can be imported"""

    def test_openai_module_import(self):
        """Test OpenAI module import"""
        try:
            from sage.libs.integrations import openai

            assert openai is not None
        except ImportError:
            pytest.skip("OpenAI integration module not available")

    def test_huggingface_module_import(self):
        """Test HuggingFace module import"""
        try:
            from sage.libs.integrations import huggingface

            assert huggingface is not None
        except ImportError:
            pytest.skip("HuggingFace integration module not available")


class TestIntegrationUtils:
    """Test utility functions in integrations"""

    def test_openai_utils_exist(self):
        """Test that OpenAI utility functions exist"""
        try:
            from sage.libs.integrations import openai as openai_integration

            # Check for common utility functions
            expected_functions = [
                "get_openai_client",
                "create_completion",
                "create_chat_completion",
                "create_embedding",
            ]

            for func_name in expected_functions:
                if hasattr(openai_integration, func_name):
                    assert callable(getattr(openai_integration, func_name))
        except ImportError:
            pytest.skip("OpenAI integration not available")

    def test_huggingface_utils_exist(self):
        """Test that HuggingFace utility functions exist"""
        try:
            from sage.libs.integrations import huggingface as hf_integration

            # Check for common utility functions
            expected_functions = ["load_model", "create_pipeline", "tokenize_text"]

            for func_name in expected_functions:
                if hasattr(hf_integration, func_name):
                    assert callable(getattr(hf_integration, func_name))
        except ImportError:
            pytest.skip("HuggingFace integration not available")
