"""
Unified Tool Selection Evaluation Framework

This module provides a unified interface for evaluating tool selection methods
across different benchmarks (SAGE, ACEBench, APIBench, etc.).

Design Principles:
- All methods implement the same ToolSelectorProtocol
- All benchmarks are converted to unified ToolSelectionSample format
- Same metrics (Top-K Accuracy, MRR, Recall@K) for all comparisons

SOTA Practice (from Gorilla, ToolACE papers):
- Input: Query + Candidate Tools (tool corpus)
- Output: Ranked list of selected tools
- Metrics: Accuracy, Recall@K, MRR (Mean Reciprocal Rank)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# =============================================================================
# 1. Unified Data Format
# =============================================================================


@dataclass
class Tool:
    """Unified tool representation."""

    id: str  # Unique identifier
    name: str  # Display name
    description: str  # Tool description
    parameters: dict[str, Any] = field(default_factory=dict)  # Optional params schema

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Tool):
            return self.id == other.id
        return False


@dataclass
class ToolSelectionSample:
    """
    Unified sample format for tool selection evaluation.

    Supports conversion from SAGE, ACEBench, and other formats.
    """

    sample_id: str
    instruction: str  # User query/instruction
    candidate_tools: list[Tool]  # Tool corpus to select from
    ground_truth: list[str]  # List of correct tool IDs
    context: dict[str, Any] = field(default_factory=dict)  # Optional context

    @classmethod
    def from_sage(cls, sample: dict[str, Any]) -> ToolSelectionSample:
        """Convert SAGE benchmark format to unified format."""
        ground_truth_raw = sample.get("ground_truth", [])
        if isinstance(ground_truth_raw, dict):
            ground_truth = ground_truth_raw.get("top_k", [])
        else:
            ground_truth = ground_truth_raw

        # Convert candidate_tools to Tool objects
        candidate_tools = []
        for t in sample.get("candidate_tools", []):
            if isinstance(t, dict):
                candidate_tools.append(
                    Tool(
                        id=t.get("id", t.get("name", "")),
                        name=t.get("name", t.get("id", "")),
                        description=t.get("description", ""),
                        parameters=t.get("parameters", {}),
                    )
                )
            elif isinstance(t, str):
                candidate_tools.append(Tool(id=t, name=t, description=""))

        return cls(
            sample_id=sample.get("sample_id", ""),
            instruction=sample.get("instruction", ""),
            candidate_tools=candidate_tools,
            ground_truth=ground_truth,
            context=sample.get("context", {}),
        )

    @classmethod
    def from_acebench(cls, sample: dict[str, Any]) -> ToolSelectionSample:
        """Convert ACEBench/ToolACE format to unified format."""
        # ACEBench format: instruction, tools (list of tool dicts), ground_truth
        candidate_tools = []
        for t in sample.get("tools", sample.get("candidate_tools", [])):
            if isinstance(t, dict):
                candidate_tools.append(
                    Tool(
                        id=t.get("name", t.get("id", "")),
                        name=t.get("name", t.get("id", "")),
                        description=t.get("description", ""),
                        parameters=t.get("parameters", {}),
                    )
                )
            elif isinstance(t, str):
                candidate_tools.append(Tool(id=t, name=t, description=""))

        ground_truth = sample.get("ground_truth", {})
        if isinstance(ground_truth, dict):
            gt_tools = ground_truth.get("top_k", ground_truth.get("tools", []))
        elif isinstance(ground_truth, list):
            gt_tools = ground_truth
        else:
            gt_tools = []

        return cls(
            sample_id=sample.get("sample_id", ""),
            instruction=sample.get("instruction", ""),
            candidate_tools=candidate_tools,
            ground_truth=gt_tools,
            context=sample.get("context", {}),
        )


@dataclass
class SelectionResult:
    """Result from a tool selection method."""

    tool_ids: list[str]  # Ranked list of selected tool IDs
    scores: list[float] = field(default_factory=list)  # Optional confidence scores
    metadata: dict[str, Any] = field(default_factory=dict)  # Method-specific metadata


# =============================================================================
# 2. Unified Selector Protocol
# =============================================================================


@runtime_checkable
class ToolSelectorProtocol(Protocol):
    """
    Protocol that all tool selection methods must implement.

    This ensures consistency across:
    - Retrieval methods (keyword, embedding)
    - LLM-based methods (direct generation, Gorilla)
    - Hybrid methods (retrieval + reranking)
    """

    def select(
        self,
        query: str,
        candidate_tools: list[Tool],
        top_k: int = 5,
    ) -> SelectionResult:
        """
        Select top_k tools from candidates for the given query.

        Args:
            query: User query/instruction
            candidate_tools: List of candidate tools to choose from
            top_k: Number of tools to select

        Returns:
            SelectionResult with ranked tool IDs
        """
        ...


# =============================================================================
# 3. Base Selector Implementations
# =============================================================================


class BaseSelectorAdapter(ABC):
    """Base class for selector adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return selector name for logging/reporting."""
        ...

    @abstractmethod
    def select(
        self,
        query: str,
        candidate_tools: list[Tool],
        top_k: int = 5,
    ) -> SelectionResult:
        """Select tools."""
        ...


class KeywordSelectorAdapter(BaseSelectorAdapter):
    """Adapter for keyword/BM25-based selector."""

    def __init__(self, selector: Any = None):
        self._selector = selector

    @property
    def name(self) -> str:
        return "keyword"

    def select(
        self,
        query: str,
        candidate_tools: list[Tool],
        top_k: int = 5,
    ) -> SelectionResult:
        if self._selector is None:
            self._init_selector()

        # Pass tool IDs only (schema expects list[str])
        tool_ids_input = [t.id for t in candidate_tools]
        results = self._selector.select(query, tool_ids_input, top_k=top_k)

        tool_ids = [r.tool_id if hasattr(r, "tool_id") else str(r) for r in results]
        scores = [r.score if hasattr(r, "score") else 1.0 for r in results]

        return SelectionResult(tool_ids=tool_ids, scores=scores)

    def _init_selector(self):
        # Use adapter_registry which handles resources correctly
        from sage.benchmark.benchmark_agent import get_adapter_registry

        registry = get_adapter_registry()
        self._selector = registry.get("selector.keyword")


class EmbeddingSelectorAdapter(BaseSelectorAdapter):
    """Adapter for embedding-based selector."""

    def __init__(self, selector: Any = None):
        self._selector = selector

    @property
    def name(self) -> str:
        return "embedding"

    def select(
        self,
        query: str,
        candidate_tools: list[Tool],
        top_k: int = 5,
    ) -> SelectionResult:
        if self._selector is None:
            self._init_selector()

        # Pass tool IDs only (schema expects list[str])
        tool_ids_input = [t.id for t in candidate_tools]
        results = self._selector.select(query, tool_ids_input, top_k=top_k)

        tool_ids = [r.tool_id if hasattr(r, "tool_id") else str(r) for r in results]
        scores = [r.score if hasattr(r, "score") else 1.0 for r in results]

        return SelectionResult(tool_ids=tool_ids, scores=scores)

    def _init_selector(self):
        from sage.benchmark.benchmark_agent import get_adapter_registry

        registry = get_adapter_registry()
        self._selector = registry.get("selector.embedding")


class HybridSelectorAdapter(BaseSelectorAdapter):
    """Adapter for hybrid (keyword + embedding) selector."""

    def __init__(self, selector: Any = None):
        self._selector = selector

    @property
    def name(self) -> str:
        return "hybrid"

    def select(
        self,
        query: str,
        candidate_tools: list[Tool],
        top_k: int = 5,
    ) -> SelectionResult:
        if self._selector is None:
            self._init_selector()

        # Pass tool IDs only (schema expects list[str])
        tool_ids_input = [t.id for t in candidate_tools]
        results = self._selector.select(query, tool_ids_input, top_k=top_k)

        tool_ids = [r.tool_id if hasattr(r, "tool_id") else str(r) for r in results]
        scores = [r.score if hasattr(r, "score") else 1.0 for r in results]

        return SelectionResult(tool_ids=tool_ids, scores=scores)

    def _init_selector(self):
        from sage.benchmark.benchmark_agent import get_adapter_registry

        registry = get_adapter_registry()
        self._selector = registry.get("selector.hybrid")


class LLMDirectSelectorAdapter(BaseSelectorAdapter):
    """
    LLM-based tool selection (direct generation).

    This is the approach used in ACEBench evaluation - let LLM directly
    choose the best tool based on the query and tool descriptions.
    """

    def __init__(
        self,
        llm_client: Any = None,
        model_id: Optional[str] = None,
        use_embedded: bool = False,
    ):
        self._llm_client = llm_client
        self._model_id = model_id
        self._use_embedded = use_embedded

    @property
    def name(self) -> str:
        return "llm_direct"

    def select(
        self,
        query: str,
        candidate_tools: list[Tool],
        top_k: int = 5,
    ) -> SelectionResult:
        if self._llm_client is None:
            self._init_client()

        # Build prompt
        prompt = self._build_prompt(query, candidate_tools, top_k)

        # Generate response
        try:
            response = self._llm_client.chat([{"role": "user", "content": prompt}])
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}")
            return SelectionResult(tool_ids=[])

        # Parse response
        tool_ids = self._parse_response(response, candidate_tools)

        return SelectionResult(tool_ids=tool_ids[:top_k])

    def _init_client(self):
        from sage.common.components.sage_llm import IntelligentLLMClient

        if self._use_embedded:
            self._llm_client = IntelligentLLMClient.create_embedded(model_id=self._model_id)
        else:
            self._llm_client = IntelligentLLMClient.create_auto()

    def _build_prompt(self, query: str, candidate_tools: list[Tool], top_k: int) -> str:
        """Build prompt for LLM tool selection."""
        tools_desc = "\n".join(f"- {t.name}: {t.description}" for t in candidate_tools)

        return f"""You are a tool selection assistant. Given a user query and a list of available tools,
select the {top_k} most relevant tool(s) for the query.

Available Tools:
{tools_desc}

User Query: {query}

Respond with ONLY the tool name(s), one per line, in order of relevance.
Do not include any explanation or additional text."""

    def _parse_response(self, response: str, candidate_tools: list[Tool]) -> list[str]:
        """Parse LLM response to extract tool names."""
        tool_names = {t.name.lower(): t.id for t in candidate_tools}
        tool_ids_map = {t.id.lower(): t.id for t in candidate_tools}

        selected = []
        for line in response.strip().split("\n"):
            line = line.strip().strip("-").strip("*").strip()
            line_lower = line.lower()

            # Try exact match
            if line_lower in tool_names:
                selected.append(tool_names[line_lower])
            elif line_lower in tool_ids_map:
                selected.append(tool_ids_map[line_lower])
            else:
                # Try partial match
                for name, tool_id in tool_names.items():
                    if name in line_lower or line_lower in name:
                        if tool_id not in selected:
                            selected.append(tool_id)
                        break

        return selected


# =============================================================================
# 4. Unified Metrics
# =============================================================================


@dataclass
class EvaluationMetrics:
    """Unified evaluation metrics."""

    # Core metrics
    top_1_accuracy: float = 0.0
    top_3_accuracy: float = 0.0
    top_5_accuracy: float = 0.0
    mrr: float = 0.0  # Mean Reciprocal Rank

    # Additional metrics
    recall_at_k: dict[int, float] = field(default_factory=dict)
    precision_at_k: dict[int, float] = field(default_factory=dict)

    # Metadata
    total_samples: int = 0
    method_name: str = ""


def compute_metrics(
    predictions: list[SelectionResult],
    references: list[list[str]],  # Ground truth tool IDs for each sample
    k_values: list[int] | None = None,
) -> EvaluationMetrics:
    """
    Compute unified evaluation metrics.

    Args:
        predictions: List of SelectionResult from selector
        references: List of ground truth tool ID lists
        k_values: K values for Top-K and Recall@K metrics

    Returns:
        EvaluationMetrics with all computed metrics
    """
    if k_values is None:
        k_values = [1, 3, 5]

    if len(predictions) != len(references):
        raise ValueError(
            f"Predictions ({len(predictions)}) and references ({len(references)}) "
            "must have same length"
        )

    n = len(predictions)
    if n == 0:
        return EvaluationMetrics()

    # Initialize counters
    top_k_correct = dict.fromkeys(k_values, 0)
    reciprocal_ranks = []
    recall_at_k = {k: [] for k in k_values}
    precision_at_k = {k: [] for k in k_values}

    for pred, ref in zip(predictions, references):
        pred_ids = pred.tool_ids
        ref_set = set(ref)

        # Top-K accuracy: any correct tool in top-k predictions
        for k in k_values:
            top_k_preds = set(pred_ids[:k])
            if top_k_preds & ref_set:
                top_k_correct[k] += 1

        # MRR: position of first correct prediction
        rr = 0.0
        for i, tool_id in enumerate(pred_ids):
            if tool_id in ref_set:
                rr = 1.0 / (i + 1)
                break
        reciprocal_ranks.append(rr)

        # Recall@K and Precision@K
        for k in k_values:
            top_k_preds = set(pred_ids[:k])
            hits = len(top_k_preds & ref_set)

            recall = hits / len(ref_set) if ref_set else 0.0
            precision = hits / k

            recall_at_k[k].append(recall)
            precision_at_k[k].append(precision)

    # Compute averages
    metrics = EvaluationMetrics(
        top_1_accuracy=top_k_correct.get(1, 0) / n,
        top_3_accuracy=top_k_correct.get(3, 0) / n,
        top_5_accuracy=top_k_correct.get(5, 0) / n,
        mrr=sum(reciprocal_ranks) / n,
        recall_at_k={k: sum(v) / n for k, v in recall_at_k.items()},
        precision_at_k={k: sum(v) / n for k, v in precision_at_k.items()},
        total_samples=n,
    )

    return metrics


# =============================================================================
# 5. Unified Evaluator
# =============================================================================


class UnifiedToolSelectionEvaluator:
    """
    Unified evaluator for tool selection methods.

    Supports multiple benchmarks and methods with consistent evaluation.
    """

    def __init__(self):
        self.selectors: dict[str, BaseSelectorAdapter] = {}

    def register_selector(self, name: str, selector: BaseSelectorAdapter):
        """Register a selector for evaluation."""
        self.selectors[name] = selector

    def register_default_selectors(self, use_embedded_llm: bool = False):
        """Register default set of selectors."""
        self.selectors["keyword"] = KeywordSelectorAdapter()
        self.selectors["embedding"] = EmbeddingSelectorAdapter()
        self.selectors["hybrid"] = HybridSelectorAdapter()
        self.selectors["llm_direct"] = LLMDirectSelectorAdapter(use_embedded=use_embedded_llm)

    def evaluate(
        self,
        samples: list[ToolSelectionSample],
        selector_names: Optional[list[str]] = None,
        top_k: int = 5,
    ) -> dict[str, EvaluationMetrics]:
        """
        Evaluate selectors on samples.

        Args:
            samples: List of unified ToolSelectionSample
            selector_names: Names of selectors to evaluate (None = all)
            top_k: Top-K value for selection

        Returns:
            Dict mapping selector name to EvaluationMetrics
        """
        if selector_names is None:
            selector_names = list(self.selectors.keys())

        results = {}

        for name in selector_names:
            if name not in self.selectors:
                logger.warning(f"Selector '{name}' not registered, skipping")
                continue

            selector = self.selectors[name]
            logger.info(f"Evaluating selector: {name}")

            predictions = []
            references = []

            for sample in samples:
                try:
                    result = selector.select(
                        query=sample.instruction,
                        candidate_tools=sample.candidate_tools,
                        top_k=top_k,
                    )
                    predictions.append(result)
                    references.append(sample.ground_truth)
                except Exception as e:
                    logger.warning(f"Selector {name} failed on sample {sample.sample_id}: {e}")
                    predictions.append(SelectionResult(tool_ids=[]))
                    references.append(sample.ground_truth)

            metrics = compute_metrics(predictions, references)
            metrics.method_name = name
            results[name] = metrics

        return results

    def print_results(self, results: dict[str, EvaluationMetrics]):
        """Print evaluation results in a table format."""
        print("\n" + "=" * 80)
        print("Tool Selection Evaluation Results")
        print("=" * 80)
        print(
            f"{'Method':<15} {'Top-1':>10} {'Top-3':>10} {'Top-5':>10} {'MRR':>10} {'Samples':>10}"
        )
        print("-" * 80)

        for name, metrics in results.items():
            print(
                f"{name:<15} "
                f"{metrics.top_1_accuracy * 100:>9.1f}% "
                f"{metrics.top_3_accuracy * 100:>9.1f}% "
                f"{metrics.top_5_accuracy * 100:>9.1f}% "
                f"{metrics.mrr * 100:>9.1f}% "
                f"{metrics.total_samples:>10}"
            )

        print("=" * 80)
