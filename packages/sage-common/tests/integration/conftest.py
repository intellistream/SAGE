# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Pytest fixtures for integration tests.

This module provides shared fixtures for integration testing of:
- Hybrid scheduling (LLM + Embedding mixed workloads)
- Unified API Server endpoints
- Unified client end-to-end flows

Fixtures are designed to work without requiring real GPUs by using
mock backends that simulate vLLM and embedding server responses.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add source path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

# Try to import control plane types, but gracefully handle if submodule is not available
try:
    from sage.llm.sageLLM.control_plane.types import (
        ExecutionInstance,
        ExecutionInstanceType,
        RequestMetadata,
        RequestPriority,
        RequestType,
    )

    _CONTROL_PLANE_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    # Create mock types for when control plane submodule is not available
    _CONTROL_PLANE_AVAILABLE = False
    from dataclasses import dataclass as dc
    from enum import Enum, auto

    class RequestType(Enum):
        LLM_CHAT = auto()
        LLM_GENERATE = auto()
        EMBEDDING = auto()

    class RequestPriority(Enum):
        LOW = auto()
        NORMAL = auto()
        HIGH = auto()
        CRITICAL = auto()

    class ExecutionInstanceType(Enum):
        GENERAL = auto()
        EMBEDDING = auto()
        LLM_EMBEDDING = auto()

    @dc
    class RequestMetadata:
        request_id: str = ""
        prompt: str = ""
        model_name: str = ""
        max_tokens: int = 100
        request_type: RequestType = RequestType.LLM_CHAT
        priority: RequestPriority = RequestPriority.NORMAL
        embedding_texts: list[str] | None = None
        embedding_model: str = ""
        embedding_batch_size: int = 32

        def __post_init__(self):
            if self.embedding_texts is None:
                self.embedding_texts = []

    @dc
    class ExecutionInstance:
        instance_id: str = ""
        host: str = "localhost"
        port: int = 8001
        instance_type: ExecutionInstanceType = ExecutionInstanceType.GENERAL
        model_name: str = ""
        supported_request_types: list[RequestType] | None = None
        embedding_model_loaded: str = ""
        embedding_max_batch_size: int = 32

        def __post_init__(self):
            if self.supported_request_types is None:
                self.supported_request_types = []


# =============================================================================
# Mock Backend Fixtures
# =============================================================================


@dataclass
class MockBackendResponse:
    """Simulated response from a mock backend."""

    status: int = 200
    data: dict[str, Any] | None = None
    delay_ms: float = 10.0


class MockLLMBackend:
    """Mock LLM backend that simulates vLLM server responses.

    This class simulates an OpenAI-compatible LLM server for testing
    without requiring actual GPU resources.
    """

    def __init__(
        self,
        model_name: str = "mock-llm-model",
        host: str = "localhost",
        port: int = 8001,
        response_delay_ms: float = 50.0,
    ) -> None:
        """Initialize mock LLM backend.

        Args:
            model_name: Name of the mock model.
            host: Host address for the mock backend.
            port: Port number for the mock backend.
            response_delay_ms: Simulated response delay in milliseconds.
        """
        self.model_name = model_name
        self.host = host
        self.port = port
        self.response_delay_ms = response_delay_ms
        self.request_count = 0
        self.last_request: dict[str, Any] | None = None

    @property
    def base_url(self) -> str:
        """Get the base URL for this backend."""
        return f"http://{self.host}:{self.port}/v1"

    async def handle_chat_completion(self, request: dict[str, Any]) -> MockBackendResponse:
        """Handle a chat completion request.

        Args:
            request: The chat completion request body.

        Returns:
            MockBackendResponse with simulated chat completion.
        """
        self.request_count += 1
        self.last_request = request

        # Simulate processing delay
        await asyncio.sleep(self.response_delay_ms / 1000)

        messages = request.get("messages", [])
        last_message = messages[-1].get("content", "") if messages else ""

        return MockBackendResponse(
            status=200,
            data={
                "id": f"chatcmpl-mock-{self.request_count}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.get("model", self.model_name),
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": f"Mock response to: {last_message[:50]}",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": len(last_message.split()) * 2,
                    "completion_tokens": 10,
                    "total_tokens": len(last_message.split()) * 2 + 10,
                },
            },
            delay_ms=self.response_delay_ms,
        )

    async def handle_completion(self, request: dict[str, Any]) -> MockBackendResponse:
        """Handle a text completion request.

        Args:
            request: The completion request body.

        Returns:
            MockBackendResponse with simulated text completion.
        """
        self.request_count += 1
        self.last_request = request

        await asyncio.sleep(self.response_delay_ms / 1000)

        prompt = request.get("prompt", "")

        return MockBackendResponse(
            status=200,
            data={
                "id": f"cmpl-mock-{self.request_count}",
                "object": "text_completion",
                "created": int(time.time()),
                "model": request.get("model", self.model_name),
                "choices": [
                    {
                        "index": 0,
                        "text": f" continued: {prompt[:20]}...",
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": 5,
                    "total_tokens": len(prompt.split()) + 5,
                },
            },
            delay_ms=self.response_delay_ms,
        )

    def get_health(self) -> dict[str, Any]:
        """Get health status of the mock backend."""
        return {
            "status": "healthy",
            "model": self.model_name,
            "request_count": self.request_count,
        }


class MockEmbeddingBackend:
    """Mock Embedding backend that simulates embedding server responses.

    This class simulates an OpenAI-compatible embedding server for testing
    without requiring actual model loading.
    """

    def __init__(
        self,
        model_name: str = "mock-embedding-model",
        host: str = "localhost",
        port: int = 8090,
        embedding_dim: int = 384,
        response_delay_ms: float = 20.0,
    ) -> None:
        """Initialize mock embedding backend.

        Args:
            model_name: Name of the mock model.
            host: Host address for the mock backend.
            port: Port number for the mock backend.
            embedding_dim: Dimension of generated embeddings.
            response_delay_ms: Simulated response delay in milliseconds.
        """
        self.model_name = model_name
        self.host = host
        self.port = port
        self.embedding_dim = embedding_dim
        self.response_delay_ms = response_delay_ms
        self.request_count = 0
        self.last_request: dict[str, Any] | None = None

    @property
    def base_url(self) -> str:
        """Get the base URL for this backend."""
        return f"http://{self.host}:{self.port}/v1"

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate a deterministic mock embedding for a text.

        Args:
            text: Input text to embed.

        Returns:
            A list of floats representing the mock embedding.
        """
        # Use hash for deterministic embeddings
        import hashlib

        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        # Generate normalized embedding vector
        embedding = []
        for i in range(self.embedding_dim):
            # Use hash to generate pseudo-random but deterministic values
            val = ((hash_val + i * 31) % 1000) / 1000.0 - 0.5
            embedding.append(val)
        # Normalize
        norm = sum(v * v for v in embedding) ** 0.5
        if norm > 0:
            embedding = [v / norm for v in embedding]
        return embedding

    async def handle_embedding(self, request: dict[str, Any]) -> MockBackendResponse:
        """Handle an embedding request.

        Args:
            request: The embedding request body.

        Returns:
            MockBackendResponse with simulated embeddings.
        """
        self.request_count += 1
        self.last_request = request

        await asyncio.sleep(self.response_delay_ms / 1000)

        # Handle both string and list inputs
        input_texts = request.get("input", [])
        if isinstance(input_texts, str):
            input_texts = [input_texts]

        embeddings_data = []
        total_tokens = 0
        for i, text in enumerate(input_texts):
            embedding = self._generate_embedding(text)
            embeddings_data.append(
                {
                    "object": "embedding",
                    "index": i,
                    "embedding": embedding,
                }
            )
            total_tokens += len(text.split())

        return MockBackendResponse(
            status=200,
            data={
                "object": "list",
                "data": embeddings_data,
                "model": request.get("model", self.model_name),
                "usage": {
                    "prompt_tokens": total_tokens,
                    "total_tokens": total_tokens,
                },
            },
            delay_ms=self.response_delay_ms,
        )

    def get_health(self) -> dict[str, Any]:
        """Get health status of the mock backend."""
        return {
            "status": "healthy",
            "model": self.model_name,
            "embedding_dim": self.embedding_dim,
            "request_count": self.request_count,
        }


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_backend() -> MockLLMBackend:
    """Create a mock LLM backend."""
    return MockLLMBackend(
        model_name="Qwen/Qwen2.5-7B-Instruct",
        host="localhost",
        port=8001,
        response_delay_ms=10.0,
    )


@pytest.fixture
def mock_embedding_backend() -> MockEmbeddingBackend:
    """Create a mock embedding backend."""
    return MockEmbeddingBackend(
        model_name="BAAI/bge-m3",
        host="localhost",
        port=8090,
        embedding_dim=1024,
        response_delay_ms=5.0,
    )


@pytest.fixture
def mock_mixed_backend() -> tuple[MockLLMBackend, MockEmbeddingBackend]:
    """Create a mock mixed backend that handles both LLM and embedding."""
    llm = MockLLMBackend(
        model_name="Qwen/Qwen2.5-7B-Instruct",
        host="localhost",
        port=8000,
        response_delay_ms=10.0,
    )
    embed = MockEmbeddingBackend(
        model_name="BAAI/bge-m3",
        host="localhost",
        port=8000,
        embedding_dim=1024,
        response_delay_ms=5.0,
    )
    return llm, embed


@pytest.fixture
def llm_execution_instance() -> ExecutionInstance:
    """Create an LLM execution instance for testing."""
    return ExecutionInstance(
        instance_id="llm-instance-1",
        host="localhost",
        port=8001,
        instance_type=ExecutionInstanceType.GENERAL,
        model_name="Qwen/Qwen2.5-7B-Instruct",
        supported_request_types=[RequestType.LLM_CHAT, RequestType.LLM_GENERATE],
    )


@pytest.fixture
def embedding_execution_instance() -> ExecutionInstance:
    """Create an embedding execution instance for testing."""
    return ExecutionInstance(
        instance_id="embed-instance-1",
        host="localhost",
        port=8090,
        instance_type=ExecutionInstanceType.EMBEDDING,
        model_name="BAAI/bge-m3",
        supported_request_types=[RequestType.EMBEDDING],
        embedding_model_loaded="BAAI/bge-m3",
        embedding_max_batch_size=32,
    )


@pytest.fixture
def mixed_execution_instance() -> ExecutionInstance:
    """Create a mixed LLM+Embedding execution instance for testing."""
    return ExecutionInstance(
        instance_id="mixed-instance-1",
        host="localhost",
        port=8000,
        instance_type=ExecutionInstanceType.LLM_EMBEDDING,
        model_name="Qwen/Qwen2.5-7B-Instruct",
        supported_request_types=[
            RequestType.LLM_CHAT,
            RequestType.LLM_GENERATE,
            RequestType.EMBEDDING,
        ],
        embedding_model_loaded="BAAI/bge-m3",
        embedding_max_batch_size=16,
    )


@pytest.fixture
def sample_llm_requests() -> list[RequestMetadata]:
    """Create sample LLM requests for testing."""
    return [
        RequestMetadata(
            request_id=f"llm-req-{i}",
            prompt=f"Test prompt {i}",
            model_name="Qwen/Qwen2.5-7B-Instruct",
            max_tokens=100,
            request_type=RequestType.LLM_CHAT,
            priority=RequestPriority.NORMAL,
        )
        for i in range(5)
    ]


@pytest.fixture
def sample_embedding_requests() -> list[RequestMetadata]:
    """Create sample embedding requests for testing."""
    return [
        RequestMetadata(
            request_id=f"embed-req-{i}",
            embedding_texts=[f"Text {i}-1", f"Text {i}-2", f"Text {i}-3"],
            embedding_model="BAAI/bge-m3",
            embedding_batch_size=32,
            request_type=RequestType.EMBEDDING,
            priority=RequestPriority.NORMAL,
        )
        for i in range(3)
    ]


@pytest.fixture
def mixed_requests(
    sample_llm_requests: list[RequestMetadata],
    sample_embedding_requests: list[RequestMetadata],
) -> list[RequestMetadata]:
    """Create mixed LLM and embedding requests for testing."""
    # Interleave requests
    mixed = []
    max_len = max(len(sample_llm_requests), len(sample_embedding_requests))
    for i in range(max_len):
        if i < len(sample_llm_requests):
            mixed.append(sample_llm_requests[i])
        if i < len(sample_embedding_requests):
            mixed.append(sample_embedding_requests[i])
    return mixed


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Helper Functions
# =============================================================================


def create_mock_aiohttp_response(
    status: int = 200,
    json_data: dict[str, Any] | None = None,
    text: str = "",
) -> AsyncMock:
    """Create a mock aiohttp response.

    Args:
        status: HTTP status code.
        json_data: JSON response data.
        text: Text response content.

    Returns:
        AsyncMock configured as aiohttp response.
    """
    mock_response = AsyncMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=json_data or {})
    mock_response.text = AsyncMock(return_value=text or json.dumps(json_data or {}))
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    return mock_response


def create_mock_openai_chat_response(
    content: str = "Mock response",
    model: str = "mock-model",
    usage: dict[str, int] | None = None,
) -> MagicMock:
    """Create a mock OpenAI chat completion response.

    Args:
        content: The assistant message content.
        model: Model name in the response.
        usage: Token usage statistics.

    Returns:
        MagicMock configured as OpenAI ChatCompletion.
    """
    mock = MagicMock()
    mock.id = f"chatcmpl-mock-{time.time()}"
    mock.model = model
    mock.choices = [MagicMock()]
    mock.choices[0].message = MagicMock()
    mock.choices[0].message.content = content
    mock.choices[0].finish_reason = "stop"
    mock.usage = MagicMock()
    usage = usage or {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    mock.usage.prompt_tokens = usage["prompt_tokens"]
    mock.usage.completion_tokens = usage["completion_tokens"]
    mock.usage.total_tokens = usage["total_tokens"]
    return mock


def create_mock_openai_embedding_response(
    embeddings: list[list[float]] | None = None,
    model: str = "mock-embedding-model",
) -> MagicMock:
    """Create a mock OpenAI embedding response.

    Args:
        embeddings: List of embedding vectors.
        model: Model name in the response.

    Returns:
        MagicMock configured as OpenAI Embedding response.
    """
    if embeddings is None:
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    mock = MagicMock()
    mock.model = model
    mock.data = []
    for i, emb in enumerate(embeddings):
        emb_obj = MagicMock()
        emb_obj.embedding = emb
        emb_obj.index = i
        mock.data.append(emb_obj)
    mock.usage = MagicMock()
    mock.usage.prompt_tokens = 10
    mock.usage.total_tokens = 10
    return mock
