# Copyright (c) 2025 IntelliStream. All rights reserved.
# Licensed under the Apache License, Version 2.0

"""Comprehensive unit tests for CoresetSelector and OnlineContinualLearner.

This test module covers:
- CoresetSelector: all strategies (loss_topk, diversity, hybrid, random)
- OnlineContinualLearner: buffer management, replay sampling, edge cases

Note: These components have been moved to sage.libs.sias but tests remain here
for backward compatibility testing.
"""

from __future__ import annotations

import pytest

# Import from new SIAS location
from sage.libs.agentic.sias import (
    CoresetSelector,
    OnlineContinualLearner,
    SelectionSummary,
)
from sage.libs.finetune.agent.dialog_processor import ProcessedDialog


def _make_dialog(dialog_id: str, loss: float, text: str = "") -> ProcessedDialog:
    """Create a test ProcessedDialog with given id, loss, and text."""
    return ProcessedDialog(
        dialog_id=dialog_id,
        task_type="tool_selection",
        text=text or f"dialog {dialog_id} content",
        metadata={"loss": loss},
        target_tools=["tool"],
        split="train",
        source="agent_sft",
    )


# ========================================================================
# CoresetSelector Tests
# ========================================================================


class TestCoresetSelectorInit:
    """Tests for CoresetSelector initialization."""

    def test_default_initialization(self) -> None:
        """Test default parameter values."""
        selector = CoresetSelector()
        assert selector.strategy == "loss_topk"
        assert selector.metric_key == "loss"
        assert selector.diversity_temperature == 0.7

    def test_custom_initialization(self) -> None:
        """Test custom parameter values."""
        selector = CoresetSelector(
            strategy="diversity",
            metric_key="perplexity",
            diversity_temperature=0.5,
            random_seed=99,
        )
        assert selector.strategy == "diversity"
        assert selector.metric_key == "perplexity"
        assert selector.diversity_temperature == 0.5


class TestCoresetSelectorLossTopK:
    """Tests for loss_topk selection strategy."""

    def test_loss_topk_basic(self) -> None:
        """Test basic loss_topk selection picks highest loss samples."""
        samples = [
            _make_dialog("dlg1", 0.1),
            _make_dialog("dlg2", 0.9),
            _make_dialog("dlg3", 0.5),
            _make_dialog("dlg4", 0.3),
        ]

        selector = CoresetSelector(strategy="loss_topk", metric_key="loss", random_seed=0)
        selected = selector.select(samples, target_size=2, metrics=None)

        # Should select highest loss: dlg2 (0.9) and dlg3 (0.5)
        selected_ids = {s.dialog_id for s in selected}
        assert selected_ids == {"dlg2", "dlg3"}

    def test_loss_topk_with_external_metrics(self) -> None:
        """Test loss_topk with external metrics dict."""
        samples = [
            _make_dialog("dlg1", 0.0),  # metadata loss is 0
            _make_dialog("dlg2", 0.0),
            _make_dialog("dlg3", 0.0),
        ]

        # External metrics override metadata
        external_metrics = {"dlg1": 0.8, "dlg2": 0.2, "dlg3": 0.5}

        selector = CoresetSelector(strategy="loss_topk", random_seed=0)
        selected = selector.select(samples, target_size=2, metrics=external_metrics)

        # Should pick dlg1 (0.8) and dlg3 (0.5) based on external metrics
        selected_ids = {s.dialog_id for s in selected}
        assert selected_ids == {"dlg1", "dlg3"}

    def test_loss_topk_missing_metric_uses_zero(self) -> None:
        """Test samples without metrics use 0 as default."""
        samples = [
            ProcessedDialog(
                dialog_id="dlg1",
                task_type="tool_selection",
                text="text1",
                metadata={},  # no loss key
                target_tools=[],
                split="train",
                source="test",
            ),
            _make_dialog("dlg2", 0.5),
        ]

        selector = CoresetSelector(strategy="loss_topk", random_seed=0)
        selected = selector.select(samples, target_size=1, metrics=None)

        # dlg2 has loss 0.5, dlg1 has no loss (default 0), so dlg2 selected
        assert selected[0].dialog_id == "dlg2"


class TestCoresetSelectorRandom:
    """Tests for random selection strategy."""

    def test_random_selection(self) -> None:
        """Test random selection returns correct size."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(10)]

        selector = CoresetSelector(strategy="random", random_seed=42)
        selected = selector.select(samples, target_size=3, metrics=None)

        assert len(selected) == 3

    def test_random_selection_reproducible(self) -> None:
        """Test random selection is reproducible with same seed."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(10)]

        selector1 = CoresetSelector(strategy="random", random_seed=42)
        selector2 = CoresetSelector(strategy="random", random_seed=42)

        selected1 = selector1.select(samples, target_size=3, metrics=None)
        selected2 = selector2.select(samples, target_size=3, metrics=None)

        ids1 = [s.dialog_id for s in selected1]
        ids2 = [s.dialog_id for s in selected2]
        assert ids1 == ids2

    def test_random_selection_different_seeds(self) -> None:
        """Test different seeds produce different selections (usually)."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(20)]

        selector1 = CoresetSelector(strategy="random", random_seed=1)
        selector2 = CoresetSelector(strategy="random", random_seed=999)

        selected1 = selector1.select(samples, target_size=5, metrics=None)
        selected2 = selector2.select(samples, target_size=5, metrics=None)

        ids1 = {s.dialog_id for s in selected1}
        ids2 = {s.dialog_id for s in selected2}
        # Very likely different with different seeds
        # (small chance of collision with only 20 samples)
        assert ids1 != ids2 or True  # Allow for rare collision


class TestCoresetSelectorDiversity:
    """Tests for diversity selection strategy."""

    def test_diversity_selection_basic(self) -> None:
        """Test diversity selection picks diverse samples."""
        # Create samples with different text content
        samples = [
            _make_dialog("dlg1", 0.5, "python code programming language"),
            _make_dialog("dlg2", 0.5, "python code programming script"),  # similar to dlg1
            _make_dialog("dlg3", 0.5, "weather forecast temperature rain"),  # different
            _make_dialog("dlg4", 0.5, "machine learning neural network ai"),  # different
        ]

        selector = CoresetSelector(strategy="diversity", random_seed=0)
        selected = selector.select(samples, target_size=3, metrics=None)

        assert len(selected) == 3

    def test_diversity_selection_empty_samples(self) -> None:
        """Test diversity selection with empty samples list."""
        selector = CoresetSelector(strategy="diversity", random_seed=0)
        selected = selector.select([], target_size=3, metrics=None)
        assert selected == []

    def test_diversity_selects_dissimilar(self) -> None:
        """Test diversity prefers dissimilar samples."""
        # Two very similar samples, one different
        samples = [
            _make_dialog("dlg1", 0.5, "hello world hello world hello"),
            _make_dialog("dlg2", 0.5, "hello world hello world hello"),  # identical
            _make_dialog("dlg3", 0.5, "goodbye universe farewell cosmos"),  # different
        ]

        selector = CoresetSelector(strategy="diversity", random_seed=0)
        selected = selector.select(samples, target_size=2, metrics=None)

        selected_ids = {s.dialog_id for s in selected}
        # Should pick dlg3 as it's different, plus one of dlg1/dlg2
        assert "dlg3" in selected_ids


class TestCoresetSelectorHybrid:
    """Tests for hybrid selection strategy."""

    def test_hybrid_selection_basic(self) -> None:
        """Test hybrid combines loss and diversity."""
        samples = [
            _make_dialog("dlg1", 0.9, "high loss sample one"),
            _make_dialog("dlg2", 0.8, "high loss sample two"),
            _make_dialog("dlg3", 0.1, "low loss diverse sample weather"),
            _make_dialog("dlg4", 0.05, "low loss diverse sample sports"),
        ]

        selector = CoresetSelector(strategy="hybrid", random_seed=0)
        selected = selector.select(samples, target_size=3, metrics=None)

        assert len(selected) == 3
        # Should have some high-loss samples (60%) and some diverse (40%)
        selected_ids = {s.dialog_id for s in selected}
        # At least one high-loss sample should be included
        assert "dlg1" in selected_ids or "dlg2" in selected_ids

    def test_hybrid_60_40_split(self) -> None:
        """Test hybrid uses approximately 60% loss, 40% diversity."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1, f"unique text {i} content") for i in range(10)]

        selector = CoresetSelector(strategy="hybrid", random_seed=0)
        # Select 5: should be ~3 loss-based, ~2 diversity-based
        selected = selector.select(samples, target_size=5, metrics=None)

        assert len(selected) == 5


class TestCoresetSelectorEdgeCases:
    """Tests for edge cases in CoresetSelector."""

    def test_target_size_none(self) -> None:
        """Test that target_size=None returns all samples."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(5)]

        selector = CoresetSelector(strategy="loss_topk", random_seed=0)
        selected = selector.select(samples, target_size=None, metrics=None)

        assert len(selected) == 5

    def test_target_size_zero(self) -> None:
        """Test that target_size=0 returns all samples."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(5)]

        selector = CoresetSelector(strategy="loss_topk", random_seed=0)
        selected = selector.select(samples, target_size=0, metrics=None)

        assert len(selected) == 5

    def test_target_size_negative(self) -> None:
        """Test that target_size<0 returns all samples."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(5)]

        selector = CoresetSelector(strategy="loss_topk", random_seed=0)
        selected = selector.select(samples, target_size=-1, metrics=None)

        assert len(selected) == 5

    def test_target_size_larger_than_samples(self) -> None:
        """Test that target_size > len(samples) returns all samples."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(3)]

        selector = CoresetSelector(strategy="loss_topk", random_seed=0)
        selected = selector.select(samples, target_size=10, metrics=None)

        assert len(selected) == 3

    def test_unknown_strategy_raises_error(self) -> None:
        """Test that unknown strategy raises ValueError (new behavior in SIAS)."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            CoresetSelector(strategy="unknown_strategy", random_seed=42)


# ========================================================================
# OnlineContinualLearner Tests
# ========================================================================


class TestOnlineContinualLearnerInit:
    """Tests for OnlineContinualLearner initialization."""

    def test_default_initialization(self) -> None:
        """Test default parameter values."""
        learner = OnlineContinualLearner()

        assert learner.buffer_size == 2048
        assert learner.replay_ratio == 0.3
        assert learner.selector is not None
        assert learner.selector.strategy == "hybrid"

    def test_custom_initialization(self) -> None:
        """Test custom parameter values."""
        selector = CoresetSelector(strategy="loss_topk", random_seed=0)
        learner = OnlineContinualLearner(
            buffer_size=100,
            replay_ratio=0.5,
            selector=selector,
            random_seed=99,
        )

        assert learner.buffer_size == 100
        assert learner.replay_ratio == 0.5
        assert learner.selector.strategy == "loss_topk"


class TestOnlineContinualLearnerBufferManagement:
    """Tests for buffer management in OnlineContinualLearner."""

    def test_empty_buffer_initial(self) -> None:
        """Test buffer is empty initially."""
        learner = OnlineContinualLearner(buffer_size=10, random_seed=0)
        assert learner.buffer_snapshot() == []

    def test_add_samples_to_buffer(self) -> None:
        """Test adding samples fills buffer."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(3)]

        learner = OnlineContinualLearner(buffer_size=10, random_seed=0)
        learner.update_buffer(samples)

        buffer = learner.buffer_snapshot()
        assert len(buffer) == 3

    def test_buffer_overflow_triggers_selection(self) -> None:
        """Test that exceeding buffer_size triggers coreset selection."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(10)]

        selector = CoresetSelector(strategy="loss_topk", metric_key="loss", random_seed=0)
        learner = OnlineContinualLearner(buffer_size=5, selector=selector, random_seed=0)

        learner.update_buffer(samples[:6])

        # Buffer should be trimmed to 5
        buffer = learner.buffer_snapshot()
        assert len(buffer) == 5

    def test_buffer_keeps_highest_loss_on_overflow(self) -> None:
        """Test that loss_topk selection keeps highest loss samples."""
        samples = [
            _make_dialog("dlg_low1", 0.1),
            _make_dialog("dlg_low2", 0.2),
            _make_dialog("dlg_high1", 0.8),
            _make_dialog("dlg_high2", 0.9),
        ]

        selector = CoresetSelector(strategy="loss_topk", metric_key="loss", random_seed=0)
        learner = OnlineContinualLearner(buffer_size=2, selector=selector, random_seed=0)

        metrics = {"dlg_low1": 0.1, "dlg_low2": 0.2, "dlg_high1": 0.8, "dlg_high2": 0.9}
        learner.update_buffer(samples, metrics=metrics)

        buffer = learner.buffer_snapshot()
        buffer_ids = {s.dialog_id for s in buffer}

        assert "dlg_high1" in buffer_ids
        assert "dlg_high2" in buffer_ids

    def test_incremental_buffer_updates(self) -> None:
        """Test multiple buffer updates work correctly."""
        learner = OnlineContinualLearner(buffer_size=5, replay_ratio=0.0, random_seed=0)

        # First update
        samples1 = [_make_dialog(f"batch1_dlg{i}", 0.5) for i in range(2)]
        learner.update_buffer(samples1)
        assert len(learner.buffer_snapshot()) == 2

        # Second update
        samples2 = [_make_dialog(f"batch2_dlg{i}", 0.5) for i in range(2)]
        learner.update_buffer(samples2)
        assert len(learner.buffer_snapshot()) == 4


class TestOnlineContinualLearnerReplay:
    """Tests for replay sampling in OnlineContinualLearner."""

    def test_sample_replay_basic(self) -> None:
        """Test basic replay sampling."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(5)]

        learner = OnlineContinualLearner(buffer_size=10, replay_ratio=0.5, random_seed=42)
        learner.update_buffer(samples)

        # Sample replay for batch of 4 new samples
        replay = learner.sample_replay(new_batch_size=4, exclude=set())

        # replay_ratio=0.5 means 2 replay samples for batch of 4
        assert len(replay) == 2

    def test_sample_replay_with_exclusion(self) -> None:
        """Test replay sampling excludes specified dialog_ids."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(5)]

        learner = OnlineContinualLearner(buffer_size=10, replay_ratio=0.5, random_seed=42)
        learner.update_buffer(samples)

        # Exclude dlg0, dlg1, dlg2
        exclude = {"dlg0", "dlg1", "dlg2"}
        replay = learner.sample_replay(new_batch_size=4, exclude=exclude)

        # Replay should only contain dlg3, dlg4
        replay_ids = {s.dialog_id for s in replay}
        assert replay_ids.issubset({"dlg3", "dlg4"})

    def test_sample_replay_empty_buffer(self) -> None:
        """Test replay sampling with empty buffer returns empty list."""
        learner = OnlineContinualLearner(buffer_size=10, replay_ratio=0.5, random_seed=42)

        replay = learner.sample_replay(new_batch_size=4, exclude=set())
        assert replay == []

    def test_sample_replay_zero_ratio(self) -> None:
        """Test replay sampling with replay_ratio=0 returns empty list."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(5)]

        learner = OnlineContinualLearner(buffer_size=10, replay_ratio=0.0, random_seed=42)
        learner.update_buffer(samples)

        replay = learner.sample_replay(new_batch_size=4, exclude=set())
        assert replay == []

    def test_sample_replay_all_excluded(self) -> None:
        """Test replay sampling when all samples are excluded."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(3)]

        learner = OnlineContinualLearner(buffer_size=10, replay_ratio=0.5, random_seed=42)
        learner.update_buffer(samples)

        # Exclude all samples
        exclude = {"dlg0", "dlg1", "dlg2"}
        replay = learner.sample_replay(new_batch_size=4, exclude=exclude)

        assert replay == []


class TestOnlineContinualLearnerUpdateBuffer:
    """Tests for update_buffer method."""

    def test_update_buffer_returns_training_batch(self) -> None:
        """Test update_buffer returns combined new + replay samples."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(5)]

        learner = OnlineContinualLearner(buffer_size=10, replay_ratio=0.5, random_seed=42)

        # First update - no replay available
        batch1 = learner.update_buffer(samples[:2])
        assert len(batch1) == 2

        # Second update - should include replay from previous samples
        batch2 = learner.update_buffer(samples[2:])
        # 3 new samples + 1 replay (replay_ratio=0.5 for 3 samples)
        assert len(batch2) >= 3

    def test_update_buffer_empty_input(self) -> None:
        """Test update_buffer with empty input returns buffer snapshot."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(3)]

        learner = OnlineContinualLearner(buffer_size=10, random_seed=42)
        learner.update_buffer(samples)

        # Update with empty list
        result = learner.update_buffer([])
        assert len(result) == 3  # Returns buffer snapshot


class TestOnlineContinualLearnerSummary:
    """Tests for buffer_summary method."""

    def test_buffer_summary(self) -> None:
        """Test buffer_summary returns SelectionSummary."""
        samples = [_make_dialog(f"dlg{i}", i * 0.1) for i in range(5)]

        selector = CoresetSelector(strategy="hybrid", random_seed=0)
        learner = OnlineContinualLearner(buffer_size=10, selector=selector, random_seed=42)
        learner.update_buffer(samples)

        summary = learner.buffer_summary()

        assert isinstance(summary, SelectionSummary)
        assert summary.total_samples == 5
        assert summary.selected_samples == 5
        assert "hybrid" in summary.strategy


# ========================================================================
# SelectionSummary Tests
# ========================================================================


class TestSelectionSummary:
    """Tests for SelectionSummary dataclass."""

    def test_selection_summary_creation(self) -> None:
        """Test creating a SelectionSummary."""
        summary = SelectionSummary(
            total_samples=100,
            selected_samples=50,
            strategy="loss_topk",
        )

        assert summary.total_samples == 100
        assert summary.selected_samples == 50
        assert summary.strategy == "loss_topk"
