#!/usr/bin/env python3
"""LLM workflow DAG demo that wires SageDB retrieval into the SAGE pipeline.

@test:allow-demo
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.middleware.operators.rag import QAPromptor

# Ensure repository packages are importable when running the script directly
REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SRC_ROOTS = [
    REPO_ROOT / "packages" / "sage" / "src",
    REPO_ROOT / "packages" / "sage-common" / "src",
    REPO_ROOT / "packages" / "sage-kernel" / "src",
    REPO_ROOT / "packages" / "sage-libs" / "src",
    REPO_ROOT / "packages" / "sage-middleware" / "src",
    REPO_ROOT / "packages" / "sage-tools" / "src",
]
for path in PACKAGE_SRC_ROOTS:
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))


try:
    from sage.common.components.sage_embedding.embedding_model import EmbeddingModel
    from sage.middleware.components.sage_vdb.python.micro_service.sage_db_service import (
        SageDBService,
    )
except ImportError as exc:  # pragma: no cover - surface build guidance early
    if "_sage_vdb" in str(exc):
        raise SystemExit(
            "❌ SageDB native extension not found. Install it before running this demo:\n"
            "   sage extensions install sage_db  # add --force to rebuild"
        ) from exc
    raise

SERVICE_NAME = "vector_store_service"


@dataclass
class KnowledgeEntry:
    title: str
    text: str
    topic: str
    tags: list[str]


KNOWLEDGE_BASE: list[KnowledgeEntry] = [
    KnowledgeEntry(
        title="SAGE 推理管道总览",
        text=(
            "SAGE 的大模型推理 DAG 通过 LocalEnvironment 串联 Source、Map 与 Sink 节点，"
            "在 JobManager 中调度执行，并支持服务调用与反馈回路。"
        ),
        topic="architecture",
        tags=["dag", "runtime", "overview"],
    ),
    KnowledgeEntry(
        title="SageDB 与 RAG 集成",
        text=(
            "SageDB 可以作为 RAG 检索后端，结合嵌入模型将文档向量化后写入，"
            "在查询阶段通过服务调用提供 Top-K 相似片段。"
        ),
        topic="rag",
        tags=["sage_db", "retrieval", "integration"],
    ),
    KnowledgeEntry(
        title="服务编排节点",
        text=(
            "LocalEnvironment.register_service 会在 DAG 执行时自动注入可复用的服务实例，"
            "算子可通过 self.call_service['name'] 以同步方式访问数据库或缓存。"
        ),
        topic="runtime",
        tags=["service", "call_service", "localenvironment"],
    ),
    KnowledgeEntry(
        title="Prompt 构建阶段",
        text=(
            "QAPromptor 接收检索结果列表，拼装 system 与 user 消息，为 OpenAI 兼容生成器提供提示模板。"
        ),
        topic="prompt",
        tags=["promptor", "qa", "template"],
    ),
]

DEFAULT_QUERIES = [
    "SAGE 的 DAG 如何把 SageDB 检索串进推理流程?",
    "QAPromptor 在这个流程里起到什么作用?",
]


class BootstrappedSageDBService(SageDBService):
    """Wrapper service that loads embeddings at construction time."""

    def __init__(
        self,
        *,
        initial_vectors: Sequence[Sequence[float]] | np.ndarray | None = None,
        initial_metadata: Sequence[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if initial_vectors is not None:
            vectors = (
                np.asarray(initial_vectors, dtype=np.float32)
                if not isinstance(initial_vectors, np.ndarray)
                else initial_vectors.astype(np.float32, copy=False)
            )

            if vectors.size == 0:
                return

            if vectors.ndim != 2:
                raise ValueError("initial_vectors must be a 2D array-like of shape (N, dim)")

            expected_count = vectors.shape[0]
            if initial_metadata is None:
                metadata = [{} for _ in range(expected_count)]
            else:
                metadata = list(initial_metadata)
                if len(metadata) != expected_count:
                    raise ValueError("initial_metadata length must match number of initial_vectors")

            self.add_batch(vectors, metadata)
            # Build index once after ingestion to accelerate queries
            self._db.build_index()


class QuerySource(SourceFunction):
    def __init__(self, queries: Iterable[str], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._queries = list(queries)
        self._cursor = 0

    def execute(self) -> dict[str, str] | None:
        if self._cursor >= len(self._queries):
            return None
        question = self._queries[self._cursor]
        self._cursor += 1
        return {"query": question}


class SageDBRetrieverNode(MapFunction):
    def __init__(
        self,
        embedder_config: dict[str, Any],
        *,
        service_name: str = SERVICE_NAME,
        top_k: int = 3,
        service_timeout: float = 10.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.embedder = EmbeddingModel(**embedder_config)
        self.service_name = service_name
        self.top_k = top_k
        self.service_timeout = service_timeout

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        query = payload.get("query", "")
        if not query:
            return {**payload, "results": [], "retrieved_docs": []}

        query_vector = np.asarray(self.embedder.embed(query), dtype=np.float32)
        service = self.call_service(self.service_name)
        raw_results = service.search(query_vector, k=self.top_k, timeout=self.service_timeout)

        formatted_results: list[dict[str, Any]] = []
        corpus_snippets: list[str] = []
        references: list[dict[str, Any]] = []

        for item in raw_results:
            metadata = dict(item.get("metadata") or {})
            snippet = metadata.get("text", "")
            formatted_results.append(
                {
                    "text": snippet,
                    "score": item.get("score"),
                    "metadata": metadata,
                }
            )
            corpus_snippets.append(snippet)
            references.append(
                {
                    "title": metadata.get("title", "unknown"),
                    "score": float(item.get("score", 0.0)),
                    "tags": (metadata.get("tags", "").split(",") if metadata.get("tags") else []),
                }
            )

        enriched = dict(payload)
        enriched.update(
            {
                "results": formatted_results,
                "retrieved_docs": corpus_snippets,
                "references": references,
            }
        )
        return enriched


class MockLLMGenerator(MapFunction):
    """Minimal generator that emulates an LLM using retrieved passages."""

    def execute(self, data: list[Any]) -> dict[str, Any]:
        if not isinstance(data, list) or len(data) != 2:
            raise ValueError("Generator expects QAPromptor output: [original_payload, messages]")
        original, messages = data
        top_hit = None
        if isinstance(original, dict):
            hits = original.get("results", []) or []
            top_hit = hits[0] if hits else None
        answer: str
        if top_hit:
            title = top_hit["metadata"].get("title", "资料")
            answer = f"参考《{title}》中的要点：{top_hit['text']} —— 该内容经 SageDB 检索返回。"
        else:
            answer = "知识库没有检索到匹配内容，建议扩充 SageDB 语料。"

        enriched = dict(original)
        enriched["prompt_messages"] = messages
        enriched["answer"] = answer
        return enriched


class ConsoleReporter(MapFunction):
    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        query = payload.get("query", "<empty>")
        answer = payload.get("answer", "<no answer>")
        refs = payload.get("references", [])

        print("\n================ Pipeline Result ================")
        print(f"❓ Query : {query}")
        print(f"💡 Answer: {answer}")
        if refs:
            print("📚 References:")
            for idx, ref in enumerate(refs, start=1):
                title = ref.get("title")
                tags = ", ".join(ref.get("tags", []))
                score = ref.get("score")
                print(f"  {idx}. {title}  (score={score:.4f}, tags={tags})")
        else:
            print("📚 References: <none>")
        print("================================================\n")
        return payload


def build_embeddings(entries: Sequence[KnowledgeEntry], model: EmbeddingModel) -> np.ndarray:
    vectors = []
    for item in entries:
        vectors.append(model.embed(item.text))
    return np.asarray(vectors, dtype=np.float32)


def prepare_metadata(entries: Sequence[KnowledgeEntry]) -> list[dict[str, str]]:
    metadata: list[dict[str, str]] = []
    for item in entries:
        metadata.append(
            {
                "title": item.title,
                "text": item.text,
                "topic": item.topic,
                "tags": ",".join(item.tags),  # Serialize list to comma-separated string
            }
        )
    return metadata


def run_pipeline(top_k: int, queries: Sequence[str]) -> None:
    CustomLogger.disable_global_console_debug()

    embedder_config = {"method": "mockembedder", "fixed_dim": 128}
    embedder = EmbeddingModel(**embedder_config)

    vectors = build_embeddings(KNOWLEDGE_BASE, embedder)
    metadata = prepare_metadata(KNOWLEDGE_BASE)

    env = LocalEnvironment("sage_db_workflow_demo")
    env.register_service(
        SERVICE_NAME,
        BootstrappedSageDBService,
        dimension=embedder.get_dim(),
        index_type="AUTO",
        initial_vectors=vectors,
        initial_metadata=metadata,
    )

    (
        env.from_source(QuerySource, queries)
        .map(
            SageDBRetrieverNode,
            embedder_config,
            service_name=SERVICE_NAME,
            top_k=top_k,
        )
        .map(QAPromptor, {"use_short_answer": False})
        .map(MockLLMGenerator)
        .map(ConsoleReporter)
    )

    env.submit()

    # Wait for processing to complete
    import time

    time.sleep(5)  # Allow enough time for processing

    # Clean up environment
    env.stop()


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of neighbors to fetch from SageDB for each query.",
    )
    parser.add_argument(
        "--query",
        action="append",
        help="Override default demo queries (can be specified multiple times).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])
    queries = args.query if args.query else DEFAULT_QUERIES
    run_pipeline(args.top_k, queries)


if __name__ == "__main__":
    main()
