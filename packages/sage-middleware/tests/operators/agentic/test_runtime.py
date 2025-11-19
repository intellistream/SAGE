"""
测试 sage.middleware.operators.agentic 模块
"""

import pytest

from sage.middleware.operators.agentic.runtime import (
    AgentRuntimeOperator,
    _build_profile,
    _build_tools,
)


@pytest.mark.unit
class TestAgentRuntimeOperatorHelpers:
    """测试AgentRuntimeOperator辅助函数"""

    def test_build_profile_from_dict(self):
        """测试从字典构建Profile"""
        config = {
            "name": "TestAgent",
            "description": "A test agent",
            "role": "assistant",
        }
        profile = _build_profile(config)
        assert profile is not None
        assert profile.name == "TestAgent"
        assert profile.role == "assistant"

    def test_build_profile_from_none(self):
        """测试从None构建默认Profile"""
        profile = _build_profile(None)
        assert profile is not None
        # Should create a default profile

    def test_build_tools_from_empty_list(self):
        """测试从空列表构建工具注册表"""
        registry = _build_tools([])
        assert registry is not None
        # Should create an empty registry

    def test_build_tools_from_none(self):
        """测试从None构建工具注册表"""
        registry = _build_tools(None)
        assert registry is not None


@pytest.mark.unit
class TestAgentRuntimeOperatorInit:
    """测试AgentRuntimeOperator初始化"""

    def test_agent_runtime_operator_config_none(self):
        """测试config为None时的行为"""
        with pytest.raises(ValueError, match="generator config"):
            # 应该因为缺少generator配置而失败
            AgentRuntimeOperator(config=None)

    def test_agent_runtime_operator_missing_generator(self):
        """测试缺少generator配置"""
        config = {
            "profile": {"name": "TestBot"},
            "tools": [],
        }
        with pytest.raises(ValueError, match="generator config"):
            AgentRuntimeOperator(config=config)

    def test_build_profile_creates_default(self):
        """测试构建默认profile"""
        from sage.libs.agentic.agents.profile.profile import BaseProfile

        profile = _build_profile(None)
        assert isinstance(profile, BaseProfile)

    def test_build_tools_creates_registry(self):
        """测试构建工具注册表"""
        from sage.libs.agentic.agents.action.mcp_registry import MCPRegistry

        registry = _build_tools([])
        assert isinstance(registry, MCPRegistry)


@pytest.mark.integration
class TestAgentRuntimeOperatorIntegration:
    """测试AgentRuntimeOperator集成（需要外部依赖）"""

    @pytest.mark.external
    def test_agent_runtime_operator_execute(self):
        """测试operator的execute方法（需要真实配置）"""
        pytest.skip("Requires real API keys and configuration")
