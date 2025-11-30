"""
Tests for embedding selector implementation.
"""

from dataclasses import dataclass

import numpy as np
import pytest

from sage.libs.agentic.agents.action.tool_selection.base import (
    SelectorResources,
)
from sage.libs.agentic.agents.action.tool_selection.embedding_selector import (
    EmbeddingSelector,
)
from sage.libs.agentic.agents.action.tool_selection.schemas import (
    EmbeddingSelectorConfig,
    ToolSelectionQuery,
)


@dataclass
class MockTool:
    """Mock tool object with required attributes."""

    tool_id: str
    name: str
    description: str
    capabilities: list[str] = None
    category: str = None
    parameters: dict = None

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
                description="Search the web for information using queries",
                capabilities=["search", "query", "web"],
                category="information",
            ),
            "calculator": MockTool(
                tool_id="calculator",
                name="Calculator",
                description="Perform mathematical calculations and computations",
                capabilities=["calculate", "math", "arithmetic"],
                category="computation",
            ),
            "weather": MockTool(
                tool_id="weather",
                name="Weather API",
                description="Get current weather information and forecasts",
                capabilities=["weather", "forecast", "temperature"],
                category="information",
            ),
            "email": MockTool(
                tool_id="email",
                name="Email Service",
                description="Send and receive emails and messages",
                capabilities=["email", "send", "message"],
                category="communication",
            ),
            "translator": MockTool(
                tool_id="translator",
                name="Translation Service",
                description="Translate text between different languages",
                capabilities=["translate", "language", "multilingual"],
                category="language",
            ),
        }

    def get_tool(self, tool_id):
        return self.tools.get(tool_id)

    def get_all_tools(self):
        return list(self.tools.values())

    def iter_all(self):
        """Iterate over all tools."""
        yield from self.tools.values()


class MockEmbeddingClient:
    """Mock embedding client for testing."""

    def __init__(self, dimension=128, noise_level=0.1):
        """
        Initialize mock embedding client.

        Args:
            dimension: Embedding dimension
            noise_level: Amount of random noise to add to embeddings
        """
        self.dimension = dimension
        self.noise_level = noise_level
        self.call_count = 0
        np.random.seed(42)  # For reproducibility

    def embed(self, texts, model=None, batch_size=32):
        """
        Generate mock embeddings based on text content.

        Creates embeddings where similar texts have higher cosine similarity.

        Args:
            texts: List of texts to embed
            model: Model identifier (ignored in mock)
            batch_size: Batch size (ignored in mock)

        Returns:
            Array of embeddings (shape: len(texts) x dimension)
        """
        self.call_count += 1

        if isinstance(texts, str):
            texts = [texts]

        embeddings = []
        for text in texts:
            # Generate embedding based on text hash for consistency
            # This ensures same text always gets same embedding
            text_hash = hash(text.lower())
            np.random.seed(abs(text_hash) % (2**32))

            # Base embedding from random seed
            embedding = np.random.randn(self.dimension)

            # Add semantic features based on keywords
            # This makes similar texts have similar embeddings
            keywords_map = {
                "search": [1, 0, 0, 0, 0],
                "web": [1, 0, 0, 0, 0],
                "query": [1, 0, 0, 0, 0],
                "calculate": [0, 1, 0, 0, 0],
                "math": [0, 1, 0, 0, 0],
                "arithmetic": [0, 1, 0, 0, 0],
                "weather": [0, 0, 1, 0, 0],
                "forecast": [0, 0, 1, 0, 0],
                "temperature": [0, 0, 1, 0, 0],
                "email": [0, 0, 0, 1, 0],
                "message": [0, 0, 0, 1, 0],
                "send": [0, 0, 0, 1, 0],
                "translate": [0, 0, 0, 0, 1],
                "language": [0, 0, 0, 0, 1],
            }

            # Add keyword features to first 5 dimensions
            text_lower = text.lower()
            for keyword, feature in keywords_map.items():
                if keyword in text_lower:
                    embedding[:5] += np.array(feature) * 10.0  # Strong signal

            # Add small noise
            embedding += np.random.randn(self.dimension) * self.noise_level

            # Normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            embeddings.append(embedding)

        return np.array(embeddings)

    def get_dimension(self):
        """Get embedding dimension."""
        return self.dimension


class TestEmbeddingSelector:
    """Tests for EmbeddingSelector implementation."""

    @pytest.fixture
    def mock_embedding_client(self):
        """Create mock embedding client."""
        return MockEmbeddingClient(dimension=128)

    @pytest.fixture
    def resources(self, mock_embedding_client):
        """Create test resources with embedding client."""
        return SelectorResources(
            tools_loader=MockToolsLoader(), embedding_client=mock_embedding_client
        )

    @pytest.fixture
    def selector(self, resources):
        """Create embedding selector with default config."""
        config = EmbeddingSelectorConfig()
        return EmbeddingSelector(config=config, resources=resources)

    def test_create_selector(self, resources):
        """Test creating embedding selector."""
        config = EmbeddingSelectorConfig()
        selector = EmbeddingSelector(config=config, resources=resources)

        assert selector.name == "embedding"
        assert selector.config == config
        assert selector._embedding_dimension == 128

    def test_create_without_embedding_client_fails(self):
        """Test that creating selector without embedding client raises error."""
        resources = SelectorResources(tools_loader=MockToolsLoader(), embedding_client=None)
        config = EmbeddingSelectorConfig()

        with pytest.raises(ValueError, match="requires embedding_client"):
            EmbeddingSelector(config=config, resources=resources)

    def test_from_config(self, resources):
        """Test creating selector from config."""
        config = EmbeddingSelectorConfig(similarity_metric="dot")
        selector = EmbeddingSelector.from_config(config, resources)

        assert selector.config.similarity_metric == "dot"

    def test_select_basic(self, selector):
        """Test basic tool selection with embeddings."""
        query = ToolSelectionQuery(
            sample_id="test-001",
            instruction="Search for weather information on the web",
            candidate_tools=["search", "calculator", "weather"],
        )

        results = selector.select(query, top_k=2)

        assert len(results) <= 2
        assert all(r.tool_id in query.candidate_tools for r in results)
        assert all(0 <= r.score <= 1 for r in results)

        # Should find relevant tools (search or weather)
        top_tool_ids = [r.tool_id for r in results]
        assert "search" in top_tool_ids or "weather" in top_tool_ids

    def test_select_returns_sorted_by_score(self, selector):
        """Test that results are sorted by score descending."""
        query = ToolSelectionQuery(
            sample_id="test-002",
            instruction="Calculate mathematical formula and arithmetic operations",
            candidate_tools=["search", "calculator", "weather", "email"],
        )

        results = selector.select(query, top_k=4)

        # Results should be sorted by score descending
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

        # Calculator should rank high for math query
        if len(results) > 0:
            assert results[0].tool_id == "calculator"

    def test_select_respects_top_k(self, selector):
        """Test that selector respects top_k limit."""
        query = ToolSelectionQuery(
            sample_id="test-003",
            instruction="Search the web for information",
            candidate_tools=["search", "calculator", "weather", "email", "translator"],
        )

        results = selector.select(query, top_k=3)

        assert len(results) <= 3

    def test_select_empty_candidates(self, selector):
        """Test selection with no candidate constraints uses all tools."""
        query = ToolSelectionQuery(
            sample_id="test-004", instruction="Search for something", candidate_tools=[]
        )

        results = selector.select(query, top_k=5)

        # Should search across all available tools
        assert isinstance(results, list)
        assert len(results) > 0

    def test_select_semantic_similarity(self, selector):
        """Test that semantically similar queries find relevant tools."""
        # Query about weather should find weather tool
        weather_query = ToolSelectionQuery(
            sample_id="test-005",
            instruction="What's the temperature and forecast today?",
            candidate_tools=[],
        )

        weather_results = selector.select(weather_query, top_k=2)
        top_tool = weather_results[0].tool_id if weather_results else None
        assert top_tool == "weather"

        # Query about math should find calculator in top results
        math_query = ToolSelectionQuery(
            sample_id="test-006",
            instruction="Compute arithmetic calculation",
            candidate_tools=[],
        )

        math_results = selector.select(math_query, top_k=3)
        # Calculator should be in top 3 results for math-related query
        top_tool_ids = [r.tool_id for r in math_results]
        assert "calculator" in top_tool_ids, f"Expected calculator in top 3, got {top_tool_ids}"

    def test_select_with_different_metrics(self, resources, mock_embedding_client):
        """Test selection with different similarity metrics."""
        for metric in ["cosine", "dot", "euclidean"]:
            config = EmbeddingSelectorConfig(similarity_metric=metric)
            selector = EmbeddingSelector(config=config, resources=resources)

            query = ToolSelectionQuery(
                sample_id=f"test-metric-{metric}",
                instruction="Search for information",
                candidate_tools=["search", "calculator", "weather"],
            )

            results = selector.select(query, top_k=2)
            assert len(results) > 0
            assert all(isinstance(r.score, float) for r in results)

    def test_get_embedding_dimension(self, selector):
        """Test getting embedding dimension."""
        assert selector.get_embedding_dimension() == 128

    def test_get_index_size(self, selector):
        """Test getting vector index size."""
        # Should have 5 tools indexed
        assert selector.get_index_size() == 5

    def test_get_stats(self, selector):
        """Test getting selector statistics."""
        stats = selector.get_stats()

        assert "embedding_dimension" in stats
        assert "index_size" in stats
        assert "similarity_metric" in stats
        assert stats["embedding_dimension"] == 128
        assert stats["index_size"] == 5

    def test_select_with_invalid_candidates(self, selector):
        """Test selection with candidates that don't exist in index."""
        query = ToolSelectionQuery(
            sample_id="test-007",
            instruction="Search for something",
            candidate_tools=["nonexistent1", "nonexistent2"],
        )

        results = selector.select(query, top_k=5)

        # Should return empty results when no valid candidates
        assert len(results) == 0

    def test_embedding_client_called(self, selector, mock_embedding_client):
        """Test that embedding client is called for queries."""
        initial_count = mock_embedding_client.call_count

        query = ToolSelectionQuery(
            sample_id="test-008", instruction="Test query", candidate_tools=["search"]
        )

        selector.select(query, top_k=1)

        # Embedding client should be called for the query
        # (Tools already embedded during initialization)
        assert mock_embedding_client.call_count > initial_count

    def test_build_tool_text(self, resources):
        """Test tool text building includes all relevant fields."""
        config = EmbeddingSelectorConfig()
        selector = EmbeddingSelector(config=config, resources=resources)

        # Check that tool text includes name, description, capabilities
        tool_text = selector._tool_texts.get("search")
        assert tool_text is not None
        assert "Web Search" in tool_text
        assert "Search the web" in tool_text or "web" in tool_text.lower()

    def test_multiple_queries_consistent(self, selector):
        """Test that same query produces consistent results."""
        query1 = ToolSelectionQuery(
            sample_id="test-009a",
            instruction="Calculate math operations",
            candidate_tools=["calculator", "search"],
        )

        query2 = ToolSelectionQuery(
            sample_id="test-009b",
            instruction="Calculate math operations",
            candidate_tools=["calculator", "search"],
        )

        results1 = selector.select(query1, top_k=2)
        results2 = selector.select(query2, top_k=2)

        # Same query should produce same rankings
        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1.tool_id == r2.tool_id
            assert abs(r1.score - r2.score) < 1e-6  # Scores should be very close


class TestEmbeddingSelectorEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def mock_embedding_client(self):
        return MockEmbeddingClient(dimension=64)

    @pytest.fixture
    def resources(self, mock_embedding_client):
        return SelectorResources(
            tools_loader=MockToolsLoader(), embedding_client=mock_embedding_client
        )

    def test_empty_query(self, resources):
        """Test handling of empty query instruction."""
        config = EmbeddingSelectorConfig()
        selector = EmbeddingSelector(config=config, resources=resources)

        query = ToolSelectionQuery(
            sample_id="test-empty", instruction="", candidate_tools=["search"]
        )

        # Should not crash, returns results based on empty embedding
        results = selector.select(query, top_k=1)
        assert isinstance(results, list)

    def test_large_top_k(self, resources):
        """Test with top_k larger than available tools."""
        config = EmbeddingSelectorConfig()
        selector = EmbeddingSelector(config=config, resources=resources)

        query = ToolSelectionQuery(
            sample_id="test-large-k", instruction="Search", candidate_tools=[]
        )

        results = selector.select(query, top_k=1000)

        # Should return all available tools
        assert len(results) <= 5  # Only 5 tools available
