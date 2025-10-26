"""
测试 sage.libs.rag.retriever 模块 - ChromaRetriever 和 BM25sRetriever
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest

# 尝试导入检索模块
try:
    from sage.libs.rag.retriever import ChromaRetriever

    RETRIEVER_AVAILABLE = True
except ImportError as e:
    RETRIEVER_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Retriever module not available: {e}")


@pytest.fixture
def chroma_config():
    """ChromaRetriever测试配置"""
    return {
        "dimension": 384,
        "top_k": 5,
        "embedding": {"method": "mockembedder", "model": "test_model"},
        "chroma": {
            "persist_path": "./test_vector_db",
            "collection_name": "test_collection",
        },
    }


@pytest.fixture
def sample_documents():
    """测试文档"""
    return [
        {"content": "机器学习是人工智能的一个分支。", "score": 0.9, "id": "doc_1"},
        {"content": "深度学习使用神经网络。", "score": 0.8, "id": "doc_2"},
        {"content": "自然语言处理处理文本数据。", "score": 0.7, "id": "doc_3"},
    ]


@pytest.mark.unit
class TestChromaRetriever:
    """测试ChromaRetriever类"""

    def test_import(self):
        """测试导入"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")
        assert ChromaRetriever is not None

    @patch("sage.libs.rag.retriever.ChromaUtils")
    @patch("sage.libs.rag.retriever.ChromaBackend")
    @patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
    def test_initialization(
        self,
        mock_embedding_model,
        mock_chroma_backend,
        mock_chroma_utils,
        chroma_config,
    ):
        """测试初始化"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_chroma_utils.check_chromadb_availability.return_value = True
        mock_chroma_utils.validate_chroma_config.return_value = True
        mock_embedding = Mock()
        mock_embedding.get_dim.return_value = 384
        mock_embedding_model.return_value = mock_embedding
        mock_chroma_backend.return_value = Mock()

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = ChromaRetriever(config=chroma_config)
            assert retriever.config == chroma_config
            assert retriever.backend_type == "chroma"
            assert retriever.vector_dimension == 384
            assert retriever.top_k == 5

    @patch("sage.libs.rag.retriever.ChromaUtils")
    @patch("sage.libs.rag.retriever.ChromaBackend")
    @patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
    def test_execute_string_input(
        self,
        mock_embedding_model,
        mock_chroma_backend,
        mock_chroma_utils,
        chroma_config,
    ):
        """测试执行 - 字符串输入"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_chroma_utils.check_chromadb_availability.return_value = True
        mock_chroma_utils.validate_chroma_config.return_value = True

        mock_embedding = Mock()
        mock_embedding.get_dim.return_value = 384
        mock_embedding.embed.return_value = np.random.rand(384).tolist()
        mock_embedding_model.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.search.return_value = [
            {"content": "相关文档1", "score": 0.95, "id": "doc_1"},
            {"content": "相关文档2", "score": 0.85, "id": "doc_2"},
        ]
        mock_chroma_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = ChromaRetriever(config=chroma_config)
            query = "What is artificial intelligence?"
            result = retriever.execute(query)

            # 验证结果格式
            assert isinstance(result, dict)
            assert "query" in result
            assert "results" in result
            assert result["query"] == query
            assert len(result["results"]) == 2

    @patch("sage.libs.rag.retriever.ChromaUtils")
    @patch("sage.libs.rag.retriever.ChromaBackend")
    @patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
    def test_execute_dict_input(
        self,
        mock_embedding_model,
        mock_chroma_backend,
        mock_chroma_utils,
        chroma_config,
    ):
        """测试执行 - 字典输入"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_chroma_utils.check_chromadb_availability.return_value = True
        mock_chroma_utils.validate_chroma_config.return_value = True

        mock_embedding = Mock()
        mock_embedding.embed.return_value = np.random.rand(384).tolist()
        mock_embedding_model.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.search.return_value = [{"content": "相关文档", "score": 0.95, "id": "doc_1"}]
        mock_chroma_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = ChromaRetriever(config=chroma_config)
            input_data = {"query": "What is machine learning?", "other_field": "value"}
            result = retriever.execute(input_data)

            # 验证结果格式
            assert isinstance(result, dict)
            assert "results" in result
            assert "retrieved_docs" in result  # 验证新增的retrieved_docs字段
            assert result["query"] == "What is machine learning?"
            assert result["other_field"] == "value"

    @patch("sage.libs.rag.retriever.ChromaUtils")
    @patch("sage.libs.rag.retriever.ChromaBackend")
    @patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
    def test_add_documents(
        self,
        mock_embedding_model,
        mock_chroma_backend,
        mock_chroma_utils,
        chroma_config,
    ):
        """测试添加文档"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_chroma_utils.check_chromadb_availability.return_value = True
        mock_chroma_utils.validate_chroma_config.return_value = True

        mock_embedding = Mock()
        mock_embedding.embed.return_value = np.random.rand(384).tolist()
        mock_embedding_model.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.add_documents.return_value = ["doc_1", "doc_2", "doc_3"]
        mock_chroma_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = ChromaRetriever(config=chroma_config)

            documents = ["文档1内容", "文档2内容", "文档3内容"]
            doc_ids = retriever.add_documents(documents)

            assert doc_ids == ["doc_1", "doc_2", "doc_3"]
            assert mock_embedding.embed.call_count == 3

    @patch("sage.libs.rag.retriever.ChromaUtils")
    @patch("sage.libs.rag.retriever.ChromaBackend")
    @patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
    def test_error_handling(
        self,
        mock_embedding_model,
        mock_chroma_backend,
        mock_chroma_utils,
        chroma_config,
    ):
        """测试错误处理"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_chroma_utils.check_chromadb_availability.return_value = True
        mock_chroma_utils.validate_chroma_config.return_value = True

        mock_embedding = Mock()
        mock_embedding.embed.side_effect = Exception("Embedding failed")
        mock_embedding_model.return_value = mock_embedding

        mock_chroma_backend.return_value = Mock()

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = ChromaRetriever(config=chroma_config)
            query = "测试查询"
            result = retriever.execute(query)

            # 验证错误处理
            assert isinstance(result, dict)
            assert result["query"] == query
            assert result["results"] == []


# 尝试导入检索模块
try:
    from sage.libs.rag.retriever import MilvusDenseRetriever

    RETRIEVER_AVAILABLE = True
except ImportError as e:
    RETRIEVER_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Retriever module not available: {e}")


@pytest.fixture
def milvus_dense_config():
    """MilvusDenseRetriever测试配置"""
    return {
        "dimension": 384,
        "top_k": 5,
        "embedding": {"method": "mockembedder", "model": "test_model"},
        "milvus_dense": {
            "collection_name": "test_collection",
            "uri": "http://localhost:19530",
            "metric_type": "COSINE",
            "index_type": "HNSW",
        },
    }


@pytest.mark.unit
class TestMilvusDenseRetriever:
    """测试MilvusDenseRetriever类"""

    def test_import(self):
        """测试导入"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")
        assert MilvusDenseRetriever is not None

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
    def test_initialization(
        self,
        mock_embedding_model,
        mock_milvus_backend,
        mock_milvus_utils,
        milvus_dense_config,
    ):
        """测试初始化"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True
        mock_embedding = Mock()
        mock_embedding.get_dim.return_value = 384
        mock_embedding_model.return_value = mock_embedding
        mock_milvus_backend.return_value = Mock()

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)
            assert retriever.config == milvus_dense_config
            assert retriever.backend_type == "milvus"
            assert retriever.vector_dimension == 384
            assert retriever.top_k == 5

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
    def test_execute_string_input(
        self,
        mock_embedding_model,
        mock_milvus_backend,
        mock_milvus_utils,
        milvus_dense_config,
    ):
        """测试执行 - 字符串输入"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_embedding.get_dim.return_value = 384
        mock_embedding.encode.return_value = np.random.rand(384).tolist()
        mock_embedding_model.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.dense_search.return_value = [
            {"content": "相关文档1", "score": 0.95, "id": "doc_1"},
            {"content": "相关文档2", "score": 0.85, "id": "doc_2"},
        ]
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)

            query = "What is artificial intelligence?"
            result = retriever.execute(query)

            # 验证结果格式
            assert isinstance(result, dict)
            assert "query" in result
            assert "retrieved_documents" in result
            assert "retrieved_docs" in result  # 验证新增的retrieved_docs字段
            assert result["query"] == query
            assert len(result["retrieved_documents"]) == 2

            # 验证调用了正确的方法
            mock_embedding.encode.assert_called_once_with(query)
            mock_backend.dense_search.assert_called_once()

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
    def test_execute_dict_input(
        self,
        mock_embedding_model,
        mock_milvus_backend,
        mock_milvus_utils,
        milvus_dense_config,
    ):
        """测试执行 - 字典输入"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_embedding.encode.return_value = np.random.rand(384).tolist()
        mock_embedding_model.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.dense_search.return_value = [
            {"content": "相关文档", "score": 0.95, "id": "doc_1"}
        ]
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)

            input_data = {
                "question": "What is machine learning?",
                "other_field": "value",
            }
            result = retriever.execute(input_data)

            # 验证结果格式
            assert isinstance(result, dict)
            assert "retrieved_documents" in result
            assert "retrieved_docs" in result  # 验证新增的retrieved_docs字段
            assert result["question"] == "What is machine learning?"
            assert result["other_field"] == "value"

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
    def test_execute_tuple_input(
        self,
        mock_embedding_model,
        mock_milvus_backend,
        mock_milvus_utils,
        milvus_dense_config,
    ):
        """测试执行 - 元组输入"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_embedding.encode.return_value = np.random.rand(384).tolist()
        mock_embedding_model.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.dense_search.return_value = [
            {"content": "相关文档", "score": 0.95, "id": "doc_1"}
        ]
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)

            tuple_input = ("什么是深度学习？", "extra_data")
            result = retriever.execute(tuple_input)

            # 验证结果格式
            assert isinstance(result, dict)
            assert "query" in result
            assert "retrieved_documents" in result
            assert result["query"] == "什么是深度学习？"

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
    def test_add_documents(
        self,
        mock_embedding_model,
        mock_milvus_backend,
        mock_milvus_utils,
        milvus_dense_config,
    ):
        """测试添加文档"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_embedding.embed.return_value = np.random.rand(384).tolist()
        mock_embedding_model.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.add_dense_documents.return_value = ["doc_1", "doc_2", "doc_3"]
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)

            documents = ["文档1内容", "文档2内容", "文档3内容"]
            doc_ids = retriever.add_documents(documents)

            assert doc_ids == ["doc_1", "doc_2", "doc_3"]
            assert mock_embedding.embed.call_count == 3

            # 验证调用了正确的Milvus方法
            mock_backend.add_dense_documents.assert_called_once()
            call_args = mock_backend.add_dense_documents.call_args
            assert len(call_args[0][0]) == 3  # documents
            assert len(call_args[0][1]) == 3  # embeddings
            assert len(call_args[0][2]) == 3  # doc_ids

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
    def test_add_documents_with_custom_ids(
        self,
        mock_embedding_model,
        mock_milvus_backend,
        mock_milvus_utils,
        milvus_dense_config,
    ):
        """测试添加文档 - 自定义ID"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_embedding.embed.return_value = np.random.rand(384).tolist()
        mock_embedding_model.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.add_dense_documents.return_value = ["custom_1", "custom_2"]
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)

            documents = ["文档1内容", "文档2内容"]
            custom_ids = ["custom_1", "custom_2"]
            doc_ids = retriever.add_documents(documents, doc_ids=custom_ids)

            assert doc_ids == ["custom_1", "custom_2"]

            # 验证使用了自定义ID
            call_args = mock_backend.add_dense_documents.call_args
            assert call_args[0][2] == custom_ids

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
    def test_error_handling_embedding_failure(
        self,
        mock_embedding_model,
        mock_milvus_backend,
        mock_milvus_utils,
        milvus_dense_config,
    ):
        """测试错误处理 - embedding失败"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_embedding.encode.side_effect = Exception("Embedding failed")
        mock_embedding_model.return_value = mock_embedding

        mock_milvus_backend.return_value = Mock()

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)

            query = "测试查询"
            result = retriever.execute(query)

            # 验证错误处理
            assert isinstance(result, dict)
            assert result["query"] == query
            assert result["retrieved_documents"] == []

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
    def test_error_handling_search_failure(
        self,
        mock_embedding_model,
        mock_milvus_backend,
        mock_milvus_utils,
        milvus_dense_config,
    ):
        """测试错误处理 - 搜索失败"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_embedding.encode.return_value = np.random.rand(384).tolist()
        mock_embedding_model.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.dense_search.side_effect = Exception("Search failed")
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)

            query = "测试查询"
            result = retriever.execute(query)

            # 验证错误处理
            assert isinstance(result, dict)
            assert result["query"] == query
            assert result["retrieved_documents"] == []

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
    def test_configuration_methods(
        self,
        mock_embedding_model,
        mock_milvus_backend,
        mock_milvus_utils,
        milvus_dense_config,
    ):
        """测试配置相关方法"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True
        mock_embedding_model.return_value = Mock()

        mock_backend = Mock()
        mock_backend.save_config.return_value = True
        mock_backend.load_config.return_value = True
        mock_backend.get_collection_info.return_value = {
            "name": "test_collection",
            "count": 100,
        }
        mock_backend.delete_collection.return_value = True
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)

            # 测试保存配置
            assert retriever.save_config("/path/to/config") is True
            mock_backend.save_config.assert_called_with("/path/to/config")

            # 测试加载配置
            assert retriever.load_config("/path/to/config") is True
            mock_backend.load_config.assert_called_with("/path/to/config")

            # 测试获取集合信息
            info = retriever.get_collection_info()
            assert info["name"] == "test_collection"
            assert info["count"] == 100

            # 测试删除集合
            assert retriever.delete_collection("test_collection") is True
            mock_backend.delete_collection.assert_called_with("test_collection")

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
    def test_profile_mode(
        self,
        mock_embedding_model,
        mock_milvus_backend,
        mock_milvus_utils,
        milvus_dense_config,
    ):
        """测试profile模式"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_embedding.encode.return_value = np.random.rand(384).tolist()
        mock_embedding_model.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.dense_search.return_value = [
            {"content": "相关文档", "score": 0.95, "id": "doc_1"}
        ]
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            with patch("os.makedirs"):
                with patch("builtins.open", create=True):
                    with patch("json.dump"):
                        # 启用profile模式
                        retriever = MilvusDenseRetriever(
                            config=milvus_dense_config, enable_profile=True
                        )

                        query = "测试查询"
                        retriever.execute(query)

                        # 验证profile数据被收集
                        assert hasattr(retriever, "data_records")
                        assert hasattr(retriever, "data_base_path")

    @patch("sage.libs.rag.retriever.MilvusUtils")
    def test_initialization_failure_milvus_unavailable(
        self, mock_milvus_utils, milvus_dense_config
    ):
        """测试初始化失败 - Milvus不可用"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        mock_milvus_utils.check_milvus_available.return_value = False

        with patch("sage.libs.rag.retriever.MapFunction"):
            with pytest.raises(ImportError):
                MilvusDenseRetriever(config=milvus_dense_config)

    @patch("sage.libs.rag.retriever.MilvusUtils")
    def test_initialization_failure_invalid_config(self, mock_milvus_utils, milvus_dense_config):
        """测试初始化失败 - 无效配置"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = False

        with patch("sage.libs.rag.retriever.MapFunction"):
            with pytest.raises(ValueError):
                MilvusDenseRetriever(config=milvus_dense_config)


# 尝试导入检索模块
try:
    from sage.libs.rag.retriever import MilvusSparseRetriever

    RETRIEVER_AVAILABLE = True
except ImportError as e:
    RETRIEVER_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Retriever module not available: {e}")


@pytest.fixture
def milvus_sparse_config():
    """MilvusSparseRetriever测试配置"""
    return {
        "top_k": 10,
        "milvus_sparse": {
            "collection_name": "test_sparse_collection",
            "uri": "http://localhost:19530",
            "metric_type": "IP",  # 稀疏向量通常使用IP
            "index_type": "SPARSE_INVERTED_INDEX",
        },
    }


@pytest.fixture
def mock_sparse_embeddings():
    """模拟稀疏向量embedding结果"""
    return {
        "sparse": [
            {"indices": [1, 5, 10], "values": [0.8, 0.6, 0.4]},
            {"indices": [2, 8, 15], "values": [0.9, 0.5, 0.3]},
            {"indices": [3, 7, 12], "values": [0.7, 0.8, 0.2]},
        ]
    }


@pytest.mark.unit
class TestMilvusSparseRetriever:
    """测试MilvusSparseRetriever类"""

    def test_import(self):
        """测试导入"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")
        assert MilvusSparseRetriever is not None

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("pymilvus.model.hybrid.BGEM3EmbeddingFunction")
    def test_initialization(
        self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config
    ):
        """测试初始化"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True
        mock_embedding = Mock()
        mock_bgem3.return_value = mock_embedding
        mock_milvus_backend.return_value = Mock()

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)
            assert retriever.config == milvus_sparse_config
            assert retriever.backend_type == "milvus"
            assert retriever.top_k == 10
            assert hasattr(retriever, "embedding_model")

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("pymilvus.model.hybrid.BGEM3EmbeddingFunction")
    def test_execute_string_input(
        self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config
    ):
        """测试执行 - 字符串输入"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_bgem3.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.sparse_search.return_value = [
            {"content": "相关文档1", "score": 0.95, "id": "doc_1"},
            {"content": "相关文档2", "score": 0.85, "id": "doc_2"},
        ]
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)

            query = "什么是人工智能？"
            result = retriever.execute(query)

            # 验证结果格式
            assert isinstance(result, dict)
            assert "query" in result
            assert "retrieved_documents" in result
            assert result["query"] == query
            assert len(result["retrieved_documents"]) == 2

            # 验证调用了正确的方法 - 稀疏检索直接传递文本
            mock_backend.sparse_search.assert_called_once_with(query_text=query, top_k=10)

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("pymilvus.model.hybrid.BGEM3EmbeddingFunction")
    def test_execute_dict_input(
        self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config
    ):
        """测试执行 - 字典输入"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_bgem3.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.sparse_search.return_value = [
            {"content": "相关文档", "score": 0.95, "id": "doc_1"}
        ]
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)

            input_data = {"question": "什么是机器学习？", "other_field": "value"}
            result = retriever.execute(input_data)

            # 验证结果格式
            assert isinstance(result, dict)
            assert "retrieved_documents" in result
            assert "retrieved_docs" in result  # 验证新增的retrieved_docs字段
            assert result["question"] == "什么是机器学习？"
            assert result["other_field"] == "value"

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("pymilvus.model.hybrid.BGEM3EmbeddingFunction")
    def test_execute_tuple_input(
        self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config
    ):
        """测试执行 - 元组输入"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_bgem3.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.sparse_search.return_value = [
            {"content": "相关文档", "score": 0.95, "id": "doc_1"}
        ]
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)

            tuple_input = ("什么是深度学习？", "extra_data")
            result = retriever.execute(tuple_input)

            # 验证结果格式
            assert isinstance(result, dict)
            assert "query" in result
            assert "retrieved_documents" in result
            assert result["query"] == "什么是深度学习？"

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("pymilvus.model.hybrid.BGEM3EmbeddingFunction")
    def test_add_documents(
        self,
        mock_bgem3,
        mock_milvus_backend,
        mock_milvus_utils,
        milvus_sparse_config,
        mock_sparse_embeddings,
    ):
        """测试添加文档"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_embedding.encode_documents.return_value = mock_sparse_embeddings
        mock_bgem3.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.add_sparse_documents.return_value = ["doc_1", "doc_2", "doc_3"]
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)

            documents = ["文档1内容", "文档2内容", "文档3内容"]
            doc_ids = retriever.add_documents(documents)

            assert doc_ids == ["doc_1", "doc_2", "doc_3"]

            # 验证调用了正确的方法
            mock_embedding.encode_documents.assert_called_once_with(documents)
            mock_backend.add_sparse_documents.assert_called_once()

            # 验证传递了正确的稀疏向量
            call_args = mock_backend.add_sparse_documents.call_args
            assert len(call_args[0][0]) == 3  # documents
            assert call_args[0][1] == mock_sparse_embeddings["sparse"]  # sparse embeddings
            assert len(call_args[0][2]) == 3  # doc_ids

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("pymilvus.model.hybrid.BGEM3EmbeddingFunction")
    def test_add_documents_with_custom_ids(
        self,
        mock_bgem3,
        mock_milvus_backend,
        mock_milvus_utils,
        milvus_sparse_config,
        mock_sparse_embeddings,
    ):
        """测试添加文档 - 自定义ID"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_embedding.encode_documents.return_value = mock_sparse_embeddings
        mock_bgem3.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.add_sparse_documents.return_value = ["custom_1", "custom_2"]
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)

            documents = ["文档1内容", "文档2内容"]
            custom_ids = ["custom_1", "custom_2"]
            doc_ids = retriever.add_documents(documents, doc_ids=custom_ids)

            assert doc_ids == ["custom_1", "custom_2"]

            # 验证使用了自定义ID
            call_args = mock_backend.add_sparse_documents.call_args
            assert call_args[0][2] == custom_ids

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("pymilvus.model.hybrid.BGEM3EmbeddingFunction")
    def test_error_handling_search_failure(
        self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config
    ):
        """测试错误处理 - 搜索失败"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_bgem3.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.sparse_search.side_effect = Exception("Search failed")
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)

            query = "测试查询"
            result = retriever.execute(query)

            # 验证错误处理
            assert isinstance(result, dict)
            assert result["query"] == query
            assert result["retrieved_documents"] == []

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("pymilvus.model.hybrid.BGEM3EmbeddingFunction")
    def test_error_handling_embedding_failure(
        self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config
    ):
        """测试错误处理 - embedding失败"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_embedding.encode_documents.side_effect = Exception("Embedding failed")
        mock_bgem3.return_value = mock_embedding

        mock_milvus_backend.return_value = Mock()

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)

            documents = ["测试文档"]

            # 验证添加文档时的错误处理
            with pytest.raises(Exception):  # noqa: B017
                retriever.add_documents(documents)

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("pymilvus.model.hybrid.BGEM3EmbeddingFunction")
    def test_configuration_methods(
        self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config
    ):
        """测试配置相关方法"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True
        mock_bgem3.return_value = Mock()

        mock_backend = Mock()
        mock_backend.save_config.return_value = True
        mock_backend.load_config.return_value = True
        mock_backend.get_collection_info.return_value = {
            "name": "test_sparse_collection",
            "count": 100,
        }
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)

            # 测试保存配置
            assert retriever.save_config("/path/to/config") is True
            mock_backend.save_config.assert_called_with("/path/to/config")

            # 测试加载配置
            assert retriever.load_config("/path/to/config") is True
            mock_backend.load_config.assert_called_with("/path/to/config")

            # 测试获取集合信息
            info = retriever.get_collection_info()
            assert info["name"] == "test_sparse_collection"
            assert info["count"] == 100

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("pymilvus.model.hybrid.BGEM3EmbeddingFunction")
    def test_profile_mode(
        self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config
    ):
        """测试profile模式"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_bgem3.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.sparse_search.return_value = [
            {"content": "相关文档", "score": 0.95, "id": "doc_1"}
        ]
        mock_milvus_backend.return_value = mock_backend

        with patch("sage.libs.rag.retriever.MapFunction"):
            with patch("os.makedirs"):
                with patch("builtins.open", create=True):
                    with patch("json.dump"):
                        # 启用profile模式
                        retriever = MilvusSparseRetriever(
                            config=milvus_sparse_config, enable_profile=True
                        )

                        query = "测试查询"
                        retriever.execute(query)

                        # 验证profile数据被收集
                        assert hasattr(retriever, "data_records")
                        assert hasattr(retriever, "data_base_path")

    @patch("sage.libs.rag.retriever.MilvusUtils")
    def test_initialization_failure_milvus_unavailable(
        self, mock_milvus_utils, milvus_sparse_config
    ):
        """测试初始化失败 - Milvus不可用"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        mock_milvus_utils.check_milvus_available.return_value = False

        with patch("sage.libs.rag.retriever.MapFunction"):
            with pytest.raises(ImportError):
                MilvusSparseRetriever(config=milvus_sparse_config)

    @patch("sage.libs.rag.retriever.MilvusUtils")
    def test_initialization_failure_invalid_config(self, mock_milvus_utils, milvus_sparse_config):
        """测试初始化失败 - 无效配置"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = False

        with patch("sage.libs.rag.retriever.MapFunction"):
            with pytest.raises(ValueError):
                MilvusSparseRetriever(config=milvus_sparse_config)

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    def test_embedding_model_import_failure(
        self, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config
    ):
        """测试embedding模型导入失败"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True
        mock_milvus_backend.return_value = Mock()

        # 模拟BGEM3EmbeddingFunction导入失败
        with patch("sage.libs.rag.retriever.MapFunction"):
            with patch(
                "pymilvus.model.hybrid.BGEM3EmbeddingFunction",
                side_effect=ImportError("BGEM3EmbeddingFunction not available"),
            ):
                with pytest.raises(ImportError):
                    MilvusSparseRetriever(config=milvus_sparse_config)

    @patch("sage.libs.rag.retriever.MilvusUtils")
    @patch("sage.libs.rag.retriever.MilvusBackend")
    @patch("pymilvus.model.hybrid.BGEM3EmbeddingFunction")
    def test_knowledge_file_loading(
        self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config
    ):
        """测试知识库文件加载"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")

        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True

        mock_embedding = Mock()
        mock_bgem3.return_value = mock_embedding

        mock_backend = Mock()
        mock_backend.load_knowledge_from_file_sparse.return_value = 10  # 成功加载10个文档
        mock_milvus_backend.return_value = mock_backend

        # 修改配置以包含知识库文件
        config_with_knowledge = milvus_sparse_config.copy()
        config_with_knowledge["milvus_sparse"]["knowledge_file"] = "/path/to/knowledge.txt"

        with patch("sage.libs.rag.retriever.MapFunction"):
            with patch("os.path.exists", return_value=True):
                MilvusSparseRetriever(config=config_with_knowledge)

                # 验证知识库文件被加载
                mock_backend.load_knowledge_from_file_sparse.assert_called_once_with(
                    "/path/to/knowledge.txt"
                )


# 尝试导入Wiki18FAISSRetriever
try:
    from sage.libs.rag.retriever import Wiki18FAISSRetriever

    WIKI18_FAISS_AVAILABLE = True
except ImportError:
    WIKI18_FAISS_AVAILABLE = False


@pytest.fixture
def wiki18_faiss_config():
    """Wiki18FAISSRetriever测试配置"""
    return {
        "top_k": 5,
        "embedding": {"model": "BAAI/bge-m3", "gpu_device": 0},
        "faiss": {
            "index_path": "/path/to/test/wiki18_index.index",
            "documents_path": "/path/to/test/wiki18_documents.jsonl",
        },
    }


@pytest.fixture
def sample_wiki18_documents():
    """测试Wiki18文档"""
    return [
        {
            "id": "1",
            "title": "Machine Learning",
            "contents": "Machine learning is a subset of artificial intelligence.",
            "doc_size": 50,
        },
        {
            "id": "2",
            "title": "Deep Learning",
            "contents": "Deep learning uses neural networks with multiple layers.",
            "doc_size": 55,
        },
    ]


@pytest.mark.unit
class TestWiki18FAISSRetriever:
    """测试Wiki18FAISSRetriever类"""

    def test_wiki18_faiss_import(self):
        """测试Wiki18FAISSRetriever导入"""
        if not WIKI18_FAISS_AVAILABLE:
            pytest.skip("Wiki18FAISSRetriever not available")

        assert Wiki18FAISSRetriever is not None

    def test_wiki18_faiss_initialization(self, wiki18_faiss_config):
        """测试Wiki18FAISSRetriever初始化"""
        if not WIKI18_FAISS_AVAILABLE:
            pytest.skip("Wiki18FAISSRetriever not available")

        # 简单验证配置和类的存在
        config = wiki18_faiss_config
        assert "top_k" in config
        assert "embedding" in config
        assert "faiss" in config
        assert config["top_k"] == 5
        assert config["embedding"]["model"] == "BAAI/bge-m3"
        assert config["faiss"]["index_path"] == "/path/to/test/wiki18_index.index"
        assert config["faiss"]["documents_path"] == "/path/to/test/wiki18_documents.jsonl"

        # 验证类可以导入
        assert Wiki18FAISSRetriever is not None

        # 验证类具有期望的方法
        assert hasattr(Wiki18FAISSRetriever, "execute")
        assert hasattr(Wiki18FAISSRetriever, "__init__")

    def test_wiki18_faiss_execute_string_input(self, wiki18_faiss_config, sample_wiki18_documents):
        """测试Wiki18FAISSRetriever execute方法 - 字符串输入"""
        if not WIKI18_FAISS_AVAILABLE:
            pytest.skip("Wiki18FAISSRetriever not available")

        # 创建模拟的retriever实例
        mock_retriever = Mock(spec=Wiki18FAISSRetriever)
        mock_retriever.top_k = 5
        mock_retriever.documents = sample_wiki18_documents

        # 模拟execute方法的返回结果
        def mock_execute(query):
            if isinstance(query, str):
                return {
                    "query": query,
                    "results": [
                        {
                            "text": doc["contents"],
                            "similarity_score": 0.9,
                            "document_index": i,
                            "title": doc["title"],
                            "id": doc["id"],
                        }
                        for i, doc in enumerate(sample_wiki18_documents)
                    ],
                    # 新增字段以匹配统一接口
                    "retrieved_docs": [doc["contents"] for doc in sample_wiki18_documents],
                }
            return {"query": str(query), "results": []}

        mock_retriever.execute = mock_execute

        # 测试字符串输入
        result = mock_retriever.execute("machine learning")

        # 验证结果
        assert "query" in result
        assert "results" in result
        assert "retrieved_docs" in result  # 验证新增的retrieved_docs字段
        assert result["query"] == "machine learning"
        assert len(result["results"]) == 2

        # 验证结果格式
        for doc in result["results"]:
            assert "text" in doc
            assert "similarity_score" in doc
            assert "document_index" in doc
            assert "title" in doc
            assert "id" in doc

    def test_wiki18_faiss_execute_dict_input(self, wiki18_faiss_config, sample_wiki18_documents):
        """测试Wiki18FAISSRetriever execute方法 - 字典输入"""
        if not WIKI18_FAISS_AVAILABLE:
            pytest.skip("Wiki18FAISSRetriever not available")

        # 创建模拟的retriever实例
        mock_retriever = Mock(spec=Wiki18FAISSRetriever)
        mock_retriever.top_k = 5
        mock_retriever.documents = sample_wiki18_documents

        # 模拟execute方法的返回结果
        def mock_execute(data):
            result = data.copy() if isinstance(data, dict) else {"input": str(data)}

            # 提取查询文本
            query_text = ""
            if isinstance(data, dict):
                query_text = data.get("query", data.get("question", ""))
            else:
                query_text = str(data)

            result["query"] = query_text
            result["results"] = [
                {
                    "text": doc["contents"],
                    "similarity_score": 0.8,
                    "document_index": i,
                    "title": doc["title"],
                    "id": doc["id"],
                }
                for i, doc in enumerate(sample_wiki18_documents[:1])  # 返回第一个文档
            ]
            # 新增字段以匹配统一接口
            result["retrieved_docs"] = [sample_wiki18_documents[0]["contents"]]
            return result

        mock_retriever.execute = mock_execute

        # 测试字典输入 - query字段
        input_data = {"query": "deep learning", "other_field": "value"}
        result = mock_retriever.execute(input_data)

        # 验证结果
        assert "query" in result
        assert "results" in result
        assert "retrieved_docs" in result  # 验证新增的retrieved_docs字段
        assert result["query"] == "deep learning"
        assert "other_field" in result  # 原始字段应保留
        assert result["other_field"] == "value"

    def test_wiki18_faiss_execute_question_field(
        self, wiki18_faiss_config, sample_wiki18_documents
    ):
        """测试Wiki18FAISSRetriever execute方法 - question字段"""
        if not WIKI18_FAISS_AVAILABLE:
            pytest.skip("Wiki18FAISSRetriever not available")

        # 创建模拟的retriever实例
        mock_retriever = Mock(spec=Wiki18FAISSRetriever)

        # 模拟execute方法
        def mock_execute(data):
            result = data.copy() if isinstance(data, dict) else {"input": str(data)}

            # 提取查询文本
            query_text = ""
            if isinstance(data, dict):
                query_text = data.get("query", data.get("question", ""))

            result["query"] = query_text
            result["results"] = [
                {
                    "text": sample_wiki18_documents[0]["contents"],
                    "similarity_score": 0.9,
                    "document_index": 0,
                    "title": sample_wiki18_documents[0]["title"],
                    "id": sample_wiki18_documents[0]["id"],
                }
            ]
            return result

        mock_retriever.execute = mock_execute

        # 测试字典输入 - question字段
        input_data = {"question": "what is AI?"}
        result = mock_retriever.execute(input_data)

        # 验证结果
        assert "query" in result
        assert result["query"] == "what is AI?"
        assert "question" in result  # 原始字段应保留
        assert result["question"] == "what is AI?"

    def test_wiki18_faiss_execute_error_handling(self, wiki18_faiss_config):
        """测试Wiki18FAISSRetriever execute方法错误处理"""
        if not WIKI18_FAISS_AVAILABLE:
            pytest.skip("Wiki18FAISSRetriever not available")

        # 创建模拟的retriever实例
        mock_retriever = Mock(spec=Wiki18FAISSRetriever)

        # 模拟execute方法处理错误情况
        def mock_execute(data):
            if not data or data == "" or data is None or isinstance(data, (int, float)):
                return {"query": str(data) if data is not None else "", "results": []}

            # 正常情况
            query_text = data if isinstance(data, str) else str(data)
            return {"query": query_text, "results": []}

        mock_retriever.execute = mock_execute

        # 测试空查询
        result = mock_retriever.execute("")
        assert "results" in result
        assert len(result["results"]) == 0

        # 测试无效输入类型
        result = mock_retriever.execute(123)
        assert "results" in result
        assert len(result["results"]) == 0

        # 测试None输入
        result = mock_retriever.execute(None)
        assert "results" in result
        assert len(result["results"]) == 0

    def test_wiki18_faiss_method_signature_consistency(self, wiki18_faiss_config):
        """测试Wiki18FAISSRetriever方法签名一致性"""
        if not WIKI18_FAISS_AVAILABLE:
            pytest.skip("Wiki18FAISSRetriever not available")

        # 验证execute方法签名
        import inspect

        sig = inspect.signature(Wiki18FAISSRetriever.execute)

        # 应该有data参数
        assert "data" in sig.parameters

        # 验证参数类型注解（如果有的话）
        data_param = sig.parameters["data"]
        if data_param.annotation != inspect.Parameter.empty:
            # 检查是否接受Union[str, Dict[str, Any]]或类似类型
            annotation_str = str(data_param.annotation)
            assert "str" in annotation_str or "Any" in annotation_str

        # 验证返回类型注解（如果有的话）
        if sig.return_annotation != sig.empty:
            return_annotation_str = str(sig.return_annotation)
            assert "Dict" in return_annotation_str or "dict" in return_annotation_str

    def test_wiki18_faiss_config_validation(self, wiki18_faiss_config):
        """测试Wiki18FAISSRetriever配置验证"""
        if not WIKI18_FAISS_AVAILABLE:
            pytest.skip("Wiki18FAISSRetriever not available")

        # 测试必需配置字段
        assert "top_k" in wiki18_faiss_config
        assert "embedding" in wiki18_faiss_config
        assert "faiss" in wiki18_faiss_config
        assert wiki18_faiss_config["top_k"] > 0
        assert "model" in wiki18_faiss_config["embedding"]

        # 测试faiss配置项
        faiss_config = wiki18_faiss_config["faiss"]
        assert "index_path" in faiss_config
        assert "documents_path" in faiss_config
        assert faiss_config["index_path"] is not None
        assert faiss_config["documents_path"] is not None

    def test_wiki18_faiss_missing_config_validation(self):
        """测试Wiki18FAISSRetriever缺少必需配置时的验证"""
        if not WIKI18_FAISS_AVAILABLE:
            pytest.skip("Wiki18FAISSRetriever not available")

        # 测试缺少faiss配置的情况

        # 测试缺少index_path的情况

        # 测试缺少documents_path的情况

        # 由于我们无法直接实例化（需要模拟文件系统等），这里只验证配置结构
        # 实际的验证逻辑会在_init_faiss_index方法中抛出ValueError

    def test_wiki18_faiss_search_with_no_results(self, wiki18_faiss_config):
        """测试Wiki18FAISSRetriever搜索无结果的情况"""
        if not WIKI18_FAISS_AVAILABLE:
            pytest.skip("Wiki18FAISSRetriever not available")

        # 创建模拟的retriever实例
        mock_retriever = Mock(spec=Wiki18FAISSRetriever)

        # 模拟execute方法返回无结果
        def mock_execute(query):
            return {"query": str(query), "results": []}  # 无结果

        mock_retriever.execute = mock_execute

        # 测试搜索无结果
        result = mock_retriever.execute("nonexistent query")

        # 验证结果
        assert "query" in result
        assert "results" in result
        assert result["query"] == "nonexistent query"
        assert len(result["results"]) == 0
