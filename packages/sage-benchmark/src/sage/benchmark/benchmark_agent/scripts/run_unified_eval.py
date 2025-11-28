#!/usr/bin/env python3
"""
Unified Tool Selection Evaluation

.. note::
    This script is now a functional module. For CLI usage, prefer:

        sage-bench eval --dataset <dataset> --methods <methods>

    Direct script invocation is still supported for backward compatibility.

This script provides a unified evaluation framework that:
1. Works with any benchmark dataset (SAGE, ACEBench, APIBench, etc.)
2. Evaluates all tool selection methods with the same interface
3. Reports consistent metrics (Top-K Accuracy, MRR, Recall@K)

This addresses the problem of inconsistent evaluation across benchmarks,
following SOTA practices from Gorilla, ToolACE, and other papers.

CLI Usage (Recommended):
    sage-bench eval --dataset sage --samples 100
    sage-bench eval --dataset all --methods keyword,embedding,gorilla
    sage-bench list datasets

Legacy Usage (Still Supported):
    python run_unified_eval.py --dataset sage --samples 100
    python run_unified_eval.py --dataset acebench --samples 100
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
# Lightweight Selector Adapters (Gorilla, DFSDT)
# =============================================================================
# These adapters are "lightweight" - they do NOT preload any tool library.
# Instead, they dynamically process the candidate_tools provided in each sample.
# This follows SOTA practice (BFCL) where each sample includes its own tools.


class GorillaSelectorAdapter(BaseSelectorAdapter):
    """
    Lightweight Gorilla-style selector: Retrieval + LLM reranking.

    From the Gorilla paper (Berkeley): combines document retrieval
    with LLM-based selection for better API call accuracy.

    Unlike the full GorillaSelector which preloads 1200+ SAGE tools,
    this adapter dynamically builds an index for each sample's candidate_tools.
    This enables cross-dataset evaluation (SAGE, ACEBench, etc.).
    """

    def __init__(self, use_embedded: bool = False, model_id: Optional[str] = None):
        self._embedding_client = None
        self._llm_client = None
        self._use_embedded = use_embedded
        self._model_id = model_id

    @property
    def name(self) -> str:
        return "gorilla"

    def _init_clients(self):
        """Lazy initialization of embedding and LLM clients."""
        if self._embedding_client is None:
            try:
                from sage.common.components.sage_embedding import (
                    EmbeddingClientAdapter,
                    EmbeddingFactory,
                )

                # Use local HuggingFace model for embedding
                raw_embedder = EmbeddingFactory.create("hf", model="BAAI/bge-small-zh-v1.5")
                self._embedding_client = EmbeddingClientAdapter(raw_embedder)
            except Exception as e:
                logger.warning(f"Failed to create embedding client: {e}")

        if self._llm_client is None:
            try:
                from sage.common.components.sage_llm import UnifiedInferenceClient

                self._llm_client = UnifiedInferenceClient.create_auto()
            except Exception as e:
                logger.warning(f"Failed to create LLM client: {e}")

    def select(
        self,
        query: str,
        candidate_tools: list[Tool],
        top_k: int = 5,
    ) -> SelectionResult:
        self._init_clients()

        if not candidate_tools:
            return SelectionResult(tool_ids=[])

        try:
            import numpy as np

            # Stage 1: Embedding retrieval on sample's candidate_tools
            tool_texts = [f"{t.name}: {t.description}" for t in candidate_tools]
            tool_ids = [t.id for t in candidate_tools]

            # Embed query and tools
            all_texts = [query] + tool_texts
            embeddings = self._embedding_client.embed(all_texts)

            query_emb = np.asarray(embeddings[0])
            tool_embs = np.asarray(embeddings[1:])

            # Compute cosine similarity
            query_norm = query_emb / (np.linalg.norm(query_emb) + 1e-8)
            tool_norms = tool_embs / (np.linalg.norm(tool_embs, axis=1, keepdims=True) + 1e-8)
            scores = np.dot(tool_norms, query_norm)

            # Get top candidates for LLM reranking
            retrieve_k = min(15, len(candidate_tools))
            top_indices = np.argsort(scores)[::-1][:retrieve_k]
            retrieved_tools = [candidate_tools[i] for i in top_indices]

            # Stage 2: LLM reranking (if available)
            if self._llm_client is not None and len(retrieved_tools) > 0:
                selected_ids = self._llm_rerank(query, retrieved_tools, top_k)
                if selected_ids:
                    return SelectionResult(tool_ids=selected_ids)

            # Fallback to embedding-only results
            result_ids = [tool_ids[i] for i in top_indices[:top_k]]
            result_scores = [float(scores[i]) for i in top_indices[:top_k]]
            return SelectionResult(tool_ids=result_ids, scores=result_scores)

        except Exception as e:
            logger.warning(f"Gorilla selector failed: {e}")
            return SelectionResult(tool_ids=[])

    def _llm_rerank(self, query: str, tools: list[Tool], top_k: int) -> list[str]:
        """Use LLM to rerank retrieved tools."""
        tools_text = "\n".join(
            f"{i + 1}. **{t.name}** (ID: `{t.id}`)\n   Description: {t.description}"
            for i, t in enumerate(tools)
        )

        prompt = f"""You are an expert API selector. Given a user task and a list of available APIs/tools,
select the {top_k} most relevant tools that can help complete the task.

## User Task
{query}

## Available Tools
{tools_text}

## Instructions
1. Analyze the user's task requirements carefully
2. Consider which tools have the capabilities to fulfill the requirements
3. Select exactly {top_k} tools, ordered by relevance (most relevant first)
4. Return ONLY a JSON array of tool IDs, no explanation needed

## Output Format
Return a JSON array of tool IDs:
["tool_id_1", "tool_id_2", ...]

## Your Selection (JSON array only):"""

        try:
            response = self._llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )

            # Parse JSON response
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
                response = response.strip()

            import json as json_module

            selected = json_module.loads(response)
            if isinstance(selected, list):
                valid_ids = {t.id for t in tools}
                return [tid for tid in selected if tid in valid_ids]
        except Exception as e:
            logger.debug(f"LLM reranking failed: {e}")

        return []


class DFSDTSelectorAdapter(BaseSelectorAdapter):
    """
    Lightweight DFSDT (Depth-First Search Decision Tree) selector.

    Tree-search based tool selection that uses LLM scoring.

    Unlike the full DFSDTSelector which preloads 1200+ SAGE tools,
    this adapter dynamically scores the candidate_tools in each sample.
    This enables cross-dataset evaluation (SAGE, ACEBench, etc.).
    """

    def __init__(self, use_embedded: bool = False, model_id: Optional[str] = None):
        self._llm_client = None
        self._use_embedded = use_embedded
        self._model_id = model_id
        self._score_threshold = 0.3

    @property
    def name(self) -> str:
        return "dfsdt"

    def _init_client(self):
        """Lazy initialization of LLM client."""
        if self._llm_client is None:
            try:
                from sage.common.components.sage_llm import UnifiedInferenceClient

                self._llm_client = UnifiedInferenceClient.create_auto()
            except Exception as e:
                logger.warning(f"Failed to create LLM client: {e}")

    def select(
        self,
        query: str,
        candidate_tools: list[Tool],
        top_k: int = 5,
    ) -> SelectionResult:
        self._init_client()

        if not candidate_tools:
            return SelectionResult(tool_ids=[])

        try:
            # Score each candidate tool using LLM
            scored_tools = []
            for tool in candidate_tools:
                score = self._score_tool(query, tool)
                if score >= self._score_threshold:
                    scored_tools.append((tool.id, score))

            # Sort by score
            scored_tools.sort(key=lambda x: x[1], reverse=True)

            # Return top-k
            result_ids = [t[0] for t in scored_tools[:top_k]]
            result_scores = [t[1] for t in scored_tools[:top_k]]

            return SelectionResult(tool_ids=result_ids, scores=result_scores)

        except Exception as e:
            logger.warning(f"DFSDT selector failed: {e}")
            return SelectionResult(tool_ids=[])

    def _score_tool(self, query: str, tool: Tool) -> float:
        """Score a single tool's relevance to the query."""
        if self._llm_client is None:
            return self._fallback_score(query, tool)

        prompt = f"""You are a tool selection expert. Given a user query and a candidate tool,
evaluate how relevant the tool is for completing the query.

User Query: {query}

Candidate Tool:
- Name: {tool.name}
- Description: {tool.description}

Rate the relevance of this tool for the given query on a scale of 0 to 10, where:
- 0-2: Not relevant at all
- 3-4: Slightly relevant, might be useful indirectly
- 5-6: Moderately relevant, could help with part of the task
- 7-8: Highly relevant, directly addresses the query
- 9-10: Perfect match, exactly what's needed

Provide your rating as a single number. Only output the number, nothing else.

Rating:"""

        try:
            response = self._llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            # Parse score
            import re

            numbers = re.findall(r"(\d+(?:\.\d+)?)", response.strip())
            if numbers:
                score = float(numbers[0])
                return min(max(score, 0.0), 10.0) / 10.0  # Normalize to 0-1
        except Exception as e:
            logger.debug(f"LLM scoring failed for {tool.id}: {e}")

        return self._fallback_score(query, tool)

    def _fallback_score(self, query: str, tool: Tool) -> float:
        """Fallback scoring using keyword matching."""
        query_lower = query.lower()
        tool_text = f"{tool.name} {tool.description}".lower()

        query_words = set(query_lower.split())
        tool_words = set(tool_text.split())

        if not query_words or not tool_words:
            return 0.0

        overlap = len(query_words & tool_words)
        return min(overlap / len(query_words), 1.0)


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
        from sage.benchmark.benchmark_agent.acebench_loader import (
            ToolACELoader,
        )

        loader = ToolACELoader(
            max_samples=max_samples or 100,
            cache_dir=cache_dir,
        )

        samples = []
        for ace_sample in loader.load():
            # Convert ACEBenchSample to dict, then to ToolSelectionSample
            sage_format = ace_sample.to_sage_format()
            sample = ToolSelectionSample.from_acebench(sage_format)
            samples.append(sample)

        logger.info(f"Loaded {len(samples)} ACEBench samples")
        return samples

    except Exception as e:
        logger.warning(f"Failed to load ACEBench: {e}")
        import traceback

        traceback.print_exc()
        return []


def load_external_benchmark(
    benchmark_name: str,
    max_samples: Optional[int] = None,
    task_type: str = "tool_selection",
) -> list[ToolSelectionSample]:
    """
    Load external benchmark from converted JSONL files.

    Supports: bfcl, toolbench, apibank, toolalpaca, taskbench, metatool

    Args:
        benchmark_name: Name of the benchmark (e.g., 'apibank', 'toolalpaca')
        max_samples: Maximum samples to load
        task_type: Task type filter (default: tool_selection)

    Returns:
        List of ToolSelectionSample
    """
    try:
        from sage.data.sources.agent_benchmark.external_benchmarks.loader import (
            ExternalBenchmarkLoader,
        )

        loader = ExternalBenchmarkLoader(benchmarks=[benchmark_name])
        external_samples = loader.get_samples(
            task_type=task_type,
            split="test",
            limit=max_samples,
        )

        if not external_samples:
            logger.warning(
                f"No samples found for {benchmark_name}. "
                f"Run 'python download_{benchmark_name}.py' to download data."
            )
            return []

        # Convert ExternalSample to ToolSelectionSample
        samples = []
        for ext_sample in external_samples:
            # Parse context for tool descriptions
            tool_descriptions = {}
            if ext_sample.context:
                try:
                    ctx = (
                        json.loads(ext_sample.context)
                        if isinstance(ext_sample.context, str)
                        else ext_sample.context
                    )
                    # Extract tool descriptions from nl_documentation
                    if "nl_documentation" in ctx:
                        nl_doc = ctx["nl_documentation"]
                        # Parse tool documentation (format: "tool_name: description\n...")
                        for line in nl_doc.split("\n"):
                            if ":" in line:
                                tool_name = line.split(":")[0].strip()
                                tool_desc = line.strip()
                                tool_descriptions[tool_name] = tool_desc
                    # Fallback to api_description
                    if "api_description" in ctx:
                        api_desc = ctx.get("api_description", "")
                        api_name = ctx.get("api_name", "")
                        # Apply to all tools if no specific description
                        for tool_id in ext_sample.candidate_tools or []:
                            if tool_id not in tool_descriptions:
                                tool_descriptions[tool_id] = f"{api_name}: {api_desc}"
                except (json.JSONDecodeError, TypeError):
                    pass

            # Build Tool objects from candidate_tools with descriptions
            candidate_tools = []
            for tool_id in ext_sample.candidate_tools or []:
                desc = tool_descriptions.get(tool_id, f"Tool: {tool_id}")
                candidate_tools.append(
                    Tool(
                        id=tool_id,
                        name=tool_id,
                        description=desc,
                    )
                )

            # Get ground truth - handle multiple formats
            gt = ext_sample.ground_truth
            ground_truth = []
            if isinstance(gt, dict):
                # Format 1: {"top_k": ["tool1", "tool2"]}
                if "top_k" in gt:
                    ground_truth = gt["top_k"]
                # Format 2: {"tool_calls": [{"tool": "tool_name"}]}
                elif "tool_calls" in gt:
                    ground_truth = [tc.get("tool", tc.get("name", "")) for tc in gt["tool_calls"]]
                # Format 3: {"selected_tools": ["tool1"]}
                elif "selected_tools" in gt:
                    ground_truth = gt["selected_tools"]
            elif isinstance(gt, list):
                ground_truth = gt

            sample = ToolSelectionSample(
                sample_id=ext_sample.sample_id,
                instruction=ext_sample.instruction,
                candidate_tools=candidate_tools,
                ground_truth=ground_truth,
                context={"source": benchmark_name, **ext_sample.metadata},
            )
            samples.append(sample)

        logger.info(f"Loaded {len(samples)} {benchmark_name} samples")
        return samples

    except ImportError as e:
        logger.warning(f"ExternalBenchmarkLoader not available: {e}")
        return []
    except Exception as e:
        logger.warning(f"Failed to load {benchmark_name}: {e}")
        import traceback

        traceback.print_exc()
        return []


# Available external benchmarks
EXTERNAL_BENCHMARKS = {
    "apibank": "API-Bank (Microsoft/Alibaba)",
    "toolalpaca": "ToolAlpaca (Microsoft)",
    "bfcl": "BFCL (Berkeley Function Calling Leaderboard)",
    "toolbench": "ToolBench (Tsinghua/OpenBMB)",
    "taskbench": "TaskBench (PKU)",
    "metatool": "MetaTool (Tsinghua)",
}


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
        dataset: 'sage', 'acebench', 'apibank', 'toolalpaca', 'bfcl', 'toolbench', or 'all'
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

    # SAGE dataset
    if dataset in ("sage", "all"):
        sage_samples = load_sage_dataset(max_samples=max_samples)
        if sage_samples:
            datasets_to_eval.append(("SAGE", sage_samples))

    # ACEBench (from HuggingFace)
    if dataset in ("acebench", "all"):
        acebench_samples = load_acebench_dataset(max_samples=max_samples)
        if acebench_samples:
            datasets_to_eval.append(("ACEBench", acebench_samples))

    # External benchmarks (from converted JSONL)
    external_to_load = []
    if dataset == "all":
        external_to_load = list(EXTERNAL_BENCHMARKS.keys())
    elif dataset in EXTERNAL_BENCHMARKS:
        external_to_load = [dataset]

    for ext_name in external_to_load:
        ext_samples = load_external_benchmark(ext_name, max_samples=max_samples)
        if ext_samples:
            display_name = ext_name.upper()
            datasets_to_eval.append((display_name, ext_samples))

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
    # Build dataset choices dynamically
    dataset_choices = ["sage", "acebench", "all"] + list(EXTERNAL_BENCHMARKS.keys())

    parser = argparse.ArgumentParser(
        description="Unified Tool Selection Evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Evaluate all methods on SAGE
    python run_unified_eval.py --dataset sage

    # Evaluate on ACEBench
    python run_unified_eval.py --dataset acebench --methods keyword,embedding,llm_direct

    # Evaluate on API-Bank
    python run_unified_eval.py --dataset apibank --samples 25

    # Compare across ALL datasets (SAGE + ACEBench + external)
    python run_unified_eval.py --dataset all --samples 50

    # Use embedded LLM
    python run_unified_eval.py --dataset sage --use-embedded --model Qwen/Qwen2.5-0.5B-Instruct

    # List available datasets
    python run_unified_eval.py --list-datasets

Available Datasets:
    sage        - SAGE-Bench (our synthetic dataset, 1200 tools)
    acebench    - ToolACE from HuggingFace
    apibank     - API-Bank (Microsoft/Alibaba)
    toolalpaca  - ToolAlpaca (Microsoft)
    bfcl        - Berkeley Function Calling Leaderboard
    toolbench   - ToolBench (Tsinghua/OpenBMB)
    taskbench   - TaskBench (PKU)
    metatool    - MetaTool (Tsinghua)
    all         - Evaluate on ALL available datasets
""",
    )
    parser.add_argument(
        "--dataset",
        choices=dataset_choices,
        default="sage",
        help="Dataset to evaluate on (see --list-datasets for details)",
    )
    parser.add_argument(
        "--list-datasets",
        action="store_true",
        help="List all available datasets and exit",
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

    # Handle --list-datasets
    if args.list_datasets:
        print("\n" + "=" * 70)
        print("Available Datasets for Tool Selection Evaluation")
        print("=" * 70)
        print(f"\n{'Dataset':<15} {'Description':<50} {'Status'}")
        print("-" * 70)
        print(f"{'sage':<15} {'SAGE-Bench (1200 synthetic tools)':<50} Built-in")
        print(f"{'acebench':<15} {'ToolACE from HuggingFace':<50} HuggingFace")
        for name, desc in EXTERNAL_BENCHMARKS.items():
            print(f"{name:<15} {desc:<50} External")
        print(f"{'all':<15} {'Evaluate on ALL available datasets':<50} -")
        print("\n" + "=" * 70)
        print("Note: External datasets require downloading first.")
        print("Run: python download_<dataset>.py  (e.g., python download_apibank.py)")
        print("=" * 70 + "\n")
        return

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

    # UnifiedInferenceClient handles cleanup internally


if __name__ == "__main__":
    main()
