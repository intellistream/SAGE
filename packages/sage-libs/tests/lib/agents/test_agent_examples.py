"""
Tests for the refactored agent.py in examples/agents/

This covers the new functionality added in commit 12aec700c63407e1f5d79455b2d64a60a6688e96:
- iter_queries function
- main function workflow
- Integration with ArxivSearchTool
- Configuration loading and validation
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

# Try to import the agent module from examples
try:
    from examples.agents import agent

    AGENT_MODULE_AVAILABLE = True
except ImportError:
    AGENT_MODULE_AVAILABLE = False
    pytestmark = pytest.mark.skip("Agent examples module not available")


@pytest.mark.unit
class TestIterQueries:
    """Test the iter_queries function."""

    def test_iter_queries_local_source(self):
        """Test iter_queries with local JSONL file source."""
        if not AGENT_MODULE_AVAILABLE:
            pytest.skip("Agent examples module not available")

        # Create a temporary JSONL file
        test_data = [
            {"query": "Test query 1", "other": "data"},
            {"query": "Test query 2"},
            {"query": "", "other": "empty query"},  # Should be skipped
            {"not_query": "no query field"},  # Should be skipped
            {"query": "   ", "other": "whitespace"},  # Should be skipped
            {"query": "Valid query 3"},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for item in test_data:
                f.write(json.dumps(item) + "\n")
            temp_path = f.name

        try:
            source_cfg = {
                "type": "local",
                "data_path": temp_path,
                "field_query": "query",
            }

            queries = list(agent.iter_queries(source_cfg))

            # Should only get non-empty queries
            expected_queries = ["Test query 1", "Test query 2", "Valid query 3"]
            assert queries == expected_queries

        finally:
            os.unlink(temp_path)

    def test_iter_queries_local_source_custom_field(self):
        """Test iter_queries with custom query field name."""
        if not AGENT_MODULE_AVAILABLE:
            pytest.skip("Agent examples module not available")

        test_data = [
            {"question": "What is AI?", "other": "data"},
            {"question": "How does ML work?"},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for item in test_data:
                f.write(json.dumps(item) + "\n")
            temp_path = f.name

        try:
            source_cfg = {
                "type": "local",
                "data_path": temp_path,
                "field_query": "question",
            }

            queries = list(agent.iter_queries(source_cfg))
            expected_queries = ["What is AI?", "How does ML work?"]
            assert queries == expected_queries

        finally:
            os.unlink(temp_path)

    def test_iter_queries_empty_file(self):
        """Test iter_queries with empty file."""
        if not AGENT_MODULE_AVAILABLE:
            pytest.skip("Agent examples module not available")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            temp_path = f.name

        try:
            source_cfg = {
                "type": "local",
                "data_path": temp_path,
                "field_query": "query",
            }

            queries = list(agent.iter_queries(source_cfg))
            assert queries == []

        finally:
            os.unlink(temp_path)

    def test_iter_queries_hf_source(self):
        """Test iter_queries with HuggingFace dataset source."""
        if not AGENT_MODULE_AVAILABLE:
            pytest.skip("Agent examples module not available")

        # Mock the datasets library at the module level
        with patch("datasets.load_dataset") as mock_load_dataset:
            mock_dataset = [
                {"query": "HF query 1", "other": "data"},
                {"query": "HF query 2"},
            ]
            mock_load_dataset.return_value = mock_dataset

            source_cfg = {
                "type": "hf",
                "hf_dataset_name": "test/dataset",
                "hf_dataset_config": "default",
                "hf_split": "test",
                "field_query": "query",
            }

            queries = list(agent.iter_queries(source_cfg))

            expected_queries = ["HF query 1", "HF query 2"]
            assert queries == expected_queries

            # Verify load_dataset was called with correct parameters
            mock_load_dataset.assert_called_once_with(
                "test/dataset", "default", split="test"
            )

    def test_iter_queries_unsupported_source_type(self):
        """Test iter_queries with unsupported source type."""
        if not AGENT_MODULE_AVAILABLE:
            pytest.skip("Agent examples module not available")

        source_cfg = {"type": "unsupported", "data_path": "/fake/path"}

        with pytest.raises(ValueError, match="Unsupported source.type"):
            list(agent.iter_queries(source_cfg))


@pytest.mark.unit
class TestMainFunction:
    """Test the main function workflow."""

    def create_mock_config(self):
        """Create a mock configuration for testing."""
        return {
            "profile": {
                "name": "TestAgent",
                "role": "assistant",
                "language": "en",
                "goals": ["Help users"],
                "constraints": ["Be helpful"],
                "persona": {"style": "friendly"},
            },
            "generator": {
                "remote": {
                    "api_key": "test-key",
                    "method": "openai",
                    "model_name": "gpt-3.5-turbo",
                    "base_url": "https://api.openai.com/v1",
                    "seed": 42,
                }
            },
            "planner": {"max_steps": 5, "enable_repair": True, "topk_tools": 3},
            "tools": [
                {
                    "module": "examples.agents.tools.arxiv_search_tool",
                    "class": "ArxivSearchTool",
                    "init_kwargs": {},
                }
            ],
            "runtime": {"max_steps": 5, "summarizer": "reuse_generator"},
            "source": {
                "type": "local",
                "data_path": "/fake/path.jsonl",
                "field_query": "query",
            },
        }

    def test_main_function_config_not_found(self):
        if not AGENT_MODULE_AVAILABLE:
            pytest.skip("Agent examples module not available")

        expected = "❌ Configuration file not found: " + os.path.join(
            os.path.dirname(agent.__file__), "..", "config", "config_agent_min.yaml"
        )

        # 关键：补丁打在“使用处”，并且用 pytest.raises 捕获 SystemExit
        with patch("examples.agents.agent.os.path.exists", return_value=False), patch(
            "builtins.print"
        ) as mock_print:
            with pytest.raises(SystemExit) as e:
                agent.main()

        assert e.value.code == 1
        # 用 assert_any_call，避免“最后一次打印不是这句”导致失败
        mock_print.assert_any_call(expected)

    # @patch("examples.agents.agent.importlib.import_module")
    # @patch("examples.agents.agent.load_config")
    # @patch("os.path.exists")
    # def test_main_function_successful_execution(
    #     self, mock_exists, mock_load_config, mock_import, mock_iter_queries
    # ):
    #     """Test successful execution of main function."""
    #     if not AGENT_MODULE_AVAILABLE:
    #         pytest.skip("Agent examples module not available")

    #     # Setup mocks
    #     mock_exists.return_value = True
    #     mock_load_config.return_value = self.create_mock_config()
    #     mock_iter_queries.return_value = ["Test query 1", "Test query 2"]

    #     # Mock tool import
    #     mock_tool_class = Mock()
    #     mock_tool_instance = Mock()
    #     mock_tool_class.return_value = mock_tool_instance
    #     mock_module = Mock()
    #     mock_module.ArxivSearchTool = mock_tool_class
    #     mock_import.return_value = mock_module

    #     # Mock all the agent components
    #     with patch("examples.agents.agent.BaseProfile") as mock_profile:
    #         with patch("examples.agents.agent.OpenAIGenerator") as mock_generator:
    #             with patch("examples.agents.agent.LLMPlanner") as mock_planner:
    #                 with patch("examples.agents.agent.MCPRegistry") as mock_registry:
    #                     with patch(
    #                         "examples.agents.agent.AgentRuntime"
    #                     ) as mock_runtime:

    #                         # Setup mock instances
    #                         mock_profile_instance = Mock()
    #                         mock_profile.from_dict.return_value = mock_profile_instance

    #                         mock_generator_instance = Mock()
    #                         mock_generator.return_value = mock_generator_instance

    #                         mock_planner_instance = Mock()
    #                         mock_planner.return_value = mock_planner_instance

    #                         mock_registry_instance = Mock()
    #                         mock_registry.return_value = mock_registry_instance

    #                         mock_runtime_instance = Mock()
    #                         mock_runtime_instance.execute.return_value = "Test response"
    #                         mock_runtime.return_value = mock_runtime_instance

    #                         # Mock print to capture output
    #                         with patch("builtins.print") as mock_print:
    #                             agent.main()

    #                             # Verify components were created correctly
    #                             mock_profile.from_dict.assert_called_once()
    #                             mock_generator.assert_called_once()
    #                             mock_planner.assert_called_once()
    #                             mock_registry.assert_called_once()
    #                             mock_runtime.assert_called_once()

    #                             # Verify tool was registered
    #                             mock_registry_instance.register.assert_called_once_with(
    #                                 mock_tool_instance
    #                             )

    #                             # Verify agent was executed for each query
    #                             assert mock_runtime_instance.execute.call_count == 2

    #                             # Verify output was printed
    #                             print_calls = [
    #                                 call[0][0] for call in mock_print.call_args_list
    #                             ]
    #                             assert any(
    #                                 "🧑‍💻 User: Test query 1" in call
    #                                 for call in print_calls
    #                             )
    #                             assert any(
    #                                 "🧑‍💻 User: Test query 2" in call
    #                                 for call in print_calls
    #                             )
    #                             assert any("🤖 Agent:" in call for call in print_calls)

    @patch("examples.agents.agent.load_config")
    @patch("examples.agents.agent.os.path.exists")
    def test_main_function_tool_import_error(self, mock_exists, mock_load):
        mock_exists.return_value = True
        config = self.create_mock_config()
        config["tools"] = [
            {"module": "nonexistent.module", "class": "NonexistentClass"}
        ]
        mock_load.return_value = config

        # 直接运行 main，应该抛 ImportError
        with pytest.raises(ImportError):
            agent.main()


@pytest.mark.integration
class TestAgentIntegration:
    """Integration tests for the agent workflow."""

    def test_test_mode_execution(self):
        """Test that test mode works correctly."""
        if not AGENT_MODULE_AVAILABLE:
            pytest.skip("Agent examples module not available")

        with patch.dict("os.environ", {"SAGE_EXAMPLES_MODE": "test"}):
            with patch("examples.agents.agent.main") as mock_main:
                with patch("builtins.print") as mock_print:
                    with patch("sys.exit") as mock_exit:

                        # Import and execute the module as if it were run directly
                        exec(
                            """
if __name__ == "__main__":
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        try:
            main()
            print("\\n✅ Test passed: Agent pipeline structure validated")
        except Exception as e:
            print(f"❌ Test failed: {e}")
            sys.exit(1)
    else:
        main()
""",
                            {
                                "__name__": "__main__",
                                "os": os,
                                "main": agent.main,
                                "print": print,
                                "sys": __import__("sys"),
                            },
                        )

                        # Verify main was called
                        mock_main.assert_called_once()

    def test_agent_with_arxiv_tool_mock(self):
        """Test complete agent workflow with mocked ArxivSearchTool."""
        if not AGENT_MODULE_AVAILABLE:
            pytest.skip("Agent examples module not available")

        # This test verifies the complete integration works with proper mocking
        with patch("examples.agents.agent.load_config") as mock_load_config:
            with patch("examples.agents.agent.iter_queries") as mock_iter_queries:
                with patch("os.path.exists", return_value=True):

                    # Setup test config
                    test_config = {
                        "profile": {
                            "name": "TestAgent",
                            "role": "assistant",
                            "language": "en",
                            "goals": ["Help users"],
                            "constraints": ["Be helpful"],
                            "persona": {"style": "friendly"},
                        },
                        "generator": {
                            "remote": {
                                "api_key": "test-key",
                                "method": "openai",
                                "model_name": "gpt-3.5-turbo",
                                "base_url": "https://api.openai.com/v1",
                                "seed": 42,
                            }
                        },
                        "planner": {
                            "max_steps": 3,
                            "enable_repair": True,
                            "topk_tools": 2,
                        },
                        "tools": [
                            {
                                "module": "examples.agents.tools.arxiv_search_tool",
                                "class": "ArxivSearchTool",
                                "init_kwargs": {},
                            }
                        ],
                        "runtime": {"max_steps": 3, "summarizer": "reuse_generator"},
                        "source": {
                            "type": "local",
                            "data_path": "/fake/path.jsonl",
                            "field_query": "query",
                        },
                    }

                    mock_load_config.return_value = test_config
                    mock_iter_queries.return_value = ["Search for ML papers"]

                    # Mock all components to avoid external dependencies
                    with patch("examples.agents.agent.BaseProfile") as mock_profile:
                        with patch(
                            "examples.agents.agent.OpenAIGenerator"
                        ) as mock_generator:
                            with patch(
                                "examples.agents.agent.LLMPlanner"
                            ) as mock_planner:
                                with patch(
                                    "examples.agents.agent.MCPRegistry"
                                ) as mock_registry:
                                    with patch(
                                        "examples.agents.agent.AgentRuntime"
                                    ) as mock_runtime:
                                        with patch(
                                            "examples.agents.agent.importlib.import_module"
                                        ) as mock_import:

                                            # Setup mock tool
                                            mock_tool_class = Mock()
                                            mock_tool_instance = Mock()
                                            mock_tool_class.return_value = (
                                                mock_tool_instance
                                            )
                                            mock_module = Mock()
                                            mock_module.ArxivSearchTool = (
                                                mock_tool_class
                                            )
                                            mock_import.return_value = mock_module

                                            # Setup mock runtime response
                                            mock_runtime_instance = Mock()
                                            mock_runtime_instance.execute.return_value = (
                                                "Found 2 relevant papers about ML"
                                            )
                                            mock_runtime.return_value = (
                                                mock_runtime_instance
                                            )

                                            with patch("builtins.print"):
                                                # Should execute without errors
                                                agent.main()

                                                # Verify the tool was registered
                                                mock_registry.return_value.register.assert_called_once()

                                                # Verify agent execution was called
                                                mock_runtime_instance.execute.assert_called_once()
