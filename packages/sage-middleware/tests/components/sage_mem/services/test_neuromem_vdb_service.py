"""
Unit tests for NeuroMemVDBService
"""

from unittest.mock import MagicMock, Mock, patch

import pytest


class TestNeuroMemVDBServiceInit:
    """Test NeuroMemVDBService initialization"""

    @patch("sage.middleware.components.sage_mem.services.neuromem_vdb_service.MemoryManager")
    def test_init_with_single_collection(self, mock_manager_class):
        """Test initialization with a single collection name"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        # Mock manager and collection
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_collection = MagicMock()
        mock_collection.indexes = {"global_index": {}}
        mock_manager.get_collection.return_value = mock_collection

        service = NeuroMemVDBService("test_collection")

        assert "test_collection" in service.online_register_collections
        assert service.online_register_collections["test_collection"] == mock_collection
        mock_manager.get_collection.assert_called_once_with("test_collection")

    @patch("sage.middleware.components.sage_mem.services.neuromem_vdb_service.MemoryManager")
    def test_init_with_list_of_collections(self, mock_manager_class):
        """Test initialization with list of collection names"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_collection1 = MagicMock()
        mock_collection1.indexes = {"global_index": {}}
        mock_collection2 = MagicMock()
        mock_collection2.indexes = {"global_index": {}}

        mock_manager.get_collection.side_effect = [mock_collection1, mock_collection2]

        service = NeuroMemVDBService(["collection1", "collection2"])

        assert len(service.online_register_collections) == 2
        assert "collection1" in service.online_register_collections
        assert "collection2" in service.online_register_collections

    @patch("sage.middleware.components.sage_mem.services.neuromem_vdb_service.MemoryManager")
    def test_init_creates_global_index_if_missing(self, mock_manager_class):
        """Test that global_index is created if it doesn't exist"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_collection = MagicMock()
        mock_collection.indexes = {}  # No global_index
        mock_manager.get_collection.return_value = mock_collection

        NeuroMemVDBService("test_collection")

        # Should have called create_index to create global_index
        mock_collection.create_index.assert_called_once_with(
            "global_index", description="Global index for all data"
        )

    @patch("sage.middleware.components.sage_mem.services.neuromem_vdb_service.MemoryManager")
    def test_init_fails_on_nonexistent_collection(self, mock_manager_class):
        """Test initialization fails when collection doesn't exist"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_collection.return_value = None

        with pytest.raises(ValueError, match="Collection 'nonexistent' not found"):
            NeuroMemVDBService("nonexistent")

    @patch("sage.middleware.components.sage_mem.services.neuromem_vdb_service.MemoryManager")
    def test_init_fails_on_wrong_collection_type(self, mock_manager_class):
        """Test initialization fails when collection is not VDBMemoryCollection"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        # Return a non-VDBMemoryCollection object
        mock_collection = Mock()  # Not a VDBMemoryCollection
        mock_manager.get_collection.return_value = mock_collection

        with pytest.raises(TypeError, match="is not a VDBMemoryCollection"):
            NeuroMemVDBService("test_collection")


class TestNeuroMemVDBServiceRetrieve:
    """Test retrieve functionality"""

    @patch("sage.middleware.components.sage_mem.services.neuromem_vdb_service.MemoryManager")
    def test_retrieve_from_single_collection(self, mock_manager_class):
        """Test retrieval from a single collection"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_collection = MagicMock()
        mock_collection.indexes = {"global_index": {}}
        mock_collection.retrieve.return_value = ["result1", "result2", "result3"]
        mock_manager.get_collection.return_value = mock_collection

        service = NeuroMemVDBService("test_collection")
        results = service.retrieve("test query", topk=3)

        assert len(results) == 3
        mock_collection.retrieve.assert_called_once()

    @patch("sage.middleware.components.sage_mem.services.neuromem_vdb_service.MemoryManager")
    def test_retrieve_with_metadata(self, mock_manager_class):
        """Test retrieval with metadata"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_collection = MagicMock()
        mock_collection.indexes = {"global_index": {}}
        mock_collection.retrieve.return_value = [
            {"text": "result1", "score": 0.9},
            {"text": "result2", "score": 0.8},
        ]
        mock_manager.get_collection.return_value = mock_collection

        service = NeuroMemVDBService("test_collection")
        results = service.retrieve("test query", topk=2, with_metadata=True)

        assert len(results) == 2
        assert all("source_collection" in r for r in results)
        assert all(r["source_collection"] == "test_collection" for r in results)

    @patch("sage.middleware.components.sage_mem.services.neuromem_vdb_service.MemoryManager")
    def test_retrieve_from_specific_collection(self, mock_manager_class):
        """Test retrieval from a specific collection"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_collection1 = MagicMock()
        mock_collection1.indexes = {"global_index": {}}
        mock_collection1.retrieve.return_value = ["result1"]

        mock_collection2 = MagicMock()
        mock_collection2.indexes = {"global_index": {}}
        mock_collection2.retrieve.return_value = ["result2"]

        mock_manager.get_collection.side_effect = [mock_collection1, mock_collection2]

        service = NeuroMemVDBService(["collection1", "collection2"])
        service.retrieve("test query", topk=5, collection_name="collection1")

        # Should only retrieve from collection1
        mock_collection1.retrieve.assert_called_once()
        mock_collection2.retrieve.assert_not_called()

    @patch("sage.middleware.components.sage_mem.services.neuromem_vdb_service.MemoryManager")
    def test_retrieve_no_collections(self, mock_manager_class):
        """Test retrieval when no collections are registered"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        # Create service without initializing collections
        service = NeuroMemVDBService.__new__(NeuroMemVDBService)
        service.manager = mock_manager
        service.online_register_collections = {}

        # Patch the logger property instead of trying to assign to it
        with patch.object(type(service), "logger", new_callable=lambda: MagicMock()):
            results = service.retrieve("test query")

            assert results == []

    @patch("sage.middleware.components.sage_mem.services.neuromem_vdb_service.MemoryManager")
    def test_retrieve_invalid_collection_name(self, mock_manager_class):
        """Test retrieval with invalid collection name"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_collection = MagicMock()
        mock_collection.indexes = {"global_index": {}}
        mock_manager.get_collection.return_value = mock_collection

        service = NeuroMemVDBService("test_collection")

        with pytest.raises(ValueError, match="Collection 'invalid' is not registered"):
            service.retrieve("test query", collection_name="invalid")

    @patch("sage.middleware.components.sage_mem.services.neuromem_vdb_service.MemoryManager")
    def test_retrieve_limits_to_topk(self, mock_manager_class):
        """Test that retrieve limits results to topk"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_collection = MagicMock()
        mock_collection.indexes = {"global_index": {}}
        mock_collection.retrieve.return_value = [f"result{i}" for i in range(10)]
        mock_manager.get_collection.return_value = mock_collection

        service = NeuroMemVDBService("test_collection")
        results = service.retrieve("test query", topk=3)

        # Results should be limited to topk (3), but we added source info, so check length
        assert len(results) <= 3


class TestNeuroMemVDBServiceIndexCreation:
    """Test index creation functionality"""

    @patch("sage.middleware.components.sage_mem.services.neuromem_vdb_service.MemoryManager")
    def test_create_index(self, mock_manager_class):
        """Test creating an index"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_collection = MagicMock()
        mock_collection.indexes = {"global_index": {}}
        mock_manager.get_collection.return_value = mock_collection

        service = NeuroMemVDBService("test_collection")
        service._create_index("test_collection", "new_index", description="Test index")

        mock_collection.create_index.assert_called()

    @patch("sage.middleware.components.sage_mem.services.neuromem_vdb_service.MemoryManager")
    def test_create_index_invalid_collection(self, mock_manager_class):
        """Test creating index on invalid collection"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_collection = MagicMock()
        mock_collection.indexes = {"global_index": {}}
        mock_manager.get_collection.return_value = mock_collection

        service = NeuroMemVDBService("test_collection")

        with pytest.raises(ValueError, match="Collection 'invalid' is not registered"):
            service._create_index("invalid", "new_index")


class TestNeuroMemVDBServiceHelpers:
    """Test helper methods"""

    def test_get_default_data_dir(self):
        """Test getting default data directory"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        with patch("os.getcwd", return_value="/test/dir"):
            data_dir = NeuroMemVDBService._get_default_data_dir()

            assert "/test/dir/data/neuromem_vdb" in data_dir

    @patch("os.makedirs")
    @patch("os.getcwd")
    def test_get_default_data_dir_creates_directory(self, mock_getcwd, mock_makedirs):
        """Test that default data dir creates directory"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        mock_getcwd.return_value = "/test/dir"

        NeuroMemVDBService._get_default_data_dir()

        mock_makedirs.assert_called_once()


class TestNeuroMemVDBServiceEdgeCases:
    """Test edge cases"""

    @patch("sage.middleware.components.sage_mem.services.neuromem_vdb_service.MemoryManager")
    def test_retrieve_handles_exceptions(self, mock_manager_class):
        """Test that retrieve handles exceptions gracefully"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_collection = MagicMock()
        mock_collection.indexes = {"global_index": {}}
        mock_collection.retrieve.side_effect = Exception("Retrieval error")
        mock_manager.get_collection.return_value = mock_collection

        service = NeuroMemVDBService("test_collection")

        # Patch logger property to track error logging
        mock_logger = MagicMock()
        with patch.object(type(service), "logger", new=mock_logger):
            results = service.retrieve("test query")

            # Should return empty list and log error
            assert results == []
            mock_logger.error.assert_called()

    @patch("sage.middleware.components.sage_mem.services.neuromem_vdb_service.MemoryManager")
    def test_init_logs_errors_on_connection_failure(self, mock_manager_class):
        """Test that init logs errors when connection fails"""
        from sage.middleware.components.sage_mem.services.neuromem_vdb_service import (
            NeuroMemVDBService,
        )

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_collection.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            NeuroMemVDBService("test_collection")
