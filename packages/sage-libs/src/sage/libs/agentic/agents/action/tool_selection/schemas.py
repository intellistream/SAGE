"""
Data schemas for tool selection.

Defines Pydantic models for queries, predictions, and configurations.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolSelectionQuery(BaseModel):
    """Query for tool selection."""

    sample_id: str = Field(..., description="Unique identifier for the query")
    instruction: str = Field(..., description="User instruction or task description")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    candidate_tools: list[str] = Field(..., description="List of candidate tool IDs")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional metadata")

    class Config:
        extra = "allow"


class ToolPrediction(BaseModel):
    """Prediction result for a single tool."""

    tool_id: str = Field(..., description="Tool identifier")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    explanation: Optional[str] = Field(default=None, description="Optional explanation")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        frozen = True  # Make immutable for caching


class SelectorConfig(BaseModel):
    """Base configuration for tool selectors."""

    name: str = Field(..., description="Selector strategy name")
    top_k: int = Field(default=5, ge=1, description="Number of tools to select")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum score threshold")
    cache_enabled: bool = Field(default=True, description="Enable result caching")
    params: dict[str, Any] = Field(default_factory=dict, description="Strategy-specific parameters")

    class Config:
        extra = "allow"


class KeywordSelectorConfig(SelectorConfig):
    """Configuration for keyword-based selector."""

    name: str = "keyword"
    method: str = Field(
        default="tfidf", description="Keyword matching method: tfidf, overlap, bm25"
    )
    lowercase: bool = Field(default=True, description="Convert to lowercase")
    remove_stopwords: bool = Field(default=True, description="Remove stopwords")
    ngram_range: tuple = Field(default=(1, 2), description="N-gram range for features")


class EmbeddingSelectorConfig(SelectorConfig):
    """Configuration for embedding-based selector."""

    name: str = "embedding"
    embedding_model: str = Field(default="default", description="Embedding model identifier")
    similarity_metric: str = Field(
        default="cosine", description="Similarity metric: cosine, dot, euclidean"
    )
    use_cache: bool = Field(default=True, description="Cache embedding vectors")
    batch_size: int = Field(default=32, ge=1, description="Batch size for embedding")


class TwoStageSelectorConfig(SelectorConfig):
    """Configuration for two-stage selector."""

    name: str = "two_stage"
    coarse_k: int = Field(
        default=20, ge=1, description="Number of candidates from coarse retrieval"
    )
    coarse_selector: str = Field(default="keyword", description="Coarse retrieval selector")
    rerank_selector: str = Field(default="embedding", description="Reranking selector")
    fusion_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="Weight for score fusion")


class AdaptiveSelectorConfig(SelectorConfig):
    """Configuration for adaptive selector."""

    name: str = "adaptive"
    strategies: list[str] = Field(
        default_factory=lambda: ["keyword", "embedding"], description="List of strategies"
    )
    selection_method: str = Field(
        default="bandit", description="Selection method: bandit, ensemble, threshold"
    )
    exploration_rate: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Exploration rate for bandit"
    )
    update_interval: int = Field(default=100, ge=1, description="Update interval for adaptation")


class DFSDTSelectorConfig(SelectorConfig):
    """
    Configuration for DFSDT (Depth-First Search-based Decision Tree) selector.

    Based on ToolLLM paper (Qin et al., 2023):
    "ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs"
    """

    name: str = "dfsdt"
    max_depth: int = Field(default=3, ge=1, le=10, description="Maximum search depth")
    beam_width: int = Field(default=5, ge=1, le=20, description="Number of candidates per level")
    llm_model: str = Field(
        default="auto", description="LLM model for scoring (auto uses UnifiedInferenceClient)"
    )
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="LLM sampling temperature")
    use_diversity_prompt: bool = Field(
        default=True, description="Use diversity prompting for exploration"
    )
    score_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum score threshold for pruning"
    )
    use_keyword_prefilter: bool = Field(
        default=True, description="Use keyword matching to pre-filter candidates"
    )
    prefilter_k: int = Field(
        default=20, ge=5, le=100, description="Number of candidates after pre-filtering"
    )


class GorillaSelectorConfig(SelectorConfig):
    """
    Configuration for Gorilla-style retrieval-augmented selector.

    Based on Gorilla paper (Patil et al., 2023):
    "Gorilla: Large Language Model Connected with Massive APIs"

    Two-stage approach: embedding retrieval + LLM selection.
    """

    name: str = "gorilla"
    top_k_retrieve: int = Field(
        default=20, ge=1, description="Number of tools to retrieve in first stage"
    )
    top_k_select: int = Field(
        default=5, ge=1, description="Number of tools to select in final output"
    )
    embedding_model: str = Field(default="default", description="Embedding model for retrieval")
    llm_model: str = Field(
        default="auto", description="LLM model for selection (auto uses UnifiedInferenceClient)"
    )
    similarity_metric: str = Field(
        default="cosine", description="Similarity metric: cosine, dot, euclidean"
    )
    temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, description="LLM temperature for selection"
    )
    use_detailed_docs: bool = Field(
        default=True, description="Include detailed parameter docs in context"
    )
    max_context_tools: int = Field(
        default=15, ge=1, description="Max tools to include in LLM context"
    )


# Config type registry
CONFIG_TYPES = {
    "keyword": KeywordSelectorConfig,
    "embedding": EmbeddingSelectorConfig,
    "two_stage": TwoStageSelectorConfig,
    "adaptive": AdaptiveSelectorConfig,
    "dfsdt": DFSDTSelectorConfig,
    "gorilla": GorillaSelectorConfig,
}


def create_selector_config(config_dict: dict[str, Any]) -> SelectorConfig:
    """
    Create appropriate selector config from dictionary.

    Args:
        config_dict: Configuration dictionary

    Returns:
        Typed SelectorConfig subclass instance

    Raises:
        ValueError: If selector name not recognized
    """
    selector_name = config_dict.get("name", "keyword")

    if selector_name not in CONFIG_TYPES:
        raise ValueError(f"Unknown selector type: {selector_name}")

    config_class = CONFIG_TYPES[selector_name]
    return config_class(**config_dict)
