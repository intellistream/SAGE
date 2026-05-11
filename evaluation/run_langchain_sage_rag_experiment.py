#!/usr/bin/env python3
"""Run shared-workload LangChain + SAGE comparison experiments."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.langchain_rag import (
    DEFAULT_VARIANT_ORDER,
    run_shared_workload_comparison,
    supported_framework_names,
    supported_variant_names,
    supported_workload_names,
)


def _parse_csv(value: str) -> tuple[str, ...]:
    normalized = tuple(part.strip() for part in value.split(",") if part.strip())
    return normalized or ("all",)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a separated LangChain + SAGE RAG comparison harness across the 15 shared workloads "
            "from the sibling llm-serving-workloads repository."
        )
    )
    parser.add_argument(
        "--workloads", default="all", help="Comma-separated workload names or 'all'."
    )
    parser.add_argument(
        "--variants",
        default=",".join(DEFAULT_VARIANT_ORDER),
        help="Comma-separated variant names.",
    )
    parser.add_argument(
        "--frameworks",
        default="sage",
        help="Comma-separated framework names. Supported: sage, langchain_native.",
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-requests-per-workload", type=int, default=None)
    parser.add_argument("--dp-size", type=int, default=8)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--chunk-size", type=int, default=320)
    parser.add_argument("--chunk-overlap", type=int, default=48)
    parser.add_argument("--max-memory-turns", type=int, default=4)
    parser.add_argument("--model", default=None)
    parser.add_argument("--model-provider", default=None)
    parser.add_argument("--generation-base-url", default=None)
    parser.add_argument("--generation-api-key", default="EMPTY")
    parser.add_argument("--embedding-model", default=None)
    parser.add_argument("--embedding-base-url", default=None)
    parser.add_argument("--embedding-api-key", default="EMPTY")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--generation-parallelism", type=int, default=1)
    parser.add_argument("--source-request-rate-qps", type=float, default=None)
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--list-workloads", action="store_true")
    parser.add_argument("--list-variants", action="store_true")
    parser.add_argument("--list-frameworks", action="store_true")
    args = parser.parse_args()

    if args.list_workloads:
        print("\n".join(supported_workload_names()))
        return 0
    if args.list_variants:
        print("\n".join(supported_variant_names()))
        return 0
    if args.list_frameworks:
        print("\n".join(supported_framework_names()))
        return 0

    try:
        batch_dir = run_shared_workload_comparison(
            output_root=args.output_root,
            framework_names=_parse_csv(args.frameworks),
            workload_names=_parse_csv(args.workloads),
            variant_names=_parse_csv(args.variants),
            seed=args.seed,
            max_requests_per_workload=args.max_requests_per_workload,
            dp_size=args.dp_size,
            top_k=args.top_k,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            max_memory_turns=args.max_memory_turns,
            model=args.model,
            model_provider=args.model_provider,
            generation_base_url=args.generation_base_url,
            generation_api_key=args.generation_api_key,
            embedding_model=args.embedding_model,
            embedding_base_url=args.embedding_base_url,
            embedding_api_key=args.embedding_api_key,
            temperature=args.temperature,
            generation_parallelism=args.generation_parallelism,
            source_request_rate_qps=args.source_request_rate_qps,
        )
    except Exception as exc:  # noqa: BLE001
        print(exc, file=sys.stderr)
        return 1

    print(f"Wrote batch results to {batch_dir}")
    return 0


__all__ = [
    "DEFAULT_VARIANT_ORDER",
    "main",
    "run_shared_workload_comparison",
    "supported_framework_names",
    "supported_variant_names",
    "supported_workload_names",
]


if __name__ == "__main__":
    raise SystemExit(main())
