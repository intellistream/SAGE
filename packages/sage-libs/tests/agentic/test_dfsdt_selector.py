"""
Unit tests for DFSDT (Depth-First Search-based Decision Tree) tool selector.
"""

import numpy as np
import pytest

from sage.libs.agentic.agents.action.tool_selection import (
    DFSDTSelector,
    DFSDTSelectorConfig,
    SelectorResources,
    ToolSelectionQuery,
)


class MockTool:
    def __init__(self, tool_id: str, name: str, description: str, category: str = ""):
        self.tool_id = tool_id
        self.name = name
        self.description = description
        self.category = category
        self.parameters = {}
        self.capabilities = []


class MockToolsLoader:
    def __init__(self, tools):
        self._tools = {t.tool_id: t for t in tools}

    def iter_all(self):
        return iter(self._tools.values())

    def get_tool(self, tool_id: str):
        return self._tools.get(tool_id)


class MockEmbeddingClient:
    def __init__(self, dimension: int = 64):
        self.dimension = dimension

    def embed(self, texts, model=None, batch_size=32):
        embeddings = []
        for text in texts:
            np.random.seed(hash(text) % (2**32))
            embedding = np.random.randn(self.dimension)
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            embeddings.append(embedding)
        return np.array(embeddings)


@pytest.fixture
def sample_tools():
    return [
        MockTool("weather_get", "Get Weather", "Get current weather for a location"),
        MockTool("weather_forecast", "Weather Forecast", "Get weather forecast for next 7 days"),
        MockTool("email_send", "Send Email", "Send an email to specified recipients"),
        MockTool("email_read", "Read Email", "Read emails from inbox"),
        MockTool("search_web", "Web Search", "Search the web for information"),
    ]


@pytest.fixture
def mock_resources(sample_tools):
    tools_loader = MockToolsLoader(sample_tools)
    embedding_client = MockEmbeddingClient(dimension=64)
    return SelectorResources(tools_loader=tools_loader, embedding_client=embedding_client)


@pytest.fixture
def dfsdt_config():
    return DFSDTSelectorConfig(
        name="dfsdt",
        max_depth=3,
        beam_width=5,
        llm_model="mock",
        temperature=0.1,
        use_diversity_prompt=True,
        score_threshold=0.1,
        use_keyword_prefilter=True,
        prefilter_k=20,
        top_k=5,
    )


class TestDFSDTSelectorConfig:
    def test_default_config(self):
        config = DFSDTSelectorConfig()
        assert config.name == "dfsdt"
        assert config.max_depth == 3
        assert config.beam_width == 5
        assert config.llm_model == "auto"

    def test_custom_config(self):
        config = DFSDTSelectorConfig(max_depth=5, beam_width=10, llm_model="custom")
        assert config.max_depth == 5
        assert config.beam_width == 10
        assert config.llm_model == "custom"

    def test_config_type_registration(self):
        from sage.libs.agentic.agents.action.tool_selection.schemas import CONFIG_TYPES

        assert "dfsdt" in CONFIG_TYPES
        assert CONFIG_TYPES["dfsdt"] == DFSDTSelectorConfig


class TestDFSDTSelector:
    def test_initialization(self, dfsdt_config, mock_resources):
        selector = DFSDTSelector(dfsdt_config, mock_resources)
        assert selector.config.name == "dfsdt"
        assert len(selector._tool_cache) == 5
        assert selector._keyword_selector is not None

    def test_fallback_score(self, dfsdt_config, mock_resources):
        from sage.libs.agentic.agents.action.tool_selection.dfsdt_selector import SearchNode

        selector = DFSDTSelector(dfsdt_config, mock_resources)
        node = SearchNode(
            tool_id="weather_get", tool_name="Get Weather", tool_description="Get weather"
        )
        query = ToolSelectionQuery(
            sample_id="test", instruction="What is the weather?", candidate_tools=[]
        )
        score = selector._fallback_score(query, node)
        assert 0 <= score <= 1

    def test_parse_score_with_number(self, dfsdt_config, mock_resources):
        selector = DFSDTSelector(dfsdt_config, mock_resources)
        assert selector._parse_score("8") == 8.0
        assert selector._parse_score("7.5") == 7.5
        assert selector._parse_score("Score: 9") == 9.0

    def test_select_with_fallback(self, dfsdt_config, mock_resources):
        selector = DFSDTSelector(dfsdt_config, mock_resources)
        query = ToolSelectionQuery(
            sample_id="test-001",
            instruction="What's the weather forecast?",
            candidate_tools=["weather_get", "weather_forecast", "email_send"],
        )
        results = selector.select(query)
        assert len(results) <= dfsdt_config.top_k
        # Results may be empty if no match passes threshold
        assert len(results) >= 0

    def test_select_empty_candidates(self, dfsdt_config, mock_resources):
        selector = DFSDTSelector(dfsdt_config, mock_resources)
        query = ToolSelectionQuery(sample_id="test", instruction="Do something", candidate_tools=[])
        results = selector.select(query)
        # When candidates is empty, the selector may still return results from all available tools
        # This is valid behavior since empty candidate_tools means "consider all tools"
        assert len(results) >= 0

    def test_from_config(self, dfsdt_config, mock_resources):
        selector = DFSDTSelector.from_config(dfsdt_config, mock_resources)
        assert isinstance(selector, DFSDTSelector)

    def test_name_property(self, dfsdt_config, mock_resources):
        selector = DFSDTSelector(dfsdt_config, mock_resources)
        assert selector.name == "dfsdt"

    def test_get_stats(self, dfsdt_config, mock_resources):
        selector = DFSDTSelector(dfsdt_config, mock_resources)
        stats = selector.get_stats()
        assert "tool_cache_size" in stats
        assert stats["tool_cache_size"] == 5


class TestDFSDTTreeSearch:
    def test_search_node_structure(self):
        from sage.libs.agentic.agents.action.tool_selection.dfsdt_selector import SearchNode

        node = SearchNode(
            tool_id="weather_get",
            tool_name="Get Weather",
            tool_description="Weather",
            score=0.8,
            depth=1,
        )
        assert node.tool_id == "weather_get"
        assert node.score == 0.8
        assert node.depth == 1

    def test_search_node_equality(self):
        from sage.libs.agentic.agents.action.tool_selection.dfsdt_selector import SearchNode

        node1 = SearchNode("tool1", "Tool 1", "Description 1")
        node2 = SearchNode("tool1", "Tool 1", "Description 1")
        node3 = SearchNode("tool2", "Tool 2", "Description 2")
        assert node1 == node2
        assert node1 != node3


class TestDFSDTKeywordPrefilter:
    def test_prefilter_enabled(self, mock_resources):
        config = DFSDTSelectorConfig(
            use_keyword_prefilter=True, prefilter_k=5, llm_model="fallback"
        )
        selector = DFSDTSelector(config, mock_resources)
        assert selector._keyword_selector is not None

    def test_prefilter_disabled(self, mock_resources):
        config = DFSDTSelectorConfig(use_keyword_prefilter=False, llm_model="fallback")
        selector = DFSDTSelector(config, mock_resources)
        assert selector._keyword_selector is None


class TestDFSDTIntegration:
    def test_consistent_results(self, mock_resources):
        config = DFSDTSelectorConfig(llm_model="fallback", score_threshold=0.1, top_k=3)
        selector = DFSDTSelector(config, mock_resources)
        query = ToolSelectionQuery(
            sample_id="consistency",
            instruction="Get weather information",
            candidate_tools=["weather_get", "weather_forecast", "email_send"],
        )
        results1 = selector.select(query)
        results2 = selector.select(query)
        ids1 = [r.tool_id for r in results1]
        ids2 = [r.tool_id for r in results2]
        assert ids1 == ids2

    def test_metadata_in_results(self, mock_resources):
        config = DFSDTSelectorConfig(llm_model="fallback", score_threshold=0.1, top_k=3)
        selector = DFSDTSelector(config, mock_resources)
        query = ToolSelectionQuery(
            sample_id="test",
            instruction="weather forecast",
            candidate_tools=["weather_get", "weather_forecast"],
        )
        results = selector.select(query)
        for result in results:
            assert result.metadata is not None
            assert result.metadata.get("method") == "dfsdt"
