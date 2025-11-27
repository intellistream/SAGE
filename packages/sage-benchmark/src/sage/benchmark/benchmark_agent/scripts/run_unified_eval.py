#!/usr/bin/env python3
"""
Unified Tool Selection Evaluation

This script provides a unified evaluation framework that:
1. Works with any benchmark dataset (SAGE, ACEBench, APIBench, etc.)
2. Evaluates all tool selection methods with the same interface
3. Reports consistent metrics (Top-K Accuracy, MRR, Recall@K)

This addresses the problem of inconsistent evaluation across benchmarks,
following SOTA practices from Gorilla, ToolACE, and other papers.

Usage:
    # Evaluate on SAGE dataset
    python run_unified_eval.py --dataset sage --samples 100

    # Evaluate on ACEBench dataset
    python run_unified_eval.py --dataset acebench --samples 100

    # Evaluate specific methods
    python run_unified_eval.py --dataset sage --methods keyword,embedding,llm_direct

    # Use embedded LLM for llm_direct method
    python run_unified_eval.py --dataset sage --use-embedded

    # Compare all methods on all datasets
    python run_unified_eval.py --dataset all --samples 50
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sage.benchmark.benchmark_agent.evaluation.unified_tool_selection import (
    BaseSelectorAdapter,
    EmbeddingSelectorAdapter,
    EvaluationMetrics,
    HybridSelectorAdapter,
    KeywordSelectorAdapter,
    LLMDirectSelectorAdapter,
    SelectionResult,
    Tool,
    ToolSelectionSample,
    UnifiedToolSelectionEvaluator,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Additional Selector Adapters (Gorilla, DFSDT)
# =============================================================================


class GorillaSelectorAdapter(BaseSelectorAdapter):
    """
    Gorilla-style selector: Retrieval + LLM reranking.

    From the Gorilla paper (Berkeley): combines document retrieval
    with LLM-based selection for better API call accuracy.
    """

    def __init__(self, use_embedded: bool = False, model_id: Optional[str] = None):
        self._selector = None
        self._use_embedded = use_embedded
        self._model_id = model_id

    @property
    def name(self) -> str:
        return "gorilla"

    def select(
        self,
        query: str,
        candidate_tools: list[Tool],
        top_k: int = 5,
    ) -> SelectionResult:
        if self._selector is None:
            self._init_selector()

        from sage.libs.agentic.agents.action.tool_selection.schemas import (
            ToolSelectionQuery,
        )

        selector_query = ToolSelectionQuery(
            sample_id="eval",
            instruction=query,
            candidate_tools=[
                {"id": t.id, "name": t.name, "description": t.description} for t in candidate_tools
            ],
            context={},
        )

        try:
            results = self._selector.select(selector_query, top_k=top_k)
            tool_ids = [r.tool_id if hasattr(r, "tool_id") else str(r) for r in results]
            scores = [r.score if hasattr(r, "score") else 1.0 for r in results]
            return SelectionResult(tool_ids=tool_ids, scores=scores)
        except Exception as e:
            logger.warning(f"Gorilla selector failed: {e}")
            return SelectionResult(tool_ids=[])

    def _init_selector(self):
        from sage.libs.agentic.agents.action.tool_selection import SelectorRegistry

        registry = SelectorRegistry()
        self._selector = registry.create("gorilla")


class DFSDTSelectorAdapter(BaseSelectorAdapter):
    """
    DFSDT (Depth-First Search Decision Tree) selector.

    Tree-search based tool selection that explores tool combinations.
    """

    def __init__(self, use_embedded: bool = False, model_id: Optional[str] = None):
        self._selector = None
        self._use_embedded = use_embedded
        self._model_id = model_id

    @property
    def name(self) -> str:
        return "dfsdt"

    def select(
        self,
        query: str,
        candidate_tools: list[Tool],
        top_k: int = 5,
    ) -> SelectionResult:
        if self._selector is None:
            self._init_selector()

        from sage.libs.agentic.agents.action.tool_selection.schemas import (
            ToolSelectionQuery,
        )

        selector_query = ToolSelectionQuery(
            sample_id="eval",
            instruction=query,
            candidate_tools=[
                {"id": t.id, "name": t.name, "description": t.description} for t in candidate_tools
            ],
            context={},
        )

        try:
            results = self._selector.select(selector_query, top_k=top_k)
            tool_ids = [r.tool_id if hasattr(r, "tool_id") else str(r) for r in results]
            scores = [r.score if hasattr(r, "score") else 1.0 for r in results]
            return SelectionResult(tool_ids=tool_ids, scores=scores)
        except Exception as e:
            logger.warning(f"DFSDT selector failed: {e}")
            return SelectionResult(tool_ids=[])

    def _init_selector(self):
        from sage.libs.agentic.agents.action.tool_selection import SelectorRegistry

        registry = SelectorRegistry()
        self._selector = registry.create("dfsdt")


# =============================================================================
# Dataset Loaders
# =============================================================================


def load_sage_dataset(
    data_path: Optional[Path] = None, max_samples: Optional[int] = None
) -> list[ToolSelectionSample]:
    """Load SAGE tool selection dataset."""
    # Default path
    if data_path is None:
        data_path = (
            Path(__file__).parent.parent.parent.parent
            / "data"
            / "sources"
            / "agent_benchmark"
            / "splits"
            / "tool_selection.jsonl"
        )

    if not data_path.exists():
        logger.warning(f"SAGE data not found at {data_path}")
        return []

    samples = []
    with open(data_path) as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            # Filter to test split only
            if data.get("split") != "test":
                continue
            sample = ToolSelectionSample.from_sage(data)
            samples.append(sample)
            if max_samples and len(samples) >= max_samples:
                break

    logger.info(f"Loaded {len(samples)} SAGE samples")
    return samples


def load_acebench_dataset(
    max_samples: Optional[int] = None,
    cache_dir: Optional[Path] = None,
) -> list[ToolSelectionSample]:
    """Load ACEBench/ToolACE dataset from HuggingFace."""
    try:
        from sage.benchmark.benchmark_agent.data.acebench_loader import (
            ACEBenchLoader,
        )

        loader = ACEBenchLoader(cache_dir=cache_dir)
        raw_samples = loader.load_samples(max_samples=max_samples or 100)

        samples = []
        for raw in raw_samples:
            sample = ToolSelectionSample.from_acebench(raw)
            samples.append(sample)

        logger.info(f"Loaded {len(samples)} ACEBench samples")
        return samples

    except Exception as e:
        logger.warning(f"Failed to load ACEBench: {e}")
        return []


# =============================================================================
# Main Evaluation Logic
# =============================================================================


def create_evaluator(
    methods: list[str], use_embedded: bool = False, model_id: Optional[str] = None
) -> UnifiedToolSelectionEvaluator:
    """Create evaluator with specified methods."""
    evaluator = UnifiedToolSelectionEvaluator()

    method_map = {
        "keyword": lambda: KeywordSelectorAdapter(),
        "embedding": lambda: EmbeddingSelectorAdapter(),
        "hybrid": lambda: HybridSelectorAdapter(),
        "llm_direct": lambda: LLMDirectSelectorAdapter(
            use_embedded=use_embedded, model_id=model_id
        ),
        "gorilla": lambda: GorillaSelectorAdapter(use_embedded=use_embedded, model_id=model_id),
        "dfsdt": lambda: DFSDTSelectorAdapter(use_embedded=use_embedded, model_id=model_id),
    }

    for method in methods:
        if method in method_map:
            try:
                evaluator.register_selector(method, method_map[method]())
                logger.info(f"Registered selector: {method}")
            except Exception as e:
                logger.warning(f"Failed to create selector '{method}': {e}")
        else:
            logger.warning(f"Unknown method: {method}")

    return evaluator


def run_evaluation(
    dataset: str,
    methods: list[str],
    max_samples: int,
    use_embedded: bool,
    model_id: Optional[str],
    output_dir: Path,
    top_k: int = 5,
) -> dict[str, dict[str, EvaluationMetrics]]:
    """
    Run unified evaluation.

    Args:
        dataset: 'sage', 'acebench', or 'all'
        methods: List of method names
        max_samples: Max samples per dataset
        use_embedded: Use embedded LLM
        model_id: Model ID for embedded LLM
        output_dir: Output directory for results
        top_k: Top-K value

    Returns:
        Dict[dataset_name, Dict[method_name, EvaluationMetrics]]
    """
    all_results = {}

    # Load datasets
    datasets_to_eval = []
    if dataset in ("sage", "all"):
        sage_samples = load_sage_dataset(max_samples=max_samples)
        if sage_samples:
            datasets_to_eval.append(("SAGE", sage_samples))

    if dataset in ("acebench", "all"):
        acebench_samples = load_acebench_dataset(max_samples=max_samples)
        if acebench_samples:
            datasets_to_eval.append(("ACEBench", acebench_samples))

    if not datasets_to_eval:
        logger.error("No datasets loaded")
        return {}

    # Create evaluator
    evaluator = create_evaluator(methods, use_embedded, model_id)

    # Evaluate on each dataset
    for dataset_name, samples in datasets_to_eval:
        print(f"\n{'=' * 70}")
        print(f"Evaluating on {dataset_name} ({len(samples)} samples)")
        print(f"{'=' * 70}")

        results = evaluator.evaluate(samples, top_k=top_k)
        all_results[dataset_name] = results
        evaluator.print_results(results)

    return all_results


def save_results(
    results: dict[str, dict[str, EvaluationMetrics]],
    output_dir: Path,
):
    """Save results to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert to serializable format
    serializable = {}
    for dataset_name, method_results in results.items():
        serializable[dataset_name] = {}
        for method_name, metrics in method_results.items():
            serializable[dataset_name][method_name] = {
                "top_1_accuracy": metrics.top_1_accuracy,
                "top_3_accuracy": metrics.top_3_accuracy,
                "top_5_accuracy": metrics.top_5_accuracy,
                "mrr": metrics.mrr,
                "recall_at_k": metrics.recall_at_k,
                "precision_at_k": metrics.precision_at_k,
                "total_samples": metrics.total_samples,
            }

    # Add metadata
    output = {
        "timestamp": datetime.now().isoformat(),
        "results": serializable,
    }

    output_file = output_dir / "unified_eval_results.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(f"Results saved to {output_file}")


def print_comparison_table(results: dict[str, dict[str, EvaluationMetrics]]):
    """Print a comparison table across datasets."""
    if len(results) <= 1:
        return

    print("\n" + "=" * 90)
    print("Cross-Dataset Comparison")
    print("=" * 90)

    # Get all methods
    all_methods = set()
    for method_results in results.values():
        all_methods.update(method_results.keys())

    # Header
    datasets = list(results.keys())
    header = f"{'Method':<15}"
    for ds in datasets:
        header += f" | {ds + ' Top-5':>15}"
    print(header)
    print("-" * 90)

    # Rows
    for method in sorted(all_methods):
        row = f"{method:<15}"
        for ds in datasets:
            if method in results.get(ds, {}):
                acc = results[ds][method].top_5_accuracy * 100
                row += f" | {acc:>14.1f}%"
            else:
                row += f" | {'N/A':>15}"
        print(row)

    print("=" * 90)


def main():
    parser = argparse.ArgumentParser(
        description="Unified Tool Selection Evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Evaluate all methods on SAGE
    python run_unified_eval.py --dataset sage

    # Evaluate specific methods on ACEBench
    python run_unified_eval.py --dataset acebench --methods keyword,embedding,llm_direct

    # Compare across datasets
    python run_unified_eval.py --dataset all --samples 50

    # Use embedded LLM
    python run_unified_eval.py --dataset sage --use-embedded --model Qwen/Qwen2.5-0.5B-Instruct
""",
    )
    parser.add_argument(
        "--dataset",
        choices=["sage", "acebench", "all"],
        default="sage",
        help="Dataset to evaluate on",
    )
    parser.add_argument(
        "--methods",
        type=str,
        default="keyword,embedding,hybrid,llm_direct",
        help="Comma-separated list of methods to evaluate",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=100,
        help="Max samples per dataset",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-K value for selection",
    )
    parser.add_argument(
        "--use-embedded",
        action="store_true",
        help="Use embedded vLLM for LLM-based methods",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model ID for embedded LLM",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for results",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse methods
    methods = [m.strip() for m in args.methods.split(",")]

    # Output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = (
            Path(__file__).parent.parent.parent.parent.parent.parent.parent.parent
            / ".sage"
            / "benchmark"
            / "results"
        )

    print("\n" + "=" * 70)
    print("Unified Tool Selection Evaluation")
    print("=" * 70)
    print(f"Dataset(s): {args.dataset}")
    print(f"Methods: {', '.join(methods)}")
    print(f"Max samples: {args.samples}")
    print(f"Top-K: {args.top_k}")
    print(f"Use embedded LLM: {args.use_embedded}")
    if args.model:
        print(f"Model: {args.model}")
    print("=" * 70)

    # Run evaluation
    results = run_evaluation(
        dataset=args.dataset,
        methods=methods,
        max_samples=args.samples,
        use_embedded=args.use_embedded,
        model_id=args.model,
        output_dir=output_dir,
        top_k=args.top_k,
    )

    if results:
        # Print cross-dataset comparison
        print_comparison_table(results)

        # Save results
        save_results(results, output_dir)

    # Cleanup embedded LLM if used
    if args.use_embedded:
        try:
            from sage.common.components.sage_llm import IntelligentLLMClient

            IntelligentLLMClient.clear_embedded_instances()
        except Exception:
            pass


if __name__ == "__main__":
    main()
