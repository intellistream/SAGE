"""
测试 sage.libs.rag.types 模块
"""

import pytest

from sage.libs.rag.types import (
    RAGDocument,
    RAGQuery,
    RAGResponse,
    create_rag_document,
    create_rag_query,
    create_rag_response,
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

    def test_create_rag_document(self):
        """测试create_rag_document辅助函数"""
        doc = create_rag_document(
            text="Sample text",
            title="Sample",
            relevance_score=0.85,
            source="test.pdf",
        )
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

    def test_create_rag_query(self):
        """测试create_rag_query辅助函数"""
        query = create_rag_query(
            query="Test query",
            results=["r1", "r2", "r3"],
            generated="Generated answer",
            reranked=True,
        )
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
        doc = create_rag_document(text="test", title="Test")
        assert isinstance(doc, dict)
        assert "text" in doc
        assert doc.get("title") == "Test"

    def test_rag_query_is_dict(self):
        """验证RAGQuery可以作为普通字典使用"""
        query = create_rag_query(query="test", results=["r1"])
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
        doc = create_rag_document(text="test")
        assert "text" in doc
        assert doc.get("relevance_score") is None

        query = create_rag_query(query="test", results=[])
        assert "query" in query
        assert query.get("generated") is None

        response = create_rag_response(query="test", results=[])
        assert "query" in response
        assert response.get("generated") is None
