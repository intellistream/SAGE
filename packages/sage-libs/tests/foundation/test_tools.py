"""
Tests for foundation/tools module

Tests cover:
- Tool base class
- ToolRegistry
"""

import pytest


@pytest.mark.unit
class TestTool:
    """Test Tool base class"""

    def test_import(self):
        """测试能够导入BaseTool"""
        from sage.libs.foundation.tools.tool import BaseTool

        assert BaseTool is not None
        assert hasattr(BaseTool, "__init__")

    def test_tool_structure(self):
        """测试BaseTool类结构"""
        from sage.libs.foundation.tools.tool import BaseTool

        # Check that BaseTool has required attributes
        assert hasattr(BaseTool, "execute")
        assert hasattr(BaseTool, "get_metadata")


@pytest.mark.unit
class TestToolRegistry:
    """Test ToolRegistry"""

    def test_import(self):
        """测试能够导入ToolRegistry"""
        from sage.libs.foundation.tools.registry import ToolRegistry

        assert ToolRegistry is not None

    def test_registry_singleton(self):
        """测试注册表是单例"""
        from sage.libs.foundation.tools.registry import ToolRegistry

        registry1 = ToolRegistry()
        registry2 = ToolRegistry()

        # Should be the same instance
        assert registry1 is registry2

    def test_register_and_get_tool(self):
        """测试注册和获取工具"""
        from sage.libs.foundation.tools.registry import ToolRegistry
        from sage.libs.foundation.tools.tool import BaseTool

        registry = ToolRegistry()

        # Create a simple mock tool that inherits from BaseTool
        class MockTool(BaseTool):
            def __init__(self):
                super().__init__(
                    tool_name="mock_tool",
                    tool_description="A mock tool for testing",
                )

            def execute(self):
                return "executed"

        # Register the tool instance
        tool_instance = MockTool()
        registry.register(tool_instance)

        # Get the tool
        tool = registry.get("mock_tool")
        assert tool is not None
        assert tool.tool_name == "mock_tool"

    def test_get_nonexistent_tool(self):
        """测试获取不存在的工具"""
        from sage.libs.foundation.tools.registry import ToolRegistry

        registry = ToolRegistry()

        tool = registry.get("nonexistent_tool")
        assert tool is None

    def test_list_tools(self):
        """测试列出所有工具"""
        from sage.libs.foundation.tools.registry import ToolRegistry

        registry = ToolRegistry()

        # Clear registry first (if possible)
        # Get list of tools
        tools = registry.list_tools()

        assert isinstance(tools, (list, dict))
