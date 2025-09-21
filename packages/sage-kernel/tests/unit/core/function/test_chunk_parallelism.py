import logging
import threading
import time
from typing import Any, Dict, List

import pytest
from sage.core.api.function.base_function import BaseFunction
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.source_function import SourceFunction
from sage.core.api.local_environment import LocalEnvironment


class DocumentSource(SourceFunction):
    """生成文档数据源"""

    def __init__(self, documents=None, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.documents = documents or [
            {
                "content": "This is a sample document with some text content.",
                "id": "doc1",
            },
            {
                "content": "Another document containing different information and data.",
                "id": "doc2",
            },
            {
                "content": "Large document with extensive content that needs chunking for processing.",
                "id": "doc3",
            },
            {"content": "Short text document.", "id": "doc4"},
            {
                "content": "Medium sized document with reasonable content length.",
                "id": "doc5",
            },
        ]

    def execute(self):
        if self.counter >= len(self.documents):
            return None

        data = self.documents[self.counter]
        self.counter += 1
        self.logger.info(f"DocumentSource generated: {data['id']}")
        return data


class CharacterSplitter(BaseFunction):
    """字符级文本分块算子 - 使用parallelism hints进行性能优化"""

    def __init__(self, chunk_size=50, overlap=10, **kwargs):
        super().__init__(**kwargs)
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.instance_id = id(self)
        self.thread_id = threading.get_ident()
        logging.info(
            f"🔧 CharacterSplitter instance {self.instance_id} created in thread {self.thread_id}"
        )

    def execute(self, document):
        """单文档处理逻辑，框架会自动并行化"""
        content = document.get("content", "")
        doc_id = document.get("id", "unknown")
        chunks = []

        current_thread = threading.get_ident()
        instance_id = id(self)

        logging.info(
            f"⚙️ CharacterSplitter[{instance_id}]: Processing {doc_id} (thread: {current_thread})"
        )

        # 模拟处理时间
        time.sleep(0.01)

        for i in range(0, len(content), self.chunk_size - self.overlap):
            chunk_text = content[i : i + self.chunk_size]
            if chunk_text.strip():  # 过滤空块
                chunks.append(
                    {
                        "content": chunk_text,
                        "doc_id": doc_id,
                        "start_idx": i,
                        "end_idx": min(i + self.chunk_size, len(content)),
                        "chunk_id": f"{doc_id}_chunk_{len(chunks)}",
                    }
                )

        logging.info(
            f"✅ CharacterSplitter[{instance_id}]: Generated {len(chunks)} chunks for {doc_id}"
        )
        return chunks


class ChunkCollector(SinkFunction):
    """收集分块结果的sink算子"""

    _collected_chunks: List[Dict] = []
    _lock = threading.Lock()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.instance_id = id(self)
        self.thread_id = threading.get_ident()
        logging.info(
            f"🔧 ChunkCollector instance {self.instance_id} created in thread {self.thread_id}"
        )

    def execute(self, chunks):
        current_thread = threading.get_ident()
        instance_id = id(self)

        with self._lock:
            if isinstance(chunks, list):
                self._collected_chunks.extend(chunks)
                logging.info(
                    f"🎯 ChunkCollector[{instance_id}]: Collected {len(chunks)} chunks (thread: {current_thread})"
                )
            else:
                self._collected_chunks.append(chunks)
                logging.info(
                    f"🎯 ChunkCollector[{instance_id}]: Collected 1 chunk (thread: {current_thread})"
                )

    @classmethod
    def get_collected_chunks(cls):
        """获取收集到的所有chunks"""
        return cls._collected_chunks.copy()

    @classmethod
    def clear_collected_chunks(cls):
        """清空收集到的chunks"""
        cls._collected_chunks.clear()


class TestChunkParallelism:
    """测试chunk算子的并行性优化"""

    def test_chunk_parallelism_hints_basic(self):
        """测试基本的chunk并行性hints功能"""
        logging.info("\n" + "=" * 70)
        logging.info("TEST: Basic Chunk Parallelism Hints")
        logging.info("=" * 70)

        # 清空之前的数据
        ChunkCollector.clear_collected_chunks()

        env = LocalEnvironment(name="chunk_parallelism_test")

        # 测试文档
        documents = [
            {"content": "This is document one with some content.", "id": "doc1"},
            {"content": "This is document two with different content.", "id": "doc2"},
            {"content": "This is document three with more content here.", "id": "doc3"},
        ]

        # 使用parallelism参数直接设置2个并行chunk实例
        result_stream = (
            env.from_collection(DocumentSource, documents)
            .map(CharacterSplitter, chunk_size=20, overlap=5, parallelism=2)
            .sink(ChunkCollector, parallelism=1)
        )

        # 执行
        env.submit()

        # 等待处理完成
        time.sleep(2)
        env.close()

        # 验证结果
        collected_chunks = ChunkCollector.get_collected_chunks()
        assert len(collected_chunks) > 0
        assert all(chunk.get("chunk_id") for chunk in collected_chunks)

        # 验证所有文档都被处理
        processed_doc_ids = set(chunk["doc_id"] for chunk in collected_chunks)
        expected_doc_ids = set(doc["id"] for doc in documents)
        assert processed_doc_ids == expected_doc_ids

        logging.info(
            f"✅ Collected {len(collected_chunks)} chunks from {len(processed_doc_ids)} documents"
        )

    def test_chunk_parallelism_hints_multiple_levels(self):
        """测试多级并行度设置"""
        logging.info("\n" + "=" * 70)
        logging.info("TEST: Multi-level Chunk Parallelism Hints")
        logging.info("=" * 70)

        # 清空之前的数据
        ChunkCollector.clear_collected_chunks()

        env = LocalEnvironment(name="multi_level_parallelism_test")

        # 更多测试文档
        documents = [
            {"content": "Document one content here.", "id": "doc1"},
            {"content": "Document two content here.", "id": "doc2"},
            {"content": "Document three content here.", "id": "doc3"},
            {"content": "Document four content here.", "id": "doc4"},
            {"content": "Document five content here.", "id": "doc5"},
        ]

        # 测试不同的并行度设置
        result_stream = (
            env.from_collection(DocumentSource, documents)
            .map(CharacterSplitter, chunk_size=15, overlap=3, parallelism=3)
            .sink(ChunkCollector, parallelism=2)
        )

        env.submit()

        # 验证结果
        collected_chunks = ChunkCollector.get_collected_chunks()
        assert len(collected_chunks) > 0

        # 验证chunk结构
        for chunk in collected_chunks:
            assert "content" in chunk
            assert "doc_id" in chunk
            assert "start_idx" in chunk
            assert "end_idx" in chunk
            assert "chunk_id" in chunk
            assert len(chunk["content"]) > 0

        logging.info(
            f"✅ Multi-level parallelism test completed with {len(collected_chunks)} chunks"
        )

    def test_chunk_parallelism_hints_large_documents(self):
        """测试大文档的chunk并行处理"""
        logging.info("\n" + "=" * 70)
        logging.info("TEST: Large Document Chunk Parallelism")
        logging.info("=" * 70)

        # 清空之前的数据
        ChunkCollector.clear_collected_chunks()

        env = LocalEnvironment(name="large_doc_test")

        # 模拟大文档
        large_content = "This is a large document with extensive content. " * 50
        documents = [
            {"content": large_content, "id": "large_doc1"},
            {"content": large_content, "id": "large_doc2"},
        ]

        # 使用更高的并行度处理大文档
        result_stream = (
            env.from_collection(DocumentSource, documents)
            .map(CharacterSplitter, chunk_size=100, overlap=20, parallelism=4)
            .sink(ChunkCollector, parallelism=1)
        )

        env.submit()

        # 验证大文档被正确分块
        collected_chunks = ChunkCollector.get_collected_chunks()
        assert len(collected_chunks) > 0

        # 检查大文档产生了多个chunk
        large_doc_chunks = [c for c in collected_chunks if c["doc_id"] == "large_doc1"]
        assert len(large_doc_chunks) > 1  # 大文档应该被分成多个chunk

        logging.info(f"✅ Large document test: {len(large_doc_chunks)} chunks from large_doc1")

    def test_chunk_parallelism_hints_vs_manual_parallelization(self):
        """对比parallelism hints与手动并行化的区别"""
        logging.info("\n" + "=" * 70)
        logging.info("TEST: Parallelism Hints vs Manual Parallelization")
        logging.info("=" * 70)

        # 清空之前的数据
        ChunkCollector.clear_collected_chunks()

        # 使用parallelism hints的方式
        env1 = LocalEnvironment(name="hints_test")
        documents = [
            {"content": "Test document one.", "id": "test1"},
            {"content": "Test document two.", "id": "test2"},
        ]

        result1 = (
            env1.from_collection(DocumentSource, documents)
            .map(CharacterSplitter, chunk_size=10, overlap=2, parallelism=2)
            .sink(ChunkCollector)
        )
        env1.submit()

        # 验证hints方式工作正常
        collected_chunks = ChunkCollector.get_collected_chunks()
        assert len(collected_chunks) > 0

        logging.info("✅ Parallelism hints approach works correctly")
        logging.info("💡 Key advantage: Framework manages parallelism, code stays simple")
