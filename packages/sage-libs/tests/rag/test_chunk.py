"""
Tests for RAG chunk module

Tests cover:
- CharacterSplitter: Basic splitting, overlap, separator
- SentenceTransformersTokenTextSplitter: Mocked initialization
"""

from unittest.mock import Mock, patch

import pytest


@pytest.mark.unit
class TestCharacterSplitter:
    """Test CharacterSplitter"""

    def test_basic_split(self):
        """测试基本字符分割"""
        from sage.libs.rag.chunk import CharacterSplitter

        splitter = CharacterSplitter(chunk_size=10, overlap=2)
        text = "This is a test text for chunking"
        chunks = splitter.split(text)

        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)
        # First chunk should be 10 characters
        assert len(chunks[0]) == 10

    def test_overlap(self):
        """测试重叠"""
        from sage.libs.rag.chunk import CharacterSplitter

        splitter = CharacterSplitter(chunk_size=5, overlap=2)
        text = "abcdefghij"
        chunks = splitter.split(text)

        # With overlap=2, each chunk should overlap with next
        assert len(chunks) > 1
        # Check that chunks overlap
        assert chunks[0][-2:] in chunks[1] or len(chunks[1]) < 2

    def test_separator_split(self):
        """测试使用分隔符分割"""
        from sage.libs.rag.chunk import CharacterSplitter

        splitter = CharacterSplitter(separator=",")
        text = "chunk1,chunk2,chunk3"
        chunks = splitter.split(text)

        assert len(chunks) == 3
        assert chunks[0] == "chunk1"
        assert chunks[1] == "chunk2"
        assert chunks[2] == "chunk3"

    def test_empty_text(self):
        """测试空文本"""
        from sage.libs.rag.chunk import CharacterSplitter

        splitter = CharacterSplitter(chunk_size=10, overlap=2)
        chunks = splitter.split("")

        assert isinstance(chunks, list)
        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_config(self):
        """测试配置"""
        from sage.libs.rag.chunk import CharacterSplitter

        splitter = CharacterSplitter(chunk_size=100, overlap=20, separator="\n")

        assert splitter.chunk_size == 100
        assert splitter.overlap == 20
        assert splitter.separator == "\n"


@pytest.mark.unit
class TestSentenceTransformersTokenTextSplitter:
    """Test SentenceTransformersTokenTextSplitter with mocking"""

    @patch("sage.libs.rag.chunk.AutoTokenizer")
    @patch("sage.libs.rag.chunk.SentenceTransformer")
    def test_init(self, mock_st, mock_tokenizer):
        """测试初始化"""
        from sage.libs.rag.chunk import SentenceTransformersTokenTextSplitter

        mock_model = Mock()
        mock_st.return_value = mock_model

        mock_tok = Mock()
        mock_tokenizer.from_pretrained.return_value = mock_tok

        splitter = SentenceTransformersTokenTextSplitter(
            model_name="test-model", chunk_size=512, chunk_overlap=50
        )

        assert splitter.model_name == "test-model"
        assert splitter.chunk_size == 512
        assert splitter.chunk_overlap == 50
        mock_st.assert_called_once_with("test-model")
        mock_tokenizer.from_pretrained.assert_called_once_with("test-model")

    @patch("sage.libs.rag.chunk.AutoTokenizer")
    @patch("sage.libs.rag.chunk.SentenceTransformer")
    def test_invalid_config(self, mock_st, mock_tokenizer):
        """测试无效配置"""
        from sage.libs.rag.chunk import SentenceTransformersTokenTextSplitter

        mock_st.return_value = Mock()
        mock_tokenizer.from_pretrained.return_value = Mock()

        # Overlap >= chunk_size (checked first in source)
        with pytest.raises(ValueError, match="must be less than"):
            SentenceTransformersTokenTextSplitter(chunk_size=100, chunk_overlap=100)

        # Chunk size <= 0
        with pytest.raises(ValueError, match="must be greater than"):
            SentenceTransformersTokenTextSplitter(chunk_size=0, chunk_overlap=-1)

    @patch("sage.libs.rag.chunk.AutoTokenizer")
    @patch("sage.libs.rag.chunk.SentenceTransformer")
    def test_split(self, mock_st, mock_tokenizer):
        """测试分割"""
        from sage.libs.rag.chunk import SentenceTransformersTokenTextSplitter

        mock_st.return_value = Mock()

        # Mock tokenizer
        mock_tok = Mock()
        mock_tok.encode.return_value = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        mock_tok.decode.side_effect = lambda ids, **kwargs: " ".join(str(i) for i in ids)
        mock_tokenizer.from_pretrained.return_value = mock_tok

        splitter = SentenceTransformersTokenTextSplitter(chunk_size=5, chunk_overlap=2)
        chunks = splitter.split("test text")

        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)
        mock_tok.encode.assert_called_once()
        assert mock_tok.decode.call_count > 0
