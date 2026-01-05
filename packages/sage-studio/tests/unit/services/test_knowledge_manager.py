from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sage.studio.services.knowledge_manager import KnowledgeManager


@pytest.fixture
def mock_config_file(tmp_path):
    config_path = tmp_path / "knowledge_sources.yaml"
    config_content = """
knowledge_sources:
  test_source:
    type: markdown
    path: "tests/data"
    description: "Test Source"
    enabled: true
    auto_load: false
    file_patterns: ["*.md"]

vector_store:
  type: chroma
  persist_dir: "/tmp/sage_test_db"
  collection_prefix: "test_kb_"

embedding:
  model: "test-model"
"""
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def knowledge_manager(mock_config_file):
    with patch("sage.studio.services.document_loader.DocumentLoader") as MockLoader:
        manager = KnowledgeManager(config_path=mock_config_file)
        manager._doc_loader = MockLoader.return_value
        yield manager


@pytest.mark.asyncio
async def test_ensure_source_loaded(knowledge_manager):
    # Mock VectorStore
    with patch("sage.studio.services.vector_store.VectorStore") as MockVectorStore:
        mock_vs = AsyncMock()
        mock_vs.add_documents.return_value = 10
        MockVectorStore.return_value = mock_vs

        # Mock DocumentLoader
        knowledge_manager._doc_loader.load_directory.return_value = ["chunk1", "chunk2"]

        # Test loading
        result = await knowledge_manager.ensure_source_loaded("test_source")

        assert result is True
        assert "test_source" in knowledge_manager.get_loaded_sources()
        knowledge_manager._doc_loader.load_directory.assert_called_once()
        mock_vs.add_documents.assert_called_once()


@pytest.mark.asyncio
async def test_search(knowledge_manager):
    # Mock VectorStore
    with patch("sage.studio.services.vector_store.VectorStore") as MockVectorStore:
        mock_vs = AsyncMock()
        mock_result = MagicMock()
        mock_result.score = 0.9
        mock_result.content = "test content"
        mock_vs.search.return_value = [mock_result]
        MockVectorStore.return_value = mock_vs

        # Pre-load source
        knowledge_manager._loaded_sources.add("test_source")
        knowledge_manager._vector_stores["test_source"] = mock_vs

        # Test search
        results = await knowledge_manager.search("query", sources=["test_source"])

        assert len(results) == 1
        assert results[0].content == "test content"
        mock_vs.search.assert_called_once()


@pytest.mark.asyncio
async def test_add_document(knowledge_manager, tmp_path):
    # Create a dummy file
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test")

    # Mock VectorStore
    with patch("sage.studio.services.vector_store.VectorStore") as MockVectorStore:
        mock_vs = AsyncMock()
        mock_vs.add_documents.return_value = 1
        MockVectorStore.return_value = mock_vs

        # Mock DocumentLoader
        knowledge_manager._doc_loader.load_file.return_value = ["chunk"]

        # Test adding document
        result = await knowledge_manager.add_document(test_file, source_name="user_uploads")

        assert result is True
        assert "user_uploads" in knowledge_manager.get_loaded_sources()
        knowledge_manager._doc_loader.load_file.assert_called_once()
        mock_vs.add_documents.assert_called_once()


@pytest.mark.asyncio
async def test_env_var_expansion(tmp_path):
    # Set env var
    import os

    os.environ["TEST_ROOT"] = str(tmp_path)

    config_path = tmp_path / "env_config.yaml"
    config_content = """
knowledge_sources:
  env_source:
    type: markdown
    path: "${TEST_ROOT}/docs"
    description: "Env Source"
    enabled: true
"""
    config_path.write_text(config_content)

    # Create docs dir
    (tmp_path / "docs").mkdir()

    with patch("sage.studio.services.document_loader.DocumentLoader"):
        manager = KnowledgeManager(config_path=config_path)
        source = manager.sources["env_source"]

        assert source.path == tmp_path / "docs"


@pytest.mark.asyncio
async def test_ingest_texts_uses_vector_store(knowledge_manager):
    vs = AsyncMock()
    vs.add_documents.return_value = 2
    knowledge_manager._get_or_create_vector_store = MagicMock(return_value=vs)

    added = await knowledge_manager.ingest_texts(
        ["a", "b"], source_name="agentic", metadata={"session_id": "s1"}
    )

    assert added == 2
    vs.add_documents.assert_called_once()
    chunks = vs.add_documents.call_args[0][0]
    assert chunks[0].metadata.get("session_id") == "s1"
    assert "agentic" in knowledge_manager.get_loaded_sources()
