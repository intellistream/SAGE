"""
Tests for Milvus integration module

Tests cover basic functionality with mocked MilvusClient
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest


@pytest.mark.unit
class TestMilvusBackendBasic:
    """Test basic Milvus backend operations"""

    @patch("pymilvus.MilvusClient")
    def test_init_and_add_dense_documents(self, mock_milvus_client):
        """测试初始化和添加稠密向量文档"""
        from sage.libs.integrations.milvus import MilvusBackend

        mock_client = Mock()
        mock_milvus_client.return_value = mock_client
        mock_client.has_collection.return_value = True
        mock_client.insert.return_value = {"insert_count": 3}

        backend = MilvusBackend(
            {"host": "localhost", "collection_name": "test", "search_type": "dense", "dim": 768}
        )

        # Add documents (note: API parameter is dense_embeddings not embeddings)
        documents = ["doc1", "doc2", "doc3"]
        dense_embeddings = [np.random.rand(768) for _ in range(3)]
        doc_ids = ["id1", "id2", "id3"]

        result = backend.add_dense_documents(
            documents=documents, dense_embeddings=dense_embeddings, doc_ids=doc_ids
        )

        # Verify insert was called and returned IDs
        mock_client.insert.assert_called_once()
        assert len(result) == 3  # Returns generated doc_ids

    @patch("pymilvus.MilvusClient")
    def test_dense_search(self, mock_milvus_client):
        """测试稠密向量搜索"""
        from sage.libs.integrations.milvus import MilvusBackend

        mock_client = Mock()
        mock_milvus_client.return_value = mock_client
        mock_client.has_collection.return_value = True

        # Create mock result objects with entity attribute
        mock_result1 = Mock()
        mock_result1.entity = {"text": "doc1"}
        mock_result2 = Mock()
        mock_result2.entity = {"text": "doc2"}

        mock_client.search.return_value = [[mock_result1, mock_result2]]

        backend = MilvusBackend(
            {"host": "localhost", "collection_name": "test", "search_type": "dense"}
        )

        query_vector = np.random.rand(1024)
        results = backend.dense_search(query_vector=query_vector, top_k=2)

        mock_client.search.assert_called_once()
        assert len(results) == 2
        assert results[0] == "doc1"
        assert results[1] == "doc2"

    @patch("pymilvus.MilvusClient")
    def test_sparse_operations(self, mock_milvus_client):
        """测试稀疏向量操作"""
        from sage.libs.integrations.milvus import MilvusBackend

        mock_client = Mock()
        mock_milvus_client.return_value = mock_client
        mock_client.has_collection.return_value = True
        mock_client.insert.return_value = {"insert_count": 2}

        backend = MilvusBackend(
            {"host": "localhost", "collection_name": "test", "search_type": "sparse"}
        )

        documents = ["doc1", "doc2"]
        sparse_embeddings = [{0: 0.5, 10: 0.3}, {5: 0.7, 50: 0.3}]
        doc_ids = ["id1", "id2"]

        result = backend.add_sparse_documents(
            documents=documents, sparse_embeddings=sparse_embeddings, doc_ids=doc_ids
        )

        mock_client.insert.assert_called_once()
        assert result == doc_ids

    @patch("pymilvus.MilvusClient")
    def test_collection_management(self, mock_milvus_client):
        """测试集合管理操作"""
        from sage.libs.integrations.milvus import MilvusBackend

        mock_client = Mock()
        mock_milvus_client.return_value = mock_client
        mock_client.has_collection.return_value = True
        mock_client.drop_collection.return_value = None
        mock_client.describe_collection.return_value = {
            "collection_name": "test",
            "num_entities": 100,
        }

        backend = MilvusBackend({"host": "localhost", "collection_name": "test"})

        # Test get info
        info = backend.get_collection_info()
        assert isinstance(info, dict)
        assert info["backend"] == "milvus"
        assert info["collection_name"] == "test"

        # Test delete
        result = backend.delete_collection("test")
        mock_client.drop_collection.assert_called_once_with("test")
        assert result is True
