import threading
import time
from typing import Any, Dict, List

import pytest
from sage.core.api.function.base_function import BaseFunction
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.source_function import SourceFunction
from sage.core.api.local_environment import LocalEnvironment

# 添加全局打印锁来防止并发输出混乱
_print_lock = threading.Lock()


def thread_safe_print(*args, **kwargs):
    """线程安全的打印函数"""
    with _print_lock:
        print(*args, **kwargs)


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
        thread_safe_print(
            f":gear: CharacterSplitter instance {self.instance_id} created in thread {self.thread_id}"
        )

    def execute(self, document):
        """单文档处理逻辑，框架会自动并行化"""
        content = document.get("content", "")
        doc_id = document.get("id", "unknown")
        chunks = []

        current_thread = threading.get_ident()
        instance_id = id(self)

        thread_safe_print(
            f":gear: CharacterSplitter[{instance_id}]: Processing {doc_id} (thread: {current_thread})"
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

        thread_safe_print(
            f":white_check_mark: CharacterSplitter[{instance_id}]: Generated {len(chunks)} chunks for {doc_id}"
        )
        return chunks


class SlowCharacterSplitter(CharacterSplitter):
    """延长处理时间的CharacterSplitter，用于模拟在途数据"""

    def execute(self, document):
        time.sleep(0.05)
        return super().execute(document)


class ChunkCollector(SinkFunction):
    """收集分块结果的sink算子"""

    # 类级别的结果收集 - 只用于测试目的
    _collected_chunks: List[Dict] = None
    _lock = threading.Lock()

    @classmethod
    def _ensure_chunks_list(cls):
        """确保chunks列表被初始化"""
        if cls._collected_chunks is None:
            cls._collected_chunks = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.instance_id = id(self)
        self.thread_id = threading.get_ident()
        thread_safe_print(
            f":gear: ChunkCollector instance {self.instance_id} created in thread {self.thread_id}"
        )

    def execute(self, chunks):
        current_thread = threading.get_ident()
        instance_id = id(self)

        with self._lock:
            self._ensure_chunks_list()

            if chunks is None:  # Stop signal
                return

            if isinstance(chunks, list):
                self._collected_chunks.extend(chunks)
                thread_safe_print(
                    f":dart: ChunkCollector[{instance_id}]: Collected {len(chunks)} chunks (thread: {current_thread})"
                )
            else:
                self._collected_chunks.append(chunks)
                thread_safe_print(
                    f":dart: ChunkCollector[{instance_id}]: Collected 1 chunk (thread: {current_thread})"
                )

    def close(self):
        """SinkFunction的关闭方法，在停止信号时被调用"""
        current_thread = threading.get_ident()
        instance_id = id(self)
        thread_safe_print(
            f":stop_sign: ChunkCollector[{instance_id}]: Received close signal (thread: {current_thread})"
        )

    @classmethod
    def get_collected_chunks(cls):
        """获取收集到的所有chunks"""
        with cls._lock:
            cls._ensure_chunks_list()
            return cls._collected_chunks.copy()

    @classmethod
    def clear_collected_chunks(cls):
        """清空收集到的chunks"""
        with cls._lock:
            cls._collected_chunks = []


class LaggyChunkCollector(ChunkCollector):
    """处理延迟的Sink算子，模拟慢速消费者"""

    def execute(self, chunks):
        time.sleep(0.05)
        super().execute(chunks)


class TestChunkParallelism:
    """测试chunk算子的并行性优化"""

    def test_chunk_parallelism_hints_basic(self):
        """测试基本的chunk并行性hints功能"""
        print("\n" + "=" * 70)
        print("TEST: Basic Chunk Parallelism Hints")
        print("=" * 70)

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

        # 使用autostop=True让SAGE自动检测批处理完成
        env.submit(autostop=True)

        # 获取收集的结果
        collected_chunks = ChunkCollector.get_collected_chunks()

        # 验证结果
        assert len(collected_chunks) > 0
        assert all(chunk.get("chunk_id") for chunk in collected_chunks)

        # 验证所有文档都被处理
        processed_doc_ids = set(chunk["doc_id"] for chunk in collected_chunks)
        expected_doc_ids = set(doc["id"] for doc in documents)
        assert processed_doc_ids == expected_doc_ids

        print(
            f"✅ Collected {len(collected_chunks)} chunks from {len(processed_doc_ids)} documents"
        )

    def test_chunk_parallelism_hints_multiple_levels(self):
        """测试多级并行度设置"""
        print("\n" + "=" * 70)
        print("TEST: Multi-level Chunk Parallelism Hints")
        print("=" * 70)

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

        # 使用autostop=True让SAGE自动检测批处理完成
        env.submit(autostop=True)

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

        print(
            f"✅ Multi-level parallelism test completed with {len(collected_chunks)} chunks"
        )

    def test_chunk_parallelism_hints_large_documents(self):
        """测试大文档的chunk并行处理"""
        print("\n" + "=" * 70)
        print("TEST: Large Document Chunk Parallelism")
        print("=" * 70)

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

        # 使用autostop=True让SAGE自动检测批处理完成
        env.submit(autostop=True)

        # 验证大文档被正确分块
        collected_chunks = ChunkCollector.get_collected_chunks()
        assert len(collected_chunks) > 0

        # 检查大文档产生了多个chunk
        large_doc_chunks = [c for c in collected_chunks if c["doc_id"] == "large_doc1"]
        assert len(large_doc_chunks) > 1  # 大文档应该被分成多个chunk

        print(f"✅ Large document test: {len(large_doc_chunks)} chunks from large_doc1")

    def test_mixed_document_chunk_parallelism(self):
        """测试混合文档（普通文档+大文档）的并行处理场景"""
        print("\n" + "=" * 70)
        print("TEST: Mixed Document Chunk Parallelism")
        print("=" * 70)

        # 清空之前的数据
        ChunkCollector.clear_collected_chunks()

        env = LocalEnvironment(name="mixed_doc_test")

        # 创建完整的测试文档集合，包括普通文档和大文档
        large_content = "This is a large document with extensive content. " * 50
        documents = [
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
            {"content": large_content, "id": "large_doc1"},
            {"content": large_content, "id": "large_doc2"},
        ]

        # 使用高并行度处理混合文档类型
        result_stream = (
            env.from_collection(DocumentSource, documents)
            .map(CharacterSplitter, chunk_size=50, overlap=10, parallelism=4)
            .sink(ChunkCollector, parallelism=2)
        )

        # 使用autostop=True让SAGE自动检测批处理完成
        env.submit(autostop=True)

        # 验证处理结果
        collected_chunks = ChunkCollector.get_collected_chunks()
        assert len(collected_chunks) > 0

        # 验证所有文档都被处理
        processed_doc_ids = set(chunk["doc_id"] for chunk in collected_chunks)
        expected_doc_ids = {"doc2", "doc3", "doc4", "doc5", "large_doc1", "large_doc2"}

        assert (
            processed_doc_ids == expected_doc_ids
        ), f"Expected documents {expected_doc_ids}, got {processed_doc_ids}"

        # 验证大文档产生了足够的chunks（如果被处理的话）
        large_doc1_chunks = [c for c in collected_chunks if c["doc_id"] == "large_doc1"]
        large_doc2_chunks = [c for c in collected_chunks if c["doc_id"] == "large_doc2"]

        # 大文档应该产生大量chunks
        assert (
            len(large_doc1_chunks) > 30
        ), f"large_doc1 should generate many chunks, got {len(large_doc1_chunks)}"
        assert (
            len(large_doc2_chunks) > 30
        ), f"large_doc2 should generate many chunks, got {len(large_doc2_chunks)}"

        print(f"✅ Mixed document test completed: {len(collected_chunks)} total chunks")
        print(f"   - large_doc1: {len(large_doc1_chunks)} chunks")
        print(f"   - large_doc2: {len(large_doc2_chunks)} chunks")

    def test_chunk_parallelism_hints_vs_manual_parallelization(self):
        """对比parallelism hints与手动并行化的区别"""
        print("\n" + "=" * 70)
        print("TEST: Parallelism Hints vs Manual Parallelization")
        print("=" * 70)

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
        # 使用autostop=True让SAGE自动检测批处理完成
        env1.submit(autostop=True)

        # 验证hints方式工作正常
        collected_chunks = ChunkCollector.get_collected_chunks()
        assert len(collected_chunks) > 0

        print("✅ Parallelism hints approach works correctly")
        print("💡 Key advantage: Framework manages parallelism, code stays simple")

    def test_autostop_graceful_shutdown_drains_sink(self):
        """验证autostop在存在在途数据时不会丢失数据"""
        print("\n" + "=" * 70)
        print("TEST: Autostop Graceful Shutdown Drains Sink")
        print("=" * 70)

        ChunkCollector.clear_collected_chunks()
        LaggyChunkCollector.clear_collected_chunks()

        env = LocalEnvironment(name="graceful_shutdown_drain_test")

        large_content = (
            "Synthetic large document content to simulate heavy processing. " * 60
        )
        documents = [
            {"content": large_content, "id": "slow_doc1"},
            {"content": large_content, "id": "slow_doc2"},
        ]

        result_stream = (
            env.from_collection(DocumentSource, documents)
            .map(SlowCharacterSplitter, chunk_size=60, overlap=15, parallelism=2)
            .sink(LaggyChunkCollector, parallelism=1)
        )

        env.submit(autostop=True)

        collected_chunks = LaggyChunkCollector.get_collected_chunks()
        assert len(collected_chunks) > 0

        expected_doc_ids = {doc["id"] for doc in documents}
        processed_doc_ids = {chunk["doc_id"] for chunk in collected_chunks}

        assert (
            processed_doc_ids == expected_doc_ids
        ), f"Expected documents {expected_doc_ids}, got {processed_doc_ids}"

        for doc_id in expected_doc_ids:
            doc_chunks = [c for c in collected_chunks if c["doc_id"] == doc_id]
            assert (
                len(doc_chunks) > 20
            ), f"Document {doc_id} should generate many chunks, got {len(doc_chunks)}"

        print(
            f"✅ Graceful shutdown drained sink with {len(collected_chunks)} total chunks across {len(expected_doc_ids)} documents"
        )
