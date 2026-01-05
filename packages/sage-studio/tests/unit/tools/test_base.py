"""
Tests for Studio Tools Base Classes

Layer: L6 (sage-studio)
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pydantic import BaseModel, Field

from sage.studio.tools import (
    BaseTool,
    ToolRegistry,
    get_tool_registry,
    reset_tool_registry,
)

# =============================================================================
# Test Fixtures and Helper Classes
# =============================================================================


class EchoInput(BaseModel):
    """Echo 工具的输入 Schema"""

    message: str = Field(..., description="要回显的消息")
    repeat: int = Field(1, description="重复次数", ge=1, le=10)


class EchoTool(BaseTool):
    """测试用 Echo 工具"""

    name = "echo"
    description = "回显输入消息"
    args_schema = EchoInput

    async def _run(self, message: str, repeat: int = 1) -> str:
        return message * repeat


class NoSchemaTool(BaseTool):
    """无参数 Schema 的工具"""

    name = "no_schema"
    description = "无参数工具"

    async def _run(self, **kwargs: Any) -> str:
        return "ok"


class ErrorTool(BaseTool):
    """总是抛出异常的工具"""

    name = "error"
    description = "总是失败的工具"

    async def _run(self, **kwargs: Any) -> Any:
        raise ValueError("Intentional error for testing")


class SlowTool(BaseTool):
    """执行很慢的工具"""

    name = "slow"
    description = "执行很慢的工具"
    timeout = 0.1  # 100ms 超时

    async def _run(self, **kwargs: Any) -> str:
        await asyncio.sleep(1.0)  # 超过超时时间
        return "done"


@pytest.fixture
def echo_tool() -> EchoTool:
    return EchoTool()


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry()


@pytest.fixture(autouse=True)
def reset_global_registry():
    """每个测试前重置全局注册表"""
    reset_tool_registry()
    yield
    reset_tool_registry()


# =============================================================================
# BaseTool Tests
# =============================================================================


class TestBaseTool:
    """BaseTool 基类测试"""

    @pytest.mark.asyncio
    async def test_run_success(self, echo_tool: EchoTool):
        """测试正常执行"""
        result = await echo_tool.run(message="hello", repeat=2)

        assert result["status"] == "success"
        assert result["result"] == "hellohello"

    @pytest.mark.asyncio
    async def test_run_with_validation(self, echo_tool: EchoTool):
        """测试参数验证成功"""
        result = await echo_tool.run(message="test", repeat=3)

        assert result["status"] == "success"
        assert result["result"] == "testtesttest"

    @pytest.mark.asyncio
    async def test_run_validation_error(self, echo_tool: EchoTool):
        """测试参数验证失败"""
        # repeat 必须 >= 1
        result = await echo_tool.run(message="test", repeat=0)

        assert result["status"] == "error"
        assert "参数验证失败" in result["error"]

    @pytest.mark.asyncio
    async def test_run_validation_error_missing_required(self, echo_tool: EchoTool):
        """测试缺少必需参数"""
        result = await echo_tool.run()  # 缺少 message

        assert result["status"] == "error"
        assert "参数验证失败" in result["error"]

    @pytest.mark.asyncio
    async def test_run_validation_error_wrong_type(self, echo_tool: EchoTool):
        """测试参数类型错误"""
        result = await echo_tool.run(message=123, repeat="not_int")

        assert result["status"] == "error"
        assert "参数验证失败" in result["error"]

    @pytest.mark.asyncio
    async def test_run_execution_error(self):
        """测试执行时异常"""
        tool = ErrorTool()
        result = await tool.run()

        assert result["status"] == "error"
        assert "Intentional error" in result["error"]

    @pytest.mark.asyncio
    async def test_run_timeout(self):
        """测试执行超时"""
        tool = SlowTool()
        result = await tool.run()

        assert result["status"] == "error"
        assert "超时" in result["error"]

    @pytest.mark.asyncio
    async def test_run_no_schema(self):
        """测试无参数 Schema 的工具"""
        tool = NoSchemaTool()
        result = await tool.run(any_param="value")

        assert result["status"] == "success"
        assert result["result"] == "ok"

    def test_run_sync(self, echo_tool: EchoTool):
        """测试同步执行"""
        result = echo_tool.run_sync(message="sync", repeat=1)

        assert result["status"] == "success"
        assert result["result"] == "sync"

    def test_get_schema_with_args(self, echo_tool: EchoTool):
        """测试获取带参数的 Schema"""
        schema = echo_tool.get_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "echo"
        assert schema["function"]["description"] == "回显输入消息"
        assert "parameters" in schema["function"]

        params = schema["function"]["parameters"]
        assert params["type"] == "object"
        assert "message" in params["properties"]
        assert "repeat" in params["properties"]
        assert "message" in params["required"]

    def test_get_schema_without_args(self):
        """测试获取无参数的 Schema"""
        tool = NoSchemaTool()
        schema = tool.get_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "no_schema"
        assert schema["function"]["parameters"]["properties"] == {}
        assert schema["function"]["parameters"]["required"] == []

    def test_str_repr(self, echo_tool: EchoTool):
        """测试字符串表示"""
        assert str(echo_tool) == "Tool(echo)"
        assert "echo" in repr(echo_tool)
        assert "回显输入消息" in repr(echo_tool)


# =============================================================================
# ToolRegistry Tests
# =============================================================================


class TestToolRegistry:
    """ToolRegistry 测试"""

    def test_register_tool(self, registry: ToolRegistry, echo_tool: EchoTool):
        """测试注册工具"""
        registry.register(echo_tool)

        assert "echo" in registry
        assert len(registry) == 1

    def test_register_invalid_type(self, registry: ToolRegistry):
        """测试注册无效类型"""
        with pytest.raises(TypeError, match="Expected BaseTool"):
            registry.register("not a tool")  # type: ignore

    def test_get_tool(self, registry: ToolRegistry, echo_tool: EchoTool):
        """测试获取工具"""
        registry.register(echo_tool)

        tool = registry.get("echo")
        assert tool is echo_tool

    def test_get_nonexistent_tool(self, registry: ToolRegistry):
        """测试获取不存在的工具"""
        tool = registry.get("nonexistent")
        assert tool is None

    def test_unregister_tool(self, registry: ToolRegistry, echo_tool: EchoTool):
        """测试取消注册"""
        registry.register(echo_tool)
        assert "echo" in registry

        result = registry.unregister("echo")
        assert result is True
        assert "echo" not in registry

    def test_unregister_nonexistent(self, registry: ToolRegistry):
        """测试取消注册不存在的工具"""
        result = registry.unregister("nonexistent")
        assert result is False

    def test_list_tools(self, registry: ToolRegistry):
        """测试列出工具"""
        registry.register(EchoTool())
        registry.register(NoSchemaTool())

        tools = registry.list_tools()
        assert len(tools) == 2

    def test_list_names(self, registry: ToolRegistry):
        """测试列出工具名称"""
        registry.register(EchoTool())
        registry.register(NoSchemaTool())

        names = registry.list_names()
        assert set(names) == {"echo", "no_schema"}

    def test_list_schemas(self, registry: ToolRegistry):
        """测试列出所有 Schema"""
        registry.register(EchoTool())
        registry.register(NoSchemaTool())

        schemas = registry.list_schemas()
        assert len(schemas) == 2

        names = {s["function"]["name"] for s in schemas}
        assert names == {"echo", "no_schema"}

    def test_clear(self, registry: ToolRegistry, echo_tool: EchoTool):
        """测试清空注册表"""
        registry.register(echo_tool)
        assert len(registry) == 1

        registry.clear()
        assert len(registry) == 0

    def test_iteration(self, registry: ToolRegistry):
        """测试迭代注册表"""
        registry.register(EchoTool())
        registry.register(NoSchemaTool())

        tools = list(registry)
        assert len(tools) == 2


# =============================================================================
# Global Registry Tests
# =============================================================================


class TestGlobalRegistry:
    """全局注册表测试"""

    def test_get_tool_registry_singleton(self):
        """测试全局注册表是单例"""
        reg1 = get_tool_registry()
        reg2 = get_tool_registry()

        assert reg1 is reg2

    def test_global_registry_operations(self):
        """测试全局注册表操作"""
        registry = get_tool_registry()
        registry.register(EchoTool())

        assert "echo" in get_tool_registry()

    def test_reset_global_registry(self):
        """测试重置全局注册表"""
        registry = get_tool_registry()
        registry.register(EchoTool())
        assert len(registry) == 1

        reset_tool_registry()

        new_registry = get_tool_registry()
        assert len(new_registry) == 0
        # 重置后应该是新实例
        assert new_registry is not registry
