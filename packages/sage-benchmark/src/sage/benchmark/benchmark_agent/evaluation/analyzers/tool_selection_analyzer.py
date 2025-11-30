"""Tool selection analyzer for detailed error analysis."""

from collections import Counter, defaultdict
from typing import Any, Sequence


class ToolSelectionAnalyzer:
    """
    Analyzer for tool selection predictions.

    Provides breakdowns by:
    - Category coverage
    - Error patterns (wrong tool categories)
    - Tool popularity in predictions vs references
    """

    name = "tool_selection"

    def __init__(self, tools_metadata: dict[str, Any] = None):
        """
        Initialize analyzer.

        Args:
            tools_metadata: Optional metadata about tools (categories, etc.)
        """
        self.tools_metadata = tools_metadata or {}

    def analyze(
        self,
        predictions: Sequence[list[str]],
        references: Sequence[list[str]],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Analyze tool selection predictions.

        Args:
            predictions: List of predicted tool ID lists
            references: List of reference tool ID lists
            metadata: Additional context

        Returns:
            Dictionary with analysis results
        """
        # Tool frequency analysis
        pred_tools = Counter()
        ref_tools = Counter()

        for pred_list in predictions:
            pred_tools.update(pred_list)
        for ref_list in references:
            ref_tools.update(ref_list)

        # Error pattern analysis
        errors_by_type = defaultdict(int)
        correct_selections = 0
        total_predictions = 0

        category_hits = defaultdict(int)
        category_misses = defaultdict(int)

        for pred, ref in zip(predictions, references):
            ref_set = set(ref)
            pred_set = set(pred)

            # Count correct and incorrect
            correct = pred_set & ref_set
            incorrect = pred_set - ref_set

            correct_selections += len(correct)
            total_predictions += len(pred)

            if len(correct) == 0:
                errors_by_type["complete_miss"] += 1
            elif len(incorrect) > 0:
                errors_by_type["partial_correct"] += 1
            else:
                errors_by_type["all_correct"] += 1

            # Category-level analysis if metadata available
            for tool_id in ref:
                category = self._get_category(tool_id)
                if tool_id in pred_set:
                    category_hits[category] += 1
                else:
                    category_misses[category] += 1

        # Coverage statistics
        pred_tool_set = set(pred_tools.keys())
        ref_tool_set = set(ref_tools.keys())

        return {
            "error_patterns": dict(errors_by_type),
            "tool_coverage": {
                "predicted_tools": len(pred_tool_set),
                "reference_tools": len(ref_tool_set),
                "overlap": len(pred_tool_set & ref_tool_set),
                "predicted_only": len(pred_tool_set - ref_tool_set),
                "missed": len(ref_tool_set - pred_tool_set),
            },
            "tool_frequency": {
                "top_predicted": pred_tools.most_common(10),
                "top_reference": ref_tools.most_common(10),
            },
            "category_performance": {
                "hits_by_category": dict(category_hits),
                "misses_by_category": dict(category_misses),
            },
            "selection_accuracy": {
                "correct_selections": correct_selections,
                "total_predictions": total_predictions,
                "accuracy": correct_selections / total_predictions
                if total_predictions > 0
                else 0.0,
            },
        }

    def _get_category(self, tool_id: str) -> str:
        """Extract category from tool ID."""
        # Tool ID format: {domain}_{category}_{number}
        parts = tool_id.split("_")
        if len(parts) >= 2:
            return f"{parts[0]}_{parts[1]}"
        return "unknown"
