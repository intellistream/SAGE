"""
Unit tests for Gorilla-style retrieval-augmented tool selector.

Tests the two-stage approach: embedding retrieval + LLM selection.
"""

import numpy as np
import pytest

from sage.libs.agentic.agents.action.tool_selection import (
    GorillaSelector,
    GorillaSelectorConfig,
    SelectorResources,
    ToolSelectionQuery,
)


class MockTool:
    """Mock tool for testing."""

    def __init__(self, tool_id: str, name: str, description: str, category: str = ""):
        self.tool_id = tool_id
        self.name = name
        self.description = description
        self.category = category
        self.parameters = {}


class MockToolsLoader:
    """Mock tools loader for testing."""

    def __init__(self, tools: list[MockTool]):
        self._tools = {t.tool_id: t for t in tools}

    def iter_all(self):
        return iter(self._tools.values())

    def get_tool(self, tool_id: str) -> MockTool:
        return self._tools.get(tool_id)


class MockEmbeddingClient:
    """Mock embedding client for testing."""

    def __init__(self, dimension: int = 64):
        self.dimension = dimension
        self._call_count = 0

    def embed(self, texts: list[str], model: str = None, batch_size: int = 32) -> np.ndarray:
        """Return deterministic embeddings based on text content."""
        self._call_count += 1
        embeddings = []
        for text in texts:
            # Create deterministic embedding from text
            np.random.seed(hash(text) % (2**32))
            embedding = np.random.randn(self.dimension)
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            embeddings.append(embedding)
        return np.array(embeddings)


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, return_tools: list[str] = None):
        self.return_tools = return_tools or []
        self._call_count = 0
        self._last_messages = None

    def chat(self, messages: list[dict], temperature: float = 0.1, max_tokens: int = 512) -> str:
        """Return mock LLM response."""
        self._call_count += 1
        self._last_messages = messages

        # Return tool IDs as JSON array
        import json

        return json.dumps(self.return_tools)


@pytest.fixture
def sample_tools():
    """Create sample tools for testing."""
    return [
        MockTool("weather_get", "Get Weather", "Get current weather for a location", "weather"),
        MockTool(
            "weather_forecast",
            "Weather Forecast",
            "Get weather forecast for next 7 days",
            "weather",
        ),
        MockTool(
            "email_send", "Send Email", "Send an email to specified recipients", "communication"
        ),
        MockTool("email_read", "Read Email", "Read emails from inbox", "communication"),
        MockTool(
            "calendar_add", "Add Calendar Event", "Add a new event to calendar", "productivity"
        ),
        MockTool(
            "calendar_list", "List Calendar Events", "List upcoming calendar events", "productivity"
        ),
        MockTool("search_web", "Web Search", "Search the web for information", "search"),
        MockTool(
            "translate_text",
            "Translate Text",
            "Translate text between languages",
            "language",
        ),
    ]


@pytest.fixture
def mock_resources(sample_tools):
    """Create mock resources."""
    tools_loader = MockToolsLoader(sample_tools)
    embedding_client = MockEmbeddingClient(dimension=64)
    return SelectorResources(
        tools_loader=tools_loader,
        embedding_client=embedding_client,
    )


@pytest.fixture
def gorilla_config():
    """Create Gorilla selector config."""
    return GorillaSelectorConfig(
        name="gorilla",
        top_k_retrieve=5,
        top_k_select=3,
        embedding_model="default",
        llm_model="mock",
        similarity_metric="cosine",
        temperature=0.1,
        use_detailed_docs=True,
        max_context_tools=10,
    )


class TestGorillaSelectorConfig:
    """Test Gorilla selector configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GorillaSelectorConfig()
        assert config.name == "gorilla"
        assert config.top_k_retrieve == 20
        assert config.top_k_select == 5
        assert config.similarity_metric == "cosine"
        assert config.temperature == 0.1

    def test_custom_config(self):
        """Test custom configuration."""
        config = GorillaSelectorConfig(
            top_k_retrieve=30,
            top_k_select=10,
            llm_model="custom-model",
        )
        assert config.top_k_retrieve == 30
        assert config.top_k_select == 10
        assert config.llm_model == "custom-model"


class TestGorillaSelector:
    """Test Gorilla selector functionality."""

    def test_initialization(self, gorilla_config, mock_resources):
        """Test selector initialization."""
        mock_llm = MockLLMClient(return_tools=["weather_get", "weather_forecast"])
        selector = GorillaSelector(gorilla_config, mock_resources, llm_client=mock_llm)

        assert selector.config.name == "gorilla"
        assert len(selector._tool_ids) == 8
        assert selector._tool_embeddings is not None
        assert selector._tool_embeddings.shape[0] == 8

    def test_initialization_requires_embedding_client(self, gorilla_config):
        """Test that initialization fails without embedding client."""
        tools_loader = MockToolsLoader([MockTool("t1", "Tool 1", "Description 1")])
        resources = SelectorResources(tools_loader=tools_loader, embedding_client=None)

        with pytest.raises(ValueError, match="embedding_client"):
            GorillaSelector(gorilla_config, resources)

    def test_retrieve_candidates(self, gorilla_config, mock_resources):
        """Test candidate retrieval using embeddings."""
        mock_llm = MockLLMClient(return_tools=["weather_get"])
        selector = GorillaSelector(gorilla_config, mock_resources, llm_client=mock_llm)

        # Retrieve candidates
        candidates = selector._retrieve_candidates(
            query="What is the weather today?", candidate_ids=None, top_k=5
        )

        assert len(candidates) == 5
        assert all(hasattr(c, "tool_id") for c in candidates)
        assert all(hasattr(c, "retrieval_score") for c in candidates)

    def test_retrieve_with_candidate_filter(self, gorilla_config, mock_resources):
        """Test retrieval with candidate ID filtering."""
        mock_llm = MockLLMClient(return_tools=["weather_get"])
        selector = GorillaSelector(gorilla_config, mock_resources, llm_client=mock_llm)

        # Only consider weather tools
        candidate_ids = {"weather_get", "weather_forecast"}
        candidates = selector._retrieve_candidates(
            query="What is the weather?", candidate_ids=candidate_ids, top_k=5
        )

        assert len(candidates) <= 2
        assert all(c.tool_id in candidate_ids for c in candidates)

    def test_build_llm_prompt(self, gorilla_config, mock_resources):
        """Test LLM prompt building."""
        mock_llm = MockLLMClient(return_tools=["weather_get"])
        selector = GorillaSelector(gorilla_config, mock_resources, llm_client=mock_llm)

        candidates = selector._retrieve_candidates(
            query="What is the weather?", candidate_ids=None, top_k=5
        )

        prompt = selector._build_llm_prompt("What is the weather?", candidates, top_k=3)

        assert "What is the weather?" in prompt
        assert "weather" in prompt.lower()
        assert "JSON array" in prompt

    def test_parse_llm_response_valid_json(self, gorilla_config, mock_resources):
        """Test parsing valid JSON response."""
        mock_llm = MockLLMClient(return_tools=["weather_get"])
        selector = GorillaSelector(gorilla_config, mock_resources, llm_client=mock_llm)

        # Get candidates that actually exist in the retrieval
        candidates = selector._retrieve_candidates(query="Weather", candidate_ids=None, top_k=10)
        candidate_ids = [c.tool_id for c in candidates]

        # Valid JSON response - use IDs that are actually in candidates
        # Pick first two available IDs
        test_ids = candidate_ids[:2] if len(candidate_ids) >= 2 else candidate_ids
        response = f'["{test_ids[0]}"' + (f', "{test_ids[1]}"' if len(test_ids) > 1 else "") + "]"
        parsed = selector._parse_llm_response(response, candidates)

        # Verify parsing works correctly
        assert test_ids[0] in parsed
        if len(test_ids) > 1:
            assert test_ids[1] in parsed

    def test_parse_llm_response_with_code_block(self, gorilla_config, mock_resources):
        """Test parsing response with markdown code block."""
        mock_llm = MockLLMClient(return_tools=["weather_get"])
        selector = GorillaSelector(gorilla_config, mock_resources, llm_client=mock_llm)

        candidates = selector._retrieve_candidates(query="Weather", candidate_ids=None, top_k=5)

        # Response with code block
        response = '```json\n["weather_get", "weather_forecast"]\n```'
        parsed = selector._parse_llm_response(response, candidates)

        assert "weather_get" in parsed or "weather_forecast" in parsed

    def test_select_with_llm(self, gorilla_config, mock_resources):
        """Test full selection flow with LLM."""
        mock_llm = MockLLMClient(return_tools=["weather_get", "weather_forecast"])
        selector = GorillaSelector(gorilla_config, mock_resources, llm_client=mock_llm)

        query = ToolSelectionQuery(
            sample_id="test_1",
            instruction="What is the weather today?",
            candidate_tools=["weather_get", "weather_forecast", "email_send", "calendar_add"],
        )

        predictions = selector.select(query, top_k=3)

        assert len(predictions) > 0
        assert all(hasattr(p, "tool_id") for p in predictions)
        assert all(hasattr(p, "score") for p in predictions)
        assert mock_llm._call_count == 1

    def test_select_fallback_to_retrieval(self, gorilla_config, mock_resources):
        """Test fallback to retrieval-only when LLM fails."""
        # Create selector without LLM client
        selector = GorillaSelector(gorilla_config, mock_resources, llm_client=None)

        query = ToolSelectionQuery(
            sample_id="test_1",
            instruction="What is the weather today?",
            candidate_tools=["weather_get", "weather_forecast", "email_send"],
        )

        predictions = selector.select(query, top_k=3)

        assert len(predictions) > 0
        # Should use retrieval_only method
        assert predictions[0].metadata.get("method") == "gorilla_retrieval_only"

    def test_get_stats(self, gorilla_config, mock_resources):
        """Test getting selector statistics."""
        mock_llm = MockLLMClient(return_tools=["weather_get"])
        selector = GorillaSelector(gorilla_config, mock_resources, llm_client=mock_llm)

        stats = selector.get_stats()

        assert "num_tools" in stats
        assert stats["num_tools"] == 8
        assert "embedding_model" in stats
        assert "has_llm_client" in stats
        assert stats["has_llm_client"] is True


class TestGorillaAdapterRegistry:
    """Test Gorilla selector in AdapterRegistry."""

    def test_registry_has_gorilla(self):
        """Test that AdapterRegistry has gorilla selector registered."""
        from sage.benchmark.benchmark_agent.adapter_registry import get_adapter_registry

        registry = get_adapter_registry()
        strategies = registry.list_strategies()

        assert "selector.gorilla" in strategies or "gorilla" in strategies
