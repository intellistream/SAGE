from __future__ import annotations

import time
from typing import Any

import numpy as np

from sage.common.components.sage_embedding.factory import EmbeddingFactory
from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.kernel.api import LocalEnvironment
from sage.middleware.components.sage_flow.hotspot import SageFlowHotspotPairCoMap
from sage.middleware.components.sage_flow.hotspot_flatten import HotspotPairListFlatten


class OpenAIEmbeddingMap(MapFunction):
    """使用 SAGE 内置 EmbeddingFactory(openai) 调用 OpenAI-compatible embeddings 服务。"""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "dummy",
        text_field: str = "title",
    ):
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.text_field = text_field

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

        vec = self._embedder.embed(text)
        emb = np.array(vec, dtype=np.float32)
        # 归一化（避免不同服务默认是否 normalize 不一致导致阈值难调）
        emb = emb / (np.linalg.norm(emb) + 1e-8)

        return {**data, "embedding": emb}


class HotspotCollectorSink(SinkFunction):
    """收集所有热点对结果，用于后续排序展示。"""

    def __init__(self, results_list: list):
        super().__init__()
        self.results = results_list

    def execute(self, data: dict[str, Any]):
        if data and "left" in data and "right" in data:
            self.results.append(data)


def main():
    print("=" * 70)
    print("SAGE x SageFlow: Hotspot News Aggregation (Real Embeddings)")
    print("=" * 70)

    # 你提供的 embedding 服务配置
    embedding_base_url = "http://localhost:8090/v1"
    embedding_model = "BAAI/bge-large-en-v1.5"

    # SageFlow join 阈值：真实 embedding 下通常需要你按实际服务调一下
    similarity_threshold = 0.75
    top_k = 10

    env = LocalEnvironment("hotspot-detection-pipeline")

    docs_a = [
        {"id": "A01", "platform": "Platform-A", "title": "Nvidia's new Blackwell GPUs are here"},
        {"id": "A02", "platform": "Platform-A", "title": "Apple unveils M4 chip for next-gen Macs"},
        {"id": "A03", "platform": "Platform-A", "title": "Lakers win NBA championship in a dramatic final"},
        {"id": "A04", "platform": "Platform-A", "title": "Google I/O 2025 focuses on Gemini AI"},
        {"id": "A05", "platform": "Platform-A", "title": "FIFA World Cup 2026 host cities announced"},
        {"id": "A06", "platform": "Platform-A", "title": "Microsoft launches new Surface Pro 11"},
    ]

    docs_b = [
        {"id": "B01", "platform": "Platform-B", "title": "Nvidia announces the Blackwell GPU architecture"},
        {"id": "B02", "platform": "Platform-B", "title": "Next generation of Macs to be powered by Apple's M4"},
        {"id": "B03", "platform": "Platform-B", "title": "Dramatic NBA finals see Lakers take the crown"},
        {"id": "B04", "platform": "Platform-B", "title": "Gemini AI is the star of Google I/O 2025"},
        {"id": "B05", "platform": "Platform-B", "title": "FIFA reveals host cities for World Cup 2026"},
        {"id": "B06", "platform": "Platform-B", "title": "First look at the new Surface Pro from Microsoft"},
        {"id": "B07", "platform": "Platform-B", "title": "Boston Celtics trade update"},
    ]

    embed_map = OpenAIEmbeddingMap(
        base_url=embedding_base_url,
        model=embedding_model,
        api_key="dummy",
        text_field="title",
    )

    dim = embed_map.dim
    print(f"Embedding model: {embedding_model}")
    print(f"Embedding base_url: {embedding_base_url}")
    print(f"Embedding dim: {dim}")
    print(f"SageFlow similarity_threshold: {similarity_threshold}")

    stream_a = env.from_batch(docs_a).map(lambda x: embed_map.execute(x))
    stream_b = env.from_batch(docs_b).map(lambda x: embed_map.execute(x))

    all_hotspots: list[dict[str, Any]] = []

    (
        stream_a.connect(stream_b)
        .comap(
            SageFlowHotspotPairCoMap,
            dim=dim,
            similarity_threshold=similarity_threshold,
        )
        .flatmap(HotspotPairListFlatten)
        .sink(HotspotCollectorSink, results_list=all_hotspots)
    )

    print("Submitting pipeline...")
    start_time = time.time()
    env.submit(autostop=True)
    print(f"Pipeline finished in {time.time() - start_time:.2f}s")

    print(f"\nTop-{top_k} hotspot pairs:")
    print("-" * 70)

    if not all_hotspots:
        print("No hotspot pairs found. Try lowering similarity_threshold.")
        return

    sorted_hotspots = sorted(all_hotspots, key=lambda p: p.get("similarity", 0.0), reverse=True)

    for i, pair in enumerate(sorted_hotspots[:top_k]):
        left = pair.get("left", {})
        right = pair.get("right", {})
        sim = pair.get("similarity", 0.0)

        print(f"#{i+1:02d} | sim={sim:.4f}")
        print(f"  -> [{left.get('platform')}] {left.get('title')}")
        print(f"  -> [{right.get('platform')}] {right.get('title')}")
        print("-" * 70)


if __name__ == "__main__":
    main()
