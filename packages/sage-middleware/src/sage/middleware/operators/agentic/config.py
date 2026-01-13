"""Agent Runtime Operator Configuration.

Provides dataclass-based configuration for AgentRuntimeOperator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class GeneratorConfig:
    """Generator configuration for agent LLM calls.

    Attributes:
        engine_type: Engine type to use:
            - "sagellm" (default): SageLLMGenerator with configurable backend
            - "openai": OpenAIGenerator for OpenAI-compatible APIs
            - "hf": HFGenerator for HuggingFace models
        backend_type: Backend type for sagellm engine:
            - "auto" (default): Automatically select best available backend
            - "mock": Mock backend for testing without GPU
            - "cuda": NVIDIA CUDA backend
            - "ascend": Huawei Ascend NPU backend
        model_path: Model path or HuggingFace model ID (sagellm only)
        device_map: Device mapping strategy (auto/cuda:0/cpu)
        dtype: Data type (auto/float16/bfloat16)
        max_tokens: Maximum generation tokens
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        top_k: Top-k sampling parameter
        timeout: Request timeout in seconds
        default_options: Default generation options
        model_name: Model name for OpenAI (openai only)
        base_url: API base URL (openai only)
        api_key: API key (openai only)
    """

    engine_type: Literal["sagellm", "openai", "hf"] = "sagellm"

    # SageLLM options
    backend_type: str = "auto"
    model_path: str = ""
    device_map: str = "auto"
    dtype: str = "auto"
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 50
    timeout: float = 120.0
    default_options: dict[str, Any] = field(default_factory=dict)

    # OpenAI options
    model_name: str = ""
    base_url: str = ""
    api_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for operator initialization."""
        return {
            "engine_type": self.engine_type,
            "backend_type": self.backend_type,
            "model_path": self.model_path,
            "device_map": self.device_map,
            "dtype": self.dtype,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "timeout": self.timeout,
            "default_options": self.default_options,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "api_key": self.api_key,
        }


@dataclass
class ProfileConfig:
    """Agent profile configuration.

    Attributes:
        name: Agent name
        description: Agent description
        role: Agent role (assistant/user/system)
        system_prompt: System prompt for the agent
    """

    name: str = "DefaultAgent"
    description: str = "A general-purpose AI assistant"
    role: str = "assistant"
    system_prompt: str = "You are a helpful assistant."

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for operator initialization."""
        return {
            "name": self.name,
            "description": self.description,
            "role": self.role,
            "system_prompt": self.system_prompt,
        }


@dataclass
class RuntimeSettings:
    """Runtime settings for agent execution.

    Attributes:
        max_steps: Maximum execution steps
        summarizer: Summarizer config (null/"reuse_generator"/dict)
    """

    max_steps: int = 6
    summarizer: str | dict[str, Any] | None = "reuse_generator"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for operator initialization."""
        return {
            "max_steps": self.max_steps,
            "summarizer": self.summarizer,
        }


@dataclass
class AgentRuntimeConfig:
    """Complete configuration for AgentRuntimeOperator.

    Example:
        ```python
        # Create config with mock backend for testing
        config = AgentRuntimeConfig(
            generator=GeneratorConfig(
                engine_type="sagellm",
                backend_type="mock",
            ),
            profile=ProfileConfig(name="TestBot"),
        )
        operator = AgentRuntimeOperator(config=config.to_dict())

        # Create config with OpenAI
        config = AgentRuntimeConfig(
            generator=GeneratorConfig(
                engine_type="openai",
                model_name="gpt-4o-mini",
                api_key="sk-xxx",  # pragma: allowlist secret
            ),
        )
        ```

    Attributes:
        generator: Generator configuration
        profile: Agent profile configuration
        planner: Planner configuration (optional)
        tools: List of tool specifications
        runtime: Runtime settings
    """

    generator: GeneratorConfig = field(default_factory=GeneratorConfig)
    profile: ProfileConfig = field(default_factory=ProfileConfig)
    planner: dict[str, Any] = field(default_factory=dict)
    tools: list[dict[str, Any]] = field(default_factory=list)
    runtime: RuntimeSettings = field(default_factory=RuntimeSettings)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for operator initialization."""
        return {
            "generator": self.generator.to_dict(),
            "profile": self.profile.to_dict(),
            "planner": self.planner,
            "tools": self.tools,
            "runtime": self.runtime.to_dict(),
        }

    @classmethod
    def for_mock_testing(cls, profile_name: str = "TestBot") -> AgentRuntimeConfig:
        """Create a configuration for mock testing.

        Args:
            profile_name: Name for the test agent profile

        Returns:
            AgentRuntimeConfig configured for mock backend
        """
        return cls(
            generator=GeneratorConfig(
                engine_type="sagellm",
                backend_type="mock",
            ),
            profile=ProfileConfig(name=profile_name),
        )

    @classmethod
    def for_openai(
        cls,
        model_name: str = "gpt-4o-mini",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        profile_name: str = "OpenAIAgent",
    ) -> AgentRuntimeConfig:
        """Create a configuration for OpenAI.

        Args:
            model_name: OpenAI model name
            api_key: OpenAI API key
            base_url: API base URL
            profile_name: Name for the agent profile

        Returns:
            AgentRuntimeConfig configured for OpenAI
        """
        return cls(
            generator=GeneratorConfig(
                engine_type="openai",
                model_name=model_name,
                api_key=api_key,
                base_url=base_url,
            ),
            profile=ProfileConfig(name=profile_name),
        )

    @classmethod
    def for_sagellm(
        cls,
        model_path: str,
        backend_type: str = "auto",
        profile_name: str = "SageLLMAgent",
    ) -> AgentRuntimeConfig:
        """Create a configuration for SageLLM.

        Args:
            model_path: Model path or HuggingFace model ID
            backend_type: Backend type (auto/mock/cuda/ascend)
            profile_name: Name for the agent profile

        Returns:
            AgentRuntimeConfig configured for SageLLM
        """
        return cls(
            generator=GeneratorConfig(
                engine_type="sagellm",
                backend_type=backend_type,
                model_path=model_path,
            ),
            profile=ProfileConfig(name=profile_name),
        )


__all__ = [
    "AgentRuntimeConfig",
    "GeneratorConfig",
    "ProfileConfig",
    "RuntimeSettings",
]
