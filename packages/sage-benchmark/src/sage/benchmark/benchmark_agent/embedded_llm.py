"""
Embedded LLM Service for Benchmarks

Provides a unified interface to run LLM inference using embedded vLLM
when GPU is available, or fallback to API-based LLM.

This enables running benchmarks without external API dependencies when
GPU is available locally.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def check_gpu_available() -> bool:
    """Check if GPU is available for local LLM inference."""
    try:
        import torch

        return torch.cuda.is_available()
    except ImportError:
        return False


def check_vllm_available() -> bool:
    """Check if vLLM is installed and GPU is available."""
    if not check_gpu_available():
        return False
    try:
        import vllm  # noqa: F401

        return True
    except ImportError:
        return False


class EmbeddedLLMClient:
    """
    Embedded LLM client using VLLMService for local inference.

    Provides OpenAI-compatible interface for benchmark compatibility.
    """

    # Default small model for testing
    DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

    # Class-level singleton cache
    _instances: dict[str, EmbeddedLLMClient] = {}

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL,
        auto_download: bool = True,
        max_tokens: int = 512,
        temperature: float = 0.1,
        gpu_memory_utilization: float = 0.5,  # Conservative for testing
    ):
        """
        Initialize embedded LLM client.

        Args:
            model_id: HuggingFace model ID
            auto_download: Whether to auto-download model if not found
            max_tokens: Default max tokens for generation
            temperature: Default temperature
            gpu_memory_utilization: GPU memory fraction to use
        """
        self.model_id = model_id
        self.auto_download = auto_download
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.gpu_memory_utilization = gpu_memory_utilization

        self._service: Any = None
        self._initialized = False

    @classmethod
    def get_instance(
        cls,
        model_id: str = DEFAULT_MODEL,
        **kwargs,
    ) -> EmbeddedLLMClient:
        """Get or create cached client instance."""
        cache_key = model_id
        if cache_key not in cls._instances:
            cls._instances[cache_key] = cls(model_id=model_id, **kwargs)
        return cls._instances[cache_key]

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all cached instances and free GPU memory."""
        for instance in cls._instances.values():
            instance.teardown()
        cls._instances.clear()

    def setup(self) -> None:
        """Initialize the VLLMService and load model."""
        if self._initialized:
            return

        if not check_vllm_available():
            raise RuntimeError(
                "vLLM is not available. Install with: pip install vllm, "
                "and ensure GPU is available."
            )

        from sage.common.components.sage_llm import VLLMService

        config = {
            "model_id": self.model_id,
            "auto_download": self.auto_download,
            "sampling": {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
            "engine": {
                "gpu_memory_utilization": self.gpu_memory_utilization,
                "max_model_len": 4096,
            },
        }

        logger.info(f"Loading embedded LLM: {self.model_id}")
        self._service = VLLMService(config)
        self._service.setup()
        self._initialized = True
        logger.info(f"Embedded LLM ready: {self.model_id}")

    def teardown(self) -> None:
        """Release resources."""
        if self._service is not None:
            try:
                self._service.cleanup()
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")
            self._service = None
            self._initialized = False

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Returns:
            Generated text response
        """
        if not self._initialized:
            self.setup()

        # Convert messages to prompt
        prompt = self._format_messages(messages)

        # Generate
        results = self._service.generate(
            prompt,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
        )

        if results and results[0].get("generations"):
            return results[0]["generations"][0]["text"]
        return ""

    def _format_messages(self, messages: list[dict[str, str]]) -> str:
        """Format messages into a prompt string."""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"System: {content}\n")
            elif role == "user":
                parts.append(f"User: {content}\n")
            elif role == "assistant":
                parts.append(f"Assistant: {content}\n")
        parts.append("Assistant:")
        return "".join(parts)

    @property
    def is_available(self) -> bool:
        """Check if this client can be used."""
        return check_vllm_available()


def get_embedded_llm_client(model_id: str = EmbeddedLLMClient.DEFAULT_MODEL) -> EmbeddedLLMClient:
    """
    Get a cached embedded LLM client.

    This is the recommended way to get an embedded LLM for benchmarks.
    The client is lazily initialized on first use.

    Args:
        model_id: HuggingFace model ID

    Returns:
        EmbeddedLLMClient instance
    """
    return EmbeddedLLMClient.get_instance(model_id=model_id)


def cleanup_embedded_llm() -> None:
    """Clean up all embedded LLM instances and free GPU memory."""
    EmbeddedLLMClient.clear_instances()
