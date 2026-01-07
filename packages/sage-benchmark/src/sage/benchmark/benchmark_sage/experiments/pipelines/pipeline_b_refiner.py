"""
Pipeline B: Long Context Refiner (长文本精炼)
============================================

拓扑: Source → FlatMap(Chunking) → Filter(Relevance) → Map(Embedding) → Future(Summarize) → Aggregate → Sink

算子:
- Source: 加载长文档数据集 (LoCoMo)
- FlatMap (Chunking): 将长文档切分为多个块
- Filter (Relevance): 过滤低相关性的块
- Map (Embedding): 对每个块进行向量化
- Map (Summarize): 调用 LLM 对每个块生成摘要 (Future 语义)
- Sink (Aggregate): 合并所有块的摘要并输出

数据集: LoCoMo
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

# 禁用代理，确保内网服务可访问
os.environ.pop("http_proxy", None)
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("https_proxy", None)
os.environ.pop("HTTPS_PROXY", None)

import httpx

from sage.common.core import (
    FilterFunction,
    FlatMapFunction,
    MapFunction,
    SinkFunction,
    SourceFunction,
)
from sage.kernel.api import RemoteEnvironment

from .scheduler import HeadNodeScheduler


@dataclass
class RefinerConfig:
    """Refiner Pipeline 配置"""
    # 数据集
    num_samples: int = 50
    min_context_length: int = 8000

    # Chunking
    chunk_size: int = 2000
    chunk_overlap: int = 200

    # Filter
    relevance_threshold: float = 0.3

    # 模型
    embedding_model: str = "BAAI/bge-m3"
    llm_model: str = "Qwen/Qwen2.5-7B-Instruct"

    # 服务端点
    embedding_base_url: str = "http://localhost:8090/v1"
    llm_base_url: str = "http://localhost:8001/v1"

    # 运行时
    job_manager_host: str = "localhost"
    job_manager_port: int = 19001
    request_timeout: float = 120.0


@dataclass
class Chunk:
    """文档块"""
    doc_id: int
    chunk_index: int
    text: str
    query: str
    embedding: list[float] = field(default_factory=list)
    relevance_score: float = 0.0
    summary: str = ""


# ============================================================================
# Source: 数据集加载
# ============================================================================


class RefinerSourceFunction(SourceFunction):
    """Refiner Source: 从 LoCoMo 数据集加载长文档"""

    def __init__(
        self,
        num_samples: int = 50,
        min_context_length: int = 8000,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.num_samples = num_samples
        self.min_context_length = min_context_length
        self._data: list[dict] = []
        self._index = 0
        self._loaded = False

    def _load_data(self) -> None:
        """加载数据集"""
        if self._loaded:
            return

        from sage.data.sources.locomo.dataloader import LocomoDataLoader
        loader = LocomoDataLoader()
        raw_data = loader.load()

        # 过滤出长文档
        self._data = [
            d for d in raw_data
            if len(d.get("context", d.get("conversation", ""))) >= self.min_context_length
        ][: self.num_samples]

        self._loaded = True
        print(f"📂 Loaded {len(self._data)} long documents from LoCoMo")

    def execute(self, data: Any = None) -> Optional[dict]:
        """返回下一个长文档"""
        self._load_data()

        if self._index >= len(self._data):
            return None

        sample = self._data[self._index]
        self._index += 1

        return {
            "doc_id": self._index,
            "query": sample.get("question", sample.get("query", "")),
            "context": sample.get("context", sample.get("conversation", "")),
            "ground_truth": sample.get("answer", ""),
        }


# ============================================================================
# FlatMap (Chunking): 文档分块
# ============================================================================


class ChunkingFlatMapFunction(FlatMapFunction):
    """FlatMap (Chunking): 将长文档切分为多个块"""

    def __init__(
        self,
        chunk_size: int = 2000,
        chunk_overlap: int = 200,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def execute(self, data: dict) -> list[Chunk]:
        """执行分块"""
        doc_id = data["doc_id"]
        query = data["query"]
        context = data["context"]

        chunks = []
        step = self.chunk_size - self.chunk_overlap

        for i, start in enumerate(range(0, len(context), step)):
            end = min(start + self.chunk_size, len(context))
            chunk_text = context[start:end]

            chunks.append(Chunk(
                doc_id=doc_id,
                chunk_index=i,
                text=chunk_text,
                query=query,
            ))

        print(f"📄 Doc {doc_id}: Split into {len(chunks)} chunks")
        return chunks


# ============================================================================
# Filter (Relevance): 相关性过滤
# ============================================================================


class RelevanceScoreMapFunction(MapFunction):
    """Map (RelevanceScore): 计算块的相关性分数"""

    def execute(self, chunk: Chunk) -> Chunk:
        """计算相关性分数"""
        query_terms = set(chunk.query.lower().split())
        chunk_terms = set(chunk.text.lower().split())

        overlap = len(query_terms & chunk_terms)
        chunk.relevance_score = overlap / (len(query_terms) + 1)
        return chunk


class RelevanceFilterFunction(FilterFunction):
    """Filter (Relevance): 过滤低相关性的块

    注意: FilterFunction.execute() 应该返回 bool，表示数据是否通过过滤。
    数据本身不会被修改。如果需要在过滤前计算分数，应该先使用 MapFunction。
    """

    def __init__(self, relevance_threshold: float = 0.3, **kwargs):
        super().__init__(**kwargs)
        self.relevance_threshold = relevance_threshold

    def execute(self, chunk: Chunk) -> bool:
        """执行相关性过滤: 返回 True 表示通过, False 表示过滤掉"""
        return chunk.relevance_score >= self.relevance_threshold


# ============================================================================
# Map (Embedding): 块向量化
# ============================================================================


class ChunkEmbeddingMapFunction(MapFunction):
    """Map (Embedding): 对每个块进行向量化"""

    def __init__(
        self,
        embedding_base_url: str = "http://localhost:8090/v1",
        embedding_model: str = "BAAI/bge-m3",
        timeout: float = 60.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.embedding_base_url = embedding_base_url
        self.embedding_model = embedding_model
        self.timeout = timeout

    def execute(self, chunk: Chunk) -> Chunk:
        """执行 embedding"""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.embedding_base_url}/embeddings",
                json={"input": chunk.text[:1000], "model": self.embedding_model},
            )
            response.raise_for_status()
            result = response.json()

        chunk.embedding = result["data"][0]["embedding"]
        return chunk


# ============================================================================
# Map (Summarize): 摘要生成
# ============================================================================


class SummarizeMapFunction(MapFunction):
    """Map (Summarize): 调用 LLM 对每个块生成摘要"""

    def __init__(
        self,
        llm_base_url: str = "http://localhost:8001/v1",
        llm_model: str = "Qwen/Qwen2.5-7B-Instruct",
        timeout: float = 120.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.timeout = timeout

    def execute(self, chunk: Chunk) -> Chunk:
        """执行摘要生成"""
        prompt = f"""Summarize the following text in 2-3 sentences:

{chunk.text[:2000]}

Summary:"""

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.llm_base_url}/chat/completions",
                json={
                    "model": self.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.5,
                },
            )
            response.raise_for_status()
            result = response.json()

        chunk.summary = result["choices"][0]["message"]["content"]
        return chunk


# ============================================================================
# Sink (Aggregate): 合并摘要并输出
# ============================================================================


class RefinerSinkFunction(SinkFunction):
    """Refiner Sink: 合并摘要并输出结果

    注: 这里用 Sink 实现 Aggregate 语义，收集同一文档的所有块摘要后合并
    """

    def __init__(self, output_path: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.output_path = output_path
        self.doc_chunks: dict[int, list[Chunk]] = {}
        self.results: list[dict] = []

    def execute(self, chunk: Chunk) -> None:
        """收集块并合并摘要"""
        doc_id = chunk.doc_id

        if doc_id not in self.doc_chunks:
            self.doc_chunks[doc_id] = []

        self.doc_chunks[doc_id].append(chunk)

        # 检查是否所有块都已收集（简化版本：每次收到一个块就输出该块的摘要）
        print(f"✅ Doc {doc_id} Chunk {chunk.chunk_index}: {chunk.summary[:50]}...")

        if self.output_path:
            import json
            result = {
                "doc_id": doc_id,
                "chunk_index": chunk.chunk_index,
                "query": chunk.query,
                "summary": chunk.summary,
            }
            with open(self.output_path, "a") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")


# ============================================================================
# Refiner Pipeline 封装
# ============================================================================


class RefinerPipeline:
    """Refiner Pipeline 封装类"""

    def __init__(self, config: RefinerConfig):
        self.config = config
        self.env: Optional[RemoteEnvironment] = None

    def build(self) -> RemoteEnvironment:
        """构建 Refiner Pipeline"""
        scheduler = HeadNodeScheduler()

        self.env = RemoteEnvironment(
            "refiner_pipeline",
            host=self.config.job_manager_host,
            port=self.config.job_manager_port,
            scheduler=scheduler,
        )

        # 构建 Pipeline: Source → FlatMap → Map(Score) → Filter → Map → Map → Sink
        (
            self.env.from_source(
                RefinerSourceFunction,
                num_samples=self.config.num_samples,
                min_context_length=self.config.min_context_length,
            )
            .flatmap(
                ChunkingFlatMapFunction,
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
            )
            .map(RelevanceScoreMapFunction)
            .filter(
                RelevanceFilterFunction,
                relevance_threshold=self.config.relevance_threshold,
            )
            .map(
                ChunkEmbeddingMapFunction,
                embedding_base_url=self.config.embedding_base_url,
                embedding_model=self.config.embedding_model,
                timeout=self.config.request_timeout,
            )
            .map(
                SummarizeMapFunction,
                llm_base_url=self.config.llm_base_url,
                llm_model=self.config.llm_model,
                timeout=self.config.request_timeout,
            )
            .sink(RefinerSinkFunction)
        )

        return self.env

    def run(self) -> dict:
        """运行 Pipeline"""
        if self.env is None:
            self.build()

        start_time = time.time()
        try:
            self.env.submit()
            time.sleep(10)  # 长文档处理需要更多时间
        finally:
            self.env.close()

        duration = time.time() - start_time
        return {
            "pipeline": "B (Refiner)",
            "duration_seconds": duration,
            "config": {
                "num_samples": self.config.num_samples,
                "chunk_size": self.config.chunk_size,
            },
        }
