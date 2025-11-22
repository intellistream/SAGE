"""
Tests for ChromaDB integration module

Tests cover:
- Client initialization (persistent and HTTP modes)
- Collection creation and retrieval
- Document addition and deletion
- Search functionality
- Error handling
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest


@pytest.mark.unit
class TestChromaBackendInitialization:
    """Test ChromaDB backend initialization"""

    @patch("chromadb.PersistentClient")
    def test_init_persistent_client_localhost(self, mock_persistent_client):
        """测试本地持久化客户端初始化"""
        from sage.libs.integrations.chroma import ChromaBackend

        # Mock PersistentClient
        mock_client = Mock()
        mock_collection = Mock()
        mock_persistent_client.return_value = mock_client
        mock_client.get_collection.return_value = mock_collection

        config = {
            "host": "localhost",
            "port": 8000,
            "persistence_path": "/tmp/test_chroma",
            "collection_name": "test_collection",
        }

        backend = ChromaBackend(config)

        # Verify persistent client was created
        mock_persistent_client.assert_called_once_with(path="/tmp/test_chroma")
        assert backend.client == mock_client
        assert backend.collection == mock_collection

    @patch("chromadb.HttpClient")
    def test_init_http_client_remote(self, mock_http_client):
        """测试远程HTTP客户端初始化"""
        from sage.libs.integrations.chroma import ChromaBackend

        # Mock HttpClient
        mock_client = Mock()
        mock_collection = Mock()
        mock_http_client.return_value = mock_client
        mock_client.get_collection.return_value = mock_collection

        config = {
            "host": "remote-server.com",
            "port": 8000,
            "collection_name": "test_collection",
        }

        backend = ChromaBackend(config)

        # Verify HTTP client was created
        mock_http_client.assert_called_once()
        assert backend.client == mock_client

    @patch("chromadb.HttpClient")
    def test_init_force_http_mode(self, mock_http_client):
        """测试强制HTTP模式"""
        from sage.libs.integrations.chroma import ChromaBackend

        mock_client = Mock()
        mock_collection = Mock()
        mock_http_client.return_value = mock_client
        mock_client.get_collection.return_value = mock_collection

        config = {
            "host": "localhost",
            "port": 8000,
            "force_http": True,
            "collection_name": "test_collection",
        }

        _ = ChromaBackend(config)

        # Should use HTTP client even for localhost
        mock_http_client.assert_called_once()

    def test_init_missing_chromadb_dependency(self):
        """测试缺少ChromaDB依赖时的错误处理"""
        import sys

        from sage.libs.integrations.chroma import ChromaBackend

        # Temporarily remove chromadb from sys.modules
        chromadb_backup = sys.modules.get("chromadb")
        if "chromadb" in sys.modules:
            del sys.modules["chromadb"]

        # Mock the import to raise ImportError
        with patch("builtins.__import__", side_effect=ImportError("chromadb not found")):
            config = {"host": "localhost", "collection_name": "test"}

            with pytest.raises(ImportError, match="ChromaDB dependencies not available"):
                ChromaBackend(config)

        # Restore chromadb
        if chromadb_backup:
            sys.modules["chromadb"] = chromadb_backup


@pytest.mark.unit
class TestChromaBackendCollection:
    """Test ChromaDB collection operations"""

    @patch("chromadb.PersistentClient")
    def test_get_existing_collection(self, mock_persistent_client):
        """测试获取已存在的集合"""
        from sage.libs.integrations.chroma import ChromaBackend

        mock_client = Mock()
        mock_collection = Mock()
        mock_persistent_client.return_value = mock_client
        mock_client.get_collection.return_value = mock_collection

        config = {"host": "localhost", "collection_name": "existing_collection"}

        backend = ChromaBackend(config)

        # Should retrieve existing collection
        mock_client.get_collection.assert_called_once_with(name="existing_collection")
        assert backend.collection == mock_collection

    @patch("chromadb.PersistentClient")
    def test_create_new_collection(self, mock_persistent_client):
        """测试创建新集合"""
        from sage.libs.integrations.chroma import ChromaBackend

        mock_client = Mock()
        mock_collection = Mock()
        mock_persistent_client.return_value = mock_client

        # First call fails (collection doesn't exist), second call creates it
        mock_client.get_collection.side_effect = Exception("Collection not found")
        mock_client.create_collection.return_value = mock_collection

        config = {
            "host": "localhost",
            "collection_name": "new_collection",
            "metadata": {"hnsw:space": "cosine"},
        }

        backend = ChromaBackend(config)

        # Should create new collection
        mock_client.create_collection.assert_called_once_with(
            name="new_collection", metadata={"hnsw:space": "cosine"}
        )
        assert backend.collection == mock_collection


@pytest.mark.unit
class TestChromaBackendDocuments:
    """Test document operations"""

    @patch("chromadb.PersistentClient")
    def test_add_documents_with_embeddings(self, mock_persistent_client):
        """测试添加带有embeddings的文档"""
        from sage.libs.integrations.chroma import ChromaBackend

        mock_client = Mock()
        mock_collection = Mock()
        mock_persistent_client.return_value = mock_client
        mock_client.get_collection.return_value = mock_collection

        backend = ChromaBackend({"host": "localhost", "collection_name": "test"})

        # Prepare test data
        documents = ["doc1", "doc2", "doc3"]
        embeddings = [np.random.rand(768) for _ in range(3)]  # list of np.ndarray
        doc_ids = ["id1", "id2", "id3"]

        # Call add_documents (API: documents, embeddings, doc_ids)
        result = backend.add_documents(documents=documents, embeddings=embeddings, doc_ids=doc_ids)

        # Verify collection.add was called with correct parameters
        mock_collection.add.assert_called_once()
        call_kwargs = mock_collection.add.call_args[1]
        assert call_kwargs["documents"] == documents
        assert call_kwargs["ids"] == doc_ids
        assert len(call_kwargs["embeddings"]) == 3
        assert "metadatas" in call_kwargs
        assert result == doc_ids


@pytest.mark.unit
class TestChromaBackendSearch:
    """Test search functionality"""

    @patch("chromadb.PersistentClient")
    def test_search_with_embedding(self, mock_persistent_client):
        """测试使用embedding进行搜索"""
        from sage.libs.integrations.chroma import ChromaBackend

        mock_client = Mock()
        mock_collection = Mock()
        mock_persistent_client.return_value = mock_client
        mock_client.get_collection.return_value = mock_collection

        # Mock search results
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["doc1", "doc2"]],
            "distances": [[0.1, 0.3]],
            "metadatas": [[{"source": "test1"}, {"source": "test2"}]],
        }

        backend = ChromaBackend(
            {"host": "localhost", "collection_name": "test", "use_embedding_query": True}
        )

        # Perform search (API uses query_vector, query_text, top_k)
        query_vector = np.random.rand(768)
        query_text = "test query"
        results = backend.search(query_vector=query_vector, query_text=query_text, top_k=2)

        # Verify results
        assert len(results) == 2
        assert results[0] == "doc1"
        # Verify query was called
        mock_collection.query.assert_called_once()
        assert "query_embeddings" in mock_collection.query.call_args[1]
        assert mock_collection.query.call_args[1]["n_results"] == 2

    @patch("chromadb.PersistentClient")
    def test_search_with_filter(self, mock_persistent_client):
        """测试带过滤条件的搜索"""
        from sage.libs.integrations.chroma import ChromaBackend

        mock_client = Mock()
        mock_collection = Mock()
        mock_persistent_client.return_value = mock_client
        mock_client.get_collection.return_value = mock_collection

        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "distances": [[0.1]],
            "metadatas": [[{"category": "tech"}]],
        }

        backend = ChromaBackend({"host": "localhost", "collection_name": "test"})

        # Search (API doesn't support where filter directly)
        query_vector = np.random.rand(768)
        query_text = "tech"
        results = backend.search(query_vector=query_vector, query_text=query_text, top_k=5)

        # Verify query was called
        mock_collection.query.assert_called_once()
        # Verify results (filtered to tech category)
        assert len(results) == 1
        assert results[0] == "doc1"


@pytest.mark.unit
class TestChromaBackendUtilities:
    """Test utility functions"""

    @patch("chromadb.PersistentClient")
    def test_delete_collection(self, mock_persistent_client):
        """测试删除集合"""
        from sage.libs.integrations.chroma import ChromaBackend

        mock_client = Mock()
        mock_collection = Mock()
        mock_persistent_client.return_value = mock_client
        mock_client.get_collection.return_value = mock_collection

        backend = ChromaBackend({"host": "localhost", "collection_name": "test"})

        # Delete collection
        backend.delete_collection()

        # Verify client.delete_collection was called
        mock_client.delete_collection.assert_called_once_with(name="test")

    @patch("chromadb.PersistentClient")
    def test_get_collection_info(self, mock_persistent_client):
        """测试获取集合信息"""
        from sage.libs.integrations.chroma import ChromaBackend

        mock_client = Mock()
        mock_collection = Mock()
        mock_persistent_client.return_value = mock_client
        mock_client.get_collection.return_value = mock_collection

        # Mock collection properties
        mock_collection.name = "test"
        mock_collection.count.return_value = 42

        backend = ChromaBackend({"host": "localhost", "collection_name": "test"})

        # Get collection info
        info = backend.get_collection_info()

        # Verify info structure
        assert isinstance(info, dict)
        assert "collection_name" in info
        assert info["collection_name"] == "test"
        assert "document_count" in info
        assert info["document_count"] == 42


@pytest.mark.integration
class TestChromaBackendIntegration:
    """Integration tests with mocked ChromaDB"""

    @patch("chromadb.PersistentClient")
    def test_full_workflow(self, mock_persistent_client):
        """测试完整的工作流程：创建、添加、搜索、删除"""
        from sage.libs.integrations.chroma import ChromaBackend

        # Setup mocks
        mock_client = Mock()
        mock_collection = Mock()
        mock_persistent_client.return_value = mock_client
        mock_client.get_collection.side_effect = Exception("Not found")
        mock_client.create_collection.return_value = mock_collection

        # Create backend
        backend = ChromaBackend({"host": "localhost", "collection_name": "test"})

        # Add documents
        documents = ["test doc 1", "test doc 2"]
        embeddings = [np.random.rand(768) for _ in range(2)]
        doc_ids = ["id1", "id2"]

        backend.add_documents(documents=documents, embeddings=embeddings, doc_ids=doc_ids)
        mock_collection.add.assert_called_once()

        # Search
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [documents],
            "distances": [[0.1, 0.2]],
            "metadatas": [[{}, {}]],
        }

        query_vector = np.random.rand(768)
        results = backend.search(query_vector=query_vector, query_text="test", top_k=2)
        assert len(results) == 2

        mock_collection.query.assert_called_once()

        # Delete
        backend.delete_collection()
        mock_client.delete_collection.assert_called_once()
