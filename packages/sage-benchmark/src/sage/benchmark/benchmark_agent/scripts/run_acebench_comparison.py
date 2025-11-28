#!/usr/bin/env python3
"""
ACEBench Multi-Method Tool Selection Comparison

.. deprecated::
    This script is DEPRECATED. Please use run_unified_eval.py instead:

        python run_unified_eval.py --dataset acebench --samples 100
        python run_unified_eval.py --dataset all --samples 100  # Cross-dataset comparison

    run_unified_eval.py supports all datasets (SAGE, ACEBench, APIBank, ToolAlpaca, etc.)
    with a unified interface.

Legacy usage (deprecated):
    python run_acebench_comparison.py --samples 100
    python run_acebench_comparison.py --samples 50 --use-embedded
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

# Emit deprecation warning
warnings.warn(
    "run_acebench_comparison.py is deprecated. "
    "Use 'python run_unified_eval.py --dataset acebench' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class MethodResult:
    """Result from a single method evaluation."""

    method: str
    accuracy: float
    mrr: float
    recall_at_k: float
    avg_latency_ms: float
    total_samples: int
    correct: int


@dataclass
class ComparisonResults:
    """Aggregated comparison results."""

    methods: list[MethodResult] = field(default_factory=list)
    dataset: str = "ACEBench (ToolACE)"
    timestamp: str = ""


# ============================================================================
# Tool Selection Strategies (work with dynamic candidate tools)
# ============================================================================


class BaseSelector(ABC):
    """Base class for tool selectors."""

    name: str = "base"

    @abstractmethod
    def select(self, query: str, candidate_tools: list[str], top_k: int = 5) -> list[str]:
        """Select top-k tools for a query."""
        pass

    def setup(self) -> None:
        """Setup resources (optional)."""
        pass

    def teardown(self) -> None:
        """Cleanup resources (optional)."""
        pass


class KeywordSelector(BaseSelector):
    """BM25-based keyword matching selector."""

    name = "Keyword (BM25)"

    def __init__(self):
        self._bm25 = None

    def select(self, query: str, candidate_tools: list[str], top_k: int = 5) -> list[str]:
        """Select tools using BM25 keyword matching."""
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            # Fallback to simple keyword matching
            return self._simple_keyword_match(query, candidate_tools, top_k)

        # Tokenize tools and query
        tokenized_tools = [tool.lower().replace("_", " ").split() for tool in candidate_tools]
        tokenized_query = query.lower().split()

        # Build BM25 index
        bm25 = BM25Okapi(tokenized_tools)
        scores = bm25.get_scores(tokenized_query)

        # Get top-k
        scored_tools = list(zip(candidate_tools, scores))
        scored_tools.sort(key=lambda x: x[1], reverse=True)

        return [tool for tool, _ in scored_tools[:top_k]]

    def _simple_keyword_match(
        self, query: str, candidate_tools: list[str], top_k: int
    ) -> list[str]:
        """Simple keyword matching fallback."""
        query_words = set(query.lower().split())
        scores = []
        for tool in candidate_tools:
            tool_words = set(tool.lower().replace("_", " ").split())
            score = len(query_words & tool_words)
            scores.append((tool, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [tool for tool, _ in scores[:top_k]]


class EmbeddingSelector(BaseSelector):
    """Embedding-based semantic similarity selector."""

    name = "Embedding"

    def __init__(self):
        self._embedder = None

    def setup(self) -> None:
        """Load embedding model."""
        try:
            from sage.common.components.sage_embedding import (
                EmbeddingFactory,
                adapt_embedding_client,
            )

            raw_embedder = EmbeddingFactory.create("hf", model="BAAI/bge-small-zh-v1.5")
            self._embedder = adapt_embedding_client(raw_embedder)
            logger.info("Embedding model loaded: BAAI/bge-small-zh-v1.5")
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}")
            self._embedder = None

    def select(self, query: str, candidate_tools: list[str], top_k: int = 5) -> list[str]:
        """Select tools using embedding similarity."""
        if self._embedder is None:
            # Fallback to keyword
            return KeywordSelector().select(query, candidate_tools, top_k)

        import numpy as np

        # Embed query and tools
        all_texts = [query] + candidate_tools
        embeddings = self._embedder.embed(all_texts)

        query_emb = np.array(embeddings[0])
        tool_embs = np.array(embeddings[1:])

        # Compute cosine similarity
        query_norm = query_emb / (np.linalg.norm(query_emb) + 1e-8)
        tool_norms = tool_embs / (np.linalg.norm(tool_embs, axis=1, keepdims=True) + 1e-8)
        scores = np.dot(tool_norms, query_norm)

        # Get top-k
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [candidate_tools[i] for i in top_indices]


class HybridSelector(BaseSelector):
    """Hybrid selector combining keyword and embedding."""

    name = "Hybrid"

    def __init__(self):
        self._keyword = KeywordSelector()
        self._embedding = EmbeddingSelector()

    def setup(self) -> None:
        self._embedding.setup()

    def select(self, query: str, candidate_tools: list[str], top_k: int = 5) -> list[str]:
        """Select tools using hybrid approach."""
        # Get keyword scores
        keyword_results = self._keyword.select(query, candidate_tools, top_k=len(candidate_tools))
        keyword_scores = {tool: len(candidate_tools) - i for i, tool in enumerate(keyword_results)}

        # Get embedding scores
        if self._embedding._embedder is not None:
            emb_results = self._embedding.select(query, candidate_tools, top_k=len(candidate_tools))
            emb_scores = {tool: len(candidate_tools) - i for i, tool in enumerate(emb_results)}
        else:
            emb_scores = keyword_scores

        # Combine scores (weighted average)
        combined_scores = {}
        for tool in candidate_tools:
            kw_score = keyword_scores.get(tool, 0)
            emb_score = emb_scores.get(tool, 0)
            combined_scores[tool] = 0.4 * kw_score + 0.6 * emb_score

        # Sort and return top-k
        sorted_tools = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        return [tool for tool, _ in sorted_tools[:top_k]]


class LLMSelector(BaseSelector):
    """LLM-based direct prompting selector using UnifiedInferenceClient."""

    name = "LLM Direct"

    def __init__(self, use_embedded: bool = False, model_id: str | None = None):
        self.use_embedded = use_embedded
        self.model_id = model_id
        self._client = None

    def setup(self) -> None:
        """Setup LLM client using UnifiedInferenceClient."""
        from sage.common.components.sage_llm import UnifiedInferenceClient

        logger.info("Setting up LLM client via UnifiedInferenceClient...")
        self._client = UnifiedInferenceClient.create_auto()
        self.model_id = getattr(self._client, "llm_model", self.model_id) or "auto"

    def teardown(self) -> None:
        """Cleanup LLM resources."""
        pass  # UnifiedInferenceClient handles cleanup internally

    def select(self, query: str, candidate_tools: list[str], top_k: int = 5) -> list[str]:
        """Select tools using LLM."""
        if self._client is None:
            return []

        # Build prompt
        tools_str = ", ".join(candidate_tools[:20])
        prompt = f"""You are an AI assistant that selects the most appropriate tools for user requests.

Available tools: {tools_str}

User request: {query}

Select the most relevant tool(s) for this request. Respond with ONLY the tool name(s), one per line.
If multiple tools are needed, list them in order of relevance.

Selected tool(s):"""

        # Generate response - UnifiedInferenceClient.chat() returns string directly
        response = self._client.chat([{"role": "user", "content": prompt}])

        # Parse response
        return self._parse_response(response, candidate_tools, top_k)

    def _parse_response(self, response: str, candidate_tools: list[str], top_k: int) -> list[str]:
        """Parse tool names from response."""
        if not response:
            return []

        response = response.strip().lower()
        candidate_lower = {t.lower(): t for t in candidate_tools}

        predicted = []
        for line in response.split("\n"):
            line = line.strip().strip("-").strip("*").strip()
            if not line:
                continue
            for cand_lower, cand_orig in candidate_lower.items():
                if cand_lower in line or line in cand_lower:
                    if cand_orig not in predicted:
                        predicted.append(cand_orig)
                    break

        return predicted[:top_k]


# ============================================================================
# Evaluation Logic
# ============================================================================


def compute_metrics(
    predictions: list[list[str]], references: list[list[str]], top_k: int = 5
) -> dict[str, float]:
    """Compute evaluation metrics."""
    correct = 0
    mrr_sum = 0.0
    recall_sum = 0.0

    for pred, ref in zip(predictions, references):
        # Top-K accuracy: any expected tool in predictions
        if any(t in pred[:top_k] for t in ref):
            correct += 1

        # MRR: reciprocal rank of first correct prediction
        for i, p in enumerate(pred[:top_k]):
            if p in ref:
                mrr_sum += 1.0 / (i + 1)
                break

        # Recall@K: how many reference tools are in predictions
        if ref:
            hits = sum(1 for t in ref if t in pred[:top_k])
            recall_sum += hits / len(ref)

    n = len(predictions)
    return {
        "accuracy": correct / n if n > 0 else 0,
        "mrr": mrr_sum / n if n > 0 else 0,
        "recall_at_k": recall_sum / n if n > 0 else 0,
    }


def run_method_evaluation(
    selector: BaseSelector,
    samples: list[dict],
    top_k: int = 5,
) -> MethodResult:
    """Run evaluation for a single method."""
    predictions = []
    references = []
    latencies = []

    for sample in samples:
        query = sample["instruction"]
        candidate_tools = sample.get("candidate_tools", [])
        ground_truth = sample.get("ground_truth", {})

        if isinstance(ground_truth, dict):
            expected = ground_truth.get("top_k", [])
        else:
            expected = ground_truth

        # Time the selection
        start = time.perf_counter()
        try:
            pred = selector.select(query, candidate_tools, top_k=top_k)
        except Exception as e:
            logger.warning(f"Selection failed: {e}")
            pred = []
        latency = (time.perf_counter() - start) * 1000

        predictions.append(pred)
        references.append(expected)
        latencies.append(latency)

    # Compute metrics
    metrics = compute_metrics(predictions, references, top_k)

    return MethodResult(
        method=selector.name,
        accuracy=metrics["accuracy"],
        mrr=metrics["mrr"],
        recall_at_k=metrics["recall_at_k"],
        avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
        total_samples=len(samples),
        correct=int(metrics["accuracy"] * len(samples)),
    )


def run_comparison(
    samples: list[dict],
    use_embedded: bool = False,
    model_id: str | None = None,
    top_k: int = 5,
) -> ComparisonResults:
    """Run comparison across all methods."""
    results = ComparisonResults(timestamp=time.strftime("%Y-%m-%d %H:%M:%S"))

    methods: list[BaseSelector] = [
        KeywordSelector(),
        EmbeddingSelector(),
        HybridSelector(),
        LLMSelector(use_embedded=use_embedded, model_id=model_id),
    ]

    for selector in methods:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Testing: {selector.name}")
        logger.info(f"{'=' * 60}")

        try:
            selector.setup()
            result = run_method_evaluation(selector, samples, top_k)
            results.methods.append(result)

            logger.info(
                f"  Accuracy: {result.accuracy * 100:.1f}% "
                f"({result.correct}/{result.total_samples})"
            )
            logger.info(f"  MRR: {result.mrr * 100:.1f}%")
            logger.info(f"  Recall@{top_k}: {result.recall_at_k * 100:.1f}%")
            logger.info(f"  Avg Latency: {result.avg_latency_ms:.1f}ms")

        except Exception as e:
            logger.error(f"  Failed: {e}")
            import traceback

            traceback.print_exc()
        finally:
            selector.teardown()

    return results


def main():
    parser = argparse.ArgumentParser(description="ACEBench Multi-Method Comparison")
    parser.add_argument("--samples", type=int, default=100, help="Number of samples to evaluate")
    parser.add_argument(
        "--use-embedded",
        action="store_true",
        help="Use embedded VLLMService (requires GPU)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model ID for LLM selector",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-K for evaluation",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for results JSON",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="train",
        help="Dataset split to use",
    )

    args = parser.parse_args()

    # Load samples
    from sage.benchmark.benchmark_agent.acebench_loader import load_acebench_samples

    logger.info(f"Loading {args.samples} samples from ToolACE...")
    samples = load_acebench_samples(max_samples=args.samples, split=args.split)

    if not samples:
        logger.error("No samples loaded. Check dataset availability.")
        return 1

    logger.info(f"Loaded {len(samples)} samples")

    # Run comparison
    results = run_comparison(
        samples,
        use_embedded=args.use_embedded,
        model_id=args.model,
        top_k=args.top_k,
    )

    # Print summary
    print("\n" + "=" * 70)
    print("ACEBench Tool Selection Comparison Summary")
    print("=" * 70)
    print(f"Dataset: {results.dataset}")
    print(f"Samples: {len(samples)}")
    print(f"Top-K: {args.top_k}")
    print(f"Timestamp: {results.timestamp}")
    print("-" * 70)
    print(f"{'Method':<20} {'Accuracy':>10} {'MRR':>10} {'Recall@K':>10} {'Latency':>10}")
    print("-" * 70)

    for r in results.methods:
        print(
            f"{r.method:<20} {r.accuracy * 100:>9.1f}% {r.mrr * 100:>9.1f}% "
            f"{r.recall_at_k * 100:>9.1f}% {r.avg_latency_ms:>9.1f}ms"
        )

    print("=" * 70)

    # Find best method
    if results.methods:
        best = max(results.methods, key=lambda x: x.accuracy)
        print(f"\nBest Method: {best.method} ({best.accuracy * 100:.1f}% accuracy)")

    # Save results
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(".sage/benchmark/results/acebench_comparison.json")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "dataset": results.dataset,
        "timestamp": results.timestamp,
        "samples": len(samples),
        "top_k": args.top_k,
        "methods": [
            {
                "method": r.method,
                "accuracy": r.accuracy,
                "mrr": r.mrr,
                "recall_at_k": r.recall_at_k,
                "avg_latency_ms": r.avg_latency_ms,
                "correct": r.correct,
                "total": r.total_samples,
            }
            for r in results.methods
        ],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    logger.info(f"\nResults saved to {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
