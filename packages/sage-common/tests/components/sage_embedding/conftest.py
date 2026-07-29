"""
Shared fixtures for embedding wrapper tests.
"""

from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    mock_response = Mock()
    mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3] * 512)]  # 1536 dims
    return mock_response


@pytest.fixture
def mock_openai_batch_response():
    """Mock OpenAI API batch response"""
    mock_response = Mock()
    mock_response.data = [
        Mock(embedding=[0.1, 0.2, 0.3] * 512),
        Mock(embedding=[0.4, 0.5, 0.6] * 512),
    ]
    return mock_response


@pytest.fixture
def mock_hf_model():
    """Mock HuggingFace model"""
    mock_model = MagicMock()
    mock_tokenizer = MagicMock()

    # Mock encode method
    mock_tokenizer.return_value = {"input_ids": [[1, 2, 3]], "attention_mask": [[1, 1, 1]]}

    # Mock model output
    mock_output = Mock()
    mock_output.last_hidden_state = Mock()
    # Mock tensor with mean() method
    mock_tensor = Mock()
    mock_tensor.mean.return_value = Mock()
    mock_tensor.mean.return_value.squeeze.return_value = Mock()
    mock_tensor.mean.return_value.squeeze.return_value.cpu.return_value = Mock()
    mock_tensor.mean.return_value.squeeze.return_value.cpu.return_value.numpy.return_value = [
        0.1,
        0.2,
        0.3,
    ] * 256
    mock_output.last_hidden_state = mock_tensor

    mock_model.return_value = mock_output

    return mock_model, mock_tokenizer


@pytest.fixture
def mock_jina_response():
    """Mock Jina API response"""
    mock_response = Mock()
    mock_response.json.return_value = {"data": [{"embedding": [0.1, 0.2, 0.3] * 256}]}
    mock_response.status_code = 200
    return mock_response


@pytest.fixture
def mock_zhipu_response():
    """Mock Zhipu API response"""
    mock_response = Mock()
    mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3] * 512)]
    return mock_response


@pytest.fixture
def mock_cohere_response():
    """Mock Cohere API response"""
    mock_response = Mock()
    mock_response.embeddings = [[0.1, 0.2, 0.3] * 512]
    return mock_response


@pytest.fixture
def mock_bedrock_response():
    """Mock AWS Bedrock response"""
    return {"embedding": [0.1, 0.2, 0.3] * 512}


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response"""
    mock_response = Mock()
    mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3] * 256}
    mock_response.status_code = 200
    return mock_response


@pytest.fixture
def mock_siliconcloud_response():
    """Mock SiliconCloud API response"""
    mock_response = Mock()
    mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3] * 512)]
    return mock_response


@pytest.fixture
def mock_nvidia_openai_response():
    """Mock NVIDIA OpenAI compatible response"""
    mock_response = Mock()
    mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3] * 256)]
    return mock_response


@pytest.fixture
def sample_texts():
    """Sample texts for testing"""
    return ["Hello world", "This is a test", "Embedding models are cool"]


@pytest.fixture
def sample_text():
    """Single sample text"""
    return "Hello world"
