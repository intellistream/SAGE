"""
Tests for the config_agent_min.yaml configuration file structure.

This validates the configuration file added/modified in commit 12aec700c63407e1f5d79455b2d64a60a6688e96.
"""

import os

import pytest
import yaml

from sage.common.utils.config.loader import load_config


@pytest.mark.unit
class TestAgentConfigValidation:
    """Test configuration file structure and content."""

    def setup_method(self):
        """Set up config path."""
        self.config_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "..",
            "examples",
            "tutorials",
            "agents",
            "config",
            "config_agent_min.yaml",
        )

    def test_config_file_exists(self):
        """Test that the config file exists."""
        assert os.path.exists(self.config_path), f"Config file not found: {self.config_path}"

    def test_config_loads_successfully(self):
        """Test that the config file can be loaded without errors."""
        try:
            config = load_config(self.config_path)
            assert config is not None
            assert isinstance(config, dict)
        except Exception as e:
            pytest.fail(f"Config loading failed: {e}")

    def test_config_required_sections(self):
        """Test that all required configuration sections are present."""
        config = load_config(self.config_path)

        required_sections = [
            "pipeline",
            "source",
            "profile",
            "planner",
            "generator",
            "runtime",
            "tools",
            "sink",
        ]

        for section in required_sections:
            assert section in config, f"Required section '{section}' missing from config"

    def test_pipeline_config(self):
        """Test pipeline configuration structure."""
        config = load_config(self.config_path)
        pipeline = config["pipeline"]

        assert "name" in pipeline
        assert "description" in pipeline
        assert "version" in pipeline

        assert pipeline["name"] == "sage-agent-base-pipeline"
        assert "agent pipeline" in pipeline["description"].lower()

    def test_source_config(self):
        """Test source configuration structure."""
        config = load_config(self.config_path)
        source = config["source"]

        assert "type" in source
        assert "data_path" in source
        assert "field_query" in source

        assert source["type"] == "local"
        assert source["field_query"] == "query"
        assert source["data_path"].endswith(".jsonl")

    def test_profile_config(self):
        """Test profile configuration structure."""
        config = load_config(self.config_path)
        profile = config["profile"]

        required_fields = [
            "name",
            "role",
            "language",
            "goals",
            "constraints",
            "persona",
        ]
        for field in required_fields:
            assert field in profile, f"Profile field '{field}' missing"

        assert isinstance(profile["goals"], list)
        assert isinstance(profile["constraints"], list)
        assert isinstance(profile["persona"], dict)
        assert profile["language"] == "zh"

    def test_planner_config(self):
        """Test planner configuration structure."""
        config = load_config(self.config_path)
        planner = config["planner"]

        required_fields = ["llm", "max_steps", "enable_repair", "topk_tools"]
        for field in required_fields:
            assert field in planner, f"Planner field '{field}' missing"

        # Test LLM sub-config
        llm = planner["llm"]
        assert "method" in llm
        assert "model_name" in llm
        assert "base_url" in llm
        assert "api_key" in llm

        assert isinstance(planner["max_steps"], int)
        assert isinstance(planner["enable_repair"], bool)
        assert isinstance(planner["topk_tools"], int)

    def test_generator_configs(self):
        """Test generator configuration structure."""
        config = load_config(self.config_path)
        generator = config["generator"]

        # Should have multiple generator options
        expected_types = ["local", "vllm", "remote"]
        for gen_type in expected_types:
            assert gen_type in generator, f"Generator type '{gen_type}' missing"

            gen_config = generator[gen_type]
            assert "method" in gen_config
            assert "model_name" in gen_config
            assert "seed" in gen_config

    def test_tools_config(self):
        """Test tools configuration structure."""
        config = load_config(self.config_path)
        tools = config["tools"]

        assert isinstance(tools, list)
        assert len(tools) > 0

        # Test ArxivSearchTool config
        arxiv_tool = tools[0]
        assert "module" in arxiv_tool
        assert "class" in arxiv_tool
        assert "init_kwargs" in arxiv_tool

        assert arxiv_tool["module"] == "examples.agents.tools.arxiv_search_tool"
        assert arxiv_tool["class"] == "ArxivSearchTool"
        assert isinstance(arxiv_tool["init_kwargs"], dict)

    def test_runtime_config(self):
        """Test runtime configuration structure."""
        config = load_config(self.config_path)
        runtime = config["runtime"]

        assert "max_steps" in runtime
        assert "summarizer" in runtime

        assert isinstance(runtime["max_steps"], int)
        assert runtime["summarizer"] == "reuse_generator"

    def test_memory_config(self):
        """Test memory configuration structure."""
        config = load_config(self.config_path)
        memory = config.get("memory", {})

        if memory:
            assert "enable" in memory
            # Memory should be disabled based on the commit
            assert memory.get("enable") is False

    def test_sink_config(self):
        """Test sink configuration structure."""
        config = load_config(self.config_path)
        sink = config["sink"]

        required_fields = ["platform", "format", "show_metadata", "save_to_file"]
        for field in required_fields:
            assert field in sink, f"Sink field '{field}' missing"

        assert sink["platform"] == "local"
        assert sink["format"] == "json"
        assert isinstance(sink["show_metadata"], bool)

    def test_config_values_consistency(self):
        """Test that configuration values are consistent and valid."""
        config = load_config(self.config_path)

        # Check that max_steps values are consistent
        planner_max_steps = config["planner"]["max_steps"]
        runtime_max_steps = config["runtime"]["max_steps"]

        # They should be the same or runtime should be <= planner
        assert runtime_max_steps <= planner_max_steps

        # Check that tool topk is reasonable
        topk_tools = config["planner"]["topk_tools"]
        assert 1 <= topk_tools <= 10

        # Check that language settings are consistent
        profile_lang = config["profile"]["language"]
        assert profile_lang in ["zh", "en"]

    def test_yaml_syntax_validity(self):
        """Test that the YAML file has valid syntax."""
        try:
            with open(self.config_path, encoding="utf-8") as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"YAML syntax error: {e}")

    def test_environment_variable_placeholders(self):
        """Test that environment variable placeholders are properly formatted."""
        config = load_config(self.config_path)

        # Check for ${ENV_VAR} patterns in planner LLM config
        planner_api_key = config["planner"]["llm"]["api_key"]
        if isinstance(planner_api_key, str) and planner_api_key.startswith("${"):
            # Should be properly formatted
            assert planner_api_key.endswith("}")
            assert len(planner_api_key) > 3  # More than just ${}

    def test_file_paths_validity(self):
        """Test that file paths in config are valid relative paths."""
        config = load_config(self.config_path)

        # Check source data path
        data_path = config["source"]["data_path"]
        assert not os.path.isabs(data_path), "Data path should be relative"
        assert data_path.startswith("examples/"), "Data path should start with examples/"

        # Check sink save path
        save_path = config["sink"]["save_to_file"]
        assert not os.path.isabs(save_path), "Save path should be relative"


@pytest.mark.integration
class TestConfigWithComponents:
    """Integration tests for config with actual components."""

    def test_config_compatible_with_profile(self):
        """Test that config is compatible with BaseProfile."""
        from sage.libs.agents.profile.profile import BaseProfile

        config_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "..",
            "examples",
            "tutorials",
            "agents",
            "config",
            "config_agent_min.yaml",
        )

        if not os.path.exists(config_path):
            pytest.skip("Config file not found")

        config = load_config(config_path)

        # Should be able to create profile from config
        try:
            profile = BaseProfile.from_dict(config["profile"])
            assert profile is not None
            assert profile.name == config["profile"]["name"]
            assert profile.language == config["profile"]["language"]
        except Exception as e:
            pytest.fail(f"Profile creation failed: {e}")

    def test_config_compatible_with_mcp_registry(self):
        """Test that tools config is compatible with MCPRegistry."""
        from sage.libs.agents.action.mcp_registry import MCPRegistry

        config_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "..",
            "examples",
            "tutorials",
            "agents",
            "config",
            "config_agent_min.yaml",
        )

        if not os.path.exists(config_path):
            pytest.skip("Config file not found")

        config = load_config(config_path)

        # Should be able to create registry (even if tool import fails)
        try:
            registry = MCPRegistry()
            assert registry is not None

            # Tool config should have proper structure
            tools_config = config["tools"]
            for tool_config in tools_config:
                assert "module" in tool_config
                assert "class" in tool_config
                assert "init_kwargs" in tool_config

        except Exception as e:
            pytest.fail(f"Registry creation failed: {e}")
