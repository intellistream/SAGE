"""
测试 sage.libs.rag.retriever 模块 - ChromaRetriever 和 BM25sRetriever
"""

import pytest
from unittest.mock import Mock, patch

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
        "chroma": {"persist_path": "./test_vector_db", "collection_name": "test_collection"}
    }


@pytest.fixture
def sample_documents():
    """测试文档"""
    return [
        {"content": "机器学习是人工智能的一个分支。", "score": 0.9, "id": "doc_1"},
        {"content": "深度学习使用神经网络。", "score": 0.8, "id": "doc_2"},
        {"content": "自然语言处理处理文本数据。", "score": 0.7, "id": "doc_3"}
    ]


@pytest.mark.unit
class TestChromaRetriever:
    """测试ChromaRetriever类"""
    
    def test_import(self):
        """测试导入"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")
        assert ChromaRetriever is not None
    
    @patch('sage.libs.rag.retriever.ChromaUtils')
    @patch('sage.libs.rag.retriever.ChromaBackend')
    @patch('sage.middleware.utils.embedding.embedding_model.EmbeddingModel')
    def test_initialization(self, mock_embedding_model, mock_chroma_backend, mock_chroma_utils, chroma_config):
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
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = ChromaRetriever(config=chroma_config)
            assert retriever.config == chroma_config
            assert retriever.backend_type == "chroma"
            assert retriever.vector_dimension == 384
            assert retriever.top_k == 5
    
    @patch('sage.libs.rag.retriever.ChromaUtils')
    @patch('sage.libs.rag.retriever.ChromaBackend')
    @patch('sage.middleware.utils.embedding.embedding_model.EmbeddingModel')
    def test_execute_string_input(self, mock_embedding_model, mock_chroma_backend, mock_chroma_utils, chroma_config):
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
            {"content": "相关文档2", "score": 0.85, "id": "doc_2"}
        ]
        mock_chroma_backend.return_value = mock_backend
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = ChromaRetriever(config=chroma_config)
            retriever.logger = Mock()
            
            query = "什么是人工智能？"
            result = retriever.execute(query)
            
            # 验证结果格式
            assert isinstance(result, dict)
            assert "query" in result
            assert "results" in result
            assert result["query"] == query
            assert len(result["results"]) == 2
    
    @patch('sage.libs.rag.retriever.ChromaUtils')
    @patch('sage.libs.rag.retriever.ChromaBackend')
    @patch('sage.middleware.utils.embedding.embedding_model.EmbeddingModel')
    def test_execute_dict_input(self, mock_embedding_model, mock_chroma_backend, mock_chroma_utils, chroma_config):
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
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = ChromaRetriever(config=chroma_config)
            retriever.logger = Mock()
            
            input_data = {"query": "什么是机器学习？", "other_field": "value"}
            result = retriever.execute(input_data)
            
            # 验证结果格式
            assert isinstance(result, dict)
            assert "results" in result
            assert result["query"] == "什么是机器学习？"
            assert result["other_field"] == "value"
    
    @patch('sage.libs.rag.retriever.ChromaUtils')
    @patch('sage.libs.rag.retriever.ChromaBackend')
    @patch('sage.middleware.utils.embedding.embedding_model.EmbeddingModel')
    def test_add_documents(self, mock_embedding_model, mock_chroma_backend, mock_chroma_utils, chroma_config):
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
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = ChromaRetriever(config=chroma_config)
            
            documents = ["文档1内容", "文档2内容", "文档3内容"]
            doc_ids = retriever.add_documents(documents)
            
            assert doc_ids == ["doc_1", "doc_2", "doc_3"]
            assert mock_embedding.embed.call_count == 3
    
    @patch('sage.libs.rag.retriever.ChromaUtils')
    @patch('sage.libs.rag.retriever.ChromaBackend')
    @patch('sage.middleware.utils.embedding.embedding_model.EmbeddingModel')
    def test_error_handling(self, mock_embedding_model, mock_chroma_backend, mock_chroma_utils, chroma_config):
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
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = ChromaRetriever(config=chroma_config)
            retriever.logger = Mock()
            
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
            "index_type": "HNSW"
        }
    }


@pytest.fixture
def sample_documents():
    """测试文档"""
    return [
        {"content": "机器学习是人工智能的一个分支。", "score": 0.9, "id": "doc_1"},
        {"content": "深度学习使用神经网络。", "score": 0.8, "id": "doc_2"},
        {"content": "自然语言处理处理文本数据。", "score": 0.7, "id": "doc_3"}
    ]


@pytest.mark.unit
class TestMilvusDenseRetriever:
    """测试MilvusDenseRetriever类"""
    
    def test_import(self):
        """测试导入"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")
        assert MilvusDenseRetriever is not None
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('sage.middleware.utils.embedding.embedding_model.EmbeddingModel')
    def test_initialization(self, mock_embedding_model, mock_milvus_backend, mock_milvus_utils, milvus_dense_config):
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
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)
            assert retriever.config == milvus_dense_config
            assert retriever.backend_type == "milvus"
            assert retriever.vector_dimension == 384
            assert retriever.top_k == 5
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('sage.middleware.utils.embedding.embedding_model.EmbeddingModel')
    def test_execute_string_input(self, mock_embedding_model, mock_milvus_backend, mock_milvus_utils, milvus_dense_config):
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
            {"content": "相关文档2", "score": 0.85, "id": "doc_2"}
        ]
        mock_milvus_backend.return_value = mock_backend
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)
            
            query = "什么是人工智能？"
            result = retriever.execute(query)
            
            # 验证结果格式
            assert isinstance(result, dict)
            assert "query" in result
            assert "retrieved_documents" in result
            assert result["query"] == query
            assert len(result["retrieved_documents"]) == 2
            
            # 验证调用了正确的方法
            mock_embedding.encode.assert_called_once_with(query)
            mock_backend.dense_search.assert_called_once()
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('sage.middleware.utils.embedding.embedding_model.EmbeddingModel')
    def test_execute_dict_input(self, mock_embedding_model, mock_milvus_backend, mock_milvus_utils, milvus_dense_config):
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
        mock_backend.dense_search.return_value = [{"content": "相关文档", "score": 0.95, "id": "doc_1"}]
        mock_milvus_backend.return_value = mock_backend
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)
            
            input_data = {"question": "什么是机器学习？", "other_field": "value"}
            result = retriever.execute(input_data)
            
            # 验证结果格式
            assert isinstance(result, dict)
            assert "retrieved_documents" in result
            assert result["question"] == "什么是机器学习？"
            assert result["other_field"] == "value"
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('sage.middleware.utils.embedding.embedding_model.EmbeddingModel')
    def test_execute_tuple_input(self, mock_embedding_model, mock_milvus_backend, mock_milvus_utils, milvus_dense_config):
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
        mock_backend.dense_search.return_value = [{"content": "相关文档", "score": 0.95, "id": "doc_1"}]
        mock_milvus_backend.return_value = mock_backend
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)
            
            tuple_input = ("什么是深度学习？", "extra_data")
            result = retriever.execute(tuple_input)
            
            # 验证结果格式
            assert isinstance(result, dict)
            assert "query" in result
            assert "retrieved_documents" in result
            assert result["query"] == "什么是深度学习？"
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('sage.middleware.utils.embedding.embedding_model.EmbeddingModel')
    def test_add_documents(self, mock_embedding_model, mock_milvus_backend, mock_milvus_utils, milvus_dense_config):
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
        
        with patch('sage.libs.rag.retriever.MapFunction'):
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
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('sage.middleware.utils.embedding.embedding_model.EmbeddingModel')
    def test_add_documents_with_custom_ids(self, mock_embedding_model, mock_milvus_backend, mock_milvus_utils, milvus_dense_config):
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
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)
            
            documents = ["文档1内容", "文档2内容"]
            custom_ids = ["custom_1", "custom_2"]
            doc_ids = retriever.add_documents(documents, doc_ids=custom_ids)
            
            assert doc_ids == ["custom_1", "custom_2"]
            
            # 验证使用了自定义ID
            call_args = mock_backend.add_dense_documents.call_args
            assert call_args[0][2] == custom_ids
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('sage.middleware.utils.embedding.embedding_model.EmbeddingModel')
    def test_error_handling_embedding_failure(self, mock_embedding_model, mock_milvus_backend, mock_milvus_utils, milvus_dense_config):
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
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)
            
            query = "测试查询"
            result = retriever.execute(query)
            
            # 验证错误处理
            assert isinstance(result, dict)
            assert result["query"] == query
            assert result["retrieved_documents"] == []
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('sage.middleware.utils.embedding.embedding_model.EmbeddingModel')
    def test_error_handling_search_failure(self, mock_embedding_model, mock_milvus_backend, mock_milvus_utils, milvus_dense_config):
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
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)
            
            query = "测试查询"
            result = retriever.execute(query)
            
            # 验证错误处理
            assert isinstance(result, dict)
            assert result["query"] == query
            assert result["retrieved_documents"] == []
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('sage.middleware.utils.embedding.embedding_model.EmbeddingModel')
    def test_configuration_methods(self, mock_embedding_model, mock_milvus_backend, mock_milvus_utils, milvus_dense_config):
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
        mock_backend.get_collection_info.return_value = {"name": "test_collection", "count": 100}
        mock_backend.delete_collection.return_value = True
        mock_milvus_backend.return_value = mock_backend
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = MilvusDenseRetriever(config=milvus_dense_config)
            
            # 测试保存配置
            assert retriever.save_config("/path/to/config") == True
            mock_backend.save_config.assert_called_with("/path/to/config")
            
            # 测试加载配置
            assert retriever.load_config("/path/to/config") == True
            mock_backend.load_config.assert_called_with("/path/to/config")
            
            # 测试获取集合信息
            info = retriever.get_collection_info()
            assert info["name"] == "test_collection"
            assert info["count"] == 100
            
            # 测试删除集合
            assert retriever.delete_collection("test_collection") == True
            mock_backend.delete_collection.assert_called_with("test_collection")
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('sage.middleware.utils.embedding.embedding_model.EmbeddingModel')
    def test_profile_mode(self, mock_embedding_model, mock_milvus_backend, mock_milvus_utils, milvus_dense_config):
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
        mock_backend.dense_search.return_value = [{"content": "相关文档", "score": 0.95, "id": "doc_1"}]
        mock_milvus_backend.return_value = mock_backend
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            with patch('os.makedirs'):
                with patch('builtins.open', create=True) as mock_open:
                    with patch('json.dump') as mock_json_dump:
                        # 启用profile模式
                        retriever = MilvusDenseRetriever(config=milvus_dense_config, enable_profile=True)
                        
                        query = "测试查询"
                        result = retriever.execute(query)
                        
                        # 验证profile数据被收集
                        assert hasattr(retriever, 'data_records')
                        assert hasattr(retriever, 'data_base_path')
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    def test_initialization_failure_milvus_unavailable(self, mock_milvus_utils, milvus_dense_config):
        """测试初始化失败 - Milvus不可用"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")
        
        mock_milvus_utils.check_milvus_available.return_value = False
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            with pytest.raises(ImportError):
                MilvusDenseRetriever(config=milvus_dense_config)
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    def test_initialization_failure_invalid_config(self, mock_milvus_utils, milvus_dense_config):
        """测试初始化失败 - 无效配置"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")
        
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = False
        
        with patch('sage.libs.rag.retriever.MapFunction'):
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
            "index_type": "SPARSE_INVERTED_INDEX"
        }
    }


@pytest.fixture
def sample_documents():
    """测试文档"""
    return [
        {"content": "机器学习是人工智能的一个分支。", "score": 0.9, "id": "doc_1"},
        {"content": "深度学习使用神经网络。", "score": 0.8, "id": "doc_2"},
        {"content": "自然语言处理处理文本数据。", "score": 0.7, "id": "doc_3"}
    ]


@pytest.fixture
def mock_sparse_embeddings():
    """模拟稀疏向量embedding结果"""
    return {
        "sparse": [
            {"indices": [1, 5, 10], "values": [0.8, 0.6, 0.4]},
            {"indices": [2, 8, 15], "values": [0.9, 0.5, 0.3]},
            {"indices": [3, 7, 12], "values": [0.7, 0.8, 0.2]}
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
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('pymilvus.model.hybrid.BGEM3EmbeddingFunction')
    def test_initialization(self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config):
        """测试初始化"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")
        
        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True
        mock_embedding = Mock()
        mock_bgem3.return_value = mock_embedding
        mock_milvus_backend.return_value = Mock()
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)
            assert retriever.config == milvus_sparse_config
            assert retriever.backend_type == "milvus"
            assert retriever.top_k == 10
            assert hasattr(retriever, 'embedding_model')
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('pymilvus.model.hybrid.BGEM3EmbeddingFunction')
    def test_execute_string_input(self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config):
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
            {"content": "相关文档2", "score": 0.85, "id": "doc_2"}
        ]
        mock_milvus_backend.return_value = mock_backend
        
        with patch('sage.libs.rag.retriever.MapFunction'):
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
            mock_backend.sparse_search.assert_called_once_with(
                query_text=query,
                top_k=10
            )
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('pymilvus.model.hybrid.BGEM3EmbeddingFunction')
    def test_execute_dict_input(self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config):
        """测试执行 - 字典输入"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")
        
        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True
        
        mock_embedding = Mock()
        mock_bgem3.return_value = mock_embedding
        
        mock_backend = Mock()
        mock_backend.sparse_search.return_value = [{"content": "相关文档", "score": 0.95, "id": "doc_1"}]
        mock_milvus_backend.return_value = mock_backend
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)
            
            input_data = {"question": "什么是机器学习？", "other_field": "value"}
            result = retriever.execute(input_data)
            
            # 验证结果格式
            assert isinstance(result, dict)
            assert "retrieved_documents" in result
            assert result["question"] == "什么是机器学习？"
            assert result["other_field"] == "value"
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('pymilvus.model.hybrid.BGEM3EmbeddingFunction')
    def test_execute_tuple_input(self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config):
        """测试执行 - 元组输入"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")
        
        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True
        
        mock_embedding = Mock()
        mock_bgem3.return_value = mock_embedding
        
        mock_backend = Mock()
        mock_backend.sparse_search.return_value = [{"content": "相关文档", "score": 0.95, "id": "doc_1"}]
        mock_milvus_backend.return_value = mock_backend
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)
            
            tuple_input = ("什么是深度学习？", "extra_data")
            result = retriever.execute(tuple_input)
            
            # 验证结果格式
            assert isinstance(result, dict)
            assert "query" in result
            assert "retrieved_documents" in result
            assert result["query"] == "什么是深度学习？"
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('pymilvus.model.hybrid.BGEM3EmbeddingFunction')
    def test_add_documents(self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config, mock_sparse_embeddings):
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
        
        with patch('sage.libs.rag.retriever.MapFunction'):
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
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('pymilvus.model.hybrid.BGEM3EmbeddingFunction')
    def test_add_documents_with_custom_ids(self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config, mock_sparse_embeddings):
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
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)
            
            documents = ["文档1内容", "文档2内容"]
            custom_ids = ["custom_1", "custom_2"]
            doc_ids = retriever.add_documents(documents, doc_ids=custom_ids)
            
            assert doc_ids == ["custom_1", "custom_2"]
            
            # 验证使用了自定义ID
            call_args = mock_backend.add_sparse_documents.call_args
            assert call_args[0][2] == custom_ids
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('pymilvus.model.hybrid.BGEM3EmbeddingFunction')
    def test_error_handling_search_failure(self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config):
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
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)
            
            query = "测试查询"
            result = retriever.execute(query)
            
            # 验证错误处理
            assert isinstance(result, dict)
            assert result["query"] == query
            assert result["retrieved_documents"] == []
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('pymilvus.model.hybrid.BGEM3EmbeddingFunction')
    def test_error_handling_embedding_failure(self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config):
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
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)
            
            documents = ["测试文档"]
            
            # 验证添加文档时的错误处理
            with pytest.raises(Exception):
                retriever.add_documents(documents)
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('pymilvus.model.hybrid.BGEM3EmbeddingFunction')
    def test_configuration_methods(self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config):
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
        mock_backend.get_collection_info.return_value = {"name": "test_sparse_collection", "count": 100}
        mock_milvus_backend.return_value = mock_backend
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            retriever = MilvusSparseRetriever(config=milvus_sparse_config)
            
            # 测试保存配置
            assert retriever.save_config("/path/to/config") == True
            mock_backend.save_config.assert_called_with("/path/to/config")
            
            # 测试加载配置
            assert retriever.load_config("/path/to/config") == True
            mock_backend.load_config.assert_called_with("/path/to/config")
            
            # 测试获取集合信息
            info = retriever.get_collection_info()
            assert info["name"] == "test_sparse_collection"
            assert info["count"] == 100
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('pymilvus.model.hybrid.BGEM3EmbeddingFunction')
    def test_profile_mode(self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config):
        """测试profile模式"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")
        
        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True
        
        mock_embedding = Mock()
        mock_bgem3.return_value = mock_embedding
        
        mock_backend = Mock()
        mock_backend.sparse_search.return_value = [{"content": "相关文档", "score": 0.95, "id": "doc_1"}]
        mock_milvus_backend.return_value = mock_backend
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            with patch('os.makedirs'):
                with patch('builtins.open', create=True) as mock_open:
                    with patch('json.dump') as mock_json_dump:
                        # 启用profile模式
                        retriever = MilvusSparseRetriever(config=milvus_sparse_config, enable_profile=True)
                        
                        query = "测试查询"
                        result = retriever.execute(query)
                        
                        # 验证profile数据被收集
                        assert hasattr(retriever, 'data_records')
                        assert hasattr(retriever, 'data_base_path')
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    def test_initialization_failure_milvus_unavailable(self, mock_milvus_utils, milvus_sparse_config):
        """测试初始化失败 - Milvus不可用"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")
        
        mock_milvus_utils.check_milvus_available.return_value = False
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            with pytest.raises(ImportError):
                MilvusSparseRetriever(config=milvus_sparse_config)
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    def test_initialization_failure_invalid_config(self, mock_milvus_utils, milvus_sparse_config):
        """测试初始化失败 - 无效配置"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")
        
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = False
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            with pytest.raises(ValueError):
                MilvusSparseRetriever(config=milvus_sparse_config)
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    def test_embedding_model_import_failure(self, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config):
        """测试embedding模型导入失败"""
        if not RETRIEVER_AVAILABLE:
            pytest.skip("Retriever module not available")
        
        # 设置模拟
        mock_milvus_utils.check_milvus_available.return_value = True
        mock_milvus_utils.validate_milvus_config.return_value = True
        mock_milvus_backend.return_value = Mock()
        
        # 模拟BGEM3EmbeddingFunction导入失败
        with patch('sage.libs.rag.retriever.MapFunction'):
            with patch('pymilvus.model.hybrid.BGEM3EmbeddingFunction', side_effect=ImportError("BGEM3EmbeddingFunction not available")):
                with pytest.raises(ImportError):
                    MilvusSparseRetriever(config=milvus_sparse_config)
    
    @patch('sage.libs.rag.retriever.MilvusUtils')
    @patch('sage.libs.rag.retriever.MilvusBackend')
    @patch('pymilvus.model.hybrid.BGEM3EmbeddingFunction')
    def test_knowledge_file_loading(self, mock_bgem3, mock_milvus_backend, mock_milvus_utils, milvus_sparse_config):
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
        
        with patch('sage.libs.rag.retriever.MapFunction'):
            with patch('os.path.exists', return_value=True):
                retriever = MilvusSparseRetriever(config=config_with_knowledge)
                
                # 验证知识库文件被加载
                mock_backend.load_knowledge_from_file_sparse.assert_called_once_with("/path/to/knowledge.txt") 