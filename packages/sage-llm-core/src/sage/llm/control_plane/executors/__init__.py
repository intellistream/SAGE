"""Executors package for Control Plane execution coordinators.

This package provides executor implementations for routing inference requests
to different types of backend services:

- ExecutionCoordinatorBase: Abstract base class for all executors
- HttpExecutionCoordinator: LLM execution via vLLM HTTP API
- LocalAsyncExecutionCoordinator: Local async execution
- EmbeddingExecutor: Embedding execution via OpenAI-compatible API
"""

from .base import ExecutionCoordinatorBase
from .embedding_executor import (
    EmbeddingExecutor,
    EmbeddingExecutorError,
    EmbeddingInstanceUnavailableError,
    EmbeddingMetrics,
    EmbeddingRequestError,
    EmbeddingResult,
    EmbeddingTimeoutError,
)
from .http_client import HttpExecutionCoordinator
from .local_async import LocalAsyncExecutionCoordinator

__all__ = [
    # Base
    "ExecutionCoordinatorBase",
    # LLM Executors
    "HttpExecutionCoordinator",
    "LocalAsyncExecutionCoordinator",
    # Embedding Executor
    "EmbeddingExecutor",
    "EmbeddingResult",
    "EmbeddingMetrics",
    # Embedding Exceptions
    "EmbeddingExecutorError",
    "EmbeddingInstanceUnavailableError",
    "EmbeddingTimeoutError",
    "EmbeddingRequestError",
]
