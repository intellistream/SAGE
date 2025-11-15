"""
Comprehensive tests for ContextFileSink class.

Tests cover initialization, configuration, file operations, indexing,
directory organization, and various edge cases.
"""

import json
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sage.middleware.context.model_context import ModelContext
from sage.middleware.operators.filters.context_sink import ContextFileSink


class TestContextFileSinkInitialization:
    """Test ContextFileSink initialization and configuration."""

    def test_get_default_template_directory(self, tmp_path):
        """Test getting default template directory."""
        with patch(
            "sage.middleware.operators.filters.context_sink.os.getcwd", return_value=str(tmp_path)
        ):
            default_dir = ContextFileSink.get_default_template_directory()
            expected = str(tmp_path / "data" / "model_context")
            assert default_dir == expected
            assert Path(default_dir).exists()

    def test_get_default_config(self):
        """Test default configuration."""
        config = ContextFileSink.get_default_config()

        assert config["base_directory"] is None
        assert config["stage_directory"] == "general"
        assert config["file_format"] == "json"
        assert config["organization"] == "date"
        assert config["max_files_per_dir"] == 1000
        assert config["create_index"] is True
        assert config["auto_create_dirs"] is True
        assert config["compress_old_files"] is False
        assert config["backup_index"] is True

    def test_init_with_valid_config(self, tmp_path):
        """Test initialization with valid config."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "file_format": "jsonl",
            "organization": "uuid",
        }
        sink = ContextFileSink(config=config)

        assert sink.config["base_directory"] == str(tmp_path)
        assert sink.config["stage_directory"] == "test_stage"
        assert sink.config["file_format"] == "jsonl"
        assert sink.config["organization"] == "uuid"
        assert sink.full_directory.exists()

    def test_init_with_invalid_config_type(self):
        """Test initialization with invalid config type raises TypeError."""
        with pytest.raises(TypeError, match="Expected a dict for config"):
            ContextFileSink(config="not_a_dict")

    def test_init_with_empty_config(self, tmp_path):
        """Test initialization with empty config uses defaults."""
        config = {}
        sink = ContextFileSink(config=config)

        assert sink.config["stage_directory"] == "general"
        assert sink.config["file_format"] == "json"
        assert sink.config["organization"] == "date"

    def test_init_with_legacy_parameters(self, tmp_path):
        """Test backward compatibility with legacy parameters."""
        config = {"base_directory": str(tmp_path)}
        sink = ContextFileSink(
            config=config,
            stage_directory="custom_stage",
            file_format="jsonl",
        )

        # Legacy params should override config if provided
        assert sink.config["stage_directory"] == "custom_stage"
        assert sink.config["file_format"] == "jsonl"

    def test_init_creates_directories(self, tmp_path):
        """Test that initialization creates necessary directories."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "my_stage",
            "auto_create_dirs": True,
        }
        sink = ContextFileSink(config=config)

        assert sink.full_directory.exists()
        assert sink.full_directory == tmp_path / "my_stage"


class TestContextFileSinkDirectorySetup:
    """Test directory setup and organization."""

    def test_setup_directories_with_base_directory(self, tmp_path):
        """Test directory setup with base directory."""
        config = {"base_directory": str(tmp_path), "stage_directory": "stage1"}
        sink = ContextFileSink(config=config)

        assert sink.base_directory == tmp_path
        assert sink.stage_directory == tmp_path / "stage1"
        assert sink.full_directory == tmp_path / "stage1"

    def test_setup_directories_with_default_base(self, tmp_path):
        """Test directory setup with default base directory."""
        config = {"base_directory": None, "stage_directory": "stage1"}
        with patch(
            "sage.middleware.operators.filters.context_sink.ContextFileSink.get_default_template_directory",
            return_value=str(tmp_path / "data" / "model_context"),
        ):
            sink = ContextFileSink(config=config)
            assert str(sink.base_directory).endswith("data/model_context")

    def test_setup_directories_auto_create_disabled(self, tmp_path):
        """Test directory setup with auto_create_dirs disabled."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "stage1",
            "auto_create_dirs": False,
            "create_index": False,  # Disable index creation to avoid file creation errors
        }
        sink = ContextFileSink(config=config)

        # Directory should not exist since auto_create_dirs is False
        assert not sink.full_directory.exists()

    def test_set_stage_directory(self, tmp_path):
        """Test dynamically setting stage directory."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "initial_stage",
        }
        sink = ContextFileSink(config=config)
        old_dir = sink.full_directory

        sink.set_stage_directory("new_stage")

        assert sink.config["stage_directory"] == "new_stage"
        assert sink.full_directory == tmp_path / "new_stage"
        assert sink.full_directory != old_dir


class TestContextFileSinkIndexing:
    """Test index file creation and updates."""

    def test_initialize_index(self, tmp_path):
        """Test index file initialization."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "create_index": True,
        }
        sink = ContextFileSink(config=config)

        assert sink.index_file.exists()
        with open(sink.index_file, encoding="utf-8") as f:
            index_data = json.load(f)

        assert "created_at" in index_data
        assert index_data["total_templates"] == 0
        assert "config" in index_data
        assert "directory_structure" in index_data
        assert "templates" in index_data

    def test_index_not_created_when_disabled(self, tmp_path):
        """Test that index is not created when create_index is False."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "create_index": False,
        }
        sink = ContextFileSink(config=config)

        assert not sink.index_file.exists()

    def test_index_backup_on_reinit(self, tmp_path):
        """Test that existing index is backed up when reinitializing."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "create_index": True,
            "backup_index": True,
        }
        sink = ContextFileSink(config=config)

        # Reinitialize with new sink
        sink._initialize_index()

        # Backup should be created
        backup_files = list((tmp_path / "test_stage").glob("template_index.backup_*.json"))
        assert len(backup_files) > 0


class TestContextFileSinkFilePathGeneration:
    """Test file path generation based on organization strategy."""

    def create_model_context(self, uuid="test-uuid", sequence=1, timestamp=None):
        """Helper to create a ModelContext instance."""
        if timestamp is None:
            timestamp = int(time.time() * 1000)

        ctx = ModelContext(
            uuid=uuid,
            sequence=sequence,
            timestamp=timestamp,
            raw_question="test question",
        )
        return ctx

    def test_get_file_path_date_organization(self, tmp_path):
        """Test file path with date-based organization."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "organization": "date",
            "file_format": "json",
        }
        sink = ContextFileSink(config=config)

        ctx = self.create_model_context(timestamp=1704067200000)  # 2024-01-01
        file_path = sink._get_file_path(ctx)

        # Path should contain year/month/day structure
        assert "2024" in str(file_path)
        assert "01" in str(file_path)
        assert "01" in str(file_path)
        assert file_path.name.startswith("template_")
        assert file_path.suffix == ".json"

    def test_get_file_path_sequence_organization(self, tmp_path):
        """Test file path with sequence-based organization."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "organization": "sequence",
            "file_format": "json",
            "max_files_per_dir": 1000,
        }
        sink = ContextFileSink(config=config)

        ctx = self.create_model_context(sequence=100)
        file_path = sink._get_file_path(ctx)

        assert "seq_000000-000999" in str(file_path)
        assert file_path.suffix == ".json"

    def test_get_file_path_uuid_organization(self, tmp_path):
        """Test file path with UUID-based organization."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "organization": "uuid",
            "file_format": "json",
        }
        sink = ContextFileSink(config=config)

        ctx = self.create_model_context(uuid="abcdef1234567890")
        file_path = sink._get_file_path(ctx)

        # Path should contain first two chars as first dir, next two as second dir
        assert "ab" in str(file_path) or "cd" in str(file_path)

    def test_get_file_path_with_jsonl_format(self, tmp_path):
        """Test file path with JSONL format."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "organization": "date",
            "file_format": "jsonl",
        }
        sink = ContextFileSink(config=config)

        ctx = self.create_model_context()
        file_path = sink._get_file_path(ctx)

        assert file_path.suffix == ".jsonl"

    def test_get_file_path_creates_directories(self, tmp_path):
        """Test that get_file_path creates necessary directories."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "organization": "uuid",
            "auto_create_dirs": True,
        }
        sink = ContextFileSink(config=config)

        ctx = self.create_model_context(uuid="abcd1234567890ef")
        file_path = sink._get_file_path(ctx)

        # Directory should be created
        assert file_path.parent.exists()


class TestContextFileSinkExecution:
    """Test file saving and index updates."""

    def create_model_context(self, uuid="test-uuid"):
        """Helper to create a ModelContext instance."""
        ctx = ModelContext(
            uuid=uuid,
            sequence=1,
            timestamp=int(time.time() * 1000),
            raw_question="test question",
            response="test response",
        )
        return ctx

    @patch("sage.middleware.operators.filters.context_sink.ModelContext.save_to_file")
    def test_execute_saves_json_file(self, mock_save, tmp_path):
        """Test that execute saves file in JSON format."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "file_format": "json",
            "create_index": False,
        }
        sink = ContextFileSink(config=config)

        ctx = self.create_model_context()
        sink.execute(ctx)

        # Check that save_to_file was called
        assert mock_save.called

    def test_execute_saves_jsonl_file(self, tmp_path):
        """Test that execute saves file in JSONL format."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "file_format": "jsonl",
            "organization": "date",
            "create_index": False,
        }
        sink = ContextFileSink(config=config)

        ctx = self.create_model_context()
        with patch.object(ctx, "to_json", return_value='{"test": "data"}'):
            sink.execute(ctx)

        # Find and verify JSONL file was created
        jsonl_files = list(tmp_path.glob("**/template_*.jsonl"))
        assert len(jsonl_files) > 0

    def test_execute_updates_index(self, tmp_path):
        """Test that execute updates the index file."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "create_index": True,
        }
        sink = ContextFileSink(config=config)

        ctx = self.create_model_context(uuid="test-uuid-123")
        with patch.object(ctx, "save_to_file"):
            sink.execute(ctx)

        # Check index was updated
        with open(sink.index_file, encoding="utf-8") as f:
            index_data = json.load(f)

        assert index_data["total_templates"] == 1
        assert "test-uuid-123" in index_data["templates"]

    def test_execute_increments_saved_count(self, tmp_path):
        """Test that execute increments saved_count."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "create_index": False,
        }
        sink = ContextFileSink(config=config)

        ctx1 = self.create_model_context(uuid="uuid1")
        ctx2 = self.create_model_context(uuid="uuid2")

        with patch.object(ctx1, "save_to_file"):
            sink.execute(ctx1)
            assert sink.saved_count == 1

        with patch.object(ctx2, "save_to_file"):
            sink.execute(ctx2)
            assert sink.saved_count == 2

    def test_execute_handles_exceptions(self, tmp_path):
        """Test that execute handles exceptions gracefully."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "create_index": False,
        }
        sink = ContextFileSink(config=config)

        ctx = self.create_model_context()
        with patch.object(ctx, "save_to_file", side_effect=Exception("Test error")):
            # Should not raise, but log error
            sink.execute(ctx)
            assert sink.saved_count == 0


class TestContextFileSinkStatistics:
    """Test statistics and information methods."""

    def test_get_storage_info(self, tmp_path):
        """Test getting storage information."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
        }
        sink = ContextFileSink(config=config)

        info = sink.get_storage_info()

        assert "config" in info
        assert "directory_structure" in info
        assert "runtime_stats" in info
        assert info["runtime_stats"]["saved_count"] == 0
        assert info["directory_structure"]["stage_directory"] == str(tmp_path / "test_stage")

    def test_get_stage_statistics_no_index(self, tmp_path):
        """Test get_stage_statistics when index doesn't exist."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "create_index": False,
        }
        sink = ContextFileSink(config=config)

        stats = sink.get_stage_statistics()

        assert "error" in stats

    def test_get_stage_statistics_with_data(self, tmp_path):
        """Test get_stage_statistics with template data."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "create_index": True,
        }
        sink = ContextFileSink(config=config)

        # Manually add template to index
        with open(sink.index_file, encoding="utf-8") as f:
            index_data = json.load(f)

        index_data["total_templates"] = 2
        index_data["templates"]["uuid1"] = {
            "has_response": True,
            "response_length": 100,
            "chunks_count": 5,
            "prompts_count": 3,
            "timestamp": 1704067200000,
        }
        index_data["templates"]["uuid2"] = {
            "has_response": False,
            "response_length": 0,
            "chunks_count": 3,
            "prompts_count": 2,
            "timestamp": 1704067300000,
        }

        with open(sink.index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f)

        stats = sink.get_stage_statistics()

        assert stats["total_templates"] == 2
        assert stats["with_response"] == 1
        assert stats["without_response"] == 1
        assert stats["avg_chunks"] > 0
        assert stats["avg_prompts"] > 0


class TestContextFileSinkRuntimeInit:
    """Test runtime initialization."""

    def test_runtime_init(self, tmp_path):
        """Test runtime_init logs correctly."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
        }
        sink = ContextFileSink(config=config)

        # Verify runtime_init doesn't raise an exception
        sink.runtime_init(Mock())
        # If we reach here, the test passes (logger is written internally)


class TestContextFileSinkThreadSafety:
    """Test thread safety of index operations."""

    def test_index_lock_exists(self, tmp_path):
        """Test that index_lock is created."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "create_index": True,
        }
        sink = ContextFileSink(config=config)

        # Check that index_lock exists and is a lock-like object
        assert hasattr(sink, "index_lock")
        assert sink.index_lock is not None
        assert hasattr(sink.index_lock, "acquire")
        assert hasattr(sink.index_lock, "release")

    def test_concurrent_index_updates(self, tmp_path):
        """Test concurrent index updates are handled safely."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "create_index": True,
            "file_format": "json",
        }
        sink = ContextFileSink(config=config)

        def update_index():
            ctx = ModelContext(
                uuid=f"test-uuid-{threading.current_thread().ident}",
                sequence=1,
                timestamp=int(time.time() * 1000),
                raw_question="test",
                response="test",
            )
            with patch.object(ctx, "save_to_file"):
                sink.execute(ctx)

        threads = [threading.Thread(target=update_index) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify all updates were recorded
        with open(sink.index_file, encoding="utf-8") as f:
            index_data = json.load(f)

        assert index_data["total_templates"] == 5


class TestContextFileSinkEdgeCases:
    """Test edge cases and error conditions."""

    def test_execute_with_none_response(self, tmp_path):
        """Test execute with None response."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "create_index": True,
        }
        sink = ContextFileSink(config=config)

        ctx = ModelContext(
            uuid="test-uuid",
            sequence=1,
            timestamp=int(time.time() * 1000),
            raw_question="test question",
            response=None,
        )

        with patch.object(ctx, "save_to_file"):
            sink.execute(ctx)

        # Should complete without error
        assert sink.saved_count == 1

    def test_execute_with_empty_raw_question(self, tmp_path):
        """Test execute with empty raw_question."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "create_index": True,
        }
        sink = ContextFileSink(config=config)

        ctx = ModelContext(
            uuid="test-uuid",
            sequence=1,
            timestamp=int(time.time() * 1000),
            raw_question=None,
            response="test response",
        )

        with patch.object(ctx, "save_to_file"):
            sink.execute(ctx)

        assert sink.saved_count == 1

    def test_large_sequence_numbers(self, tmp_path):
        """Test with large sequence numbers."""
        config = {
            "base_directory": str(tmp_path),
            "stage_directory": "test_stage",
            "organization": "sequence",
            "max_files_per_dir": 1000,
        }
        sink = ContextFileSink(config=config)

        ctx = ModelContext(
            uuid="test-uuid",
            sequence=999999,
            timestamp=int(time.time() * 1000),
            raw_question="test",
        )

        file_path = sink._get_file_path(ctx)

        # Should handle large numbers gracefully
        assert file_path is not None
        assert file_path.parent.exists() or not sink.config["auto_create_dirs"]
