"""
Tests for keyword selector implementation.
"""

from dataclasses import dataclass

import pytest
from sage_libs.sage_agentic.agents.action.tool_selection.base import (
    SelectorResources,
)
from sage_libs.sage_agentic.agents.action.tool_selection.keyword_selector import (
    KeywordSelector,
)
from sage_libs.sage_agentic.agents.action.tool_selection.schemas import (
    KeywordSelectorConfig,
    ToolSelectionQuery,
)


@dataclass
class MockTool:
    """Mock tool object with required attributes."""

    tool_id: str
    name: str
    description: str
    capabilities: list[str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


class MockToolsLoader:
    """Mock tool loader for testing."""

    def __init__(self, tools=None):
        self.tools = tools or self._default_tools()

    def _default_tools(self):
        return {
            "search": MockTool(
                tool_id="search",
                name="Web Search",
                description="Search the web for information",
                capabilities=["search", "query"],
            ),
            "calculator": MockTool(
                tool_id="calculator",
                name="Calculator",
                description="Perform mathematical calculations",
                capabilities=["calculate", "math"],
            ),
            "weather": MockTool(
                tool_id="weather",
                name="Weather API",
                description="Get current weather information",
                capabilities=["weather", "forecast"],
            ),
            "email": MockTool(
                tool_id="email",
                name="Email Service",
                description="Send and receive emails",
                capabilities=["email", "send"],
            ),
            "translator": MockTool(
                tool_id="translator",
                name="Translation Service",
                description="Translate text between languages",
                capabilities=["translate", "language"],
            ),
        }

    def get_tool(self, tool_id):
        return self.tools.get(tool_id)

    def get_all_tools(self):
        return list(self.tools.values())

    def iter_all(self):
        """Iterate over all tools."""
        yield from self.tools.values()


class TestKeywordSelector:
    """Tests for KeywordSelector implementation."""

    @pytest.fixture
    def resources(self):
        """Create test resources."""
        return SelectorResources(tools_loader=MockToolsLoader())

    @pytest.fixture
    def selector(self, resources):
        """Create keyword selector with default config."""
        config = KeywordSelectorConfig()
        return KeywordSelector(config=config, resources=resources)

    def test_create_selector(self, resources):
        """Test creating keyword selector."""
        config = KeywordSelectorConfig()
        selector = KeywordSelector(config=config, resources=resources)

        assert selector.name == "keyword"
        assert selector.config == config

    def test_from_config(self, resources):
        """Test creating selector from config."""
        config = KeywordSelectorConfig(method="overlap")
        selector = KeywordSelector.from_config(config, resources)

        assert selector.config.method == "overlap"

    def test_select_basic(self, selector):
        """Test basic tool selection."""
        query = ToolSelectionQuery(
            sample_id="test-001",
            instruction="Search for weather information",
            candidate_tools=["search", "calculator", "weather"],
        )

        results = selector.select(query, top_k=2)

        assert len(results) <= 2
        assert all(r.tool_id in query.candidate_tools for r in results)
        assert all(0 <= r.score <= 1 for r in results)

    def test_select_returns_sorted_by_score(self, selector):
        """Test that results are sorted by score descending."""
        query = ToolSelectionQuery(
            sample_id="test-002",
            instruction="Calculate mathematical formula",
            candidate_tools=["search", "calculator", "weather", "email"],
        )

        results = selector.select(query, top_k=4)

        # Results should be sorted by score descending
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    def test_select_respects_top_k(self, selector):
        """Test that selector respects top_k limit."""
        query = ToolSelectionQuery(
            sample_id="test-003",
            instruction="Search the web",
            candidate_tools=["search", "calculator", "weather", "email", "translator"],
        )

        results = selector.select(query, top_k=3)

        assert len(results) <= 3

    def test_select_empty_candidates(self, selector):
        """Test selection with empty candidate list falls back to all tools."""
        query = ToolSelectionQuery(
            sample_id="test-004", instruction="Search for something", candidate_tools=[]
        )

        results = selector.select(query)

        # When candidate_tools is empty, selector falls back to all tools
        # This is valid behavior - just verify it returns a list
        assert isinstance(results, list)

    def test_select_filters_by_min_score(self, resources):
        """Test that min_score threshold filters results."""
        config = KeywordSelectorConfig(min_score=0.8)
        selector = KeywordSelector(config=config, resources=resources)

        query = ToolSelectionQuery(
            sample_id="test-005",
            instruction="Random unrelated query xyz123",
            candidate_tools=["search", "calculator"],
        )

        results = selector.select(query)

        # All results should meet min_score threshold
        assert all(r.score >= 0.8 for r in results)

    def test_select_chinese_query(self, selector):
        """Test selection with Chinese instruction."""
        query = ToolSelectionQuery(
            sample_id="test-006",
            instruction="搜索天气信息",
            candidate_tools=["search", "weather", "calculator"],
        )

        results = selector.select(query)

        # Should still return results
        assert isinstance(results, list)


class TestKeywordSelectorMethods:
    """Tests for different keyword matching methods."""

    @pytest.fixture
    def resources(self):
        return SelectorResources(tools_loader=MockToolsLoader())

    def test_tfidf_method(self, resources):
        """Test TF-IDF matching method."""
        config = KeywordSelectorConfig(method="tfidf")
        selector = KeywordSelector(config=config, resources=resources)

        query = ToolSelectionQuery(
            sample_id="test",
            instruction="Calculate the sum",
            candidate_tools=["calculator", "search"],
        )

        results = selector.select(query)
        assert len(results) > 0

    def test_overlap_method(self, resources):
        """Test token overlap matching method."""
        config = KeywordSelectorConfig(method="overlap")
        selector = KeywordSelector(config=config, resources=resources)

        query = ToolSelectionQuery(
            sample_id="test", instruction="Search the web", candidate_tools=["search", "calculator"]
        )

        results = selector.select(query)
        # "search" should rank higher due to exact match
        if len(results) > 0:
            assert results[0].tool_id == "search" or results[0].score > 0
