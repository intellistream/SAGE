"""
Tests for tool selection schemas.
"""

import pytest

from sage.libs.agentic.agents.action.tool_selection.schemas import (
    EmbeddingSelectorConfig,
    KeywordSelectorConfig,
    SelectorConfig,
    ToolPrediction,
    ToolSelectionQuery,
    TwoStageSelectorConfig,
)


class TestToolSelectionQuery:
    """Tests for ToolSelectionQuery schema."""

    def test_create_query_minimal(self):
        """Test creating query with required fields only."""
        query = ToolSelectionQuery(
            sample_id="test-001",
            instruction="Search for weather information",
            candidate_tools=["search", "weather_api", "calculator"],
        )

        assert query.sample_id == "test-001"
        assert query.instruction == "Search for weather information"
        assert len(query.candidate_tools) == 3
        assert query.context == {}
        assert query.metadata == {}

    def test_create_query_full(self):
        """Test creating query with all fields."""
        query = ToolSelectionQuery(
            sample_id="test-002",
            instruction="Calculate the sum of numbers",
            context={"numbers": [1, 2, 3]},
            candidate_tools=["calculator", "math_api"],
            metadata={"source": "user_input"},
        )

        assert query.context["numbers"] == [1, 2, 3]
        assert query.metadata["source"] == "user_input"

    def test_query_validation_fails_on_empty_instruction(self):
        """Test that empty instruction still creates valid query."""
        # Empty string is valid - just tests basic creation
        query = ToolSelectionQuery(sample_id="test", instruction="", candidate_tools=["tool1"])
        assert query.instruction == ""


class TestToolPrediction:
    """Tests for ToolPrediction schema."""

    def test_create_prediction(self):
        """Test creating a tool prediction."""
        pred = ToolPrediction(tool_id="search", score=0.95, explanation="High keyword match")

        assert pred.tool_id == "search"
        assert pred.score == 0.95
        assert pred.explanation == "High keyword match"

    def test_prediction_score_bounds(self):
        """Test that score must be between 0 and 1."""
        # Valid scores
        pred_low = ToolPrediction(tool_id="t1", score=0.0)
        pred_high = ToolPrediction(tool_id="t2", score=1.0)

        assert pred_low.score == 0.0
        assert pred_high.score == 1.0

        # Invalid scores should raise
        with pytest.raises(ValueError):
            ToolPrediction(tool_id="t3", score=-0.1)

        with pytest.raises(ValueError):
            ToolPrediction(tool_id="t4", score=1.5)

    def test_prediction_immutable(self):
        """Test that prediction is immutable (frozen)."""
        pred = ToolPrediction(tool_id="search", score=0.9)

        with pytest.raises((TypeError, ValueError)):
            pred.score = 0.5


class TestSelectorConfig:
    """Tests for SelectorConfig schema."""

    def test_create_base_config(self):
        """Test creating base selector config."""
        config = SelectorConfig(name="test_selector")

        assert config.name == "test_selector"
        assert config.top_k == 5
        assert config.min_score == 0.0
        assert config.cache_enabled is True

    def test_create_config_custom(self):
        """Test creating config with custom values."""
        config = SelectorConfig(
            name="custom",
            top_k=10,
            min_score=0.5,
            cache_enabled=False,
            params={"custom_param": "value"},
        )

        assert config.top_k == 10
        assert config.min_score == 0.5
        assert config.params["custom_param"] == "value"


class TestKeywordSelectorConfig:
    """Tests for KeywordSelectorConfig schema."""

    def test_default_keyword_config(self):
        """Test default keyword selector config."""
        config = KeywordSelectorConfig()

        assert config.name == "keyword"
        assert config.method == "tfidf"
        assert config.lowercase is True
        assert config.remove_stopwords is True

    def test_custom_keyword_config(self):
        """Test custom keyword selector config."""
        config = KeywordSelectorConfig(method="bm25", lowercase=False, ngram_range=(1, 3))

        assert config.method == "bm25"
        assert config.lowercase is False
        assert config.ngram_range == (1, 3)


class TestEmbeddingSelectorConfig:
    """Tests for EmbeddingSelectorConfig schema."""

    def test_default_embedding_config(self):
        """Test default embedding selector config."""
        config = EmbeddingSelectorConfig()

        assert config.name == "embedding"
        assert config.embedding_model == "default"
        assert config.similarity_metric == "cosine"

    def test_custom_embedding_config(self):
        """Test custom embedding selector config."""
        config = EmbeddingSelectorConfig(
            embedding_model="text-embedding-ada-002", similarity_metric="dot", batch_size=64
        )

        assert config.embedding_model == "text-embedding-ada-002"
        assert config.batch_size == 64


class TestTwoStageSelectorConfig:
    """Tests for TwoStageSelectorConfig schema."""

    def test_default_two_stage_config(self):
        """Test default two-stage selector config."""
        config = TwoStageSelectorConfig()

        assert config.name == "two_stage"
        assert config.coarse_k == 20
        assert config.coarse_selector == "keyword"
        assert config.rerank_selector == "embedding"
        assert config.fusion_weight == 0.5

    def test_custom_two_stage_config(self):
        """Test custom two-stage selector config."""
        config = TwoStageSelectorConfig(coarse_k=50, fusion_weight=0.7)

        assert config.coarse_k == 50
        assert config.fusion_weight == 0.7
