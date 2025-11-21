"""Focused tests for the BedrockEmbedding wrapper."""

from unittest.mock import MagicMock, patch

import pytest

from sage.common.components.sage_embedding.wrappers.bedrock_wrapper import BedrockEmbedding


@pytest.mark.unit
class TestBedrockEmbedding:
    """Validate Bedrock embedding wrapper behavior."""

    @patch.dict(
        "os.environ", {"AWS_ACCESS_KEY_ID": "test-key", "AWS_SECRET_ACCESS_KEY": "test-secret"}
    )
    def test_initialization_with_env_vars(self):
        """Test that wrapper initializes with environment variables."""
        emb = BedrockEmbedding(model="amazon.titan-embed-text-v2:0")

        assert emb._model == "amazon.titan-embed-text-v2:0"
        assert emb.get_dim() == 1024
        assert emb.method_name == "bedrock"

    def test_initialization_with_explicit_credentials(self):
        """Test that wrapper initializes with explicit credentials."""
        emb = BedrockEmbedding(
            model="cohere.embed-multilingual-v3",
            aws_access_key_id="explicit-key",
            aws_secret_access_key="explicit-secret",
        )

        assert emb._model == "cohere.embed-multilingual-v3"
        assert emb.get_dim() == 1024

    def test_initialization_fails_without_credentials(self):
        """Test that wrapper fails without AWS credentials."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError, match="Bedrock embedding 需要 AWS 凭证"):
                BedrockEmbedding(model="amazon.titan-embed-text-v2:0")

    def test_get_model_info(self):
        """Test model info metadata."""
        info = BedrockEmbedding.get_model_info()

        assert info["method"] == "bedrock"
        assert info["requires_api_key"] is True
        assert info["requires_model_download"] is False
        assert info["default_dimension"] == 1024

    @patch.dict(
        "os.environ", {"AWS_ACCESS_KEY_ID": "test-key", "AWS_SECRET_ACCESS_KEY": "test-secret"}
    )
    @patch("boto3.client")
    def test_embed_batch_cohere_uses_native_batch(self, mock_boto3_client):
        """Test that Cohere models use native batch API."""
        # Setup mock
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock

        mock_response = {
            "body": MagicMock(read=lambda: b'{"embeddings": [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]}')
        }
        mock_bedrock.invoke_model.return_value = mock_response

        # Test
        emb = BedrockEmbedding(model="cohere.embed-multilingual-v3")
        texts = ["text1", "text2", "text3"]
        result = emb.embed_batch(texts)

        # Verify batch API was called once with all texts
        assert mock_bedrock.invoke_model.call_count == 1
        call_args = mock_bedrock.invoke_model.call_args
        assert '"texts": ["text1", "text2", "text3"]' in call_args[1]["body"]

        # Verify result
        assert len(result) == 3
        assert result[0] == [0.1, 0.2]
        assert result[1] == [0.3, 0.4]
        assert result[2] == [0.5, 0.6]

    @patch.dict(
        "os.environ", {"AWS_ACCESS_KEY_ID": "test-key", "AWS_SECRET_ACCESS_KEY": "test-secret"}
    )
    @patch("boto3.client")
    def test_embed_batch_titan_uses_sequential_calls(self, mock_boto3_client):
        """Test that Titan models use sequential embed() calls."""
        # Setup mock
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock

        # Mock responses for sequential calls
        mock_responses = [
            {"body": MagicMock(read=lambda: b'{"embedding": [0.1, 0.2]}')},
            {"body": MagicMock(read=lambda: b'{"embedding": [0.3, 0.4]}')},
        ]
        mock_bedrock.invoke_model.side_effect = mock_responses

        # Test
        emb = BedrockEmbedding(model="amazon.titan-embed-text-v2:0")
        texts = ["text1", "text2"]
        result = emb.embed_batch(texts)

        # Verify embed() was called twice (sequential)
        assert mock_bedrock.invoke_model.call_count == 2

        # Verify result
        assert len(result) == 2
        assert result[0] == [0.1, 0.2]
        assert result[1] == [0.3, 0.4]

    @patch.dict(
        "os.environ", {"AWS_ACCESS_KEY_ID": "test-key", "AWS_SECRET_ACCESS_KEY": "test-secret"}
    )
    def test_embed_batch_empty_list(self):
        """Test that empty list returns empty result."""
        emb = BedrockEmbedding(model="cohere.embed-multilingual-v3")
        result = emb.embed_batch([])

        assert result == []

    @patch.dict(
        "os.environ", {"AWS_ACCESS_KEY_ID": "test-key", "AWS_SECRET_ACCESS_KEY": "test-secret"}
    )
    def test_repr(self):
        """Test string representation."""
        emb = BedrockEmbedding(model="amazon.titan-embed-text-v1")

        repr_str = repr(emb)

        assert "BedrockEmbedding" in repr_str
        assert "amazon.titan-embed-text-v1" in repr_str
        assert "1536" in repr_str  # dimension for v1
