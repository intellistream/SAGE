#!/usr/bin/env python3
"""
ACEBench Tool Selection Evaluation

Runs tool selection evaluation on ToolACE benchmark using embedded LLM
or API-based LLM.

Usage:
    # Quick test with 10 samples
    python run_acebench_eval.py --samples 10

    # Full evaluation with embedded LLM
    python run_acebench_eval.py --samples 100 --use-embedded

    # Use specific model
    python run_acebench_eval.py --model "Qwen/Qwen2.5-1.5B-Instruct" --samples 50
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    """Single evaluation result."""

    sample_id: str
    instruction: str
    expected_tools: list[str]
    predicted_tools: list[str]
    correct: bool
    latency_ms: float


@dataclass
class EvalSummary:
    """Evaluation summary statistics."""

    total_samples: int
    correct: int
    accuracy: float
    avg_latency_ms: float
    model_id: str
    timestamp: str


class ACEBenchEvaluator:
    """Evaluator for ACEBench tool selection."""

    def __init__(
        self,
        use_embedded: bool = False,
        model_id: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        """
        Initialize evaluator.

        Args:
            use_embedded: Use embedded VLLMService instead of API
            model_id: Model ID (for embedded) or model name (for API)
            api_base: API base URL (for API mode)
        """
        self.use_embedded = use_embedded
        self.model_id = model_id
        self.api_base = api_base
        self._client: Any = None

    def setup(self) -> None:
        """Initialize LLM client."""
        from sage.common.components.sage_llm import (
            IntelligentLLMClient,
            check_vllm_available,
        )

        if self.use_embedded:
            if not check_vllm_available():
                raise RuntimeError(
                    "Embedded LLM requires vLLM and GPU. Install vLLM or use API mode."
                )
            model = self.model_id or IntelligentLLMClient.DEFAULT_EMBEDDED_MODEL
            logger.info(f"Setting up embedded LLM: {model}")
            self._client = IntelligentLLMClient.create_embedded(model_id=model)
            self.model_id = model
        else:
            logger.info("Setting up API-based LLM client...")
            self._client = IntelligentLLMClient.create_auto()
            self.model_id = self._client.model_name

    def teardown(self) -> None:
        """Cleanup resources."""
        if self.use_embedded:
            from sage.common.components.sage_llm import IntelligentLLMClient

            IntelligentLLMClient.clear_embedded_instances()

    def evaluate_sample(self, sample: dict[str, Any]) -> EvalResult:
        """
        Evaluate a single sample.

        Args:
            sample: Sample in SAGE format with instruction and ground_truth

        Returns:
            EvalResult with prediction and correctness
        """
        instruction = sample["instruction"]
        expected_tools = sample["ground_truth"]["top_k"]
        context = sample.get("context", "")
        candidate_tools = sample.get("candidate_tools", [])

        # Build prompt for tool selection
        prompt = self._build_prompt(instruction, context, candidate_tools)

        # Generate response
        start_time = time.perf_counter()
        try:
            response = self._generate(prompt)
        except Exception as e:
            logger.warning(f"Generation failed for {sample['sample_id']}: {e}")
            response = ""
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Parse predicted tools from response
        predicted_tools = self._parse_response(response, candidate_tools)

        # Check correctness (any expected tool in predictions)
        correct = any(t in predicted_tools for t in expected_tools) if expected_tools else True

        return EvalResult(
            sample_id=sample["sample_id"],
            instruction=instruction,
            expected_tools=expected_tools,
            predicted_tools=predicted_tools,
            correct=correct,
            latency_ms=latency_ms,
        )

    def _build_prompt(
        self,
        instruction: str,
        context: str,
        candidate_tools: list[str],
    ) -> str:
        """Build prompt for tool selection."""
        tools_str = ", ".join(candidate_tools[:20])  # Limit for prompt length

        prompt = f"""You are an AI assistant that selects the most appropriate tools for user requests.

Available tools: {tools_str}

User request: {instruction}

Select the most relevant tool(s) for this request. Respond with ONLY the tool name(s), one per line.
If multiple tools are needed, list them in order of relevance.

Selected tool(s):"""

        return prompt

    def _generate(self, prompt: str) -> str:
        """Generate response from LLM."""
        # IntelligentLLMClient provides unified chat interface
        return self._client.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
        )

    def _parse_response(self, response: str, candidate_tools: list[str]) -> list[str]:
        """Parse tool names from response."""
        if not response:
            return []

        # Normalize response
        response = response.strip().lower()
        candidate_lower = {t.lower(): t for t in candidate_tools}

        predicted = []
        for line in response.split("\n"):
            line = line.strip().strip("-").strip("*").strip()
            if not line:
                continue
            # Check if line matches any candidate
            for cand_lower, cand_orig in candidate_lower.items():
                if cand_lower in line or line in cand_lower:
                    if cand_orig not in predicted:
                        predicted.append(cand_orig)
                    break

        return predicted


def run_evaluation(
    samples: list[dict[str, Any]],
    evaluator: ACEBenchEvaluator,
    output_path: Optional[Path] = None,
) -> EvalSummary:
    """
    Run evaluation on samples.

    Args:
        samples: List of samples in SAGE format
        evaluator: ACEBenchEvaluator instance
        output_path: Optional path to save detailed results

    Returns:
        EvalSummary with statistics
    """
    results: list[EvalResult] = []
    correct_count = 0

    logger.info(f"Evaluating {len(samples)} samples...")

    for i, sample in enumerate(samples):
        result = evaluator.evaluate_sample(sample)
        results.append(result)

        if result.correct:
            correct_count += 1

        if (i + 1) % 10 == 0:
            acc = correct_count / (i + 1)
            logger.info(f"Progress: {i + 1}/{len(samples)} | Accuracy: {acc:.1%}")

    # Calculate summary
    accuracy = correct_count / len(samples) if samples else 0
    avg_latency = sum(r.latency_ms for r in results) / len(results) if results else 0

    summary = EvalSummary(
        total_samples=len(samples),
        correct=correct_count,
        accuracy=accuracy,
        avg_latency_ms=avg_latency,
        model_id=evaluator.model_id or "unknown",
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
    )

    # Save detailed results if requested
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_data = {
            "summary": {
                "total_samples": summary.total_samples,
                "correct": summary.correct,
                "accuracy": summary.accuracy,
                "avg_latency_ms": summary.avg_latency_ms,
                "model_id": summary.model_id,
                "timestamp": summary.timestamp,
            },
            "results": [
                {
                    "sample_id": r.sample_id,
                    "instruction": r.instruction[:200],
                    "expected_tools": r.expected_tools,
                    "predicted_tools": r.predicted_tools,
                    "correct": r.correct,
                    "latency_ms": r.latency_ms,
                }
                for r in results
            ],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to {output_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="ACEBench Tool Selection Evaluation")
    parser.add_argument("--samples", type=int, default=50, help="Number of samples to evaluate")
    parser.add_argument(
        "--use-embedded",
        action="store_true",
        help="Use embedded VLLMService (requires GPU)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model ID for embedded mode",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for detailed results",
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

    # Setup evaluator
    evaluator = ACEBenchEvaluator(
        use_embedded=args.use_embedded,
        model_id=args.model,
    )

    try:
        evaluator.setup()

        # Determine output path
        output_path = None
        if args.output:
            output_path = Path(args.output)
        else:
            # Default output path
            output_path = Path(".sage/benchmark/results/acebench_eval.json")

        # Run evaluation
        summary = run_evaluation(samples, evaluator, output_path)

        # Print summary
        print("\n" + "=" * 60)
        print("ACEBench Evaluation Summary")
        print("=" * 60)
        print(f"Model: {summary.model_id}")
        print(f"Samples: {summary.total_samples}")
        print(f"Correct: {summary.correct}")
        print(f"Accuracy: {summary.accuracy:.1%}")
        print(f"Avg Latency: {summary.avg_latency_ms:.1f}ms")
        print(f"Timestamp: {summary.timestamp}")
        print("=" * 60)

        return 0 if summary.accuracy > 0 else 1

    finally:
        evaluator.teardown()


if __name__ == "__main__":
    sys.exit(main())
