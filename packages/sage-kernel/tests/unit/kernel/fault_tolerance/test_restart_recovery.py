"""
Tests for RestartBasedRecovery

Comprehensive test coverage for restart-based fault tolerance recovery.
"""

import time
from unittest.mock import Mock, patch

import pytest

from sage.kernel.fault_tolerance.impl.restart_recovery import RestartBasedRecovery
from sage.kernel.fault_tolerance.impl.restart_strategy import (
    ExponentialBackoffStrategy,
    FixedDelayStrategy,
)


@pytest.fixture
def recovery_handler():
    """Create a recovery handler with fixed delay strategy"""
    strategy = FixedDelayStrategy(delay=0.01, max_attempts=3)  # Short delay for tests
    return RestartBasedRecovery(restart_strategy=strategy)


@pytest.fixture
def exponential_handler():
    """Create a recovery handler with exponential backoff strategy"""
    strategy = ExponentialBackoffStrategy(
        initial_delay=0.01, max_delay=1.0, multiplier=2.0, max_attempts=5
    )
    return RestartBasedRecovery(restart_strategy=strategy)


class TestRestartBasedRecoveryInitialization:
    """Test RestartBasedRecovery initialization"""

    def test_init_with_strategy(self):
        """Test initialization with provided restart strategy"""
        strategy = FixedDelayStrategy()
        handler = RestartBasedRecovery(restart_strategy=strategy)

        assert handler.restart_strategy is strategy
        assert handler.failure_counts == {}
        assert handler.failure_history == {}
        assert handler.logger is None

    def test_init_creates_default_strategy(self):
        """Test initialization creates default exponential backoff strategy"""
        handler = RestartBasedRecovery()

        assert handler.restart_strategy is not None
        assert isinstance(handler.restart_strategy, ExponentialBackoffStrategy)


class TestHandleFailure:
    """Test handle_failure method"""

    def test_handle_failure_first_attempt(self, recovery_handler):
        """Test handling first failure"""
        task_id = "task1"
        error = Exception("Test error")

        # For restart-based recovery, no actual restart happens in current implementation
        # (recover() returns True by default)
        result = recovery_handler.handle_failure(task_id, error)

        assert recovery_handler.failure_counts[task_id] == 1
        assert len(recovery_handler.failure_history[task_id]) == 1
        assert result is True  # Should succeed since can_recover is True

    def test_handle_failure_increments_counter(self, recovery_handler):
        """Test that handle_failure increments failure counter"""
        task_id = "task1"
        error = Exception("Test error")

        # Multiple failures
        recovery_handler.handle_failure(task_id, error)
        recovery_handler.handle_failure(task_id, error)

        assert recovery_handler.failure_counts[task_id] == 2
        assert len(recovery_handler.failure_history[task_id]) == 2

    def test_handle_failure_records_history(self, recovery_handler):
        """Test that handle_failure records failure history"""
        task_id = "task1"
        error = Exception("Test error")

        recovery_handler.handle_failure(task_id, error)

        history = recovery_handler.failure_history[task_id]
        assert len(history) == 1
        assert "timestamp" in history[0]
        assert history[0]["error"] == "Test error"
        assert history[0]["failure_count"] == 1

    def test_handle_failure_max_attempts_exceeded(self, recovery_handler):
        """Test handle_failure when max attempts exceeded"""
        task_id = "task1"
        error = Exception("Test error")

        # Reach max attempts (3)
        for _ in range(3):
            recovery_handler.handle_failure(task_id, error)

        # 4th failure should fail
        result = recovery_handler.handle_failure(task_id, error)
        assert result is False

    def test_handle_failure_with_logger(self, recovery_handler):
        """Test handle_failure with logger attached"""
        task_id = "task1"
        error = Exception("Test error")
        logger = Mock()
        recovery_handler.logger = logger

        recovery_handler.handle_failure(task_id, error)

        # Verify logger was called
        assert logger.warning.call_count >= 1
        assert logger.info.call_count >= 1

    def test_handle_failure_multiple_tasks(self, recovery_handler):
        """Test handling failures for multiple tasks"""
        error = Exception("Test error")

        recovery_handler.handle_failure("task1", error)
        recovery_handler.handle_failure("task2", error)
        recovery_handler.handle_failure("task1", error)

        assert recovery_handler.failure_counts["task1"] == 2
        assert recovery_handler.failure_counts["task2"] == 1


class TestCanRecover:
    """Test can_recover method"""

    def test_can_recover_first_failure(self, recovery_handler):
        """Test can_recover returns True on first failure"""
        task_id = "task1"
        recovery_handler.failure_counts[task_id] = 1

        assert recovery_handler.can_recover(task_id) is True

    def test_can_recover_below_max(self, recovery_handler):
        """Test can_recover returns True when below max attempts"""
        task_id = "task1"
        recovery_handler.failure_counts[task_id] = 2

        assert recovery_handler.can_recover(task_id) is True

    def test_can_recover_at_max(self, recovery_handler):
        """Test can_recover returns False at max attempts"""
        task_id = "task1"
        recovery_handler.failure_counts[task_id] = 3

        assert recovery_handler.can_recover(task_id) is False

    def test_can_recover_no_failures(self, recovery_handler):
        """Test can_recover with no previous failures"""
        task_id = "task1"

        # No failure count means 0 failures, should be able to recover
        assert recovery_handler.can_recover(task_id) is True


class TestRecover:
    """Test recover method"""

    def test_recover_basic(self, recovery_handler):
        """Test basic recovery"""
        task_id = "task1"

        result = recovery_handler.recover(task_id)

        # Current implementation returns True by default
        assert result is True

    def test_recover_respects_restart_delay(self, recovery_handler):
        """Test that recover respects restart delay"""
        task_id = "task1"
        recovery_handler.failure_counts[task_id] = 1

        start_time = time.time()
        recovery_handler.recover(task_id)
        elapsed = time.time() - start_time

        # Should have some delay (at least 0.01s from fixture)
        assert elapsed >= 0.01

    def test_recover_exponential_backoff(self, exponential_handler):
        """Test recover with exponential backoff delays"""
        task_id = "task1"

        # First recovery (failure_count=0)
        start_time = time.time()
        exponential_handler.recover(task_id)
        elapsed1 = time.time() - start_time

        # Second recovery (failure_count=1 after handle_failure)
        exponential_handler.failure_counts[task_id] = 1
        start_time = time.time()
        exponential_handler.recover(task_id)
        elapsed2 = time.time() - start_time

        # Second should take longer due to backoff
        # (0.01 * 2^0 = 0.01, 0.01 * 2^1 = 0.02)
        assert elapsed2 >= elapsed1

    def test_recover_with_logger(self, recovery_handler):
        """Test recover with logger attached"""
        task_id = "task1"
        logger = Mock()
        recovery_handler.logger = logger

        recovery_handler.recover(task_id)

        # Verify logger was called
        assert logger.info.call_count >= 1

    def test_recover_incremental_failure_count(self, recovery_handler):
        """Test recover uses current failure count for delay"""
        task_id = "task1"

        # Set failure count
        recovery_handler.failure_counts[task_id] = 2

        # Recover should use this count for delay calculation
        result = recovery_handler.recover(task_id)
        assert result is True


class TestRecoverJob:
    """Test recover_job method"""

    def test_recover_job_successful(self, recovery_handler):
        """Test successful job recovery"""
        job_id = "job123"
        dispatcher = Mock()
        dispatcher.start = Mock()

        result = recovery_handler.recover_job(job_id, dispatcher, restart_count=0)

        assert result["success"] is True
        assert result["job_id"] == job_id
        assert result["restart_count"] == 1
        dispatcher.start.assert_called_once()

    def test_recover_job_with_restart_count(self, recovery_handler):
        """Test job recovery tracks restart count"""
        job_id = "job123"
        dispatcher = Mock()
        dispatcher.start = Mock()

        result = recovery_handler.recover_job(job_id, dispatcher, restart_count=5)

        assert result["restart_count"] == 6

    def test_recover_job_dispatcher_fails(self, recovery_handler):
        """Test job recovery when dispatcher start fails"""
        job_id = "job123"
        dispatcher = Mock()
        dispatcher.start = Mock(side_effect=Exception("Start failed"))

        result = recovery_handler.recover_job(job_id, dispatcher, restart_count=0)

        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Start failed"

    def test_recover_job_with_logger(self, recovery_handler):
        """Test job recovery with logger attached"""
        job_id = "job123"
        dispatcher = Mock()
        dispatcher.start = Mock()
        logger = Mock()
        recovery_handler.logger = logger

        recovery_handler.recover_job(job_id, dispatcher, restart_count=0)

        # Verify logger was called
        assert logger.info.call_count >= 1


class TestGetFailureStatistics:
    """Test get_failure_statistics method"""

    def test_get_statistics_for_specific_task(self, recovery_handler):
        """Test getting statistics for a specific task"""
        task_id = "task1"
        error = Exception("Test error")

        recovery_handler.handle_failure(task_id, error)
        recovery_handler.handle_failure(task_id, error)

        stats = recovery_handler.get_failure_statistics(task_id)

        assert stats["task_id"] == task_id
        assert stats["failure_count"] == 2
        assert len(stats["failure_history"]) == 2

    def test_get_statistics_for_nonexistent_task(self, recovery_handler):
        """Test getting statistics for nonexistent task"""
        task_id = "nonexistent"

        stats = recovery_handler.get_failure_statistics(task_id)

        assert stats["task_id"] == task_id
        assert stats["failure_count"] == 0
        assert stats["failure_history"] == []

    def test_get_statistics_all_tasks(self, recovery_handler):
        """Test getting statistics for all tasks"""
        error = Exception("Test error")

        recovery_handler.handle_failure("task1", error)
        recovery_handler.handle_failure("task1", error)
        recovery_handler.handle_failure("task2", error)

        stats = recovery_handler.get_failure_statistics(None)

        assert stats["total_failed_tasks"] == 2
        assert stats["total_failures"] == 3
        assert stats["failure_counts"]["task1"] == 2
        assert stats["failure_counts"]["task2"] == 1

    def test_get_statistics_empty(self, recovery_handler):
        """Test getting statistics when no failures"""
        stats = recovery_handler.get_failure_statistics(None)

        assert stats["total_failed_tasks"] == 0
        assert stats["total_failures"] == 0
        assert stats["failure_counts"] == {}


class TestResetFailureCount:
    """Test reset_failure_count method"""

    def test_reset_failure_count(self, recovery_handler):
        """Test resetting failure count for a task"""
        task_id = "task1"
        error = Exception("Test error")

        recovery_handler.handle_failure(task_id, error)
        recovery_handler.handle_failure(task_id, error)

        # Reset
        recovery_handler.reset_failure_count(task_id)

        assert task_id not in recovery_handler.failure_counts
        assert task_id not in recovery_handler.failure_history

    def test_reset_nonexistent_task(self, recovery_handler):
        """Test resetting failure count for nonexistent task"""
        task_id = "nonexistent"

        # Should not raise exception
        recovery_handler.reset_failure_count(task_id)

    def test_reset_preserves_other_tasks(self, recovery_handler):
        """Test that reset only affects specified task"""
        error = Exception("Test error")

        recovery_handler.handle_failure("task1", error)
        recovery_handler.handle_failure("task2", error)

        recovery_handler.reset_failure_count("task1")

        assert "task1" not in recovery_handler.failure_counts
        assert "task2" in recovery_handler.failure_counts


class TestCallbacks:
    """Test callback methods (inherited from base)"""

    def test_on_failure_detected_in_handle_failure(self, recovery_handler):
        """Test that on_failure_detected is called during handle_failure"""
        task_id = "task1"
        error = Exception("Test error")

        # Mock the callback
        with patch.object(recovery_handler, "on_failure_detected") as mock_callback:
            recovery_handler.handle_failure(task_id, error)
            mock_callback.assert_called_once_with(task_id, error)

    def test_on_recovery_started_in_recover(self, recovery_handler):
        """Test that on_recovery_started is called during recover"""
        task_id = "task1"

        with patch.object(recovery_handler, "on_recovery_started") as mock_callback:
            recovery_handler.recover(task_id)
            mock_callback.assert_called_once_with(task_id)

    def test_on_recovery_completed_in_recover(self, recovery_handler):
        """Test that on_recovery_completed is called during recover"""
        task_id = "task1"

        with patch.object(recovery_handler, "on_recovery_completed") as mock_callback:
            recovery_handler.recover(task_id)
            mock_callback.assert_called_once_with(task_id, True)


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_multiple_failures_same_task(self, recovery_handler):
        """Test multiple failures for the same task"""
        task_id = "task1"
        error = Exception("Test error")

        results = []
        for _ in range(5):
            result = recovery_handler.handle_failure(task_id, error)
            results.append(result)

        # With max_attempts=3: failure_count < 3 allows recovery
        # Attempt 1 (count=1): can recover -> True
        # Attempt 2 (count=2): can recover -> True
        # Attempt 3 (count=3): cannot recover (3 < 3 is False) -> False
        # Attempt 4 (count=4): cannot recover -> False
        # Attempt 5 (count=5): cannot recover -> False
        assert results == [True, True, False, False, False]

    def test_concurrent_task_failures(self, recovery_handler):
        """Test handling failures for multiple tasks concurrently"""
        error = Exception("Test error")
        tasks = [f"task{i}" for i in range(5)]

        for task_id in tasks:
            result = recovery_handler.handle_failure(task_id, error)
            assert result is True

        # Verify all tracked
        assert len(recovery_handler.failure_counts) == 5

    def test_very_short_delay(self):
        """Test recovery with very short delays"""
        strategy = FixedDelayStrategy(delay=0.001, max_attempts=3)
        handler = RestartBasedRecovery(restart_strategy=strategy)

        task_id = "task1"

        start = time.time()
        handler.recover(task_id)
        elapsed = time.time() - start

        # Should complete quickly
        assert elapsed < 1.0

    def test_zero_delay(self):
        """Test recovery with zero delay"""
        strategy = FixedDelayStrategy(delay=0.0, max_attempts=3)
        handler = RestartBasedRecovery(restart_strategy=strategy)

        task_id = "task1"

        # Should not raise exception
        result = handler.recover(task_id)
        assert result is True

    def test_failure_history_timestamps_ordered(self, recovery_handler):
        """Test that failure history maintains chronological order"""
        task_id = "task1"
        error = Exception("Test error")

        for _ in range(3):
            recovery_handler.handle_failure(task_id, error)
            time.sleep(0.01)

        history = recovery_handler.failure_history[task_id]
        timestamps = [entry["timestamp"] for entry in history]

        # Verify chronological order
        assert timestamps == sorted(timestamps)

    def test_failure_counts_consistency(self, recovery_handler):
        """Test that failure counts stay consistent with history"""
        task_id = "task1"
        error = Exception("Test error")

        for i in range(3):
            recovery_handler.handle_failure(task_id, error)

            # Check consistency
            assert recovery_handler.failure_counts[task_id] == i + 1
            assert len(recovery_handler.failure_history[task_id]) == i + 1
            assert recovery_handler.failure_history[task_id][-1]["failure_count"] == i + 1

    def test_different_strategies_different_delays(self):
        """Test that different strategies produce different delay behaviors"""
        fixed = RestartBasedRecovery(restart_strategy=FixedDelayStrategy(delay=0.01))
        exponential = RestartBasedRecovery(
            restart_strategy=ExponentialBackoffStrategy(initial_delay=0.01)
        )

        task_id = "task1"

        # Measure delays for same failure count
        fixed.failure_counts[task_id] = 2
        exponential.failure_counts[task_id] = 2

        fixed_delay = fixed.restart_strategy.get_restart_delay(2)
        exp_delay = exponential.restart_strategy.get_restart_delay(2)

        # Exponential should be larger
        assert exp_delay > fixed_delay
