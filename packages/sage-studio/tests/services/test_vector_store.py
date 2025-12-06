"""Unit tests for VectorStore service.

Tests for VectorStore class which wraps neuromem VDBMemoryCollection
for SAGE Studio knowledge base storage and retrieval.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sage.studio.services.vector_store import (
    DocumentChunk,
    SearchResult,
    VectorStore,
    create_vector_store,
)


class TestDocumentChunk:
    """Tests for DocumentChunk dataclass."""

    def test_basic_creation(self):
        """Test basic DocumentChunk creation."""
        chunk = DocumentChunk(
            content="Hello, world!",
            source_file="/path/to/file.md",
            chunk_index=0,
        )
        assert chunk.content == "Hello, world!"
        assert chunk.source_file == "/path/to/file.md"
        assert chunk.chunk_index == 0
        assert chunk.metadata == {}

    def test_with_metadata(self):
        """Test DocumentChunk with metadata."""
        chunk = DocumentChunk(
            content="Test content",
            source_file="/path/to/file.py",
            chunk_index=1,
            metadata={"title": "Test", "language": "python"},
        )
        assert chunk.metadata["title"] == "Test"
        assert chunk.metadata["language"] == "python"

    def test_chunk_id_generation(self):
        """Test unique chunk ID generation."""
        chunk1 = DocumentChunk(
            content="Content A",
            source_file="/file1.md",
            chunk_index=0,
        )
        chunk2 = DocumentChunk(
            content="Content B",
            source_file="/file1.md",
            chunk_index=1,
        )
        chunk3 = DocumentChunk(
            content="Content A",
            source_file="/file1.md",
            chunk_index=0,
        )

        # Different chunks should have different IDs
        assert chunk1.chunk_id != chunk2.chunk_id
        # Same content should produce same ID
        assert chunk1.chunk_id == chunk3.chunk_id

    def test_chunk_id_is_string(self):
        """Test that chunk_id is a hex string."""
        chunk = DocumentChunk(
            content="Test",
            source_file="/test.md",
            chunk_index=0,
        )
        assert isinstance(chunk.chunk_id, str)
        assert len(chunk.chunk_id) == 16  # SHA256 truncated to 16 chars


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_basic_creation(self):
        """Test basic SearchResult creation."""
        result = SearchResult(
            content="Found content",
            score=0.95,
            source="/path/to/source.md",
        )
        assert result.content == "Found content"
        assert result.score == 0.95
        assert result.source == "/path/to/source.md"
        assert result.metadata == {}

    def test_with_metadata(self):
        """Test SearchResult with metadata."""
        result = SearchResult(
            content="Found content",
            score=0.85,
            source="/path/to/source.md",
            metadata={"chunk_index": "1", "title": "Section A"},
        )
        assert result.metadata["chunk_index"] == "1"
        assert result.metadata["title"] == "Section A"


class TestVectorStoreInit:
    """Tests for VectorStore initialization."""

    def test_default_initialization(self):
        """Test VectorStore with default parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStore(
                collection_name="test_collection",
                persist_dir=tmpdir,
            )
            assert store.collection_name == "test_collection"
            assert store.embedding_model == "BAAI/bge-m3"
            assert store.embedding_dim == 1024
            assert store.persist_dir == Path(tmpdir)

    def test_custom_parameters(self):
        """Test VectorStore with custom parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStore(
                collection_name="custom_kb",
                embedding_model="custom-model",
                embedding_dim=768,
                persist_dir=tmpdir,
            )
            assert store.collection_name == "custom_kb"
            assert store.embedding_model == "custom-model"
            assert store.embedding_dim == 768

    def test_external_embedder(self):
        """Test VectorStore with external embedder."""
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [[0.1] * 512]
        mock_embedder.get_dim.return_value = 512

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStore(
                collection_name="test_external",
                persist_dir=tmpdir,
                embedder=mock_embedder,
            )
            assert store._embedder is mock_embedder


class TestVectorStoreOperations:
    """Tests for VectorStore operations using mocks."""

    @pytest.fixture
    def mock_store(self):
        """Create a VectorStore with mocked dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock embedder - return multiple vectors for batch operations
            mock_embedder = MagicMock()
            mock_embedder.embed.side_effect = lambda texts: [[0.1] * 1024 for _ in texts]
            mock_embedder.get_dim.return_value = 1024

            store = VectorStore(
                collection_name="mock_test",
                embedding_dim=1024,
                persist_dir=tmpdir,
                embedder=mock_embedder,
            )

            # Mock collection
            mock_collection = MagicMock()
            mock_collection.insert.return_value = "test_id"
            mock_collection.retrieve.return_value = [
                {
                    "text": "Found text",
                    "score": 0.9,
                    "metadata": {"source_file": "/test.md"},
                }
            ]
            mock_collection.statistics = {"total_vectors": 100}
            mock_collection.list_indexes.return_value = []

            store._collection = mock_collection

            yield store

    @pytest.mark.asyncio
    async def test_add_documents(self, mock_store):
        """Test adding documents to vector store."""
        chunks = [
            DocumentChunk(
                content="Test content 1",
                source_file="/test1.md",
                chunk_index=0,
            ),
            DocumentChunk(
                content="Test content 2",
                source_file="/test2.md",
                chunk_index=0,
            ),
        ]

        count = await mock_store.add_documents(chunks)
        assert count == 2
        assert mock_store._collection.insert.call_count == 2

    @pytest.mark.asyncio
    async def test_add_empty_documents(self, mock_store):
        """Test adding empty document list."""
        count = await mock_store.add_documents([])
        assert count == 0
        mock_store._collection.insert.assert_not_called()

    @pytest.mark.asyncio
    async def test_search(self, mock_store):
        """Test search functionality."""
        results = await mock_store.search("test query", top_k=5)

        assert len(results) == 1
        assert results[0].content == "Found text"
        assert results[0].score == 0.9
        assert results[0].source == "/test.md"

    @pytest.mark.asyncio
    async def test_search_with_threshold(self, mock_store):
        """Test search with score threshold."""
        # Mock returns result with score 0.9
        results = await mock_store.search(
            "test query",
            top_k=5,
            score_threshold=0.95,  # Higher than result score
        )

        # Result should be filtered out
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_with_source_filter(self, mock_store):
        """Test search with source filter."""
        # Result has source "/test.md"
        results = await mock_store.search(
            "test query",
            source_filter="/other.md",  # Different from result source
        )

        # Result should be filtered out
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_empty_results(self, mock_store):
        """Test search returning empty results."""
        mock_store._collection.retrieve.return_value = None

        results = await mock_store.search("no results query")
        assert results == []

    def test_get_stats(self, mock_store):
        """Test getting statistics."""
        stats = mock_store.get_stats()

        assert stats["collection_name"] == "mock_test"
        assert stats["embedding_model"] == "BAAI/bge-m3"
        assert stats["embedding_dim"] == 1024
        assert "total_vectors" in stats

    def test_close(self, mock_store):
        """Test closing the store."""
        mock_store.close()

        assert mock_store._collection is None
        assert mock_store._manager is None
        assert mock_store._embedder is None


class TestCreateVectorStore:
    """Tests for create_vector_store factory function."""

    def test_default_creation(self):
        """Test factory with defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_vector_store(persist_dir=tmpdir)

            assert store.collection_name == "studio_default"
            assert store.embedding_model == "BAAI/bge-small-zh-v1.5"

    def test_custom_creation(self):
        """Test factory with custom parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_vector_store(
                collection_name="custom",
                embedding_model="custom-model",
                persist_dir=tmpdir,
            )

            assert store.collection_name == "custom"
            assert store.embedding_model == "custom-model"


# Integration test marker - these tests require actual dependencies
@pytest.mark.integration
class TestVectorStoreIntegration:
    """Integration tests for VectorStore with real components.

    These tests require:
    - sage-mem/neuromem installed
    - sage-embedding with HuggingFace support

    Run with: pytest -m integration
    """

    @pytest.fixture
    def real_store(self):
        """Create a real VectorStore for integration testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                store = VectorStore(
                    collection_name="integration_test",
                    embedding_model="BAAI/bge-small-zh-v1.5",
                    embedding_dim=512,
                    persist_dir=tmpdir,
                )
                yield store
                store.close()
            except ImportError as e:
                pytest.skip(f"Required dependency not available: {e}")

    @pytest.mark.asyncio
    async def test_full_workflow(self, real_store):
        """Test complete add -> search workflow."""
        # Add documents
        chunks = [
            DocumentChunk(
                content="SAGE is a framework for building AI pipelines.",
                source_file="/docs/intro.md",
                chunk_index=0,
                metadata={"title": "Introduction"},
            ),
            DocumentChunk(
                content="Pipelines can be created using the Pipeline Builder.",
                source_file="/docs/pipeline.md",
                chunk_index=0,
                metadata={"title": "Pipeline Guide"},
            ),
        ]

        added = await real_store.add_documents(chunks)
        assert added == 2

        # Search
        results = await real_store.search("How to create pipelines?")

        # Should find relevant content
        assert len(results) > 0
        # Pipeline-related doc should rank higher
        assert "pipeline" in results[0].content.lower() or "SAGE" in results[0].content
