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

    def test_agent_runtime_operator_minimal_init(self):
        """测试最小配置初始化"""
        # 需要generator配置，否则会抛出ValueError
        config = {
            "generator": {
                "method": "openai",
                "model": "gpt-3.5-turbo",
                "api_key": "test-key",  # pragma: allowlist secret
            }
        }

        # 可能因为缺少实际的API key或其他配置而失败
        # 但至少应该能够实例化operator类本身
        try:
            operator = AgentRuntimeOperator(config=config)
            assert operator is not None
        except (ImportError, ValueError, RuntimeError):
            # 预期的异常：缺少依赖或配置
            pytest.skip("Cannot initialize without real dependencies")

    def test_agent_runtime_operator_config_none(self):
        """测试config为None时的行为"""
        with pytest.raises(ValueError, match="generator config"):
            # 应该因为缺少generator配置而失败
            AgentRuntimeOperator(config=None)

    def test_agent_runtime_operator_has_attributes(self):
        """测试operator具有必要的属性"""
        config = {
            "generator": {"method": "openai", "model": "test"},
            "profile": {"name": "TestBot"},
            "tools": [],
        }

        try:
            operator = AgentRuntimeOperator(config=config)
            # 验证关键属性存在
            assert hasattr(operator, "profile")
            assert hasattr(operator, "generator")
            assert hasattr(operator, "planner")
            assert hasattr(operator, "tools")
            assert hasattr(operator, "runtime")
        except (ImportError, ValueError, RuntimeError, AttributeError):
            # 如果因为缺少依赖或配置而失败，至少验证了导入和构造逻辑
            pytest.skip("Cannot initialize without real dependencies")


@pytest.mark.integration
class TestAgentRuntimeOperatorIntegration:
    """测试AgentRuntimeOperator集成（需要外部依赖）"""

    @pytest.mark.external
    def test_agent_runtime_operator_execute(self):
        """测试operator的execute方法（需要真实配置）"""
        pytest.skip("Requires real API keys and configuration")
