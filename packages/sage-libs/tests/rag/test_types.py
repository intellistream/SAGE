"""
Tests for RAG types module

Tests cover:
- RAGDocument: TypedDict for RAG documents
- RAGQuery: TypedDict for RAG queries
- RAGResponse: TypedDict for RAG responses
- Helper functions: ensure_rag_response, extract_query, extract_results, create_rag_response
"""

import pytest


@pytest.mark.unit
class TestRAGDocument:
    """Test RAGDocument TypedDict"""

    def test_create_basic_document(self):
        """测试创建基本RAG文档"""
        from sage.libs.rag.types import RAGDocument

        doc: RAGDocument = {"text": "Test content"}

        assert doc["text"] == "Test content"

    def test_create_full_document(self):
        """测试创建完整RAG文档"""
        from sage.libs.rag.types import RAGDocument

        doc: RAGDocument = {
            "text": "Test content",
            "title": "Test Title",
            "relevance_score": 0.95,
            "source": "test.txt",
            "chunk_id": 1,
        }

        assert doc["text"] == "Test content"
        assert doc["title"] == "Test Title"
        assert doc["relevance_score"] == 0.95
        assert doc["chunk_id"] == 1


@pytest.mark.unit
class TestRAGQuery:
    """Test RAGQuery TypedDict"""

    def test_create_basic_query(self):
        """测试创建基本查询"""
        from sage.libs.rag.types import RAGQuery

        query: RAGQuery = {"query": "What is AI?", "results": ["doc1", "doc2"]}

        assert query["query"] == "What is AI?"
        assert len(query["results"]) == 2

    def test_create_full_query(self):
        """测试创建完整查询"""
        from sage.libs.rag.types import RAGQuery

        query: RAGQuery = {
            "query": "What is AI?",
            "results": ["doc1"],
            "generated": "AI is...",
            "execution_time": 1.5,
            "reranked": True,
        }

        assert query["generated"] == "AI is..."
        assert query["execution_time"] == 1.5
        assert query["reranked"] is True


@pytest.mark.unit
class TestRAGResponse:
    """Test RAGResponse TypedDict"""

    def test_create_basic_response(self):
        """测试创建基本响应"""
        from sage.libs.rag.types import RAGResponse

        response: RAGResponse = {"query": "test", "results": []}

        assert response["query"] == "test"
        assert isinstance(response["results"], list)

    def test_create_full_response(self):
        """测试创建完整响应"""
        from sage.libs.rag.types import RAGResponse

        response: RAGResponse = {
            "query": "What is AI?",
            "results": ["doc1", "doc2"],
            "generated": "AI is artificial intelligence",
            "context": "Retrieved context",
            "execution_time": 2.5,
            "metadata": {"model": "gpt-4"},
        }

        assert response["query"] == "What is AI?"
        assert response["generated"] == "AI is artificial intelligence"
        assert response["context"] == "Retrieved context"
        assert response["execution_time"] == 2.5
        assert response["metadata"]["model"] == "gpt-4"


@pytest.mark.unit
class TestHelperFunctions:
    """Test helper functions"""

    def test_ensure_rag_response_from_dict(self):
        """测试从字典创建RAG响应"""
        from sage.libs.rag.types import ensure_rag_response

        data = {"query": "test", "results": ["a", "b"]}
        response = ensure_rag_response(data)

        assert response["query"] == "test"
        assert len(response["results"]) == 2

    def test_ensure_rag_response_from_tuple(self):
        """测试从元组创建RAG响应"""
        from sage.libs.rag.types import ensure_rag_response

        data = ("query text", ["result1", "result2"])
        response = ensure_rag_response(data)

        assert response["query"] == "query text"
        assert len(response["results"]) == 2

    def test_extract_query(self):
        """测试提取查询"""
        from sage.libs.rag.types import extract_query

        query = extract_query({"query": "test query", "results": []})
        assert query == "test query"

        query = extract_query(("tuple query", []))
        assert query == "tuple query"

    def test_extract_results(self):
        """测试提取结果"""
        from sage.libs.rag.types import extract_results

        results = extract_results({"query": "test", "results": ["a", "b"]})
        assert results == ["a", "b"]

        results = extract_results(("query", ["x", "y"]))
        assert results == ["x", "y"]

    def test_create_rag_response(self):
        """测试创建RAG响应"""
        from sage.libs.rag.types import create_rag_response

        response = create_rag_response(
            query="What is Python?",
            results=["doc1", "doc2"],
            generated="Python is a programming language",
            execution_time=1.0,
        )

        assert response["query"] == "What is Python?"
        assert len(response["results"]) == 2
        assert response["generated"] == "Python is a programming language"
        assert response["execution_time"] == 1.0
