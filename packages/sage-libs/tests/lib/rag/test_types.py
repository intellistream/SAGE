"""
测试 sage.libs.rag.types 模块
"""

import pytest

from sage.libs.rag.types import (
    RAGDocument,
    RAGQuery,
    RAGResponse,
    create_rag_response,
    ensure_rag_response,
    extract_query,
    extract_results,
)


@pytest.mark.unit
class TestRAGDocument:
    """测试RAGDocument类型"""

    def test_rag_document_basic(self):
        """测试基本RAGDocument创建"""
        doc: RAGDocument = {
            "text": "This is a test document",
            "title": "Test Doc",
        }
        assert doc["text"] == "This is a test document"
        assert doc["title"] == "Test Doc"

    def test_rag_document_with_relevance_score(self):
        """测试带相关性分数的文档"""
        doc: RAGDocument = {
            "text": "Python programming",
            "relevance_score": 0.95,
            "chunk_id": 3,
        }
        assert doc["relevance_score"] == 0.95
        assert doc["chunk_id"] == 3

    def test_rag_document_creation(self):
        """测试手动创建RAGDocument"""
        doc: RAGDocument = {
            "text": "Sample text",
            "title": "Sample",
            "relevance_score": 0.85,
            "source": "test.pdf",
        }
        assert doc["text"] == "Sample text"
        assert doc["title"] == "Sample"
        assert doc["relevance_score"] == 0.85
        assert doc["source"] == "test.pdf"


@pytest.mark.unit
class TestRAGQuery:
    """测试RAGQuery类型"""

    def test_rag_query_basic(self):
        """测试基本RAGQuery创建"""
        query: RAGQuery = {
            "query": "What is Python?",
            "results": ["doc1", "doc2"],
        }
        assert query["query"] == "What is Python?"
        assert len(query["results"]) == 2

    def test_rag_query_with_generated(self):
        """测试带生成内容的查询"""
        query: RAGQuery = {
            "query": "Explain ML",
            "results": ["context1"],
            "generated": "Machine learning is...",
            "execution_time": 1.5,
        }
        assert query["generated"] == "Machine learning is..."
        assert query["execution_time"] == 1.5

    def test_rag_query_creation(self):
        """测试手动创建RAGQuery"""
        query: RAGQuery = {
            "query": "Test query",
            "results": ["r1", "r2", "r3"],
            "generated": "Generated answer",
            "reranked": True,
        }
        assert query["query"] == "Test query"
        assert len(query["results"]) == 3
        assert query["generated"] == "Generated answer"
        assert query["reranked"] is True


@pytest.mark.unit
class TestRAGResponse:
    """测试RAGResponse类型"""

    def test_rag_response_basic(self):
        """测试基本RAGResponse创建"""
        response: RAGResponse = {
            "query": "What is AI?",
            "results": ["AI is artificial intelligence"],
        }
        assert response["query"] == "What is AI?"
        assert len(response["results"]) == 1

    def test_rag_response_with_generated(self):
        """测试带生成内容的响应"""
        response: RAGResponse = {
            "query": "Explain DL",
            "results": ["context"],
            "generated": "Deep learning is...",
            "context": "Retrieved context",
            "execution_time": 2.3,
        }
        assert response["generated"] == "Deep learning is..."
        assert response["context"] == "Retrieved context"
        assert response["execution_time"] == 2.3

    def test_create_rag_response(self):
        """测试create_rag_response辅助函数"""
        response = create_rag_response(
            query="Test question",
            results=["answer1", "answer2"],
            generated="Final answer",
            execution_time=1.8,
        )
        assert response["query"] == "Test question"
        assert len(response["results"]) == 2
        assert response["generated"] == "Final answer"
        assert response["execution_time"] == 1.8

    def test_rag_response_with_metadata(self):
        """测试带元数据的响应"""
        response: RAGResponse = {
            "query": "Test",
            "results": ["r1"],
            "metadata": {
                "retriever": "bm25",
                "generator": "gpt-3.5",
                "num_chunks": 5,
            },
        }
        assert response["metadata"]["retriever"] == "bm25"
        assert response["metadata"]["num_chunks"] == 5


@pytest.mark.unit
class TestRAGTypesCompatibility:
    """测试RAG类型的兼容性"""

    def test_rag_document_is_dict(self):
        """验证RAGDocument可以作为普通字典使用"""
        doc: RAGDocument = {"text": "test", "title": "Test"}
        assert isinstance(doc, dict)
        assert "text" in doc
        assert doc.get("title") == "Test"

    def test_rag_query_is_dict(self):
        """验证RAGQuery可以作为普通字典使用"""
        query: RAGQuery = {"query": "test", "results": ["r1"]}
        assert isinstance(query, dict)
        assert "query" in query
        assert query.get("results") == ["r1"]

    def test_rag_response_is_dict(self):
        """验证RAGResponse可以作为普通字典使用"""
        response = create_rag_response(query="test", results=["r1"])
        assert isinstance(response, dict)
        assert "query" in response
        assert response.get("results") == ["r1"]

    def test_optional_fields(self):
        """测试可选字段的处理"""
        # 只包含必需字段
        doc: RAGDocument = {"text": "test"}
        assert "text" in doc
        assert doc.get("relevance_score") is None

        query: RAGQuery = {"query": "test", "results": []}
        assert "query" in query
        assert query.get("generated") is None

        response = create_rag_response(query="test", results=[])
        assert "query" in response
        assert response.get("generated") is None


@pytest.mark.unit
class TestRAGHelperFunctions:
    """测试RAG辅助函数"""

    def test_ensure_rag_response_from_dict(self):
        """测试从字典创建RAGResponse"""
        data = {
            "query": "test query",
            "results": ["r1", "r2"],
            "generated": "answer",
        }
        response = ensure_rag_response(data)
        assert response["query"] == "test query"
        assert response["results"] == ["r1", "r2"]
        assert response["generated"] == "answer"

    def test_ensure_rag_response_from_tuple(self):
        """测试从元组创建RAGResponse"""
        data = ("my query", ["result1", "result2"])
        response = ensure_rag_response(data)
        assert response["query"] == "my query"
        assert response["results"] == ["result1", "result2"]

    def test_ensure_rag_response_with_default_query(self):
        """测试使用默认查询"""
        data = {"results": ["r1"]}
        response = ensure_rag_response(data, default_query="default")
        assert response["query"] == "default"
        assert response["results"] == ["r1"]

    def test_extract_query_from_dict(self):
        """测试从字典提取查询"""
        data = {"query": "test question"}
        query = extract_query(data)
        assert query == "test question"

    def test_extract_query_from_tuple(self):
        """测试从元组提取查询"""
        data = ("my query", ["results"])
        query = extract_query(data)
        assert query == "my query"

    def test_extract_query_with_default(self):
        """测试提取查询时使用默认值"""
        data = {"results": ["r1"]}
        query = extract_query(data, default="default query")
        assert query == "default query"

    def test_extract_results_from_dict(self):
        """测试从字典提取结果"""
        data = {"query": "q", "results": ["a", "b", "c"]}
        results = extract_results(data)
        assert results == ["a", "b", "c"]

    def test_extract_results_from_tuple(self):
        """测试从元组提取结果"""
        data = ("query", ["r1", "r2"])
        results = extract_results(data)
        assert results == ["r1", "r2"]

    def test_extract_results_with_default(self):
        """测试提取结果时使用默认值"""
        data = {"query": "q"}
        results = extract_results(data, default=["default"])
        assert results == ["default"]

    def test_create_rag_response_minimal(self):
        """测试创建最小RAGResponse"""
        response = create_rag_response(query="q", results=["r"])
        assert response["query"] == "q"
        assert response["results"] == ["r"]
        assert response.get("generated") is None

    def test_create_rag_response_with_kwargs(self):
        """测试创建带额外字段的RAGResponse"""
        response = create_rag_response(
            query="test",
            results=["a", "b"],
            generated="answer",
            execution_time=1.5,
            metadata={"model": "gpt-4"},
        )
        assert response["query"] == "test"
        assert response["results"] == ["a", "b"]
        assert response["generated"] == "answer"
        assert response["execution_time"] == 1.5
        assert response["metadata"]["model"] == "gpt-4"

    def test_create_rag_response_none_values_filtered(self):
        """测试None值不会被添加到响应中"""
        response = create_rag_response(query="test", results=["r"], generated=None, metadata=None)
        assert response["query"] == "test"
        assert response["results"] == ["r"]
        assert "generated" not in response
        assert "metadata" not in response
