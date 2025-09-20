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
            {"content": "This is a sample document with some text content.", "id": "doc1"},
            {"content": "Another document containing different information and data.", "id": "doc2"},
            {"content": "Large document with extensive content that needs chunking for processing.", "id": "doc3"},
            {"content": "Short text document.", "id": "doc4"},
            {"content": "Medium sized document with reasonable content length.", "id": "doc5"},
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
        print(f"🔧 CharacterSplitter instance {self.instance_id} created in thread {self.thread_id}")

    def execute(self, document):
        """单文档处理逻辑，框架会自动并行化"""
        content = document.get("content", "")
        doc_id = document.get("id", "unknown")
        chunks = []

        current_thread = threading.get_ident()
        instance_id = id(self)

        print(f"⚙️ CharacterSplitter[{instance_id}]: Processing {doc_id} (thread: {current_thread})")

        # 模拟处理时间
        time.sleep(0.01)

        for i in range(0, len(content), self.chunk_size - self.overlap):
            chunk_text = content[i:i + self.chunk_size]
            if chunk_text.strip():  # 过滤空块
                chunks.append({
                    "content": chunk_text,
                    "doc_id": doc_id,
                    "start_idx": i,
                    "end_idx": min(i + self.chunk_size, len(content)),
                    "chunk_id": f"{doc_id}_chunk_{len(chunks)}"
                })

        print(f"✅ CharacterSplitter[{instance_id}]: Generated {len(chunks)} chunks for {doc_id}")
        return chunks


class ChunkCollector(SinkFunction):
    """收集分块结果的sink算子"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.collected_chunks = []
        self.instance_id = id(self)
        self.thread_id = threading.get_ident()
        print(f"🔧 ChunkCollector instance {self.instance_id} created in thread {self.thread_id}")

    def execute(self, chunks):
        current_thread = threading.get_ident()
        instance_id = id(self)

        if isinstance(chunks, list):
            self.collected_chunks.extend(chunks)
            print(f"🎯 ChunkCollector[{instance_id}]: Collected {len(chunks)} chunks (thread: {current_thread})")
        else:
            self.collected_chunks.append(chunks)
            print(f"🎯 ChunkCollector[{instance_id}]: Collected 1 chunk (thread: {current_thread})")


class TestChunkParallelism:
    """测试chunk算子的并行性优化"""

    def test_chunk_parallelism_hints_basic(self):
        """测试基本的chunk并行性hints功能"""
        print("\n" + "=" * 70)
        print("TEST: Basic Chunk Parallelism Hints")
        print("=" * 70)

        env = LocalEnvironment(name="chunk_parallelism_test")

        # 测试文档
        documents = [
            {"content": "This is document one with some content.", "id": "doc1"},
            {"content": "This is document two with different content.", "id": "doc2"},
            {"content": "This is document three with more content here.", "id": "doc3"},
        ]

        # 使用parallelism hints设置2个并行chunk实例
        collector = ChunkCollector()
        result_stream = (
            env.from_collection(DocumentSource, documents)
            .set_parallelism(2)  # 设置2个并行CharacterSplitter实例
            .map(CharacterSplitter, chunk_size=20, overlap=5)
            .set_parallelism(1)  # sink使用1个实例
            .sink(collector)
        )

        # 执行
        env.execute()

        # 验证结果
        assert len(collector.collected_chunks) > 0
        assert all(chunk.get("chunk_id") for chunk in collector.collected_chunks)

        # 验证所有文档都被处理
        processed_doc_ids = set(chunk["doc_id"] for chunk in collector.collected_chunks)
        expected_doc_ids = set(doc["id"] for doc in documents)
        assert processed_doc_ids == expected_doc_ids

        print(f"✅ Collected {len(collector.collected_chunks)} chunks from {len(processed_doc_ids)} documents")

    def test_chunk_parallelism_hints_multiple_levels(self):
        """测试多级并行度设置"""
        print("\n" + "=" * 70)
        print("TEST: Multi-level Chunk Parallelism Hints")
        print("=" * 70)

        env = LocalEnvironment(name="multi_level_parallelism_test")

        # 更多测试文档
        documents = [
            {"content": "Document one content here.", "id": "doc1"},
            {"content": "Document two content here.", "id": "doc2"},
            {"content": "Document three content here.", "id": "doc3"},
            {"content": "Document four content here.", "id": "doc4"},
            {"content": "Document five content here.", "id": "doc5"},
        ]

        collector = ChunkCollector()

        # 测试不同的并行度设置
        result_stream = (
            env.from_collection(DocumentSource, documents)
            .set_parallelism(3)  # 3个并行source->splitter
            .map(CharacterSplitter, chunk_size=15, overlap=3)
            .set_parallelism(2)  # 2个并行splitter->sink
            .sink(collector)
        )

        env.execute()

        # 验证结果
        assert len(collector.collected_chunks) > 0

        # 验证chunk结构
        for chunk in collector.collected_chunks:
            assert "content" in chunk
            assert "doc_id" in chunk
            assert "start_idx" in chunk
            assert "end_idx" in chunk
            assert "chunk_id" in chunk
            assert len(chunk["content"]) > 0

        print(f"✅ Multi-level parallelism test completed with {len(collector.collected_chunks)} chunks")

    def test_chunk_parallelism_hints_large_documents(self):
        """测试大文档的chunk并行处理"""
        print("\n" + "=" * 70)
        print("TEST: Large Document Chunk Parallelism")
        print("=" * 70)

        env = LocalEnvironment(name="large_doc_test")

        # 模拟大文档
        large_content = "This is a large document with extensive content. " * 50
        documents = [
            {"content": large_content, "id": "large_doc1"},
            {"content": large_content, "id": "large_doc2"},
        ]

        collector = ChunkCollector()

        # 使用更高的并行度处理大文档
        result_stream = (
            env.from_collection(DocumentSource, documents)
            .set_parallelism(4)  # 4个并行实例处理大文档
            .map(CharacterSplitter, chunk_size=100, overlap=20)
            .set_parallelism(1)
            .sink(collector)
        )

        env.execute()

        # 验证大文档被正确分块
        assert len(collector.collected_chunks) > 0

        # 检查大文档产生了多个chunk
        large_doc_chunks = [c for c in collector.collected_chunks if c["doc_id"] == "large_doc1"]
        assert len(large_doc_chunks) > 1  # 大文档应该被分成多个chunk

        print(f"✅ Large document test: {len(large_doc_chunks)} chunks from large_doc1")

    def test_chunk_parallelism_hints_vs_manual_parallelization(self):
        """对比parallelism hints与手动并行化的区别"""
        print("\n" + "=" * 70)
        print("TEST: Parallelism Hints vs Manual Parallelization")
        print("=" * 70)

        # 使用parallelism hints的方式
        env1 = LocalEnvironment(name="hints_test")
        documents = [
            {"content": "Test document one.", "id": "test1"},
            {"content": "Test document two.", "id": "test2"},
        ]

        collector1 = ChunkCollector()
        result1 = (
            env1.from_collection(DocumentSource, documents)
            .set_parallelism(2)  # 声明式并行
            .map(CharacterSplitter, chunk_size=10, overlap=2)
            .sink(collector1)
        )
        env1.execute()

        # 手动并行化（错误方式 - 仅用于对比说明）
        # 注意：这里不实现手动并行化，因为SAGE的设计理念是避免这种做法

        # 验证hints方式工作正常
        assert len(collector1.collected_chunks) > 0

        print("✅ Parallelism hints approach works correctly")
        print("💡 Key advantage: Framework manages parallelism, code stays simple")