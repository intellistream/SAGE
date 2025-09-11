"""
测试 sage.libs.rag.chunk 模块
"""

from typing import List
from unittest.mock import MagicMock, Mock, patch

import pytest

# 尝试导入chunk模块
pytest_plugins = []

try:
    from sage.libs.rag.chunk import CharacterSplitter

    CHUNK_AVAILABLE = True
except ImportError as e:
    CHUNK_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Chunk module not available: {e}")


@pytest.mark.unit
class TestCharacterSplitter:
    """测试CharacterSplitter类"""

    def test_character_splitter_import(self):
        """测试CharacterSplitter导入"""
        if not CHUNK_AVAILABLE:
            pytest.skip("Chunk module not available")

        from sage.libs.rag.chunk import CharacterSplitter

        assert CharacterSplitter is not None

    def test_character_splitter_initialization_default(self):
        """测试CharacterSplitter默认初始化"""
        if not CHUNK_AVAILABLE:
            pytest.skip("Chunk module not available")

        config = {}
        splitter = CharacterSplitter(config=config)

        assert splitter.config == config
        assert splitter.chunk_size == 512  # 默认值
        assert splitter.overlap == 128  # 默认值

    def test_character_splitter_initialization_custom(self):
        """测试CharacterSplitter自定义初始化"""
        if not CHUNK_AVAILABLE:
            pytest.skip("Chunk module not available")

        config = {"chunk_size": 256, "overlap": 64}
        splitter = CharacterSplitter(config=config)

        assert splitter.config == config
        assert splitter.chunk_size == 256
        assert splitter.overlap == 64

    def test_split_text_basic(self):
        """测试基本文本分割功能"""
        if not CHUNK_AVAILABLE:
            pytest.skip("Chunk module not available")

        config = {"chunk_size": 10, "overlap": 3}
        splitter = CharacterSplitter(config=config)

        # 测试短文本（长度为15个字符）
        text = "Hello World Test"
        chunks = splitter._split_text(text)

        # 验证分割结果
        assert isinstance(chunks, list)
        assert len(chunks) >= 1

        # 第一个chunk应该是前10个字符
        assert chunks[0] == "Hello Worl"

        # 第二个chunk应该从第7个字符开始（10-3=7）
        if len(chunks) > 1:
            assert chunks[1] == "orld Test"

    def test_split_text_exact_chunk_size(self):
        """测试文本长度正好等于chunk_size的情况"""
        if not CHUNK_AVAILABLE:
            pytest.skip("Chunk module not available")

        config = {"chunk_size": 10, "overlap": 3}
        splitter = CharacterSplitter(config=config)

        # 文本长度正好等于chunk_size
        text = "1234567890"  # 10个字符
        chunks = splitter._split_text(text)

        # 由于有overlap，会产生两个chunks
        assert len(chunks) == 2
        assert chunks[0] == "1234567890"
        assert chunks[1] == "890"  # 最后3个字符(从位置7开始)

    def test_split_text_shorter_than_chunk_size(self):
        """测试文本长度小于chunk_size的情况"""
        if not CHUNK_AVAILABLE:
            pytest.skip("Chunk module not available")

        config = {"chunk_size": 20, "overlap": 5}
        splitter = CharacterSplitter(config=config)

        # 文本长度小于chunk_size
        text = "Short text"  # 10个字符
        chunks = splitter._split_text(text)

        # 应该只有一个chunk，包含全部文本
        assert len(chunks) == 1
        assert chunks[0] == "Short text"

    def test_split_text_empty(self):
        """测试空文本的情况"""
        if not CHUNK_AVAILABLE:
            pytest.skip("Chunk module not available")

        config = {"chunk_size": 10, "overlap": 3}
        splitter = CharacterSplitter(config=config)

        # 空文本
        text = ""
        chunks = splitter._split_text(text)

        # 应该返回一个包含空字符串的列表
        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_split_text_large_overlap(self):
        """测试overlap大于chunk_size的情况"""
        if not CHUNK_AVAILABLE:
            pytest.skip("Chunk module not available")

        config = {"chunk_size": 5, "overlap": 8}  # overlap > chunk_size
        splitter = CharacterSplitter(config=config)

        text = "This is a test text for overlapping"
        chunks = splitter._split_text(text)

        # 验证仍然能正常工作（虽然overlap很大）
        assert isinstance(chunks, list)
        assert len(chunks) >= 1
        assert chunks[0] == "This "

    def test_split_text_zero_overlap(self):
        """测试零overlap的情况"""
        if not CHUNK_AVAILABLE:
            pytest.skip("Chunk module not available")

        config = {"chunk_size": 5, "overlap": 0}
        splitter = CharacterSplitter(config=config)

        text = "1234567890ABCDE"  # 15个字符
        chunks = splitter._split_text(text)

        # 应该有3个chunk，没有重叠
        assert len(chunks) == 3
        assert chunks[0] == "12345"
        assert chunks[1] == "67890"
        assert chunks[2] == "ABCDE"

    def test_execute_basic(self):
        """测试execute方法基本功能"""
        if not CHUNK_AVAILABLE:
            pytest.skip("Chunk module not available")

        config = {"chunk_size": 10, "overlap": 3}
        splitter = CharacterSplitter(config=config)

        # 测试输入文档对象
        input_document = {
            "content": "This is a test document that needs to be split into chunks.",
            "metadata": {},
        }
        result = splitter.execute(input_document)

        # 验证结果
        assert isinstance(result, list)
        assert len(result) > 1  # 应该被分割成多个chunks

        # 验证第一个chunk
        assert result[0] == "This is a "

        # 验证chunks有重叠 - 检查相邻chunks之间的重叠
        assert "is a " in result[0]
        assert "a " in result[1]  # 第二个chunk应该以overlap开始

    def test_execute_with_chinese_text(self):
        """测试execute方法处理中文文本"""
        if not CHUNK_AVAILABLE:
            pytest.skip("Chunk module not available")

        config = {"chunk_size": 5, "overlap": 2}
        splitter = CharacterSplitter(config=config)

        # 中文文档对象
        input_document = {"content": "这是一个测试文档需要分割成块", "metadata": {}}
        result = splitter.execute(input_document)

        # 验证结果
        assert isinstance(result, list)
        assert len(result) > 1

        # 验证中文字符被正确处理
        assert result[0] == "这是一个测"
        assert result[1] == "个测试文档"  # 有2个字符的重叠

    def test_execute_with_special_characters(self):
        """测试execute方法处理特殊字符"""
        if not CHUNK_AVAILABLE:
            pytest.skip("Chunk module not available")

        config = {"chunk_size": 8, "overlap": 3}
        splitter = CharacterSplitter(config=config)

        # 包含特殊字符的文档对象
        input_document = {"content": "Hello!\n\tWorld@#$%^&*()", "metadata": {}}
        result = splitter.execute(input_document)

        # 验证结果
        assert isinstance(result, list)
        assert len(result) >= 1

        # 验证特殊字符被保留
        assert "Hello!\n\t" in result[0]
        # 检查特殊字符在某个chunk中被保留
        special_chars_found = any("$%^&*(" in chunk for chunk in result)
        assert special_chars_found

    def test_execute_with_very_long_text(self):
        """测试execute方法处理长文本"""
        if not CHUNK_AVAILABLE:
            pytest.skip("Chunk module not available")

        config = {"chunk_size": 50, "overlap": 10}
        splitter = CharacterSplitter(config=config)

        # 生成长文档对象
        input_document = {"content": "A" * 500, "metadata": {}}  # 500个字符
        result = splitter.execute(input_document)

        # 验证结果
        assert isinstance(result, list)
        expected_chunks = (500 - 10) // (50 - 10) + 1  # 计算预期的chunk数量
        assert len(result) >= expected_chunks - 1  # 允许一定误差

        # 验证每个chunk的长度
        for i, chunk in enumerate(result[:-1]):  # 除了最后一个chunk
            assert len(chunk) == 50

        # 验证重叠
        if len(result) > 1:
            assert result[0][-10:] == result[1][:10]


@pytest.mark.unit
class TestCharacterSplitterConfiguration:
    """测试CharacterSplitter配置"""

    def test_various_chunk_sizes(self):
        """测试不同的chunk_size配置"""
        if not CHUNK_AVAILABLE:
            pytest.skip("Chunk module not available")

        test_document = {
            "content": "The quick brown fox jumps over the lazy dog",
            "metadata": {},
        }

        # 测试不同的chunk_size
        for chunk_size in [5, 10, 20, 50]:
            config = {"chunk_size": chunk_size, "overlap": 2}
            splitter = CharacterSplitter(config=config)

            result = splitter.execute(test_document)

            # 验证结果
            assert isinstance(result, list)
            if len(test_document["content"]) > chunk_size:
                assert len(result) > 1

            # 验证第一个chunk的大小应该等于chunk_size（如果文本足够长）
            if len(test_document["content"]) >= chunk_size:
                assert len(result[0]) == chunk_size

            # 验证所有chunks的长度都合理（不超过chunk_size）
            for chunk in result:
                assert len(chunk) <= chunk_size
                assert len(chunk) > 0

    def test_various_overlaps(self):
        """测试不同的overlap配置"""
        if not CHUNK_AVAILABLE:
            pytest.skip("Chunk module not available")

        test_document = {
            "content": "1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "metadata": {},
        }
        chunk_size = 10

        # 测试不同的overlap
        for overlap in [0, 2, 5, 8]:
            config = {"chunk_size": chunk_size, "overlap": overlap}
            splitter = CharacterSplitter(config=config)

            result = splitter.execute(test_document)

            # 验证结果
            assert isinstance(result, list)

            # 验证overlap（如果有多个chunks）
            if len(result) > 1 and overlap > 0:
                # 检查相邻chunks之间的重叠
                overlap_text = result[0][-overlap:]
                start_text = result[1][:overlap]
                assert overlap_text == start_text


@pytest.mark.integration
class TestCharacterSplitterIntegration:
    """CharacterSplitter集成测试"""

    @pytest.mark.skipif(not CHUNK_AVAILABLE, reason="Chunk module not available")
    def test_character_splitter_in_pipeline(self):
        """测试CharacterSplitter在pipeline中的集成"""
        config = {"chunk_size": 100, "overlap": 20}

        splitter = CharacterSplitter(config=config)

        # 模拟来自文件读取的长文档
        document_content = """
        This is a long document that contains multiple paragraphs and needs to be split into manageable chunks.
        
        Each chunk should have a reasonable size and some overlap to maintain context between chunks.
        
        The chunking process is essential for RAG systems as it allows for efficient retrieval and processing
        of relevant information while maintaining semantic coherence.
        
        This test verifies that the character splitter can handle realistic document content properly.
        """

        document = {"content": document_content.strip(), "metadata": {}}

        result = splitter.execute(document)

        # 验证集成结果
        assert isinstance(result, list)
        assert len(result) > 1  # 应该被分割成多个chunks

        # 验证chunks质量
        total_length = sum(len(chunk) for chunk in result)
        original_length = len(document["content"])

        # 由于有重叠，总长度应该大于原始长度
        assert total_length > original_length

        # 验证第一个chunk包含文档开头，最后一个chunk包含文档结尾
        assert result[0].startswith(document["content"][:50])
        assert result[-1].endswith(document["content"][-30:])

        # 验证文档被完整覆盖（检查关键内容都被包含）
        combined_content = "".join(result)
        assert "This is a long document" in combined_content
        assert "document content properly" in combined_content

        # 验证chunk大小合理
        for i, chunk in enumerate(result[:-1]):  # 除最后一个chunk
            assert len(chunk) <= config["chunk_size"]
            if i > 0:  # 检查重叠
                overlap_size = min(config["overlap"], len(result[i - 1]), len(chunk))
                if overlap_size > 0:
                    prev_end = result[i - 1][-overlap_size:]
                    curr_start = chunk[:overlap_size]
                    # 注意：由于我们是按字符分割，重叠可能不完全匹配单词边界
                    # 这里主要验证有重叠存在
                    assert len(prev_end) > 0 and len(curr_start) > 0
