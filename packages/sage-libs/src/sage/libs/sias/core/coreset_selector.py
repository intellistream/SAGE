"""
Coreset Selection for Efficient Training

Implements lightweight coreset selection strategies that identify the most
valuable samples for training, reducing computational cost while maintaining
model quality.

Strategies:
    - loss_topk: Select samples with highest loss (most informative)
    - diversity: Select samples maximizing coverage of feature space
    - hybrid: Combination of loss-based and diversity-based selection
    - random: Uniform random sampling (baseline)

This is a core component of SIAS (Streaming Importance-Aware Agent System).
"""

from __future__ import annotations

import math
import random
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Optional, Protocol, Sequence, runtime_checkable


@dataclass(slots=True)
class SelectionSummary:
    """Summary statistics for a selection operation."""

    total_samples: int
    selected_samples: int
    strategy: str


@runtime_checkable
class SampleProtocol(Protocol):
    """Protocol for samples that can be used with CoresetSelector."""

    @property
    def sample_id(self) -> str:
        """Unique identifier for the sample."""
        ...

    @property
    def text(self) -> str:
        """Text content of the sample."""
        ...

    @property
    def metadata(self) -> dict[str, Any]:
        """Metadata dictionary."""
        ...


# Type alias for any sample that implements the protocol
SampleT = Any  # Should implement SampleProtocol


class CoresetSelector:
    """
    Implements lightweight coreset selection strategies.

    This class provides several strategies for selecting a representative
    subset of samples from a larger dataset, optimizing for training efficiency.

    Attributes:
        strategy: Selection strategy ("loss_topk", "diversity", "hybrid", "random")
        metric_key: Key in metadata to use for loss-based selection
        diversity_temperature: Temperature for diversity scoring
        random_seed: Seed for reproducibility

    Example:
        >>> selector = CoresetSelector(strategy="hybrid")
        >>> selected = selector.select(samples, target_size=1000)
        >>> print(f"Selected {len(selected)} from {len(samples)} samples")
    """

    STRATEGIES = ("loss_topk", "diversity", "hybrid", "random")

    def __init__(
        self,
        strategy: str = "loss_topk",
        metric_key: str = "loss",
        diversity_temperature: float = 0.7,
        random_seed: int = 13,
    ) -> None:
        """
        Initialize CoresetSelector.

        Args:
            strategy: Selection strategy to use
            metric_key: Metadata key for loss-based selection
            diversity_temperature: Temperature for diversity scoring
            random_seed: Random seed for reproducibility
        """
        if strategy not in self.STRATEGIES:
            raise ValueError(f"Unknown strategy: {strategy}. Choose from {self.STRATEGIES}")

        self.strategy = strategy
        self.metric_key = metric_key
        self.diversity_temperature = diversity_temperature
        self._rng = random.Random(random_seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def select(
        self,
        samples: Sequence[SampleT],
        *,
        target_size: Optional[int],
        metrics: Optional[dict[str, float]] = None,
    ) -> list[SampleT]:
        """
        Select a subset of samples using the configured strategy.

        Args:
            samples: Input samples to select from
            target_size: Number of samples to select (None = keep all)
            metrics: Optional external metrics dict mapping sample_id to score

        Returns:
            List of selected samples
        """
        if target_size is None or target_size <= 0 or target_size >= len(samples):
            return list(samples)

        if self.strategy == "loss_topk":
            return self._select_loss(samples, target_size, metrics)
        if self.strategy == "diversity":
            return self._select_diversity(samples, target_size)
        if self.strategy == "hybrid":
            return self._select_hybrid(samples, target_size, metrics)
        return self._select_random(samples, target_size)

    def summary(self, original_size: int, selected_size: int) -> SelectionSummary:
        """Create a summary of the selection operation."""
        return SelectionSummary(
            total_samples=original_size,
            selected_samples=selected_size,
            strategy=self.strategy,
        )

    # ------------------------------------------------------------------
    # Selection Strategies
    # ------------------------------------------------------------------
    def _select_loss(
        self,
        samples: Sequence[SampleT],
        target_size: int,
        metrics: Optional[dict[str, float]],
    ) -> list[SampleT]:
        """Select samples with highest loss/importance scores."""

        def score(sample: SampleT) -> float:
            sample_id = self._get_sample_id(sample)
            if metrics and sample_id in metrics:
                return metrics[sample_id]
            meta = self._get_metadata(sample)
            meta_val = meta.get(self.metric_key)
            if isinstance(meta_val, (int, float)):
                return float(meta_val)
            return 0.0

        ranked = sorted(samples, key=score, reverse=True)
        return list(ranked[:target_size])

    def _select_random(
        self,
        samples: Sequence[SampleT],
        target_size: int,
    ) -> list[SampleT]:
        """Uniform random sampling."""
        return self._rng.sample(list(samples), target_size)

    def _select_hybrid(
        self,
        samples: Sequence[SampleT],
        target_size: int,
        metrics: Optional[dict[str, float]],
    ) -> list[SampleT]:
        """Hybrid selection: 60% loss-based + 40% diversity-based."""
        loss_portion = int(target_size * 0.6)
        div_portion = target_size - loss_portion

        # First select high-loss samples
        top_loss = self._select_loss(samples, loss_portion or 1, metrics)
        top_loss_ids = {self._get_sample_id(s) for s in top_loss}

        # Then select diverse samples from remaining
        remaining = [s for s in samples if self._get_sample_id(s) not in top_loss_ids]
        if not remaining:
            return top_loss

        diversity = self._select_diversity(remaining, max(div_portion, 1))
        merged = (top_loss + diversity)[:target_size]
        return merged

    def _select_diversity(
        self,
        samples: Sequence[SampleT],
        target_size: int,
    ) -> list[SampleT]:
        """Select samples maximizing feature space coverage."""
        if not samples:
            return []

        # Extract features for all samples
        features = {
            self._get_sample_id(sample): self._text_features(self._get_text(sample))
            for sample in samples
        }

        selected: list[SampleT] = []
        candidates = list(samples)

        # Start with the sample that has the highest token variance
        scores = {
            self._get_sample_id(sample): self._feature_norm(features[self._get_sample_id(sample)])
            for sample in samples
        }
        first = max(candidates, key=lambda s: scores.get(self._get_sample_id(s), 0.0))
        selected.append(first)
        candidates = [s for s in candidates if self._get_sample_id(s) != self._get_sample_id(first)]

        # Iteratively select most diverse samples
        while candidates and len(selected) < target_size:
            best_candidate = max(
                candidates,
                key=lambda sample: self._min_distance(sample, selected, features),
            )
            selected.append(best_candidate)
            candidates = [
                s
                for s in candidates
                if self._get_sample_id(s) != self._get_sample_id(best_candidate)
            ]

        return selected

    # ------------------------------------------------------------------
    # Feature Extraction Helpers
    # ------------------------------------------------------------------
    def _text_features(self, text: str) -> Counter:
        """Extract normalized token frequency features from text."""
        tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
        filtered = [token for token in tokens if len(token) > 2]
        counts = Counter(filtered)
        total = sum(counts.values()) or 1.0
        for key in counts:
            counts[key] /= total
        return counts

    def _feature_norm(self, features: Counter) -> float:
        """Compute L2 norm of feature vector."""
        return math.sqrt(sum(value * value for value in features.values()))

    def _cosine_similarity(self, left: Counter, right: Counter) -> float:
        """Compute cosine similarity between two feature vectors."""
        keys = left.keys() & right.keys()
        if not keys:
            return 0.0
        return sum(left[key] * right[key] for key in keys)

    def _min_distance(
        self,
        candidate: SampleT,
        selected: Sequence[SampleT],
        features: dict[str, Counter],
    ) -> float:
        """Compute minimum distance from candidate to selected set."""
        cand_feat = features[self._get_sample_id(candidate)]
        if not selected:
            return 1.0
        sims = [
            self._cosine_similarity(cand_feat, features[self._get_sample_id(item)])
            for item in selected
        ]
        similarity = max(sims) if sims else 0.0
        return 1.0 - similarity

    # ------------------------------------------------------------------
    # Sample Access Helpers (support both dict and object access)
    # ------------------------------------------------------------------
    def _get_sample_id(self, sample: SampleT) -> str:
        """Get sample_id from sample (supports dict or object)."""
        if isinstance(sample, dict):
            return sample.get("sample_id", sample.get("dialog_id", str(id(sample))))
        return getattr(sample, "sample_id", getattr(sample, "dialog_id", str(id(sample))))

    def _get_text(self, sample: SampleT) -> str:
        """Get text from sample (supports dict or object)."""
        if isinstance(sample, dict):
            return sample.get("text", "")
        return getattr(sample, "text", "")

    def _get_metadata(self, sample: SampleT) -> dict[str, Any]:
        """Get metadata from sample (supports dict or object)."""
        if isinstance(sample, dict):
            return sample.get("metadata", {})
        return getattr(sample, "metadata", {})
