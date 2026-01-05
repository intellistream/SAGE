"""
Tests for KnowledgeSearchTool

Layer: L6 (sage-studio)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sage.studio.tools.knowledge_search import KnowledgeSearchInput, KnowledgeSearchTool

# =============================================================================
# Mock Classes
# =============================================================================


class MockSearchResult:
    """模拟搜索结果"""

    def __init__(
        self,
        content: str,
        source: str,
        score: float,
        file_path: str = "",
        chunk_id: str = "",
        metadata: dict[str, Any] | None = None,
    ):
        self.content = content
        self.source = source
        self.score = score
        self.file_path = file_path
        self.chunk_id = chunk_id
        self.metadata = metadata or {}


class MockKnowledgeManager:
    """模拟 KnowledgeManager"""

    def __init__(self, search_results: list[MockSearchResult] | None = None):
        self._search_results = search_results or []
        self.search = AsyncMock(return_value=self._search_results)
        self.list_sources = MagicMock(
            return_value=[
                {"name": "sage_docs", "enabled": True, "loaded": True},
                {"name": "examples", "enabled": True, "loaded": False},
                {"name": "user_uploads", "enabled": True, "loaded": False},
            ]
        )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_km() -> MockKnowledgeManager:
    """创建模拟的 KnowledgeManager"""
    return MockKnowledgeManager(
        search_results=[
            MockSearchResult(
                content="Pipeline is a core component in SAGE...",
                source="sage_docs",
                score=0.95,
                file_path="docs/pipeline.md",
                chunk_id="chunk_001",
                metadata={"section": "Introduction"},
            ),
            MockSearchResult(
                content="Example of creating a Pipeline...",
                source="examples",
                score=0.85,
                file_path="examples/basic_pipeline.py",
                chunk_id="chunk_002",
            ),
        ]
    )


@pytest.fixture
def tool(mock_km: MockKnowledgeManager) -> KnowledgeSearchTool:
    """创建 KnowledgeSearchTool 实例"""
    return KnowledgeSearchTool(mock_km)  # type: ignore


# =============================================================================
# KnowledgeSearchInput Tests
# =============================================================================


class TestKnowledgeSearchInput:
    """KnowledgeSearchInput 参数模型测试"""

    def test_valid_input(self):
        """测试有效输入"""
        input_model = KnowledgeSearchInput(query="pipeline")
        assert input_model.query == "pipeline"
        assert input_model.sources is None
        assert input_model.top_k == 5
        assert input_model.score_threshold == 0.5

    def test_valid_input_with_all_params(self):
        """测试带所有参数的输入"""
        input_model = KnowledgeSearchInput(
            query="how to use Pipeline",
            sources=["sage_docs", "examples"],
            top_k=10,
            score_threshold=0.7,
        )
        assert input_model.query == "how to use Pipeline"
        assert input_model.sources == ["sage_docs", "examples"]
        assert input_model.top_k == 10
        assert input_model.score_threshold == 0.7

    def test_query_min_length(self):
        """测试 query 最小长度限制"""
        with pytest.raises(ValueError):
            KnowledgeSearchInput(query="")

    def test_top_k_range(self):
        """测试 top_k 范围限制"""
        # 有效范围
        assert KnowledgeSearchInput(query="test", top_k=1).top_k == 1
        assert KnowledgeSearchInput(query="test", top_k=20).top_k == 20

        # 超出范围
        with pytest.raises(ValueError):
            KnowledgeSearchInput(query="test", top_k=0)
        with pytest.raises(ValueError):
            KnowledgeSearchInput(query="test", top_k=21)

    def test_score_threshold_range(self):
        """测试 score_threshold 范围限制"""
        # 有效范围
        assert KnowledgeSearchInput(query="test", score_threshold=0.0).score_threshold == 0.0
        assert KnowledgeSearchInput(query="test", score_threshold=1.0).score_threshold == 1.0

        # 超出范围
        with pytest.raises(ValueError):
            KnowledgeSearchInput(query="test", score_threshold=-0.1)
        with pytest.raises(ValueError):
            KnowledgeSearchInput(query="test", score_threshold=1.1)


# =============================================================================
# KnowledgeSearchTool Tests
# =============================================================================


class TestKnowledgeSearchTool:
    """KnowledgeSearchTool 测试"""

    def test_tool_attributes(self, tool: KnowledgeSearchTool):
        """测试工具属性"""
        assert tool.name == "knowledge_search"
        assert "SAGE" in tool.description or "知识库" in tool.description
        assert tool.args_schema is KnowledgeSearchInput

    def test_knowledge_manager_property(
        self, tool: KnowledgeSearchTool, mock_km: MockKnowledgeManager
    ):
        """测试 knowledge_manager 属性"""
        assert tool.knowledge_manager is mock_km

    @pytest.mark.asyncio
    async def test_run_basic_search(self, tool: KnowledgeSearchTool, mock_km: MockKnowledgeManager):
        """测试基本搜索"""
        result = await tool.run(query="pipeline")

        assert result["status"] == "success"
        assert len(result["result"]) == 2

        # 验证调用参数
        mock_km.search.assert_called_once()
        call_kwargs = mock_km.search.call_args.kwargs
        assert call_kwargs["query"] == "pipeline"
        assert call_kwargs["limit"] == 5

    @pytest.mark.asyncio
    async def test_run_with_sources(self, tool: KnowledgeSearchTool, mock_km: MockKnowledgeManager):
        """测试指定知识源搜索"""
        result = await tool.run(query="pipeline", sources=["sage_docs"])

        assert result["status"] == "success"

        call_kwargs = mock_km.search.call_args.kwargs
        assert call_kwargs["sources"] == ["sage_docs"]

    @pytest.mark.asyncio
    async def test_run_with_custom_params(
        self, tool: KnowledgeSearchTool, mock_km: MockKnowledgeManager
    ):
        """测试自定义参数"""
        result = await tool.run(
            query="pipeline",
            sources=["sage_docs", "examples"],
            top_k=10,
            score_threshold=0.8,
        )

        assert result["status"] == "success"

        call_kwargs = mock_km.search.call_args.kwargs
        assert call_kwargs["limit"] == 10
        assert call_kwargs["score_threshold"] == 0.8

    @pytest.mark.asyncio
    async def test_run_result_format(
        self, tool: KnowledgeSearchTool, mock_km: MockKnowledgeManager
    ):
        """测试结果格式"""
        result = await tool.run(query="pipeline")

        assert result["status"] == "success"
        results = result["result"]

        # 检查第一个结果的格式
        first_result = results[0]
        assert "content" in first_result
        assert "source" in first_result
        assert "score" in first_result
        assert "metadata" in first_result

        assert first_result["source"] == "sage_docs"
        assert first_result["score"] == 0.95
        assert first_result["metadata"]["file_path"] == "docs/pipeline.md"

    @pytest.mark.asyncio
    async def test_run_validation_error(self, tool: KnowledgeSearchTool):
        """测试参数验证错误"""
        # 缺少必需参数
        result = await tool.run()
        assert result["status"] == "error"
        assert "参数验证失败" in result["error"]

    @pytest.mark.asyncio
    async def test_run_empty_results(self, mock_km: MockKnowledgeManager):
        """测试空结果"""
        mock_km._search_results = []
        mock_km.search = AsyncMock(return_value=[])

        tool = KnowledgeSearchTool(mock_km)  # type: ignore
        result = await tool.run(query="nonexistent topic")

        assert result["status"] == "success"
        assert result["result"] == []

    @pytest.mark.asyncio
    async def test_run_search_error(self, mock_km: MockKnowledgeManager):
        """测试搜索错误"""
        mock_km.search = AsyncMock(side_effect=Exception("Search service unavailable"))

        tool = KnowledgeSearchTool(mock_km)  # type: ignore
        result = await tool.run(query="pipeline")

        assert result["status"] == "error"
        assert "Search service unavailable" in result["error"]

    def test_get_schema(self, tool: KnowledgeSearchTool):
        """测试 OpenAI schema 生成"""
        schema = tool.get_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "knowledge_search"
        assert "parameters" in schema["function"]

        params = schema["function"]["parameters"]
        assert "query" in params["properties"]
        assert "sources" in params["properties"]
        assert "top_k" in params["properties"]
        assert "query" in params["required"]

    def test_get_available_sources(self, tool: KnowledgeSearchTool, mock_km: MockKnowledgeManager):
        """测试获取可用知识源"""
        sources = tool.get_available_sources()

        assert len(sources) == 3
        mock_km.list_sources.assert_called_once()

    def test_default_sources(self, tool: KnowledgeSearchTool):
        """测试默认知识源"""
        assert "sage_docs" in tool.DEFAULT_SOURCES
        assert "examples" in tool.DEFAULT_SOURCES
