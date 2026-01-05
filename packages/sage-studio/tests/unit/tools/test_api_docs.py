"""
Tests for APIDocsTool

Layer: L6 (sage-studio)
"""

from __future__ import annotations

import pytest

from sage.studio.tools.api_docs import APIDocsInput, APIDocsTool

# =============================================================================
# APIDocsInput Tests
# =============================================================================


class TestAPIDocsInput:
    """APIDocsInput 参数模型测试"""

    def test_valid_input(self):
        """测试有效输入"""
        input_model = APIDocsInput(symbol="sage.studio.tools.BaseTool")
        assert input_model.symbol == "sage.studio.tools.BaseTool"
        assert input_model.include_source is False

    def test_valid_input_with_source(self):
        """测试带 include_source 的输入"""
        input_model = APIDocsInput(
            symbol="sage.studio.tools.BaseTool",
            include_source=True,
        )
        assert input_model.include_source is True

    def test_symbol_min_length(self):
        """测试 symbol 最小长度限制"""
        with pytest.raises(ValueError):
            APIDocsInput(symbol="")


# =============================================================================
# APIDocsTool Tests
# =============================================================================


class TestAPIDocsTool:
    """APIDocsTool 测试"""

    @pytest.fixture
    def tool(self) -> APIDocsTool:
        return APIDocsTool()

    def test_tool_attributes(self, tool: APIDocsTool):
        """测试工具属性"""
        assert tool.name == "api_docs_lookup"
        assert "API" in tool.description or "文档" in tool.description
        assert tool.args_schema is APIDocsInput

    @pytest.mark.asyncio
    async def test_lookup_module(self, tool: APIDocsTool):
        """测试查询模块"""
        result = await tool.run(symbol="sage.studio.tools")

        assert result["status"] == "success"
        data = result["result"]
        assert data["type"] == "module"
        assert data["symbol"] == "sage.studio.tools"
        assert "members" in data

    @pytest.mark.asyncio
    async def test_lookup_class(self, tool: APIDocsTool):
        """测试查询类"""
        result = await tool.run(symbol="sage.studio.tools.BaseTool")

        assert result["status"] == "success"
        data = result["result"]
        assert data["type"] == "class"
        assert data["symbol"] == "sage.studio.tools.BaseTool"
        assert "docstring" in data
        assert "methods" in data
        assert "signature" in data

    @pytest.mark.asyncio
    async def test_lookup_function(self, tool: APIDocsTool):
        """测试查询函数"""
        result = await tool.run(symbol="sage.studio.tools.get_all_tools")

        assert result["status"] == "success"
        data = result["result"]
        assert data["type"] == "function"
        assert "signature" in data
        assert "parameters" in data
        assert "docstring" in data

    @pytest.mark.asyncio
    async def test_lookup_with_source(self, tool: APIDocsTool):
        """测试包含源代码"""
        result = await tool.run(
            symbol="sage.studio.tools.get_all_tools",
            include_source=True,
        )

        assert result["status"] == "success"
        data = result["result"]
        assert "source" in data
        # 源代码应该包含函数定义
        if data["source"]:
            assert "def get_all_tools" in data["source"]

    @pytest.mark.asyncio
    async def test_lookup_class_method(self, tool: APIDocsTool):
        """测试查询类方法"""
        result = await tool.run(symbol="sage.studio.tools.BaseTool.run")

        assert result["status"] == "success"
        data = result["result"]
        assert data["type"] in ("function", "method")
        assert "signature" in data

    @pytest.mark.asyncio
    async def test_lookup_nonexistent_symbol(self, tool: APIDocsTool):
        """测试查询不存在的符号"""
        result = await tool.run(symbol="sage.studio.tools.NonExistentClass")

        assert result["status"] == "error"
        assert "has no attribute" in result["error"] or "Cannot import" in result["error"]

    @pytest.mark.asyncio
    async def test_lookup_nonexistent_module(self, tool: APIDocsTool):
        """测试查询不存在的模块"""
        result = await tool.run(symbol="sage.nonexistent.module")

        assert result["status"] == "error"
        # 可能是 "Cannot import" 或 "has no attribute" 取决于路径解析
        assert "Cannot import" in result["error"] or "has no attribute" in result["error"]

    @pytest.mark.asyncio
    async def test_security_restriction(self, tool: APIDocsTool):
        """测试安全限制 - 只允许 SAGE 相关符号"""
        # 尝试查询非 SAGE 模块
        result = await tool.run(symbol="os.path.join")

        assert result["status"] == "error"
        assert "Only SAGE-related symbols" in result["error"]

    @pytest.mark.asyncio
    async def test_security_allows_sage_prefix(self, tool: APIDocsTool):
        """测试安全限制 - 允许 sage. 前缀"""
        result = await tool.run(symbol="sage.studio.tools.BaseTool")
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_lookup_constant(self, tool: APIDocsTool):
        """测试查询常量/属性"""
        result = await tool.run(symbol="sage.studio.tools.BaseTool.name")

        assert result["status"] == "success"
        # name 是类变量，应该能获取到信息

    def test_get_schema(self, tool: APIDocsTool):
        """测试 OpenAI schema 生成"""
        schema = tool.get_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "api_docs_lookup"
        assert "parameters" in schema["function"]

        params = schema["function"]["parameters"]
        assert "symbol" in params["properties"]
        assert "include_source" in params["properties"]
        assert "symbol" in params["required"]

    @pytest.mark.asyncio
    async def test_validation_error(self, tool: APIDocsTool):
        """测试参数验证错误"""
        result = await tool.run()  # 缺少必需参数

        assert result["status"] == "error"
        assert "参数验证失败" in result["error"]

    @pytest.mark.asyncio
    async def test_class_docs_contains_bases(self, tool: APIDocsTool):
        """测试类文档包含基类信息"""
        result = await tool.run(symbol="sage.studio.tools.KnowledgeSearchTool")

        assert result["status"] == "success"
        data = result["result"]
        assert data["type"] == "class"
        assert "bases" in data
        assert "BaseTool" in data["bases"]

    @pytest.mark.asyncio
    async def test_function_docs_contains_parameters(self, tool: APIDocsTool):
        """测试函数文档包含参数信息"""
        result = await tool.run(symbol="sage.studio.tools.get_all_tools")

        assert result["status"] == "success"
        data = result["result"]
        assert "parameters" in data
        # 应该有 knowledge_manager 参数
        param_names = [p["name"] for p in data["parameters"]]
        assert "knowledge_manager" in param_names
