"""
Unit tests for sage.middleware.operators.rag.writer module.
Tests MemoryWriter operator.
"""

from unittest.mock import Mock

import pytest

try:
    from sage.middleware.operators.rag.writer import MemoryWriter

    WRITER_AVAILABLE = True
except ImportError as e:
    WRITER_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Writer module not available: {e}")


@pytest.mark.unit
class TestMemoryWriter:
    """Test MemoryWriter operator."""

    def test_initialization_no_memory_types(self):
        """Test MemoryWriter initialization without memory types."""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer not available")

        config = {}
        writer = MemoryWriter(config)

        assert writer.state is None
        assert writer.config == {}
        assert writer.collections == {}

    def test_initialization_with_stm(self):
        """Test MemoryWriter initialization with STM config."""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer not available")

        config = {
            "stm": True,
            "stm_collection": "short_term_memory",
            "stm_config": {"max_size": 100},
        }
        writer = MemoryWriter(config)

        assert "stm" in writer.collections
        assert writer.collections["stm"]["collection"] == "short_term_memory"
        assert writer.collections["stm"]["config"] == {"max_size": 100}

    def test_initialization_with_ltm(self):
        """Test MemoryWriter initialization with LTM config."""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer not available")

        config = {
            "ltm": True,
            "ltm_collection": "long_term_memory",
            "ltm_config": {"persistence": True},
        }
        writer = MemoryWriter(config)

        assert "ltm" in writer.collections
        assert writer.collections["ltm"]["collection"] == "long_term_memory"
        assert writer.collections["ltm"]["config"] == {"persistence": True}

    def test_initialization_with_dcm(self):
        """Test MemoryWriter initialization with DCM config."""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer not available")

        config = {
            "dcm": True,
            "dcm_collection": "dynamic_context_memory",
            "dcm_config": {"ttl": 3600},
        }
        writer = MemoryWriter(config)

        assert "dcm" in writer.collections
        assert writer.collections["dcm"]["collection"] == "dynamic_context_memory"
        assert writer.collections["dcm"]["config"] == {"ttl": 3600}

    def test_initialization_with_all_memory_types(self):
        """Test MemoryWriter initialization with all memory types."""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer not available")

        config = {
            "stm": True,
            "stm_collection": "stm",
            "stm_config": {},
            "ltm": True,
            "ltm_collection": "ltm",
            "ltm_config": {},
            "dcm": True,
            "dcm_collection": "dcm",
            "dcm_config": {},
        }
        writer = MemoryWriter(config)

        assert len(writer.collections) == 3
        assert "stm" in writer.collections
        assert "ltm" in writer.collections
        assert "dcm" in writer.collections

    def test_execute_with_string_input(self):
        """Test execute with string input."""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer not available")

        config = {}
        writer = MemoryWriter(config)

        result = writer.execute("test string")

        # Should return original data
        assert result == "test string"

    def test_execute_with_list_input(self):
        """Test execute with list input."""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer not available")

        config = {}
        writer = MemoryWriter(config)

        input_data = ["item1", "item2", "item3"]
        result = writer.execute(input_data)

        assert result == input_data

    def test_execute_with_tuple_input(self):
        """Test execute with tuple input (query, context pattern)."""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer not available")

        config = {}
        writer = MemoryWriter(config)

        input_data = ("query: ", "what is AI?")
        result = writer.execute(input_data)

        assert result == input_data

    def test_execute_with_unsupported_type(self):
        """Test execute with unsupported data type."""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer not available")

        config = {}
        writer = MemoryWriter(config)

        input_data = {"key": "value"}  # Dict not supported
        result = writer.execute(input_data)

        # Should return original data
        assert result == input_data

    def test_execute_without_state_manager(self):
        """Test execute without state manager (should log warning)."""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer not available")

        config = {
            "stm": True,
            "stm_collection": "test_stm",
            "stm_config": {},
        }
        writer = MemoryWriter(config)

        # State is None by default
        result = writer.execute("test data")

        # Should return original data even without state
        assert result == "test data"

    def test_execute_with_state_manager(self):
        """Test execute with mocked state manager."""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer not available")

        config = {
            "stm": True,
            "stm_collection": "test_stm",
            "stm_config": {"max_size": 50},
        }
        writer = MemoryWriter(config)

        # Mock state manager
        mock_state = Mock()
        writer.state = mock_state

        result = writer.execute("test document")

        # Should call state.store
        mock_state.store.assert_called_once()
        call_args = mock_state.store.call_args[1]
        assert call_args["collection"] == "test_stm"
        assert call_args["documents"] == ["test document"]
        assert call_args["collection_config"] == {"max_size": 50}

        # Should return original data
        assert result == "test document"

    def test_execute_with_multiple_collections(self):
        """Test execute writes to multiple collections."""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer not available")

        config = {
            "stm": True,
            "stm_collection": "stm",
            "stm_config": {},
            "ltm": True,
            "ltm_collection": "ltm",
            "ltm_config": {},
        }
        writer = MemoryWriter(config)

        mock_state = Mock()
        writer.state = mock_state

        writer.execute(["doc1", "doc2"])

        # Should be called twice (once for stm, once for ltm)
        assert mock_state.store.call_count == 2

    def test_execute_with_missing_collection_name(self):
        """Test execute handles missing collection name."""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer not available")

        config = {
            "stm": True,
            # stm_collection is missing
            "stm_config": {},
        }
        writer = MemoryWriter(config)

        mock_state = Mock()
        writer.state = mock_state

        result = writer.execute("test")

        # Should not call store when collection is None
        mock_state.store.assert_not_called()
        assert result == "test"

    def test_execute_with_store_exception(self):
        """Test execute handles store exceptions gracefully."""
        if not WRITER_AVAILABLE:
            pytest.skip("Writer not available")

        config = {
            "stm": True,
            "stm_collection": "test_stm",
            "stm_config": {},
        }
        writer = MemoryWriter(config)

        mock_state = Mock()
        mock_state.store.side_effect = Exception("Storage failed")
        writer.state = mock_state

        # Should not raise exception
        result = writer.execute("test data")

        # Should still return original data
        assert result == "test data"
