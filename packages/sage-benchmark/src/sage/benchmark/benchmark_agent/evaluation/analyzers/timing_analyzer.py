"""Timing analyzer for confusion matrix and threshold analysis."""

from typing import Any, Sequence

import numpy as np


class TimingAnalyzer:
    """
    Analyzer for timing judgment predictions.

    Provides breakdowns by:
    - Confusion matrix
    - Confidence distribution
    - Threshold sensitivity (if confidence scores available)
    """

    name = "timing"

    def analyze(
        self, predictions: Sequence[bool], references: Sequence[bool], metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze timing predictions.

        Args:
            predictions: List of predicted decisions (True = call tool)
            references: List of reference decisions
            metadata: Additional context (may include confidence scores)

        Returns:
            Dictionary with analysis results
        """
        preds = np.array(predictions, dtype=bool)
        refs = np.array(references, dtype=bool)

        # Confusion matrix
        true_positives = int(np.sum(preds & refs))
        false_positives = int(np.sum(preds & ~refs))
        false_negatives = int(np.sum(~preds & refs))
        true_negatives = int(np.sum(~preds & ~refs))

        confusion_matrix = {
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "true_negatives": true_negatives,
        }

        # Derived metrics
        total = len(predictions)
        positive_rate = (true_positives + false_positives) / total if total > 0 else 0.0
        true_positive_rate = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )
        false_positive_rate = (
            false_positives / (false_positives + true_negatives)
            if (false_positives + true_negatives) > 0
            else 0.0
        )

        # Class distribution
        class_distribution = {
            "reference_positive_ratio": float(np.mean(refs)),
            "predicted_positive_ratio": float(np.mean(preds)),
            "reference_positive_count": int(np.sum(refs)),
            "predicted_positive_count": int(np.sum(preds)),
        }

        # Confidence analysis if available
        confidence_analysis = {}
        if "confidences" in metadata:
            confidences = np.array(metadata["confidences"])

            # Confidence by correctness
            correct_mask = preds == refs
            confidence_analysis = {
                "mean_confidence_correct": float(np.mean(confidences[correct_mask]))
                if np.any(correct_mask)
                else 0.0,
                "mean_confidence_incorrect": float(np.mean(confidences[~correct_mask]))
                if np.any(~correct_mask)
                else 0.0,
                "mean_confidence_overall": float(np.mean(confidences)),
                "confidence_distribution": {
                    "bins": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                    "counts": np.histogram(confidences, bins=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0])[
                        0
                    ].tolist(),
                },
            }

            # Threshold sensitivity analysis
            thresholds = np.linspace(0.1, 0.9, 9)
            threshold_metrics = []

            for threshold in thresholds:
                thresh_preds = confidences >= threshold
                tp = int(np.sum(thresh_preds & refs))
                fp = int(np.sum(thresh_preds & ~refs))
                fn = int(np.sum(~thresh_preds & refs))
                # tn = int(np.sum(~thresh_preds & ~refs))  # Not used in metrics

                precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                f1 = (
                    2 * (precision * recall) / (precision + recall)
                    if (precision + recall) > 0
                    else 0.0
                )

                threshold_metrics.append(
                    {
                        "threshold": float(threshold),
                        "precision": precision,
                        "recall": recall,
                        "f1": f1,
                    }
                )

            confidence_analysis["threshold_sensitivity"] = threshold_metrics

        return {
            "confusion_matrix": confusion_matrix,
            "rates": {
                "true_positive_rate": true_positive_rate,
                "false_positive_rate": false_positive_rate,
                "predicted_positive_rate": positive_rate,
            },
            "class_distribution": class_distribution,
            "confidence_analysis": confidence_analysis,
            "total_samples": total,
        }
