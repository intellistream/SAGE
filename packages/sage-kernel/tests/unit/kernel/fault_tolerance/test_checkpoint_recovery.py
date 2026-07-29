"""
Tests for CheckpointBasedRecovery

Comprehensive test coverage for checkpoint-based fault tolerance recovery strategy.
"""

import tempfile
import time
from unittest.mock import Mock, patch

import pytest

from sage.kernel.fault_tolerance.impl.checkpoint_impl import CheckpointManagerImpl
from sage.kernel.fault_tolerance.impl.checkpoint_recovery import CheckpointBasedRecovery


@pytest.fixture
def temp_checkpoint_dir():
    """Create a temporary directory for checkpoints"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def checkpoint_manager(temp_checkpoint_dir):
    """Create a checkpoint manager instance"""
    return CheckpointManagerImpl(temp_checkpoint_dir)


@pytest.fixture
def recovery_handler(checkpoint_manager):
    """Create a recovery handler instance"""
    return CheckpointBasedRecovery(
        checkpoint_manager=checkpoint_manager,
        checkpoint_interval=1.0,  # Short interval for testing
        max_recovery_attempts=3,
    )


@pytest.fixture
def sample_state():
    """Sample task state"""
    return {
        "processed_count": 100,
        "checkpoint_counter": 5,
        "data": "test_data",
    }


class TestCheckpointBasedRecoveryInitialization:
    """Test CheckpointBasedRecovery initialization"""

    def test_init_with_checkpoint_manager(self, checkpoint_manager):
        """Test initialization with provided checkpoint manager"""
        handler = CheckpointBasedRecovery(checkpoint_manager=checkpoint_manager)
        assert handler.checkpoint_manager is checkpoint_manager
        assert handler.checkpoint_interval == 60.0
        assert handler.max_recovery_attempts == 3
        assert handler.failure_counts == {}
        assert handler.last_checkpoint_time == {}

    def test_init_with_custom_parameters(self, checkpoint_manager):
        """Test initialization with custom parameters"""
        handler = CheckpointBasedRecovery(
            checkpoint_manager=checkpoint_manager,
            checkpoint_interval=30.0,
            max_recovery_attempts=5,
            checkpoint_dir="/tmp/test",
        )
        assert handler.checkpoint_interval == 30.0
        assert handler.max_recovery_attempts == 5

    def test_init_creates_default_checkpoint_manager(self):
        """Test initialization creates default checkpoint manager if not provided"""
        handler = CheckpointBasedRecovery(checkpoint_dir=".sage/test_checkpoints")
        assert handler.checkpoint_manager is not None
        assert isinstance(handler.checkpoint_manager, CheckpointManagerImpl)


class TestSaveCheckpoint:
    """Test save_checkpoint method"""

    def test_save_checkpoint_basic(self, recovery_handler, sample_state):
        """Test basic checkpoint saving"""
        task_id = "task1"
        result = recovery_handler.save_checkpoint(task_id, sample_state)
        assert result is True
        assert task_id in recovery_handler.last_checkpoint_time

        # Verify checkpoint was saved
        loaded = recovery_handler.checkpoint_manager.load_checkpoint(task_id)
        assert loaded == sample_state

    def test_save_checkpoint_respects_interval(self, recovery_handler, sample_state):
        """Test that checkpoint saving respects time interval"""
        task_id = "task1"

        # First save should succeed
        result1 = recovery_handler.save_checkpoint(task_id, sample_state)
        assert result1 is True

        # Immediate second save should fail (interval not elapsed)
        result2 = recovery_handler.save_checkpoint(task_id, sample_state)
        assert result2 is False

    def test_save_checkpoint_force_ignores_interval(self, recovery_handler, sample_state):
        """Test that force=True ignores time interval"""
        task_id = "task1"

        # First save
        recovery_handler.save_checkpoint(task_id, sample_state)

        # Immediate second save with force=True should succeed
        modified_state = {**sample_state, "processed_count": 200}
        result = recovery_handler.save_checkpoint(task_id, modified_state, force=True)
        assert result is True

        # Verify latest state
        loaded = recovery_handler.checkpoint_manager.load_checkpoint(task_id)
        assert loaded["processed_count"] == 200

    def test_save_checkpoint_after_interval_elapsed(self, recovery_handler, sample_state):
        """Test checkpoint saving after interval has elapsed"""
        task_id = "task1"

        # First save
        recovery_handler.save_checkpoint(task_id, sample_state)

        # Wait for interval to elapse
        time.sleep(1.1)

        # Second save should succeed
        modified_state = {**sample_state, "processed_count": 200}
        result = recovery_handler.save_checkpoint(task_id, modified_state)
        assert result is True

    def test_save_checkpoint_error_handling(self, recovery_handler, sample_state):
        """Test error handling during checkpoint save"""
        task_id = "task1"

        # Mock checkpoint manager to raise error
        with patch.object(
            recovery_handler.checkpoint_manager,
            "save_checkpoint",
            side_effect=Exception("Save failed"),
        ):
            result = recovery_handler.save_checkpoint(task_id, sample_state)
            assert result is False

    def test_save_checkpoint_with_logger(self, recovery_handler, sample_state):
        """Test checkpoint saving with logger attached"""
        task_id = "task1"
        logger = Mock()
        recovery_handler.logger = logger

        recovery_handler.save_checkpoint(task_id, sample_state)
        logger.debug.assert_called_once()

    def test_save_checkpoint_multiple_tasks(self, recovery_handler, sample_state):
        """Test saving checkpoints for multiple tasks"""
        tasks = ["task1", "task2", "task3"]

        for task_id in tasks:
            result = recovery_handler.save_checkpoint(task_id, sample_state)
            assert result is True

        # Verify all checkpoints exist
        for task_id in tasks:
            loaded = recovery_handler.checkpoint_manager.load_checkpoint(task_id)
            assert loaded is not None


class TestCanRecover:
    """Test can_recover method"""

    def test_can_recover_with_checkpoint(self, recovery_handler, sample_state):
        """Test can_recover returns True when checkpoint exists and attempts < max"""
        task_id = "task1"

        # Save checkpoint
        recovery_handler.save_checkpoint(task_id, sample_state)

        # Should be able to recover
        assert recovery_handler.can_recover(task_id) is True

    def test_can_recover_no_checkpoint(self, recovery_handler):
        """Test can_recover returns False when no checkpoint exists"""
        task_id = "task1"

        # No checkpoint saved
        assert recovery_handler.can_recover(task_id) is False

    def test_can_recover_max_attempts_reached(self, recovery_handler, sample_state):
        """Test can_recover returns False when max attempts reached"""
        task_id = "task1"

        # Save checkpoint
        recovery_handler.save_checkpoint(task_id, sample_state)

        # Simulate max failures
        recovery_handler.failure_counts[task_id] = 3

        # Should not be able to recover
        assert recovery_handler.can_recover(task_id) is False

    def test_can_recover_just_below_max_attempts(self, recovery_handler, sample_state):
        """Test can_recover returns True when just below max attempts"""
        task_id = "task1"

        # Save checkpoint
        recovery_handler.save_checkpoint(task_id, sample_state)

        # Simulate failures just below max
        recovery_handler.failure_counts[task_id] = 2

        # Should still be able to recover
        assert recovery_handler.can_recover(task_id) is True


class TestHandleFailure:
    """Test handle_failure method"""

    def test_handle_failure_first_attempt(self, recovery_handler, sample_state):
        """Test handling first failure with successful recovery"""
        task_id = "task1"
        error = Exception("Test error")

        # Save checkpoint
        recovery_handler.save_checkpoint(task_id, sample_state)

        # Mock dispatcher
        dispatcher = Mock()
        dispatcher.restart_task_with_state = Mock(return_value=True)
        recovery_handler.dispatcher = dispatcher

        # Handle failure
        result = recovery_handler.handle_failure(task_id, error)

        assert result is True
        assert recovery_handler.failure_counts[task_id] == 1
        dispatcher.restart_task_with_state.assert_called_once()

    def test_handle_failure_increments_counter(self, recovery_handler, sample_state):
        """Test that handle_failure increments failure counter"""
        task_id = "task1"
        error = Exception("Test error")

        # Save checkpoint
        recovery_handler.save_checkpoint(task_id, sample_state)

        # Mock dispatcher
        dispatcher = Mock()
        dispatcher.restart_task_with_state = Mock(return_value=True)
        recovery_handler.dispatcher = dispatcher

        # Multiple failures
        recovery_handler.handle_failure(task_id, error)
        recovery_handler.handle_failure(task_id, error)

        assert recovery_handler.failure_counts[task_id] == 2

    def test_handle_failure_max_attempts_exceeded(self, recovery_handler, sample_state):
        """Test handle_failure when max attempts exceeded"""
        task_id = "task1"
        error = Exception("Test error")

        # Save checkpoint
        recovery_handler.save_checkpoint(task_id, sample_state)

        # Set failure count to max
        recovery_handler.failure_counts[task_id] = 3

        # Handle failure
        result = recovery_handler.handle_failure(task_id, error)

        assert result is False

    def test_handle_failure_no_checkpoint(self, recovery_handler):
        """Test handle_failure when no checkpoint exists"""
        task_id = "task1"
        error = Exception("Test error")

        # No checkpoint saved
        result = recovery_handler.handle_failure(task_id, error)

        assert result is False

    def test_handle_failure_with_logger(self, recovery_handler, sample_state):
        """Test handle_failure with logger attached"""
        task_id = "task1"
        error = Exception("Test error")
        logger = Mock()
        recovery_handler.logger = logger

        # Save checkpoint
        recovery_handler.save_checkpoint(task_id, sample_state)

        # Mock dispatcher
        dispatcher = Mock()
        dispatcher.restart_task_with_state = Mock(return_value=True)
        recovery_handler.dispatcher = dispatcher

        recovery_handler.handle_failure(task_id, error)

        # Verify logger was called
        assert logger.warning.call_count >= 1


class TestRecover:
    """Test recover method"""

    def test_recover_successful(self, recovery_handler, sample_state):
        """Test successful recovery from checkpoint"""
        task_id = "task1"

        # Save checkpoint
        recovery_handler.save_checkpoint(task_id, sample_state)

        # Mock dispatcher
        dispatcher = Mock()
        dispatcher.restart_task_with_state = Mock(return_value=True)
        recovery_handler.dispatcher = dispatcher

        # Recover
        result = recovery_handler.recover(task_id)

        assert result is True
        dispatcher.restart_task_with_state.assert_called_once_with(task_id, sample_state)

    def test_recover_no_checkpoint(self, recovery_handler):
        """Test recovery when no checkpoint exists"""
        task_id = "task1"

        # Mock dispatcher
        dispatcher = Mock()
        recovery_handler.dispatcher = dispatcher

        # Attempt recovery
        result = recovery_handler.recover(task_id)

        assert result is False

    def test_recover_no_dispatcher(self, recovery_handler, sample_state):
        """Test recovery when no dispatcher is available"""
        task_id = "task1"

        # Save checkpoint
        recovery_handler.save_checkpoint(task_id, sample_state)

        # No dispatcher
        recovery_handler.dispatcher = None

        # Attempt recovery
        result = recovery_handler.recover(task_id)

        assert result is False

    def test_recover_dispatcher_restart_fails(self, recovery_handler, sample_state):
        """Test recovery when dispatcher restart fails"""
        task_id = "task1"

        # Save checkpoint
        recovery_handler.save_checkpoint(task_id, sample_state)

        # Mock dispatcher with failing restart
        dispatcher = Mock()
        dispatcher.restart_task_with_state = Mock(return_value=False)
        recovery_handler.dispatcher = dispatcher

        # Attempt recovery
        result = recovery_handler.recover(task_id)

        assert result is False

    def test_recover_exception_during_recovery(self, recovery_handler, sample_state):
        """Test recovery when exception occurs during restart"""
        task_id = "task1"

        # Save checkpoint
        recovery_handler.save_checkpoint(task_id, sample_state)

        # Mock dispatcher to raise exception
        dispatcher = Mock()
        dispatcher.restart_task_with_state = Mock(side_effect=Exception("Restart failed"))
        recovery_handler.dispatcher = dispatcher

        # Attempt recovery
        result = recovery_handler.recover(task_id)

        assert result is False

    def test_recover_with_logger(self, recovery_handler, sample_state):
        """Test recovery with logger attached"""
        task_id = "task1"
        logger = Mock()
        recovery_handler.logger = logger

        # Save checkpoint
        recovery_handler.save_checkpoint(task_id, sample_state)

        # Mock dispatcher
        dispatcher = Mock()
        dispatcher.restart_task_with_state = Mock(return_value=True)
        recovery_handler.dispatcher = dispatcher

        recovery_handler.recover(task_id)

        # Verify logger was called for recovery
        assert logger.info.call_count >= 1


class TestCleanupCheckpoints:
    """Test cleanup_checkpoints method"""

    def test_cleanup_removes_checkpoints(self, recovery_handler, sample_state):
        """Test that cleanup removes all checkpoints for a task"""
        task_id = "task1"

        # Save checkpoint
        recovery_handler.save_checkpoint(task_id, sample_state)

        # Cleanup
        recovery_handler.cleanup_checkpoints(task_id)

        # Verify checkpoint is removed
        loaded = recovery_handler.checkpoint_manager.load_checkpoint(task_id)
        assert loaded is None

    def test_cleanup_removes_failure_counts(self, recovery_handler, sample_state):
        """Test that cleanup removes failure counts"""
        task_id = "task1"

        # Set failure count
        recovery_handler.failure_counts[task_id] = 2
        recovery_handler.last_checkpoint_time[task_id] = time.time()

        # Cleanup
        recovery_handler.cleanup_checkpoints(task_id)

        # Verify tracking data removed
        assert task_id not in recovery_handler.failure_counts
        assert task_id not in recovery_handler.last_checkpoint_time

    def test_cleanup_handles_nonexistent_task(self, recovery_handler):
        """Test cleanup handles nonexistent task gracefully"""
        task_id = "nonexistent"

        # Should not raise exception
        recovery_handler.cleanup_checkpoints(task_id)

    def test_cleanup_with_error_handling(self, recovery_handler):
        """Test cleanup error handling"""
        task_id = "task1"
        logger = Mock()
        recovery_handler.logger = logger

        # Mock checkpoint manager to raise error
        with patch.object(
            recovery_handler.checkpoint_manager,
            "delete_checkpoint",
            side_effect=Exception("Delete failed"),
        ):
            recovery_handler.cleanup_checkpoints(task_id)

            # Verify error was logged
            logger.error.assert_called_once()


class TestCallbacks:
    """Test callback methods"""

    def test_on_recovery_started_callback(self, recovery_handler):
        """Test on_recovery_started callback"""
        task_id = "task1"
        logger = Mock()
        recovery_handler.logger = logger

        recovery_handler.on_recovery_started(task_id)

        logger.info.assert_called_once()
        assert "Starting recovery" in logger.info.call_args[0][0]

    def test_on_recovery_completed_success(self, recovery_handler):
        """Test on_recovery_completed callback with success"""
        task_id = "task1"
        logger = Mock()
        recovery_handler.logger = logger

        recovery_handler.on_recovery_completed(task_id, True)

        logger.info.assert_called_once()
        assert "completed successfully" in logger.info.call_args[0][0]

    def test_on_recovery_completed_failure(self, recovery_handler):
        """Test on_recovery_completed callback with failure"""
        task_id = "task1"
        logger = Mock()
        recovery_handler.logger = logger

        recovery_handler.on_recovery_completed(task_id, False)

        logger.error.assert_called_once()
        assert "failed" in logger.error.call_args[0][0]

    def test_on_failure_detected_callback(self, recovery_handler):
        """Test on_failure_detected callback"""
        task_id = "task1"
        error = Exception("Test error")
        logger = Mock()
        recovery_handler.logger = logger

        recovery_handler.on_failure_detected(task_id, error)

        logger.warning.assert_called_once()
        assert "Failure detected" in logger.warning.call_args[0][0]


class TestIsRemoteTask:
    """Test _is_remote_task method"""

    def test_is_remote_task_no_dispatcher(self, recovery_handler):
        """Test _is_remote_task when no dispatcher is set"""
        task_id = "task1"
        result = recovery_handler._is_remote_task(task_id)
        assert result is False

    def test_is_remote_task_with_dispatcher_no_task(self, recovery_handler):
        """Test _is_remote_task when task doesn't exist in dispatcher"""
        task_id = "task1"
        dispatcher = Mock()
        dispatcher.tasks = {}
        recovery_handler.dispatcher = dispatcher

        result = recovery_handler._is_remote_task(task_id)
        assert result is False


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_multiple_failures_and_recoveries(self, recovery_handler, sample_state):
        """Test multiple failure and recovery cycles"""
        task_id = "task1"
        error = Exception("Test error")

        # Save checkpoint
        recovery_handler.save_checkpoint(task_id, sample_state)

        # Mock dispatcher
        dispatcher = Mock()
        dispatcher.restart_task_with_state = Mock(return_value=True)
        recovery_handler.dispatcher = dispatcher

        # Multiple failure-recovery cycles
        for i in range(2):
            result = recovery_handler.handle_failure(task_id, error)
            assert result is True

        assert recovery_handler.failure_counts[task_id] == 2

    def test_checkpoint_interval_zero(self, checkpoint_manager):
        """Test recovery handler with zero checkpoint interval"""
        handler = CheckpointBasedRecovery(
            checkpoint_manager=checkpoint_manager, checkpoint_interval=0.0
        )

        task_id = "task1"
        state = {"data": "test"}

        # All saves should succeed
        result1 = handler.save_checkpoint(task_id, state)
        result2 = handler.save_checkpoint(task_id, state)

        assert result1 is True
        assert result2 is True

    def test_max_recovery_attempts_one(self, checkpoint_manager, sample_state):
        """Test recovery handler with max_recovery_attempts=1"""
        handler = CheckpointBasedRecovery(
            checkpoint_manager=checkpoint_manager, max_recovery_attempts=1
        )

        task_id = "task1"
        handler.save_checkpoint(task_id, sample_state)

        # First failure should allow recovery
        handler.failure_counts[task_id] = 0
        assert handler.can_recover(task_id) is True

        # Second failure should not allow recovery
        handler.failure_counts[task_id] = 1
        assert handler.can_recover(task_id) is False

    def test_concurrent_task_handling(self, recovery_handler, sample_state):
        """Test handling multiple tasks concurrently"""
        tasks = [f"task{i}" for i in range(5)]

        # Save checkpoints for all tasks
        for task_id in tasks:
            recovery_handler.save_checkpoint(task_id, sample_state, force=True)

        # Verify all tasks can recover
        for task_id in tasks:
            assert recovery_handler.can_recover(task_id) is True

        # Cleanup all tasks
        for task_id in tasks:
            recovery_handler.cleanup_checkpoints(task_id)

        # Verify all cleaned up
        for task_id in tasks:
            assert recovery_handler.can_recover(task_id) is False
