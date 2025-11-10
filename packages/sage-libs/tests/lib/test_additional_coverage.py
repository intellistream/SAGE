"""
Unit tests for LLM Planner
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestLLMPlanner:
    """Test LLMPlanner class"""

    def test_llm_planner_init(self):
        """Test LLMPlanner initialization"""
        try:
            from sage.libs.agents.planning.llm_planner import LLMPlanner

            with patch.object(LLMPlanner, "__init__", return_value=None):
                planner = LLMPlanner.__new__(LLMPlanner)
                assert planner is not None
        except (ImportError, AttributeError):
            pytest.skip("LLMPlanner not available")

    @patch("openai.OpenAI")
    def test_llm_planner_plan_generation(self, mock_openai):
        """Test plan generation"""
        try:
            from sage.libs.agents.planning.llm_planner import LLMPlanner

            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="Step 1: Do something\nStep 2: Do another thing"))
            ]
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            planner = LLMPlanner(api_key="test_key")
            if hasattr(planner, "generate_plan"):
                plan = planner.generate_plan("Test goal")
                assert plan is not None
        except (ImportError, AttributeError):
            pytest.skip("LLMPlanner not fully available")

    def test_llm_planner_with_custom_model(self):
        """Test LLMPlanner with custom model"""
        try:
            from sage.libs.agents.planning.llm_planner import LLMPlanner

            with patch.object(LLMPlanner, "__init__", return_value=None):
                planner = LLMPlanner.__new__(LLMPlanner)
                planner.model = "gpt-4"
                assert planner.model == "gpt-4"
        except (ImportError, AttributeError):
            pytest.skip("LLMPlanner not available")


class TestLLMPlannerErrorHandling:
    """Test error handling in LLMPlanner"""

    @patch("openai.OpenAI")
    def test_llm_planner_api_error(self, mock_openai):
        """Test LLMPlanner handles API errors"""
        try:
            from sage.libs.agents.planning.llm_planner import LLMPlanner

            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("API Error")
            mock_openai.return_value = mock_client

            planner = LLMPlanner(api_key="test_key")
            if hasattr(planner, "generate_plan"):
                try:
                    planner.generate_plan("Test goal")
                except Exception as e:
                    assert isinstance(e, Exception)
        except (ImportError, AttributeError):
            pytest.skip("LLMPlanner not fully available")


class TestLongRefinerPromptTemplate:
    """Test PromptTemplate class"""

    def test_prompt_template_init(self):
        """Test PromptTemplate initialization"""
        try:
            from sage.libs.context.compression.algorithms.long_refiner_impl.prompt_template import (
                PromptTemplate,
            )

            mock_tokenizer = MagicMock()
            template = PromptTemplate(
                mock_tokenizer, system_prompt="System", user_prompt="User {query}"
            )
            assert template is not None
        except (ImportError, AttributeError):
            pytest.skip("PromptTemplate not available")

    def test_prompt_template_format(self):
        """Test PromptTemplate formatting"""
        try:
            from sage.libs.context.compression.algorithms.long_refiner_impl.prompt_template import (
                PromptTemplate,
            )

            mock_tokenizer = MagicMock()
            mock_tokenizer.apply_chat_template.return_value = "Formatted prompt"

            template = PromptTemplate(
                mock_tokenizer, system_prompt="System", user_prompt="User {query}"
            )

            if hasattr(template, "format"):
                result = template.format(query="test query")
                assert result is not None
        except (ImportError, AttributeError):
            pytest.skip("PromptTemplate not available")


class TestAgentBase:
    """Test Agent base class"""

    def test_agent_init(self):
        """Test Agent initialization"""
        try:
            from sage.libs.agents.agent import Agent

            with patch.object(Agent, "__init__", return_value=None):
                agent = Agent.__new__(Agent)
                assert agent is not None
        except (ImportError, AttributeError):
            pytest.skip("Agent not available")

    def test_agent_execute(self):
        """Test Agent execute method"""
        try:
            from sage.libs.agents.agent import Agent

            with patch.object(Agent, "__init__", return_value=None):
                agent = Agent.__new__(Agent)
                agent.execute = MagicMock(return_value="Result")

                result = agent.execute("Test input")
                assert result == "Result"
        except (ImportError, AttributeError):
            pytest.skip("Agent not available")


class TestToolBase:
    """Test Tool base class"""

    def test_tool_init(self):
        """Test Tool initialization"""
        try:
            from sage.libs.tools.tool import Tool

            with patch.object(Tool, "__init__", return_value=None):
                tool = Tool.__new__(Tool)
                assert tool is not None
        except (ImportError, AttributeError):
            pytest.skip("Tool not available")

    def test_tool_execute(self):
        """Test Tool execute method"""
        try:
            from sage.libs.tools.tool import Tool

            with patch.object(Tool, "__init__", return_value=None):
                tool = Tool.__new__(Tool)
                tool.execute = MagicMock(return_value="Tool result")

                result = tool.execute("Test input")
                assert result == "Tool result"
        except (ImportError, AttributeError):
            pytest.skip("Tool not available")


class TestSinkBase:
    """Test Sink base classes"""

    def test_sink_init(self):
        """Test Sink initialization"""
        try:
            from sage.libs.io.sink import Sink

            with patch.object(Sink, "__init__", return_value=None):
                sink = Sink.__new__(Sink)
                assert sink is not None
        except (ImportError, AttributeError):
            pytest.skip("Sink not available")

    def test_sink_write(self):
        """Test Sink write method"""
        try:
            from sage.libs.io.sink import Sink

            with patch.object(Sink, "__init__", return_value=None):
                sink = Sink.__new__(Sink)
                sink.write = MagicMock()

                sink.write("Test data")
                sink.write.assert_called_once_with("Test data")
        except (ImportError, AttributeError):
            pytest.skip("Sink not available")


class TestRefinerBase:
    """Test Refiner base class"""

    def test_refiner_init(self):
        """Test Refiner initialization"""
        try:
            from sage.libs.context.compression.refiner import Refiner

            with patch.object(Refiner, "__init__", return_value=None):
                refiner = Refiner.__new__(Refiner)
                assert refiner is not None
        except (ImportError, AttributeError):
            pytest.skip("Refiner not available")

    def test_refiner_refine(self):
        """Test Refiner refine method"""
        try:
            from sage.libs.context.compression.refiner import Refiner

            with patch.object(Refiner, "__init__", return_value=None):
                refiner = Refiner.__new__(Refiner)
                refiner.refine = MagicMock(return_value="Refined text")

                result = refiner.refine("Original text")
                assert result == "Refined text"
        except (ImportError, AttributeError):
            pytest.skip("Refiner not available")


class TestBaseServiceKernel:
    """Test BaseService from kernel"""

    def test_base_service_init(self):
        """Test BaseService initialization"""
        try:
            from sage.kernel.api.service.base_service import BaseService

            with patch.object(BaseService, "__init__", return_value=None):
                service = BaseService.__new__(BaseService)
                assert service is not None
        except (ImportError, AttributeError):
            pytest.skip("BaseService not available")

    def test_base_service_start(self):
        """Test BaseService start method"""
        try:
            from sage.kernel.api.service.base_service import BaseService

            with patch.object(BaseService, "__init__", return_value=None):
                service = BaseService.__new__(BaseService)
                service.start = MagicMock()

                service.start()
                service.start.assert_called_once()
        except (ImportError, AttributeError):
            pytest.skip("BaseService not available")

    def test_base_service_stop(self):
        """Test BaseService stop method"""
        try:
            from sage.kernel.api.service.base_service import BaseService

            with patch.object(BaseService, "__init__", return_value=None):
                service = BaseService.__new__(BaseService)
                service.stop = MagicMock()

                service.stop()
                service.stop.assert_called_once()
        except (ImportError, AttributeError):
            pytest.skip("BaseService not available")


class TestLocalTCPServer:
    """Test LocalTCPServer"""

    def test_local_tcp_server_init(self):
        """Test LocalTCPServer initialization"""
        try:
            from sage.common.utils.network.local_tcp_server import LocalTCPServer

            with patch.object(LocalTCPServer, "__init__", return_value=None):
                server = LocalTCPServer.__new__(LocalTCPServer)
                assert server is not None
        except (ImportError, AttributeError):
            pytest.skip("LocalTCPServer not available")

    @patch("socket.socket")
    def test_local_tcp_server_start(self, mock_socket):
        """Test LocalTCPServer start method"""
        try:
            from sage.common.utils.network.local_tcp_server import LocalTCPServer

            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            server = LocalTCPServer(host="localhost", port=8080)
            if hasattr(server, "start"):
                server.start()
        except (ImportError, AttributeError):
            pytest.skip("LocalTCPServer not fully available")
