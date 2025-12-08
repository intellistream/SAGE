"""Minimal sanity check for PostRetrieval.rerank.

Run with:

    python -m sage.benchmark.benchmark_memory.experiment.script.run_post_retrieval_sanity
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sage.benchmark.benchmark_memory.experiment.libs.post_retrieval import (
    PostRetrieval,
)
from sage.benchmark.benchmark_memory.experiment.utils.config_loader import (
    RuntimeConfig,
)


def build_runtime_config() -> RuntimeConfig:
    # 这里直接创建一个最小 YAML-less 配置：传一个不存在的路径，然后在 runtime_params 中注入所需键
    cfg = RuntimeConfig(
        config_path=None,
        **{
            "operators.post_retrieval.action": "rerank",
            "operators.post_retrieval.rerank_type": "time_weighted",
            # 使用 metadata.timestamp 做时间衰减
            "operators.post_retrieval.time_field": "timestamp",
        },
    )
    return cfg


def main() -> None:
    cfg = build_runtime_config()
    op = PostRetrieval(cfg)

    now = datetime.now(UTC)

    data = {
        "question": "What did we talk about yesterday?",
        "memory_data": [
            {
                "text": "Two days ago: talked about project planning.",
                "score": 0.8,
                "metadata": {"timestamp": (now - timedelta(days=2)).isoformat()},
            },
            {
                "text": "Just now: discussed the deployment issue.",
                "score": 0.7,
                "metadata": {"timestamp": now.isoformat()},
            },
        ],
    }

    out = op.execute(data)

    print("=== Reranked memory_data ===")
    for i, m in enumerate(out.get("memory_data", [])):
        ts = m.get("metadata", {}).get("timestamp")
        rscore = m.get("metadata", {}).get("rerank_score")
        print(f"#{i} ts={ts} rerank_score={rscore:.4f} text={m.get('text')}")

    print("\n=== history_text ===")
    print(out.get("history_text", ""))


if __name__ == "__main__":
    main()
