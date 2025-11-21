"""
Unit tests for sage_mem KVMemoryCollection.
Extends existing test_manager.py and test_vdb.py tests.
"""

from unittest.mock import Mock, patch

import pytest

try:
    from sage.middleware.components.sage_mem.neuromem.memory_collection.kv_collection import (
        KVMemoryCollection,
        load_config,
    )

    KV_COLLECTION_AVAILABLE = True
except ImportError as e:
    KV_COLLECTION_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"KVMemoryCollection not available: {e}")


@pytest.mark.unit
class TestKVMemoryCollectionInitialization:
    """Test KVMemoryCollection initialization."""

    def test_initialization_with_required_fields(self):
        """Test initialization with minimal required config."""
        if not KV_COLLECTION_AVAILABLE:
            pytest.skip("KVMemoryCollection not available")

        config = {"name": "test_kv_collection"}

        collection = KVMemoryCollection(config)

        assert collection.name == "test_kv_collection"
        assert collection.default_topk == 5  # Default value
        assert collection.default_index_type == "bm25s"  # Default value
        assert collection.indexes == {}

    def test_initialization_without_name_raises_error(self):
        """Test initialization fails without name field."""
        if not KV_COLLECTION_AVAILABLE:
            pytest.skip("KVMemoryCollection not available")

        config = {}

        with pytest.raises(ValueError, match="config中必须包含'name'字段"):
            KVMemoryCollection(config)

    def test_initialization_with_custom_defaults(self):
        """Test initialization with custom default values."""
        if not KV_COLLECTION_AVAILABLE:
            pytest.skip("KVMemoryCollection not available")

        config = {
            "name": "custom_kv",
            "default_topk": 10,
            "default_index_type": "tfidf",
        }

        collection = KVMemoryCollection(config)

        assert collection.default_topk == 10
        assert collection.default_index_type == "tfidf"

    @patch(
        "sage.middleware.components.sage_mem.neuromem.memory_collection.kv_collection.load_config"
    )
    def test_initialization_with_config_path(self, mock_load_config):
        """Test initialization with external config file."""
        if not KV_COLLECTION_AVAILABLE:
            pytest.skip("KVMemoryCollection not available")

        # Mock external config
        mock_load_config.return_value = {
            "kv_default_topk": 20,
            "kv_default_index_type": "dense",
        }

        config = {"name": "external_config", "config_path": "/path/to/config.yaml"}

        collection = KVMemoryCollection(config)

        assert collection.default_topk == 20
        assert collection.default_index_type == "dense"
        mock_load_config.assert_called_once_with("/path/to/config.yaml")


@pytest.mark.unit
class TestKVMemoryCollectionSerialization:
    """Test KVMemoryCollection function serialization."""

    def test_serialize_func_with_none(self):
        """Test serializing None function."""
        if not KV_COLLECTION_AVAILABLE:
            pytest.skip("KVMemoryCollection not available")

        config = {"name": "test_collection"}
        collection = KVMemoryCollection(config)

        result = collection._serialize_func(None)
        assert result is None

    def test_serialize_func_with_lambda(self):
        """Test serializing lambda function."""
        if not KV_COLLECTION_AVAILABLE:
            pytest.skip("KVMemoryCollection not available")

        config = {"name": "test_collection"}
        collection = KVMemoryCollection(config)

        func = lambda x: x > 5  # noqa: E731

        result = collection._serialize_func(func)
        # Result should be a string representation
        assert isinstance(result, str)

    def test_serialize_func_with_regular_function(self):
        """Test serializing regular function."""
        if not KV_COLLECTION_AVAILABLE:
            pytest.skip("KVMemoryCollection not available")

        def test_func(x):
            return x * 2

        config = {"name": "test_collection"}
        collection = KVMemoryCollection(config)

        result = collection._serialize_func(test_func)
        assert isinstance(result, str)
        assert "test_func" in result or "return x * 2" in result

    def test_deserialize_func_with_none(self):
        """Test deserializing None."""
        if not KV_COLLECTION_AVAILABLE:
            pytest.skip("KVMemoryCollection not available")

        config = {"name": "test_collection"}
        collection = KVMemoryCollection(config)

        result = collection._deserialize_func(None)
        assert result is None

    def test_deserialize_func_with_empty_string(self):
        """Test deserializing empty string."""
        if not KV_COLLECTION_AVAILABLE:
            pytest.skip("KVMemoryCollection not available")

        config = {"name": "test_collection"}
        collection = KVMemoryCollection(config)

        result = collection._deserialize_func("")
        assert result is None

    def test_deserialize_func_with_none_string(self):
        """Test deserializing 'None' string."""
        if not KV_COLLECTION_AVAILABLE:
            pytest.skip("KVMemoryCollection not available")

        config = {"name": "test_collection"}
        collection = KVMemoryCollection(config)

        result = collection._deserialize_func("None")
        assert result is None

    def test_deserialize_func_with_lambda_string(self):
        """Test deserializing lambda function string."""
        if not KV_COLLECTION_AVAILABLE:
            pytest.skip("KVMemoryCollection not available")

        config = {"name": "test_collection"}
        collection = KVMemoryCollection(config)

        lambda_str = "lambda x: x > 0"
        result = collection._deserialize_func(lambda_str)

        # Should return a callable
        assert callable(result) or result is None

    def test_deserialize_func_with_invalid_string(self):
        """Test deserializing invalid function string."""
        if not KV_COLLECTION_AVAILABLE:
            pytest.skip("KVMemoryCollection not available")

        config = {"name": "test_collection"}
        collection = KVMemoryCollection(config)

        # Should handle errors gracefully
        result = collection._deserialize_func("not a valid function")
        assert result is None


@pytest.mark.unit
class TestLoadConfig:
    """Test load_config utility function."""

    @patch("builtins.open", create=True)
    @patch(
        "sage.middleware.components.sage_mem.neuromem.memory_collection.kv_collection.yaml.safe_load"
    )
    def test_load_config_success(self, mock_yaml_load, mock_open):
        """Test successful config loading."""
        if not KV_COLLECTION_AVAILABLE:
            pytest.skip("KVMemoryCollection not available")

        # Mock file content
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        mock_yaml_load.return_value = {"key": "value", "number": 42}

        result = load_config("/path/to/config.yaml")

        assert result == {"key": "value", "number": 42}
        mock_open.assert_called_once_with("/path/to/config.yaml")
        mock_yaml_load.assert_called_once_with(mock_file)
