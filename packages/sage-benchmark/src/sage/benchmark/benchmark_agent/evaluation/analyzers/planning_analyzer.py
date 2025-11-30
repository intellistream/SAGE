"""Planning analyzer for step-level alignment analysis."""

from collections import Counter, defaultdict
from typing import Any, Sequence


class PlanningAnalyzer:
    """
    Analyzer for task planning predictions.

    Provides breakdowns by:
    - Step-level correctness
    - Tool sequence alignment
    - Failure patterns
    """

    name = "planning"

    def analyze(
        self,
        predictions: Sequence[list[str]],
        references: Sequence[list[str]],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Analyze planning predictions.

        Args:
            predictions: List of predicted tool sequences
            references: List of reference tool sequences
            metadata: Additional context

        Returns:
            Dictionary with analysis results
        """
        # Step-level analysis
        step_correctness = []
        length_diffs = []
        failure_modes = defaultdict(int)

        exact_matches = 0
        prefix_matches = 0

        for pred, ref in zip(predictions, references):
            # Length analysis
            length_diffs.append(len(pred) - len(ref))

            # Exact match
            if pred == ref:
                exact_matches += 1
                step_correctness.append(1.0)
                failure_modes["perfect"] += 1
                prefix_matches += 1
                continue

            # Prefix match
            min_len = min(len(pred), len(ref))
            if min_len > 0 and pred[:min_len] == ref[:min_len]:
                prefix_matches += 1

            # Step-by-step correctness
            correct_steps = sum(1 for p, r in zip(pred, ref) if p == r)
            step_acc = correct_steps / len(ref) if len(ref) > 0 else 0.0
            step_correctness.append(step_acc)

            # Classify failure mode
            if len(pred) == 0:
                failure_modes["empty_plan"] += 1
            elif len(pred) < len(ref):
                failure_modes["too_short"] += 1
            elif len(pred) > len(ref):
                failure_modes["too_long"] += 1
            elif set(pred) == set(ref):
                failure_modes["wrong_order"] += 1
            else:
                failure_modes["wrong_tools"] += 1

        # Tool sequence statistics
        pred_lengths = [len(p) for p in predictions]
        ref_lengths = [len(r) for r in references]

        # Tool usage analysis
        tool_usage_pred = Counter()
        tool_usage_ref = Counter()
        for pred in predictions:
            tool_usage_pred.update(pred)
        for ref in references:
            tool_usage_ref.update(ref)

        return {
            "exact_match_rate": exact_matches / len(predictions) if predictions else 0.0,
            "prefix_match_rate": prefix_matches / len(predictions) if predictions else 0.0,
            "step_correctness": {
                "mean": sum(step_correctness) / len(step_correctness) if step_correctness else 0.0,
                "min": min(step_correctness) if step_correctness else 0.0,
                "max": max(step_correctness) if step_correctness else 0.0,
                "distribution": step_correctness,
            },
            "length_analysis": {
                "pred_avg": sum(pred_lengths) / len(pred_lengths) if pred_lengths else 0.0,
                "ref_avg": sum(ref_lengths) / len(ref_lengths) if ref_lengths else 0.0,
                "length_diff_mean": sum(length_diffs) / len(length_diffs) if length_diffs else 0.0,
                "length_diff_distribution": length_diffs,
            },
            "failure_modes": dict(failure_modes),
            "tool_usage": {
                "predicted_most_common": tool_usage_pred.most_common(10),
                "reference_most_common": tool_usage_ref.most_common(10),
            },
            "total_samples": len(predictions),
        }
