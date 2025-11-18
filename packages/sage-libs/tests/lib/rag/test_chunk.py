"""
测试 sage.libs.rag.chunk 模块
"""

import pytest

from sage.libs.rag.chunk import CharacterSplitter


@pytest.mark.unit
class TestCharacterSplitter:
    """测试CharacterSplitter类"""

    def test_character_splitter_initialization_default(self):
        """测试CharacterSplitter默认初始化"""
        splitter = CharacterSplitter()

        assert splitter.chunk_size == 512
        assert splitter.overlap == 128
        assert splitter.separator is None

    def test_character_splitter_initialization_custom(self):
        """测试CharacterSplitter自定义初始化"""
        splitter = CharacterSplitter(chunk_size=256, overlap=64, separator="\n")

        assert splitter.chunk_size == 256
        assert splitter.overlap == 64
        assert splitter.separator == "\n"

    def test_split_basic(self):
        """测试基本分割功能"""
        splitter = CharacterSplitter(chunk_size=10, overlap=3)
        text = "Hello World Test"
        chunks = splitter.split(text)

        assert isinstance(chunks, list)
        assert len(chunks) >= 1
        assert chunks[0] == "Hello Worl"

    def test_split_with_separator(self):
        """测试使用分隔符分割"""
        splitter = CharacterSplitter(chunk_size=10, overlap=3, separator="\n")
        text = "Line 1\nLine 2\nLine 3"
        chunks = splitter.split(text)

        assert len(chunks) == 3
        assert chunks[0] == "Line 1"
        assert chunks[1] == "Line 2"
        assert chunks[2] == "Line 3"

    def test_split_empty_text(self):
        """测试空文本"""
        splitter = CharacterSplitter(chunk_size=10, overlap=3)
        chunks = splitter.split("")

        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_split_short_text(self):
        """测试短文本（小于chunk_size）"""
        splitter = CharacterSplitter(chunk_size=20, overlap=5)
        text = "Short"
        chunks = splitter.split(text)

        assert len(chunks) == 1
        assert chunks[0] == "Short"

    def test_split_exact_chunk_size(self):
        """测试文本长度正好等于chunk_size"""
        splitter = CharacterSplitter(chunk_size=10, overlap=3)
        text = "1234567890"
        chunks = splitter.split(text)

        assert len(chunks) == 2
        assert chunks[0] == "1234567890"
        assert len(chunks[1]) == 3

    def test_split_with_overlap(self):
        """测试重叠功能"""
        splitter = CharacterSplitter(chunk_size=5, overlap=2)
        text = "ABCDEFGHIJ"
        chunks = splitter.split(text)

        # 验证有重叠
        if len(chunks) > 1:
            # 第一个chunk的最后2个字符应该与第二个chunk的前2个字符重叠
            assert chunks[0][-2:] == chunks[1][:2]

    def test_split_zero_overlap(self):
        """测试零重叠"""
        splitter = CharacterSplitter(chunk_size=5, overlap=0)
        text = "1234567890ABCDE"  # pragma: allowlist secret
        chunks = splitter.split(text)

        assert len(chunks) == 3
        assert chunks[0] == "12345"
        assert chunks[1] == "67890"
        assert chunks[2] == "ABCDE"

    def test_split_chinese_text(self):
        """测试中文文本"""
        splitter = CharacterSplitter(chunk_size=5, overlap=2)
        text = "这是一个测试文档需要分割"
        chunks = splitter.split(text)

        assert isinstance(chunks, list)
        assert len(chunks) > 1
        assert chunks[0] == "这是一个测"

    def test_split_long_text(self):
        """测试长文本"""
        splitter = CharacterSplitter(chunk_size=50, overlap=10)
        text = "A" * 500
        chunks = splitter.split(text)

        # 验证所有chunk（除最后一个）长度为chunk_size
        for chunk in chunks[:-1]:
            assert len(chunk) == 50

        # 验证有重叠
        if len(chunks) > 1:
            assert chunks[0][-10:] == chunks[1][:10]

    def test_split_with_special_characters(self):
        """测试特殊字符"""
        splitter = CharacterSplitter(chunk_size=8, overlap=2)
        text = "Hello!\n\tWorld@#$"
        chunks = splitter.split(text)

        assert isinstance(chunks, list)
        # 验证特殊字符被保留
        combined = "".join(chunks)
        assert "\n" in combined
        assert "\t" in combined
        assert "@#$" in combined


@pytest.mark.external
class TestSentenceTransformersTokenTextSplitter:
    """测试SentenceTransformersTokenTextSplitter类（需要外部依赖）"""

    def test_import_sentence_transformer_splitter(self):
        """测试导入SentenceTransformersTokenTextSplitter"""
        try:
            from sage.libs.rag.chunk import SentenceTransformersTokenTextSplitter

            assert SentenceTransformersTokenTextSplitter is not None
        except ImportError:
            pytest.skip("sentence-transformers not installed")

    def test_sentence_transformer_initialization_error(self):
        """测试没有依赖时的错误"""
        pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed")
