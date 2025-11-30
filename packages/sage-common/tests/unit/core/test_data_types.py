"""
Tests for sage.common.core.data_types

Tests the universal data type definitions for SAGE framework.
"""

from sage.common.core.data_types import (
    BaseDocument,
    BaseQueryResult,
    ExtendedQueryResult,
    create_query_result,
    ensure_query_result,
    extract_query,
    extract_results,
)


class TestBaseDocument:
    """Tests for BaseDocument TypedDict"""

    def test_base_document_required_field(self):
        """Test BaseDocument with required text field"""
        doc: BaseDocument = {"text": "Sample text"}
        assert doc["text"] == "Sample text"

    def test_base_document_all_fields(self):
        """Test BaseDocument with all fields"""
        doc: BaseDocument = {
            "text": "Sample text",
            "id": "doc_123",
            "title": "Sample Title",
            "source": "source.pdf",
            "score": 0.95,
            "rank": 1,
            "metadata": {"key": "value"},
        }
        assert doc["text"] == "Sample text"
        assert doc["id"] == "doc_123"
        assert doc["title"] == "Sample Title"
        assert doc["source"] == "source.pdf"
        assert doc["score"] == 0.95
        assert doc["rank"] == 1
        assert doc["metadata"] == {"key": "value"}

    def test_base_document_numeric_id(self):
        """Test BaseDocument with numeric ID"""
        doc: BaseDocument = {"text": "Sample", "id": 123}
        assert doc["id"] == 123


class TestBaseQueryResult:
    """Tests for BaseQueryResult TypedDict"""

    def test_base_query_result_required_fields(self):
        """Test BaseQueryResult with required fields"""
        result: BaseQueryResult = {
            "query": "test query",
            "results": ["result1", "result2"],
        }
        assert result["query"] == "test query"
        assert result["results"] == ["result1", "result2"]

    def test_base_query_result_empty_results(self):
        """Test BaseQueryResult with empty results"""
        result: BaseQueryResult = {"query": "test", "results": []}
        assert result["query"] == "test"
        assert result["results"] == []


class TestExtendedQueryResult:
    """Tests for ExtendedQueryResult TypedDict"""

    def test_extended_query_result_basic(self):
        """Test ExtendedQueryResult with basic fields"""
        result: ExtendedQueryResult = {
            "query": "test query",
            "results": ["result1"],
        }
        assert result["query"] == "test query"
        assert result["results"] == ["result1"]

    def test_extended_query_result_with_extras(self):
        """Test ExtendedQueryResult with extra fields"""
        result: ExtendedQueryResult = {
            "query": "test",
            "results": ["a", "b"],
            "query_id": "q_123",
            "timestamp": 1234567890,
            "total_count": 100,
            "execution_time": 0.5,
            "context": "context string",
            "metadata": {"model": "gpt-4"},
        }
        assert result["query"] == "test"
        assert result["query_id"] == "q_123"
        assert result["timestamp"] == 1234567890
        assert result["total_count"] == 100
        assert result["execution_time"] == 0.5
        assert result["context"] == "context string"
        assert result["metadata"] == {"model": "gpt-4"}


class TestEnsureQueryResult:
    """Tests for ensure_query_result() function"""

    def test_ensure_from_dict(self):
        """Test ensure_query_result from dict"""
        data = {"query": "test", "results": ["a", "b"]}
        result = ensure_query_result(data)
        assert result["query"] == "test"
        assert result["results"] == ["a", "b"]

    def test_ensure_from_dict_with_question(self):
        """Test ensure_query_result from dict with 'question' key"""
        data = {"question": "test", "results": ["a"]}
        result = ensure_query_result(data)
        assert result["query"] == "test"
        assert result["results"] == ["a"]

    def test_ensure_from_dict_with_docs(self):
        """Test ensure_query_result from dict with 'docs' key"""
        data = {"query": "test", "docs": ["doc1", "doc2"]}
        result = ensure_query_result(data)
        assert result["query"] == "test"
        assert result["results"] == ["doc1", "doc2"]

    def test_ensure_from_tuple(self):
        """Test ensure_query_result from tuple"""
        data = ("query", ["result1", "result2"])
        result = ensure_query_result(data)
        assert result["query"] == "query"
        assert result["results"] == ["result1", "result2"]

    def test_ensure_from_list(self):
        """Test ensure_query_result from list"""
        data = ["query", ["result1"]]
        result = ensure_query_result(data)
        assert result["query"] == "query"
        assert result["results"] == ["result1"]

    def test_ensure_with_default_query(self):
        """Test ensure_query_result with default query"""
        data = {}
        result = ensure_query_result(data, default_query="default")
        assert result["query"] == "default"
        assert result["results"] == []

    def test_ensure_invalid_format(self):
        """Test ensure_query_result with invalid format"""
        data: dict = {}  # Type hint to avoid type error
        result = ensure_query_result(data, default_query="fallback")
        assert result["query"] == "fallback"
        assert result["results"] == []

    def test_ensure_with_non_list_results_iterable(self):
        """Test ensure_query_result converts non-list iterables to list"""
        data = {"query": "test", "results": ("a", "b", "c")}  # tuple instead of list
        result = ensure_query_result(data)
        assert result["query"] == "test"
        assert result["results"] == ["a", "b", "c"]
        assert isinstance(result["results"], list)

    def test_ensure_with_non_list_results_single_value(self):
        """Test ensure_query_result wraps single non-list value in list"""
        data = {"query": "test", "results": "single_item"}
        result = ensure_query_result(data)
        assert result["query"] == "test"
        assert result["results"] == ["single_item"]
        assert isinstance(result["results"], list)

    def test_ensure_unparseable_input(self):
        """Test ensure_query_result with completely unparseable input"""
        # Input that doesn't match any expected format
        result = ensure_query_result("invalid_string", default_query="default")
        assert result["query"] == "default"
        assert result["results"] == []


class TestExtractQuery:
    """Tests for extract_query() function"""

    def test_extract_from_string(self):
        """Test extract_query from string input"""
        assert extract_query("test query") == "test query"

    def test_extract_from_dict_query(self):
        """Test extract_query from dict with 'query' key"""
        assert extract_query({"query": "test"}) == "test"

    def test_extract_from_dict_question(self):
        """Test extract_query from dict with 'question' key"""
        assert extract_query({"question": "test"}) == "test"

    def test_extract_from_dict_q(self):
        """Test extract_query from dict with 'q' key"""
        assert extract_query({"q": "test"}) == "test"

    def test_extract_from_tuple(self):
        """Test extract_query from tuple"""
        assert extract_query(("query", ["results"])) == "query"

    def test_extract_from_list(self):
        """Test extract_query from list"""
        assert extract_query(["query", ["results"]]) == "query"

    def test_extract_with_default(self):
        """Test extract_query with default value"""
        assert extract_query({}, default="default") == "default"
        assert extract_query([], default="fallback") == "fallback"

    def test_extract_none_value(self):
        """Test extract_query with None value"""
        assert extract_query((None, ["results"]), default="default") == "default"


class TestExtractResults:
    """Tests for extract_results() function"""

    def test_extract_from_dict_results(self):
        """Test extract_results from dict with 'results' key"""
        assert extract_results({"results": ["a", "b"]}) == ["a", "b"]

    def test_extract_from_dict_documents(self):
        """Test extract_results from dict with 'documents' key"""
        assert extract_results({"documents": ["a", "b"]}) == ["a", "b"]

    def test_extract_from_dict_docs(self):
        """Test extract_results from dict with 'docs' key"""
        assert extract_results({"docs": ["a"]}) == ["a"]

    def test_extract_from_dict_items(self):
        """Test extract_results from dict with 'items' key"""
        assert extract_results({"items": ["a"]}) == ["a"]

    def test_extract_from_tuple(self):
        """Test extract_results from tuple"""
        assert extract_results(("query", ["a", "b"])) == ["a", "b"]

    def test_extract_from_list(self):
        """Test extract_results from list"""
        assert extract_results(["query", ["a", "b"]]) == ["a", "b"]

    def test_extract_single_item(self):
        """Test extract_results with single non-list item"""
        assert extract_results({"results": "single"}) == ["single"]

    def test_extract_with_default(self):
        """Test extract_results with default value"""
        assert extract_results({}, default=["default"]) == ["default"]
        assert extract_results({}) == []

    def test_extract_from_single_element_list(self):
        """Test extract_results from single-element list/tuple"""
        # Single element list/tuple (length < 2) should return as list
        assert extract_results(["only_one"]) == ["only_one"]
        assert extract_results(("single",)) == ["single"]

    def test_extract_from_invalid_type(self):
        """Test extract_results from invalid type returns default"""
        # String, int, etc. should return default
        assert extract_results("string_input", default=["fallback"]) == ["fallback"]
        assert extract_results(123, default=["default"]) == ["default"]
        assert extract_results(None) == []


class TestCreateQueryResult:
    """Tests for create_query_result() function"""

    def test_create_basic(self):
        """Test create_query_result with basic params"""
        result = create_query_result("query", ["a", "b"])
        assert result["query"] == "query"
        assert result["results"] == ["a", "b"]

    def test_create_with_extras(self):
        """Test create_query_result with extra fields"""
        result = create_query_result(
            query="test",
            results=["a"],
            execution_time=0.5,
            total_count=10,
            metadata={"key": "value"},
        )
        assert result["query"] == "test"
        assert result["results"] == ["a"]
        assert result.get("execution_time") == 0.5
        assert result.get("total_count") == 10
        assert result.get("metadata") == {"key": "value"}

    def test_create_filters_none_values(self):
        """Test create_query_result filters out None values"""
        result = create_query_result(
            query="test",
            results=[],
            execution_time=None,
            metadata={"key": "val"},
        )
        assert "query" in result
        assert "results" in result
        assert "metadata" in result
        # execution_time should not be in result since it's None
        assert "execution_time" not in result

    def test_create_empty_results(self):
        """Test create_query_result with empty results"""
        result = create_query_result("query", [])
        assert result["query"] == "query"
        assert result["results"] == []


class TestTypeCompatibility:
    """Tests for type compatibility and integration"""

    def test_pipeline_simulation(self):
        """Simulate a data pipeline using these types"""
        # Retriever output
        retriever_out = create_query_result(
            query="test query",
            results=["doc1", "doc2", "doc3"],
            total_count=3,
        )

        # Reranker input (from retriever)
        query = extract_query(retriever_out)
        docs = extract_results(retriever_out)
        assert query == "test query"
        assert len(docs) == 3

        # Reranker output
        reranker_out = create_query_result(query=query, results=docs[:2], execution_time=0.1)

        # Generator input
        final_query = extract_query(reranker_out)
        final_docs = extract_results(reranker_out)
        assert final_query == "test query"
        assert len(final_docs) == 2
