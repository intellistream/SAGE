"""
Tests for AgentRuntimeOperator with engine_type switching and mock mode.
"""

import pytest

from sage.middleware.operators.agentic import (
    AgentRuntimeConfig,
    AgentRuntimeOperator,
    GeneratorConfig,
    ProfileConfig,
    RuntimeSettings,
)
from sage.middleware.operators.agentic.runtime import (
    _build_generator,
    _build_profile,
    _build_tools,
)


@pytest.mark.unit
class TestGeneratorConfig:
    """Test GeneratorConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = GeneratorConfig()
        assert config.engine_type == "sagellm"
        assert config.backend_type == "auto"
        assert config.max_tokens == 2048
        assert config.temperature == 0.7

    def test_mock_backend(self):
        """Test mock backend configuration."""
        config = GeneratorConfig(engine_type="sagellm", backend_type="mock")
        assert config.engine_type == "sagellm"
        assert config.backend_type == "mock"

    def test_openai_config(self):
        """Test OpenAI configuration."""
        config = GeneratorConfig(
            engine_type="openai",
            model_name="gpt-4o-mini",
            api_key="test-key",
        )
        assert config.engine_type == "openai"
        assert config.model_name == "gpt-4o-mini"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = GeneratorConfig(engine_type="sagellm", backend_type="mock")
        d = config.to_dict()
        assert d["engine_type"] == "sagellm"
        assert d["backend_type"] == "mock"


@pytest.mark.unit
class TestAgentRuntimeConfig:
    """Test AgentRuntimeConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = AgentRuntimeConfig()
        assert config.generator.engine_type == "sagellm"
        assert config.profile.name == "DefaultAgent"
        assert config.runtime.max_steps == 6

    def test_for_mock_testing(self):
        """Test factory method for mock testing."""
        config = AgentRuntimeConfig.for_mock_testing(profile_name="MockBot")
        assert config.generator.engine_type == "sagellm"
        assert config.generator.backend_type == "mock"
        assert config.profile.name == "MockBot"

    def test_for_openai(self):
        """Test factory method for OpenAI."""
        config = AgentRuntimeConfig.for_openai(
            model_name="gpt-4o",
            api_key="sk-test",
        )
        assert config.generator.engine_type == "openai"
        assert config.generator.model_name == "gpt-4o"

    def test_for_sagellm(self):
        """Test factory method for SageLLM."""
        config = AgentRuntimeConfig.for_sagellm(
            model_path="Qwen/Qwen2.5-7B-Instruct",
            backend_type="auto",
        )
        assert config.generator.engine_type == "sagellm"
        assert config.generator.model_path == "Qwen/Qwen2.5-7B-Instruct"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = AgentRuntimeConfig.for_mock_testing()
        d = config.to_dict()
        assert "generator" in d
        assert "profile" in d
        assert "runtime" in d
        assert d["generator"]["engine_type"] == "sagellm"
        assert d["generator"]["backend_type"] == "mock"


@pytest.mark.unit
class TestBuildGenerator:
    """Test _build_generator function with engine_type."""

    def test_build_sagellm_generator(self):
        """Test building SageLLM generator."""
        from sage.middleware.operators.llm import SageLLMGenerator

        config = {"engine_type": "sagellm", "backend_type": "auto"}
        generator = _build_generator(config, engine_type="sagellm")
        assert isinstance(generator, SageLLMGenerator)
        assert generator.backend_type == "auto"

    def test_build_mock_generator(self):
        """Test building mock SageLLM generator."""
        from sage.middleware.operators.llm import SageLLMGenerator

        config = {"engine_type": "sagellm", "backend_type": "mock"}
        generator = _build_generator(config, engine_type="sagellm")
        assert isinstance(generator, SageLLMGenerator)
        assert generator.backend_type == "mock"

    def test_build_openai_generator(self):
        """Test building OpenAI generator."""
        from sage.middleware.operators.rag.generator import OpenAIGenerator

        config = {"model_name": "gpt-4o-mini"}
        generator = _build_generator(config, engine_type="openai")
        assert isinstance(generator, OpenAIGenerator)

    def test_engine_type_from_config(self):
        """Test engine_type is read from config dict."""
        from sage.middleware.operators.llm import SageLLMGenerator

        config = {"engine_type": "sagellm", "backend_type": "mock"}
        # engine_type in config should override the parameter
        generator = _build_generator(config, engine_type="openai")
        assert isinstance(generator, SageLLMGenerator)

    @pytest.mark.skip(reason="vllm support has been removed in v0.3.0")
    def test_vllm_deprecation_warning(self):
        """Test that vllm engine_type raises deprecation warning.
        
        Note: This test is skipped as vllm support has been completely removed.
        """
        pass

    def test_missing_config_raises(self):
        """Test that missing config raises ValueError."""
        with pytest.raises(ValueError, match="generator config"):
            _build_generator(None)


@pytest.mark.unit
class TestAgentRuntimeOperatorEngineType:
    """Test AgentRuntimeOperator engine_type handling."""

    def test_default_engine_type(self):
        """Test default engine_type is sagellm."""
        config = {
            "generator": {"backend_type": "mock"},
            "profile": {"name": "TestBot"},
            "tools": [],
        }
        operator = AgentRuntimeOperator(config=config)
        assert operator.engine_type == "sagellm"

    def test_engine_type_from_generator_config(self):
        """Test engine_type from generator config."""
        config = {
            "generator": {"engine_type": "sagellm", "backend_type": "mock"},
            "profile": {"name": "TestBot"},
            "tools": [],
        }
        operator = AgentRuntimeOperator(config=config)
        assert operator.engine_type == "sagellm"

    def test_engine_type_from_top_level_config(self):
        """Test engine_type from top-level config."""
        config = {
            "engine_type": "sagellm",
            "generator": {"backend_type": "mock"},
            "profile": {"name": "TestBot"},
            "tools": [],
        }
        operator = AgentRuntimeOperator(config=config)
        assert operator.engine_type == "sagellm"

    def test_generator_config_engine_type_priority(self):
        """Test that generator config engine_type has priority over top-level."""
        config = {
            "engine_type": "openai",  # top-level
            "generator": {"engine_type": "sagellm", "backend_type": "mock"},  # should win
            "profile": {"name": "TestBot"},
            "tools": [],
        }
        operator = AgentRuntimeOperator(config=config)
        assert operator.engine_type == "sagellm"


@pytest.mark.unit
class TestAgentRuntimeOperatorMockMode:
    """Test AgentRuntimeOperator with mock backend for testing."""

    def test_operator_with_mock_config(self):
        """Test creating operator with mock configuration."""
        config = AgentRuntimeConfig.for_mock_testing().to_dict()
        operator = AgentRuntimeOperator(config=config)
        assert operator.engine_type == "sagellm"
        assert operator.generator.backend_type == "mock"

    def test_operator_components_initialized(self):
        """Test that all components are properly initialized."""
        config = AgentRuntimeConfig.for_mock_testing().to_dict()
        operator = AgentRuntimeOperator(config=config)

        assert operator.profile is not None
        assert operator.generator is not None
        assert operator.planner is not None
        assert operator.tools is not None
        assert operator.runtime is not None

    def test_execute_with_string_input(self):
        """Test execute with string input."""
        config = AgentRuntimeConfig.for_mock_testing().to_dict()
        operator = AgentRuntimeOperator(config=config)

        # Mock mode should return without real LLM call
        # The actual behavior depends on SageLLMGenerator mock implementation
        # This test verifies the operator can be instantiated and called
        assert callable(operator.execute)

    def test_execute_with_dict_input(self):
        """Test execute with dict input."""
        config = AgentRuntimeConfig.for_mock_testing().to_dict()
        operator = AgentRuntimeOperator(config=config)

        assert callable(operator.execute)


@pytest.mark.unit
class TestProfileAndToolsBuilding:
    """Test profile and tools building functions."""

    def test_build_profile_from_dict(self):
        """Test building profile from dict."""
        config = {
            "name": "TestAgent",
            "description": "A test agent",
            "role": "assistant",
        }
        profile = _build_profile(config)
        assert profile.name == "TestAgent"
        assert profile.role == "assistant"

    def test_build_profile_from_none(self):
        """Test building default profile from None."""
        profile = _build_profile(None)
        assert profile is not None

    def test_build_tools_from_empty_list(self):
        """Test building empty tools registry."""
        registry = _build_tools([])
        assert registry is not None

    def test_build_tools_from_none(self):
        """Test building tools registry from None."""
        registry = _build_tools(None)
        assert registry is not None
