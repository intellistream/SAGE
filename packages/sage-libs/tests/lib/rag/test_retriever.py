"""
测试 sage.libs.rag.retriever 模块 - ChromaRetriever
"""

import pytest
import numpy as np
import warnings
from unittest.mock import Mock, patch

# 抑制ascii_colors的日志错误
warnings.filterwarnings("ignore", category=UserWarning, module="ascii_colors")

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
            
            query = "测试查询"
            result = retriever.execute(query)
            
            # 验证错误处理
            assert isinstance(result, dict)
            assert result["query"] == query
            assert result["results"] == []
