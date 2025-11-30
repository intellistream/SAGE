"""
Online Continual Learning with Experience Replay

Implements an experience replay buffer for online/incremental training that
prevents catastrophic forgetting. The buffer is managed using coreset selection
to retain the most valuable samples.

This is a core component of SIAS (Streaming Importance-Aware Agent System).
"""

from __future__ import annotations

import random
from typing import Iterable, Optional, Sequence

from .coreset_selector import CoresetSelector, SampleT, SelectionSummary


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
        """
        Initialize OnlineContinualLearner.

        Args:
            buffer_size: Maximum samples to keep in replay buffer
            replay_ratio: Fraction of batch size to sample from buffer
            selector: CoresetSelector for buffer management (default: hybrid)
            random_seed: Random seed for reproducibility
        """
        self.buffer_size = buffer_size
        self.replay_ratio = replay_ratio
        self.selector = selector or CoresetSelector(strategy="hybrid")
        self._buffer: list[SampleT] = []
        self._metrics: dict[str, float] = {}
        self._rng = random.Random(random_seed)

    @property
    def buffer(self) -> list[SampleT]:
        """Access the current buffer (read-only view)."""
        return list(self._buffer)

    @property
    def buffer_len(self) -> int:
        """Current number of samples in buffer."""
        return len(self._buffer)

    def update_buffer(
        self,
        new_samples: Sequence[SampleT],
        metrics: Optional[dict[str, float]] = None,
    ) -> list[SampleT]:
        """
        Update buffer with new samples and return training batch.

        This method:
        1. Adds new samples to the buffer
        2. If buffer exceeds size limit, uses coreset selection to prune
        3. Returns new samples + replay samples for training

        Args:
            new_samples: New samples to add to buffer
            metrics: Optional metrics dict mapping sample_id to importance score

        Returns:
            Training batch combining new samples with replay samples
        """
        if not new_samples:
            return list(self._buffer)

        if metrics:
            self._metrics.update(metrics)

        # Combine buffer with new samples
        combined = list(self._buffer) + list(new_samples)

        # Prune if over capacity
        if len(combined) > self.buffer_size:
            combined = self.selector.select(
                combined,
                target_size=self.buffer_size,
                metrics=self._metrics,
            )
            # Clean up metrics for removed samples
            combined_ids = {self._get_sample_id(sample) for sample in combined}
            self._metrics = {k: v for k, v in self._metrics.items() if k in combined_ids}

        self._buffer = combined
        return self._assemble_training_batch(new_samples)

    def _assemble_training_batch(
        self,
        new_samples: Sequence[SampleT],
    ) -> list[SampleT]:
        """Combine new samples with replay samples."""
        new_ids = {self._get_sample_id(s) for s in new_samples}
        replay = self.sample_replay(len(new_samples), exclude=new_ids)
        return list(new_samples) + replay

    def sample_replay(
        self,
        new_batch_size: int,
        *,
        exclude: Optional[Iterable[str]] = None,
    ) -> list[SampleT]:
        """
        Sample from replay buffer.

        Args:
            new_batch_size: Size of new batch (replay size = batch_size * ratio)
            exclude: Sample IDs to exclude from replay

        Returns:
            List of replay samples
        """
        if not self._buffer or self.replay_ratio <= 0:
            return []

        exclude = set(exclude or [])
        available = [
            sample for sample in self._buffer if self._get_sample_id(sample) not in exclude
        ]
        if not available:
            return []

        replay_size = max(1, int(new_batch_size * self.replay_ratio))
        replay_size = min(replay_size, len(available))
        return self._rng.sample(available, replay_size)

    def buffer_snapshot(self) -> list[SampleT]:
        """Return a copy of the current buffer."""
        return list(self._buffer)

    def buffer_summary(self) -> SelectionSummary:
        """Get summary statistics for the buffer."""
        return SelectionSummary(
            total_samples=len(self._buffer),
            selected_samples=len(self._buffer),
            strategy=f"buffer:{self.selector.strategy}",
        )

    def clear(self) -> None:
        """Clear the buffer and metrics."""
        self._buffer = []
        self._metrics = {}

    def update_metrics(self, metrics: dict[str, float]) -> None:
        """
        Update importance metrics for samples in buffer.

        Args:
            metrics: Dict mapping sample_id to importance score
        """
        self._metrics.update(metrics)

    def _get_sample_id(self, sample: SampleT) -> str:
        """Get sample_id from sample (supports dict or object)."""
        if isinstance(sample, dict):
            return sample.get("sample_id", sample.get("dialog_id", str(id(sample))))
        return getattr(sample, "sample_id", getattr(sample, "dialog_id", str(id(sample))))
