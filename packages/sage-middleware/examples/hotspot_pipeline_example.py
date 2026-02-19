from __future__ import annotations

import argparse
import time
from typing import Any

import numpy as np

from sage.common.components.sage_embedding.factory import EmbeddingFactory
from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.kernel.api import LocalEnvironment
from sage.middleware.components.sage_flow.hotspot import SageFlowHotspotPairCoMap
from sage.middleware.components.sage_flow.hotspot_flatten import HotspotPairListFlatten
from sage.middleware.components.sage_flow.vllm_embedding import VLLMEmbeddingMap


class ExplainableMockEmbeddingMap(MapFunction):
    """不依赖外部服务的 mock embedding。

    目标：
    - 同主题/同实体的新闻标题生成相近向量，确保 join 能产出热点 pair。
    - 仍然是确定性的（同一 title 每次得到相同向量），便于复现实验。
    """

    def __init__(
        self,
        dim: int = 128,
        text_field: str = "title",
        normalize: bool = True,
    ):
        super().__init__()
        self.dim = dim
        self.text_field = text_field
        self.normalize = normalize

        # 主题基向量：让同主题文本更接近
        self._topic_vecs = {
            "nvidia": self._base_vec("topic:nvidia"),
            "apple": self._base_vec("topic:apple"),
            "google": self._base_vec("topic:google"),
            "microsoft": self._base_vec("topic:microsoft"),
            "nba": self._base_vec("topic:nba"),
            "world cup": self._base_vec("topic:worldcup"),
            "fifa": self._base_vec("topic:fifa"),
        }

    def _base_vec(self, seed_text: str) -> np.ndarray:
        seed = hash(seed_text) % (2**32)
        rng = np.random.default_rng(seed)
        v = rng.standard_normal(self.dim).astype(np.float32)
        v = v / (np.linalg.norm(v) + 1e-8)
        return v

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        text = str(data.get(self.text_field, ""))
        if not text:
            return {**data, "embedding": None}

        lower = text.lower()
        topic = None
        for k in self._topic_vecs.keys():
            if k in lower:
                topic = k
                break

        base = self._topic_vecs.get(topic) if topic else self._base_vec("topic:other")
        tweak = self._base_vec(f"title:{lower}") * 0.12
        emb = base + tweak
        if self.normalize:
            emb = emb / (np.linalg.norm(emb) + 1e-8)
        return {**data, "embedding": emb}


class OpenAIEmbeddingMap(MapFunction):
    """使用 SAGE 内置 EmbeddingFactory(openai) 调用 OpenAI-compatible embeddings 服务。

    注意：外部服务不可用时会导致 pipeline 阻塞，所以这里加了超时与异常日志。
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "dummy",
        text_field: str = "title",
        timeout_s: float = 20.0,
    ):
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.text_field = text_field
        self.timeout_s = timeout_s

        try:
            self._embedder = EmbeddingFactory.create(
                "openai",
                base_url=self.base_url,
                model=self.model,
                api_key=self.api_key,
                timeout=self.timeout_s,
            )
        except TypeError:
            self._embedder = EmbeddingFactory.create(
                "openai",
                base_url=self.base_url,
                model=self.model,
                api_key=self.api_key,
            )

        self.dim = int(self._embedder.get_dim())

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        text = str(data.get(self.text_field, ""))
        if not text:
            return {**data, "embedding": None}

        try:
            vec = self._embedder.embed(text)
            emb = np.array(vec, dtype=np.float32)
            emb = emb / (np.linalg.norm(emb) + 1e-8)
            return {**data, "embedding": emb}
        except Exception as e:
            try:
                self.logger.error(
                    f"Embedding request failed (base_url={self.base_url}, model={self.model}, timeout_s={self.timeout_s}): {e}",
                    exc_info=True,
                )
            except Exception:
                pass
            return {**data, "embedding": None, "embedding_error": str(e)}


class HotspotCollectorSink(SinkFunction):
    """收集所有热点对结果，用于后续排序展示。"""

    def __init__(self, results_list: list):
        super().__init__()
        self.results = results_list

    def execute(self, data: dict[str, Any]):
        if data and "left" in data and "right" in data:
            self.results.append(data)


def main():
    parser = argparse.ArgumentParser(
        description="Hotspot news aggregation using SAGE runtime + SageFlow join."
    )
    parser.add_argument(
        "--embedding-mode",
        choices=["mock", "remote", "vllm"],
        default="mock",
        help="Embedding mode: mock(no deps), remote(OpenAI-compatible API), vllm(in-process vLLM).",
    )

    # mock
    parser.add_argument("--mock-dim", type=int, default=128, help="Embedding dim for mock mode.")

    # remote
    parser.add_argument(
        "--embedding-base-url",
        default="http://11.11.11.7:8090/v1",
        help="OpenAI-compatible embedding base_url (remote mode).",
    )
    parser.add_argument(
        "--embedding-model",
        default="BAAI/bge-large-en-v1.5",
        help="Embedding model name (remote mode).",
    )
    parser.add_argument(
        "--embedding-timeout-s",
        type=float,
        default=20.0,
        help="Timeout seconds for remote embedding request.",
    )

    # vllm
    parser.add_argument(
        "--vllm-model",
        default="Qwen/Qwen2-0.5B-Instruct",
        help="vLLM model id (vllm mode).",
    )

    # join
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.80,
        help="SageFlow join similarity threshold.",
    )
    parser.add_argument(
        "--window-size-ms",
        type=int,
        default=10000,
        help="SageFlow join window size in milliseconds (default: 10000 = 10s).",
    )
    parser.add_argument("--top-k", type=int, default=10, help="Top-K hotspot pairs to print.")

    args = parser.parse_args()

    print("=" * 70)
    print("SAGE x SageFlow: Hotspot News Aggregation")
    print("=" * 70)
    print(f"Embedding mode: {args.embedding_mode}")

    env = LocalEnvironment("hotspot-detection-pipeline")

    docs_a = [
        {"id": "A01", "platform": "Platform-A", "title": "Nvidia's new Blackwell GPUs are here"},
        {"id": "A02", "platform": "Platform-A", "title": "Apple unveils M4 chip for next-gen Macs"},
        {
            "id": "A03",
            "platform": "Platform-A",
            "title": "Lakers win NBA championship in a dramatic final",
        },
        {"id": "A04", "platform": "Platform-A", "title": "Google I/O 2025 focuses on Gemini AI"},
        {
            "id": "A05",
            "platform": "Platform-A",
            "title": "FIFA World Cup 2026 host cities announced",
        },
        {"id": "A06", "platform": "Platform-A", "title": "Microsoft launches new Surface Pro 11"},
    ]

    docs_b = [
        {
            "id": "B01",
            "platform": "Platform-B",
            "title": "Nvidia announces the Blackwell GPU architecture",
        },
        {
            "id": "B02",
            "platform": "Platform-B",
            "title": "Next generation of Macs to be powered by Apple's M4",
        },
        {
            "id": "B03",
            "platform": "Platform-B",
            "title": "Dramatic NBA finals see Lakers take the crown",
        },
        {
            "id": "B04",
            "platform": "Platform-B",
            "title": "Gemini AI is the star of Google I/O 2025",
        },
        {
            "id": "B05",
            "platform": "Platform-B",
            "title": "FIFA reveals host cities for World Cup 2026",
        },
        {
            "id": "B06",
            "platform": "Platform-B",
            "title": "First look at the new Surface Pro from Microsoft",
        },
        {"id": "B07", "platform": "Platform-B", "title": "Boston Celtics trade update"},
    ]

    if args.embedding_mode == "mock":
        embed_map = ExplainableMockEmbeddingMap(dim=args.mock_dim, text_field="title")
        dim = embed_map.dim
        print(f"Mock embedding dim: {dim}")

    elif args.embedding_mode == "remote":
        embed_map = OpenAIEmbeddingMap(
            base_url=args.embedding_base_url,
            model=args.embedding_model,
            api_key="dummy",
            text_field="title",
            timeout_s=args.embedding_timeout_s,
        )
        dim = embed_map.dim
        print(f"Embedding base_url: {args.embedding_base_url}")
        print(f"Embedding model: {args.embedding_model}")
        print(f"Embedding dim: {dim}")
        print(f"Embedding timeout: {args.embedding_timeout_s}s")

    else:
        vllm_map = VLLMEmbeddingMap(
            model=args.vllm_model,
            text_field="title",
            normalize=True,
            enforce_eager=True,
        )
        dim = vllm_map.get_dim()
        if dim <= 0:
            raise RuntimeError("Failed to infer embedding dim from vLLM model")
        print(f"vLLM model: {args.vllm_model}")
        print(f"Embedding dim: {dim}")

    print(f"SageFlow similarity_threshold: {args.similarity_threshold}")
    print(f"SageFlow window_size_ms: {args.window_size_ms}")

    all_hotspots: list[dict[str, Any]] = []

    # 创建流并直接添加所有数据
    stream_a = env.from_batch(docs_a)
    stream_b = env.from_batch(docs_b)

    # 应用embedding转换
    if args.embedding_mode == "mock":
        stream_a = stream_a.map(lambda x: embed_map.execute(x))
        stream_b = stream_b.map(lambda x: embed_map.execute(x))
    elif args.embedding_mode == "remote":
        stream_a = stream_a.map(lambda x: embed_map.execute(x))
        stream_b = stream_b.map(lambda x: embed_map.execute(x))
    else:
        stream_a = stream_a.map(lambda x: vllm_map.execute(x))
        stream_b = stream_b.map(lambda x: vllm_map.execute(x))

    # 构建处理流水线
    (
        stream_a.connect(stream_b)
        .comap(
            SageFlowHotspotPairCoMap,
            dim=dim,
            similarity_threshold=args.similarity_threshold,
            window_size_ms=args.window_size_ms,
        )
        .flatmap(HotspotPairListFlatten)
        .sink(HotspotCollectorSink, results_list=all_hotspots)
    )

    print("Submitting pipeline...")
    start_time = time.time()
    env.submit(autostop=True)
    print(f"Pipeline finished in {time.time() - start_time:.2f}s")

    print(f"\nTop-{args.top_k} hotspot pairs:")
    print("-" * 70)

    if not all_hotspots:
        print("No hotspot pairs found. Try lowering similarity_threshold.")
        return

    sorted_hotspots = sorted(all_hotspots, key=lambda p: p.get("similarity", 0.0), reverse=True)

    for i, pair in enumerate(sorted_hotspots[: args.top_k]):
        left = pair.get("left", {})
        right = pair.get("right", {})
        sim = pair.get("similarity", 0.0)

        print(f"#{i + 1:02d} | sim={sim:.4f}")
        print(f"  -> [{left.get('platform')}] {left.get('title')}")
        print(f"  -> [{right.get('platform')}] {right.get('title')}")
        print("-" * 70)


if __name__ == "__main__":
    main()
