"""Coreset selection and online continual learning utilities."""

from __future__ import annotations

import math
import random
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from .dialog_processor import ProcessedDialog


@dataclass(slots=True)
class SelectionSummary:
    """Simple summary statistics for selection steps."""

    total_samples: int
    selected_samples: int
    strategy: str


class CoresetSelector:
    """Implements lightweight coreset selection strategies for agent dialogs."""

    def __init__(
        self,
        strategy: str = "loss_topk",
        metric_key: str = "loss",
        diversity_temperature: float = 0.7,
        random_seed: int = 13,
    ) -> None:
        self.strategy = strategy
        self.metric_key = metric_key
        self.diversity_temperature = diversity_temperature
        self._rng = random.Random(random_seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def select(
        self,
        samples: Sequence[ProcessedDialog],
        *,
        target_size: Optional[int],
        metrics: Optional[dict[str, float]] = None,
    ) -> list[ProcessedDialog]:
        if target_size is None or target_size <= 0 or target_size >= len(samples):
            return list(samples)

        if self.strategy == "loss_topk":
            return self._select_loss(samples, target_size, metrics)
        if self.strategy == "diversity":
            return self._select_diversity(samples, target_size)
        if self.strategy == "hybrid":
            return self._select_hybrid(samples, target_size, metrics)
        return self._select_random(samples, target_size)

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------
    def _select_loss(
        self,
        samples: Sequence[ProcessedDialog],
        target_size: int,
        metrics: Optional[dict[str, float]],
    ) -> list[ProcessedDialog]:
        def score(sample: ProcessedDialog) -> float:
            if metrics and sample.dialog_id in metrics:
                return metrics[sample.dialog_id]
            meta_val = sample.metadata.get(self.metric_key)
            if isinstance(meta_val, int | float):
                return float(meta_val)
            return 0.0

        ranked = sorted(samples, key=score, reverse=True)
        return list(ranked[:target_size])

    def _select_random(
        self,
        samples: Sequence[ProcessedDialog],
        target_size: int,
    ) -> list[ProcessedDialog]:
        return self._rng.sample(list(samples), target_size)

    def _select_hybrid(
        self,
        samples: Sequence[ProcessedDialog],
        target_size: int,
        metrics: Optional[dict[str, float]],
    ) -> list[ProcessedDialog]:
        loss_portion = int(target_size * 0.6)
        div_portion = target_size - loss_portion
        top_loss = self._select_loss(samples, loss_portion or 1, metrics)
        remaining = [s for s in samples if s.dialog_id not in {d.dialog_id for d in top_loss}]
        if not remaining:
            return top_loss
        diversity = self._select_diversity(remaining, max(div_portion, 1))
        merged = (top_loss + diversity)[:target_size]
        return merged

    def _select_diversity(
        self,
        samples: Sequence[ProcessedDialog],
        target_size: int,
    ) -> list[ProcessedDialog]:
        if not samples:
            return []
        features = {sample.dialog_id: self._text_features(sample.text) for sample in samples}
        selected: list[ProcessedDialog] = []
        candidates = list(samples)

        # Start with the sample that has the highest token variance
        scores = {
            sample.dialog_id: self._feature_norm(features[sample.dialog_id]) for sample in samples
        }
        first = max(candidates, key=lambda s: scores.get(s.dialog_id, 0.0))
        selected.append(first)
        candidates = [s for s in candidates if s.dialog_id != first.dialog_id]

        while candidates and len(selected) < target_size:
            best_candidate = max(
                candidates,
                key=lambda sample: self._min_distance(sample, selected, features),
            )
            selected.append(best_candidate)
            candidates = [s for s in candidates if s.dialog_id != best_candidate.dialog_id]

        return selected

    # ------------------------------------------------------------------
    # Feature helpers
    # ------------------------------------------------------------------
    def _text_features(self, text: str) -> Counter:
        tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
        filtered = [token for token in tokens if len(token) > 2]
        counts = Counter(filtered)
        total = sum(counts.values()) or 1.0
        for key in counts:
            counts[key] /= total
        return counts

    def _feature_norm(self, features: Counter) -> float:
        return math.sqrt(sum(value * value for value in features.values()))

    def _cosine_similarity(self, left: Counter, right: Counter) -> float:
        keys = left.keys() & right.keys()
        if not keys:
            return 0.0
        return sum(left[key] * right[key] for key in keys)

    def _min_distance(
        self,
        candidate: ProcessedDialog,
        selected: Sequence[ProcessedDialog],
        features: dict[str, Counter],
    ) -> float:
        cand_feat = features[candidate.dialog_id]
        if not selected:
            return 1.0
        sims = [self._cosine_similarity(cand_feat, features[item.dialog_id]) for item in selected]
        similarity = max(sims) if sims else 0.0
        return 1.0 - similarity


class OnlineContinualLearner:
    """
    Maintain a replay buffer for online continual learning.

    Implements experience replay to prevent catastrophic forgetting during
    incremental/online training. The buffer is managed using coreset selection
    to keep the most valuable samples.

    Attributes:
        buffer_size: Maximum number of samples to keep in buffer
        replay_ratio: Ratio of replay samples to add per batch (e.g., 0.25 = 25%)
        selector: CoresetSelector for buffer management

    Example:
        >>> learner = OnlineContinualLearner(buffer_size=2048, replay_ratio=0.25)
        >>> for new_batch in data_stream:
        ...     training_batch = learner.update_buffer(new_batch)
        ...     train_step(training_batch)
    """

    def __init__(
        self,
        buffer_size: int = 2048,
        replay_ratio: float = 0.3,
        selector: Optional[CoresetSelector] = None,
        random_seed: int = 17,
    ) -> None:
        self.buffer_size = buffer_size
        self.replay_ratio = replay_ratio
        self.selector = selector or CoresetSelector(strategy="hybrid")
        self._buffer: list[ProcessedDialog] = []
        self._metrics: dict[str, float] = {}
        self._rng = random.Random(random_seed)

    def update_buffer(
        self,
        new_samples: Sequence[ProcessedDialog],
        metrics: Optional[dict[str, float]] = None,
    ) -> list[ProcessedDialog]:
        if not new_samples:
            return list(self._buffer)

        if metrics:
            self._metrics.update(metrics)

        combined = list(self._buffer) + list(new_samples)
        if len(combined) > self.buffer_size:
            combined = self.selector.select(
                combined,
                target_size=self.buffer_size,
                metrics=self._metrics,
            )
            combined_map = {sample.dialog_id for sample in combined}
            self._metrics = {k: v for k, v in self._metrics.items() if k in combined_map}

        self._buffer = combined
        return self._assemble_training_batch(new_samples)

    def _assemble_training_batch(
        self,
        new_samples: Sequence[ProcessedDialog],
    ) -> list[ProcessedDialog]:
        replay = self.sample_replay(len(new_samples), exclude={s.dialog_id for s in new_samples})
        return list(new_samples) + replay

    def sample_replay(
        self,
        new_batch_size: int,
        *,
        exclude: Optional[Iterable[str]] = None,
    ) -> list[ProcessedDialog]:
        if not self._buffer or self.replay_ratio <= 0:
            return []

        exclude = set(exclude or [])
        available = [sample for sample in self._buffer if sample.dialog_id not in exclude]
        if not available:
            return []

        replay_size = max(1, int(new_batch_size * self.replay_ratio))
        replay_size = min(replay_size, len(available))
        return self._rng.sample(available, replay_size)

    def buffer_snapshot(self) -> list[ProcessedDialog]:
        return list(self._buffer)

    def buffer_summary(self) -> SelectionSummary:
        return SelectionSummary(
            total_samples=len(self._buffer),
            selected_samples=len(self._buffer),
            strategy=f"buffer:{self.selector.strategy}",
        )
