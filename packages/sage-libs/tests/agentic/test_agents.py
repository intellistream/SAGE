"""
Tests for agentic/agents module

Tests cover:
- Tool: Basic tool functionality
- BochaSearch: Mock search API
- BaseAgent: Agent initialization and basic behavior
"""

from unittest.mock import Mock, patch

import pytest


@pytest.mark.unit
class TestTool:
    """Test Tool class"""

    def test_init(self):
        """测试工具初始化"""
        from sage.libs.agentic.agents.agent import Tool

        def mock_func(x):
            return x * 2

        tool = Tool(name="test_tool", func=mock_func, description="A test tool")

        assert tool.name == "test_tool"
        assert tool.func == mock_func
        assert tool.description == "A test tool"

    def test_run(self):
        """测试工具执行"""
        from sage.libs.agentic.agents.agent import Tool

        def mock_func(x, y):
            return x + y

        tool = Tool(name="add", func=mock_func, description="Add two numbers")

        result = tool.run(3, 5)
        assert result == 8


@pytest.mark.unit
class TestBochaSearch:
    """Test BochaSearch class"""

    def test_init(self):
        """测试搜索初始化"""
        from sage.libs.agentic.agents.agent import BochaSearch

        search = BochaSearch(api_key="test_key")  # pragma: allowlist secret

        assert search.api_key == "test_key"  # pragma: allowlist secret
        assert search.url == "https://api.bochaai.com/v1/web-search"
        assert search.headers["Authorization"] == "test_key"  # pragma: allowlist secret

    @patch("sage.libs.agentic.agents.agent.requests.request")
    def test_run(self, mock_request):
        """测试搜索执行"""
        from sage.libs.agentic.agents.agent import BochaSearch

        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"results": ["result1", "result2"]}
        mock_request.return_value = mock_response

        search = BochaSearch(api_key="test_key")  # pragma: allowlist secret
        result = search.run("test query")

        assert result == {"results": ["result1", "result2"]}
        mock_request.assert_called_once()


@pytest.mark.unit
class TestBaseAgent:
    """Test BaseAgent class"""

    def test_init_with_config(self):
        """测试使用配置初始化Agent"""
        from sage.libs.agentic.agents.agent import BaseAgent

        config = {
            "search_api_key": "test_key",  # pragma: allowlist secret
            "max_steps": 5,
        }
        mock_model = Mock()  # Must provide model parameter

        agent = BaseAgent(config=config, model=mock_model)

        assert agent.config == config
        assert len(agent.tools) > 0  # Should have at least Search tool (dict)
        assert agent.model == mock_model
        assert agent.max_steps == 5

    def test_init_with_model(self):
        """测试使用模型初始化Agent"""
        from sage.libs.agentic.agents.agent import BaseAgent

        config = {"search_api_key": "test_key"}  # pragma: allowlist secret
        mock_model = Mock()

        agent = BaseAgent(config=config, model=mock_model)

        assert agent.config == config

    def test_tools_registration(self):
        """测试工具注册"""
        from sage.libs.agentic.agents.agent import BaseAgent

        config = {"search_api_key": "test_key"}  # pragma: allowlist secret
        mock_model = Mock()
        agent = BaseAgent(config=config, model=mock_model)

        # tools is a dict, check keys
        assert isinstance(agent.tools, dict)
        assert "Search" in agent.tools
        assert agent.tool_names == "Search"

    def test_agent_has_required_attributes(self):
        """测试Agent必需属性"""
        from sage.libs.agentic.agents.agent import BaseAgent

        config = {"search_api_key": "test_key"}  # pragma: allowlist secret
        mock_model = Mock()
        agent = BaseAgent(config=config, model=mock_model)

        assert hasattr(agent, "tools")
        assert hasattr(agent, "config")
        assert hasattr(agent, "logger")

    def test_init_without_model_raises_error(self):
        """测试没有提供model会报错"""
        from sage.libs.agentic.agents.agent import BaseAgent

        config = {"search_api_key": "test_key"}  # pragma: allowlist secret

        with pytest.raises(ValueError, match="Model parameter must be provided"):
            BaseAgent(config=config)
