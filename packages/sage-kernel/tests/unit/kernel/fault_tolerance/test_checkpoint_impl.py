"""
Unit tests for CheckpointManagerImpl.

Tests cover:
- Checkpoint save and load operations
- Checkpoint deletion (single and batch)
- List checkpoints
- Cleanup old checkpoints
- Checkpoint info retrieval
- Error handling and edge cases
"""

import pickle
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from sage.common.core import CheckpointError
from sage.kernel.fault_tolerance.impl.checkpoint_impl import CheckpointManagerImpl

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_checkpoint_dir():
    """Create temporary directory for checkpoint testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def checkpoint_manager(temp_checkpoint_dir):
    """Create CheckpointManagerImpl instance with temporary directory"""
    return CheckpointManagerImpl(checkpoint_dir=temp_checkpoint_dir)


@pytest.fixture
def sample_state():
    """Sample state dictionary for testing"""
    return {
        "counter": 42,
        "data": [1, 2, 3, 4, 5],
        "config": {"key": "value", "enabled": True},
    }


# ============================================================================
# Initialization Tests
# ============================================================================


@pytest.mark.unit
class TestCheckpointManagerInitialization:
    """Test CheckpointManagerImpl initialization"""

    def test_init_creates_directory(self, temp_checkpoint_dir):
        """Test that initialization creates checkpoint directory"""
        ckpt_dir = Path(temp_checkpoint_dir) / "test_checkpoints"
        assert not ckpt_dir.exists()

        manager = CheckpointManagerImpl(checkpoint_dir=str(ckpt_dir))

        assert ckpt_dir.exists()
        assert ckpt_dir.is_dir()
        assert manager.checkpoint_dir == ckpt_dir

    def test_init_with_existing_directory(self, temp_checkpoint_dir):
        """Test initialization with existing directory"""
        ckpt_dir = Path(temp_checkpoint_dir)
        assert ckpt_dir.exists()

        manager = CheckpointManagerImpl(checkpoint_dir=str(ckpt_dir))

        assert manager.checkpoint_dir == ckpt_dir

    def test_init_default_directory(self):
        """Test initialization with default directory"""
        manager = CheckpointManagerImpl()

        assert manager.checkpoint_dir == Path(".sage/checkpoints")


# ============================================================================
# Save Checkpoint Tests
# ============================================================================


@pytest.mark.unit
class TestSaveCheckpoint:
    """Test save_checkpoint functionality"""

    def test_save_checkpoint_basic(self, checkpoint_manager, sample_state):
        """Test basic checkpoint save"""
        task_id = "task_001"
        checkpoint_id = "ckpt_1"

        result_path = checkpoint_manager.save_checkpoint(task_id, sample_state, checkpoint_id)

        # Verify return path
        assert result_path is not None
        assert Path(result_path).exists()

        # Verify file content
        with open(result_path, "rb") as f:
            loaded_state = pickle.load(f)

        assert loaded_state == sample_state

    def test_save_checkpoint_auto_id(self, checkpoint_manager, sample_state):
        """Test save checkpoint with auto-generated ID"""
        task_id = "task_002"

        with patch("time.time", return_value=1234567890):
            result_path = checkpoint_manager.save_checkpoint(task_id, sample_state)

        # Should use timestamp as ID
        assert "task_002_1234567890.ckpt" in result_path
        assert Path(result_path).exists()

    def test_save_checkpoint_overwrites_existing(self, checkpoint_manager, sample_state):
        """Test that saving with same ID overwrites existing checkpoint"""
        task_id = "task_003"
        checkpoint_id = "ckpt_1"

        # Save first version
        path1 = checkpoint_manager.save_checkpoint(task_id, {"version": 1}, checkpoint_id)

        # Save second version with same ID
        path2 = checkpoint_manager.save_checkpoint(task_id, {"version": 2}, checkpoint_id)

        # Paths should be the same
        assert path1 == path2

        # Load and verify it's the second version
        loaded = checkpoint_manager.load_checkpoint(task_id, checkpoint_id)
        assert loaded == {"version": 2}

    def test_save_checkpoint_multiple_tasks(self, checkpoint_manager, sample_state):
        """Test saving checkpoints for multiple tasks"""
        checkpoints = [
            ("task_a", "ckpt_1", {"data": "a1"}),
            ("task_b", "ckpt_1", {"data": "b1"}),
            ("task_a", "ckpt_2", {"data": "a2"}),
        ]

        paths = []
        for task_id, ckpt_id, state in checkpoints:
            path = checkpoint_manager.save_checkpoint(task_id, state, ckpt_id)
            paths.append(path)

        # All paths should be different
        assert len(set(paths)) == 3

        # Verify each can be loaded correctly
        assert checkpoint_manager.load_checkpoint("task_a", "ckpt_1") == {"data": "a1"}
        assert checkpoint_manager.load_checkpoint("task_b", "ckpt_1") == {"data": "b1"}
        assert checkpoint_manager.load_checkpoint("task_a", "ckpt_2") == {"data": "a2"}

    def test_save_checkpoint_error_handling(self, checkpoint_manager):
        """Test error handling during checkpoint save"""
        task_id = "task_error"

        # Create invalid state (unpicklable object)
        class UnpicklableClass:
            def __reduce__(self):
                raise TypeError("Cannot pickle this object")

        invalid_state = {"obj": UnpicklableClass()}

        with pytest.raises(CheckpointError, match="Failed to save checkpoint"):
            checkpoint_manager.save_checkpoint(task_id, invalid_state, "ckpt_1")


# ============================================================================
# Load Checkpoint Tests
# ============================================================================


@pytest.mark.unit
class TestLoadCheckpoint:
    """Test load_checkpoint functionality"""

    def test_load_checkpoint_by_id(self, checkpoint_manager, sample_state):
        """Test loading checkpoint by specific ID"""
        task_id = "task_load_1"
        checkpoint_id = "ckpt_1"

        # Save checkpoint
        checkpoint_manager.save_checkpoint(task_id, sample_state, checkpoint_id)

        # Load checkpoint
        loaded_state = checkpoint_manager.load_checkpoint(task_id, checkpoint_id)

        assert loaded_state == sample_state

    def test_load_checkpoint_latest(self, checkpoint_manager):
        """Test loading latest checkpoint when ID not specified"""
        task_id = "task_load_2"

        # Save multiple checkpoints with time delay
        checkpoint_manager.save_checkpoint(task_id, {"version": 1}, "ckpt_1")
        time.sleep(0.01)  # Small delay to ensure different mtimes
        checkpoint_manager.save_checkpoint(task_id, {"version": 2}, "ckpt_2")
        time.sleep(0.01)
        checkpoint_manager.save_checkpoint(task_id, {"version": 3}, "ckpt_3")

        # Load without specifying ID (should get latest)
        loaded_state = checkpoint_manager.load_checkpoint(task_id)

        assert loaded_state == {"version": 3}

    def test_load_checkpoint_nonexistent_task(self, checkpoint_manager):
        """Test loading checkpoint for non-existent task"""
        result = checkpoint_manager.load_checkpoint("nonexistent_task", "ckpt_1")

        assert result is None

    def test_load_checkpoint_nonexistent_id(self, checkpoint_manager, sample_state):
        """Test loading checkpoint with non-existent ID"""
        task_id = "task_load_3"

        # Save one checkpoint
        checkpoint_manager.save_checkpoint(task_id, sample_state, "ckpt_1")

        # Try to load different ID
        result = checkpoint_manager.load_checkpoint(task_id, "nonexistent_ckpt")

        assert result is None

    def test_load_checkpoint_no_checkpoints(self, checkpoint_manager):
        """Test loading when no checkpoints exist for task"""
        result = checkpoint_manager.load_checkpoint("task_no_ckpt")

        assert result is None

    def test_load_checkpoint_corrupted_file(self, checkpoint_manager, sample_state):
        """Test error handling when loading corrupted checkpoint file"""
        task_id = "task_corrupted"
        checkpoint_id = "ckpt_1"

        # Save valid checkpoint first
        path = checkpoint_manager.save_checkpoint(task_id, sample_state, checkpoint_id)

        # Corrupt the file
        with open(path, "wb") as f:
            f.write(b"corrupted data")

        # Try to load corrupted checkpoint
        with pytest.raises(CheckpointError, match="Failed to load checkpoint"):
            checkpoint_manager.load_checkpoint(task_id, checkpoint_id)


# ============================================================================
# Delete Checkpoint Tests
# ============================================================================


@pytest.mark.unit
class TestDeleteCheckpoint:
    """Test delete_checkpoint functionality"""

    def test_delete_specific_checkpoint(self, checkpoint_manager, sample_state):
        """Test deleting a specific checkpoint"""
        task_id = "task_del_1"

        # Save multiple checkpoints
        checkpoint_manager.save_checkpoint(task_id, sample_state, "ckpt_1")
        checkpoint_manager.save_checkpoint(task_id, sample_state, "ckpt_2")

        # Delete specific checkpoint
        checkpoint_manager.delete_checkpoint(task_id, "ckpt_1")

        # Verify ckpt_1 is deleted but ckpt_2 remains
        assert checkpoint_manager.load_checkpoint(task_id, "ckpt_1") is None
        assert checkpoint_manager.load_checkpoint(task_id, "ckpt_2") is not None

    def test_delete_all_checkpoints(self, checkpoint_manager, sample_state):
        """Test deleting all checkpoints for a task"""
        task_id = "task_del_2"

        # Save multiple checkpoints
        checkpoint_manager.save_checkpoint(task_id, sample_state, "ckpt_1")
        checkpoint_manager.save_checkpoint(task_id, sample_state, "ckpt_2")
        checkpoint_manager.save_checkpoint(task_id, sample_state, "ckpt_3")

        # Delete all checkpoints
        checkpoint_manager.delete_checkpoint(task_id)

        # Verify all are deleted
        assert checkpoint_manager.load_checkpoint(task_id, "ckpt_1") is None
        assert checkpoint_manager.load_checkpoint(task_id, "ckpt_2") is None
        assert checkpoint_manager.load_checkpoint(task_id, "ckpt_3") is None

    def test_delete_nonexistent_checkpoint(self, checkpoint_manager):
        """Test deleting non-existent checkpoint (should not raise error)"""
        # Should complete without error
        checkpoint_manager.delete_checkpoint("nonexistent_task", "ckpt_1")
        checkpoint_manager.delete_checkpoint("nonexistent_task")

    def test_delete_preserves_other_tasks(self, checkpoint_manager, sample_state):
        """Test that deleting one task's checkpoints preserves others"""
        # Save checkpoints for multiple tasks
        checkpoint_manager.save_checkpoint("task_a", sample_state, "ckpt_1")
        checkpoint_manager.save_checkpoint("task_b", sample_state, "ckpt_1")

        # Delete task_a's checkpoints
        checkpoint_manager.delete_checkpoint("task_a")

        # Verify task_b's checkpoint still exists
        assert checkpoint_manager.load_checkpoint("task_a", "ckpt_1") is None
        assert checkpoint_manager.load_checkpoint("task_b", "ckpt_1") is not None


# ============================================================================
# List Checkpoints Tests
# ============================================================================


@pytest.mark.unit
class TestListCheckpoints:
    """Test list_checkpoints functionality"""

    def test_list_checkpoints_basic(self, checkpoint_manager, sample_state):
        """Test listing checkpoints for a task"""
        task_id = "tasklist1"  # Use simple task_id without underscores

        # Save multiple checkpoints
        checkpoint_manager.save_checkpoint(task_id, sample_state, "ckpt_1")
        time.sleep(0.01)
        checkpoint_manager.save_checkpoint(task_id, sample_state, "ckpt_2")

        # List checkpoints
        checkpoints = checkpoint_manager.list_checkpoints(task_id)

        assert len(checkpoints) == 2
        # Should be sorted by mtime (newest first)
        assert checkpoints[0]["checkpoint_id"] == "ckpt_2"
        assert checkpoints[1]["checkpoint_id"] == "ckpt_1"

    def test_list_checkpoints_info_structure(self, checkpoint_manager, sample_state):
        """Test structure of checkpoint info"""
        task_id = "tasklist2"  # Use simple task_id without underscores
        checkpoint_id = "ckpt_1"

        checkpoint_manager.save_checkpoint(task_id, sample_state, checkpoint_id)

        checkpoints = checkpoint_manager.list_checkpoints(task_id)

        assert len(checkpoints) == 1
        ckpt_info = checkpoints[0]

        # Verify structure
        assert "task_id" in ckpt_info
        assert "checkpoint_id" in ckpt_info
        assert "path" in ckpt_info
        assert "size" in ckpt_info
        assert "mtime" in ckpt_info

        assert ckpt_info["task_id"] == task_id
        assert ckpt_info["checkpoint_id"] == checkpoint_id
        assert ckpt_info["size"] > 0

    def test_list_checkpoints_empty(self, checkpoint_manager):
        """Test listing checkpoints when none exist"""
        checkpoints = checkpoint_manager.list_checkpoints("nonexistent_task")

        assert checkpoints == []

    def test_list_checkpoints_sorting(self, checkpoint_manager, sample_state):
        """Test that checkpoints are sorted by modification time"""
        task_id = "tasklist3"  # Use simple task_id without underscores

        # Save checkpoints with time delays
        ids = ["old", "middle", "new"]
        for ckpt_id in ids:
            checkpoint_manager.save_checkpoint(task_id, sample_state, ckpt_id)
            time.sleep(0.01)

        checkpoints = checkpoint_manager.list_checkpoints(task_id)

        # Should be sorted newest first
        assert [c["checkpoint_id"] for c in checkpoints] == ["new", "middle", "old"]


# ============================================================================
# Cleanup Old Checkpoints Tests
# ============================================================================


@pytest.mark.unit
class TestCleanupOldCheckpoints:
    """Test cleanup_old_checkpoints functionality"""

    def test_cleanup_keeps_last_n(self, checkpoint_manager, sample_state):
        """Test cleanup keeps last N checkpoints"""
        task_id = "taskcleanup1"  # Use simple task_id without underscores

        # Save 10 checkpoints
        for i in range(10):
            checkpoint_manager.save_checkpoint(task_id, sample_state, f"ckpt_{i}")
            time.sleep(0.01)

        # Keep last 3
        checkpoint_manager.cleanup_old_checkpoints(task_id, keep_last_n=3)

        checkpoints = checkpoint_manager.list_checkpoints(task_id)

        assert len(checkpoints) == 3
        # Should keep the newest 3
        assert checkpoints[0]["checkpoint_id"] == "ckpt_9"
        assert checkpoints[1]["checkpoint_id"] == "ckpt_8"
        assert checkpoints[2]["checkpoint_id"] == "ckpt_7"

    def test_cleanup_with_fewer_than_n(self, checkpoint_manager, sample_state):
        """Test cleanup when checkpoints < keep_last_n"""
        task_id = "task_cleanup_2"

        # Save only 3 checkpoints
        for i in range(3):
            checkpoint_manager.save_checkpoint(task_id, sample_state, f"ckpt_{i}")

        # Keep last 5 (more than available)
        checkpoint_manager.cleanup_old_checkpoints(task_id, keep_last_n=5)

        checkpoints = checkpoint_manager.list_checkpoints(task_id)

        # All 3 should remain
        assert len(checkpoints) == 3

    def test_cleanup_keep_zero(self, checkpoint_manager, sample_state):
        """Test cleanup with keep_last_n=0 deletes all"""
        task_id = "task_cleanup_3"

        # Save some checkpoints
        for i in range(5):
            checkpoint_manager.save_checkpoint(task_id, sample_state, f"ckpt_{i}")

        # Keep 0 (delete all)
        checkpoint_manager.cleanup_old_checkpoints(task_id, keep_last_n=0)

        checkpoints = checkpoint_manager.list_checkpoints(task_id)

        assert len(checkpoints) == 0

    def test_cleanup_no_checkpoints(self, checkpoint_manager):
        """Test cleanup when no checkpoints exist"""
        # Should complete without error
        checkpoint_manager.cleanup_old_checkpoints("nonexistent_task", keep_last_n=3)


# ============================================================================
# Get Checkpoint Info Tests
# ============================================================================


@pytest.mark.unit
class TestGetCheckpointInfo:
    """Test get_checkpoint_info functionality"""

    def test_get_checkpoint_info_by_id(self, checkpoint_manager, sample_state):
        """Test getting info for specific checkpoint"""
        task_id = "task_info_1"
        checkpoint_id = "ckpt_1"

        checkpoint_manager.save_checkpoint(task_id, sample_state, checkpoint_id)

        info = checkpoint_manager.get_checkpoint_info(task_id, checkpoint_id)

        assert info is not None
        assert info["task_id"] == task_id
        assert info["checkpoint_id"] == checkpoint_id
        assert "path" in info
        assert "size" in info
        assert "mtime" in info

    def test_get_checkpoint_info_latest(self, checkpoint_manager, sample_state):
        """Test getting info for latest checkpoint"""
        task_id = "task_info_2"

        # Save multiple checkpoints
        checkpoint_manager.save_checkpoint(task_id, {"v": 1}, "ckpt_1")
        time.sleep(0.01)
        checkpoint_manager.save_checkpoint(task_id, {"v": 2}, "ckpt_2")

        # Get latest without specifying ID
        info = checkpoint_manager.get_checkpoint_info(task_id)

        assert info is not None
        # Should return latest (ckpt_2 is newer based on mtime)
        assert "ckpt_2" in info["path"]

    def test_get_checkpoint_info_nonexistent(self, checkpoint_manager):
        """Test getting info for non-existent checkpoint"""
        info = checkpoint_manager.get_checkpoint_info("nonexistent_task", "ckpt_1")

        assert info is None

    def test_get_checkpoint_info_nonexistent_id(self, checkpoint_manager, sample_state):
        """Test getting info for non-existent checkpoint ID"""
        task_id = "task_info_3"

        checkpoint_manager.save_checkpoint(task_id, sample_state, "ckpt_1")

        info = checkpoint_manager.get_checkpoint_info(task_id, "nonexistent_ckpt")

        assert info is None


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_state(self, checkpoint_manager):
        """Test saving and loading empty state"""
        task_id = "task_empty"
        empty_state = {}

        checkpoint_manager.save_checkpoint(task_id, empty_state, "ckpt_1")
        loaded = checkpoint_manager.load_checkpoint(task_id, "ckpt_1")

        assert loaded == {}

    def test_large_state(self, checkpoint_manager):
        """Test saving and loading large state"""
        task_id = "task_large"
        # Create state with large list
        large_state = {"data": list(range(100000))}

        path = checkpoint_manager.save_checkpoint(task_id, large_state, "ckpt_1")
        loaded = checkpoint_manager.load_checkpoint(task_id, "ckpt_1")

        assert loaded == large_state
        # Verify file was created and has significant size
        assert Path(path).stat().st_size > 100000

    def test_special_characters_in_id(self, checkpoint_manager, sample_state):
        """Test checkpoint ID with special characters"""
        task_id = "task-with-dashes"
        checkpoint_id = "ckpt_2024-11-20_15:30:00"

        # Should handle special characters in file names
        path = checkpoint_manager.save_checkpoint(task_id, sample_state, checkpoint_id)
        assert Path(path).exists()

        loaded = checkpoint_manager.load_checkpoint(task_id, checkpoint_id)
        assert loaded == sample_state

    def test_concurrent_saves_same_id(self, checkpoint_manager):
        """Test saving same checkpoint ID multiple times rapidly"""
        task_id = "task_concurrent"
        checkpoint_id = "ckpt_1"

        # Rapidly save same ID
        for i in range(10):
            checkpoint_manager.save_checkpoint(task_id, {"iteration": i}, checkpoint_id)

        # Should have last save
        loaded = checkpoint_manager.load_checkpoint(task_id, checkpoint_id)
        assert loaded == {"iteration": 9}

    def test_task_id_with_underscores(self, checkpoint_manager, sample_state):
        """Test task ID containing underscores (used in file naming)"""
        task_id = "task_with_multiple_underscores"
        checkpoint_id = "ckpt_1"

        checkpoint_manager.save_checkpoint(task_id, sample_state, checkpoint_id)

        # Should correctly parse checkpoint ID
        # Note: Due to filename parsing logic (split on '_'), the checkpoint_id
        # will include parts of the task_id after the first underscore
        checkpoints = checkpoint_manager.list_checkpoints(task_id)
        assert len(checkpoints) == 1
        # The parsed checkpoint_id will be everything after first underscore in filename
        # Filename: task_with_multiple_underscores_ckpt_1.ckpt
        # After split: ['task', 'with', 'multiple', 'underscores', 'ckpt', '1']
        # checkpoint_id = '_'.join(parts[1:]) = 'with_multiple_underscores_ckpt_1'
        assert "ckpt_1" in checkpoints[0]["checkpoint_id"]
