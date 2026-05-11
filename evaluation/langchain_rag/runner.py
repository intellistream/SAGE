from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from sage.runtime import LocalEnvironment

from .dependencies import dependency_status, require_langchain, require_shared_workloads
from .metrics import comparison_row
from .output import create_batch_output_directory, prepare_run_output_directory, write_json
from .stages import (
    LangChainGenerationStage,
    LangChainMemoryStage,
    LangChainRetrievalStage,
    WorkloadMetricsSink,
    WorkloadQuerySource,
)
from .workloads import load_workload_bundle, resolve_workload_names
from .workloads import supported_workload_names as _supported_workload_names


@dataclass(frozen=True)
class ExperimentVariant:
    name: str
    enable_retrieval: bool
    enable_memory: bool
    description: str


VARIANT_CATALOG = {
    "full_rag": ExperimentVariant(
        name="full_rag",
        enable_retrieval=True,
        enable_memory=True,
        description="Retrieval and memory are both enabled.",
    ),
    "retrieval_only": ExperimentVariant(
        name="retrieval_only",
        enable_retrieval=True,
        enable_memory=False,
        description="Retrieval enabled, memory disabled.",
    ),
    "direct_generation": ExperimentVariant(
        name="direct_generation",
        enable_retrieval=False,
        enable_memory=False,
        description="Direct generation baseline without retrieval or memory.",
    ),
}

DEFAULT_VARIANT_ORDER = ("full_rag", "retrieval_only", "direct_generation")
DEFAULT_FRAMEWORK_ORDER = ("sage",)

FRAMEWORK_LABELS = {
    "sage": "SAGE Runtime",
    "langchain_native": "LangChain Native",
}


def _stable_hash(value: str) -> int:
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def _weighted_average(values: list[tuple[float, int]]) -> float:
    weighted_total = 0.0
    total_weight = 0
    for value, weight in values:
        if weight <= 0:
            continue
        weighted_total += value * weight
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return weighted_total / total_weight


def _stage_average(summary: dict[str, Any], stage_name: str) -> float:
    return float((summary.get("stage_latency_ms") or {}).get(stage_name, {}).get("avg") or 0.0)


def _expected_generation_backend(
    model: str | None,
    model_provider: str | None,
    generation_base_url: str | None,
) -> str:
    if model and generation_base_url:
        return f"openai-compatible:{model}"
    if model and model_provider:
        return f"{model_provider}:{model}"
    return "heuristic-local"


def _validate_generation_backend(
    summary: dict[str, Any],
    *,
    model: str | None,
    model_provider: str | None,
    generation_base_url: str | None,
) -> None:
    run = summary.get("run") or {}
    generation_summary = (summary.get("stage_latency_ms") or {}).get("generation") or {}
    backends = sorted(
        str(backend) for backend in generation_summary.get("generator_backends") or []
    )
    expected_backend = _expected_generation_backend(model, model_provider, generation_base_url)
    if backends == [expected_backend]:
        return
    workload_name = str(run.get("workload_name") or "unknown-workload")
    variant_name = str(run.get("variant_name") or "unknown-variant")
    observed = ", ".join(backends) if backends else "none"
    raise RuntimeError(
        "generation backend mismatch detected for fair comparison: "
        f"workload={workload_name}, variant={variant_name}, expected={expected_backend}, observed={observed}"
    )


def _variant_execution_order(
    workload_name: str,
    variants: tuple[ExperimentVariant, ...],
    seed: int,
) -> tuple[ExperimentVariant, ...]:
    if len(variants) <= 1:
        return variants
    offset = _stable_hash(f"{workload_name}:{seed}") % len(variants)
    return variants[offset:] + variants[:offset]


def supported_workload_names() -> tuple[str, ...]:
    return _supported_workload_names()


def supported_variant_names() -> tuple[str, ...]:
    return tuple(DEFAULT_VARIANT_ORDER)


def supported_framework_names() -> tuple[str, ...]:
    return ("sage", "langchain_native")


def resolve_framework_names(
    framework_names: tuple[str, ...] | list[str] | None,
) -> tuple[str, ...]:
    if not framework_names:
        return DEFAULT_FRAMEWORK_ORDER

    normalized = tuple(name.strip() for name in framework_names if name and name.strip())
    if not normalized or normalized == ("default",):
        return DEFAULT_FRAMEWORK_ORDER

    unknown = sorted(set(normalized) - set(supported_framework_names()))
    if unknown:
        raise ValueError(f"unknown framework names: {', '.join(unknown)}")
    return normalized


def resolve_variant_specs(
    variant_names: tuple[str, ...] | list[str] | None,
) -> tuple[ExperimentVariant, ...]:
    if not variant_names:
        return tuple(VARIANT_CATALOG[name] for name in DEFAULT_VARIANT_ORDER)

    normalized = tuple(name.strip() for name in variant_names if name and name.strip())
    if not normalized or normalized == ("default",):
        return tuple(VARIANT_CATALOG[name] for name in DEFAULT_VARIANT_ORDER)

    unknown = sorted(set(normalized) - set(VARIANT_CATALOG))
    if unknown:
        raise ValueError(f"unknown variant names: {', '.join(unknown)}")
    return tuple(VARIANT_CATALOG[name] for name in normalized)


def _load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _summary_matrix(run_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [comparison_row(summary) for summary in run_summaries]


def _build_by_workload(run_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    matrix = _summary_matrix(run_summaries)
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in matrix:
        workload_name = row["workload_name"]
        framework_name = row["framework_name"]
        entry = grouped.setdefault(
            (workload_name, framework_name),
            {
                "workload_name": workload_name,
                "family_label": row["family_label"],
                "framework_name": framework_name,
                "variants": {},
            },
        )
        entry["variants"][row["variant_name"]] = row
    return {
        "workloads": [grouped[name] for name in sorted(grouped)],
    }


def _build_by_variant(run_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for summary in run_summaries:
        run = summary.get("run") or {}
        grouped.setdefault(
            (
                str(run.get("framework_name") or "sage"),
                str(run.get("variant_name") or "unknown"),
            ),
            [],
        ).append(summary)

    variants: list[dict[str, Any]] = []
    for (framework_name, variant_name), summaries in sorted(grouped.items()):
        rows = [comparison_row(summary) for summary in summaries]
        total_query_count = sum(int(summary.get("query_count") or 0) for summary in summaries)
        total_elapsed_s = sum(float(summary.get("elapsed_s") or 0.0) for summary in summaries)
        variants.append(
            {
                "framework_name": framework_name,
                "variant_name": variant_name,
                "workload_count": len(rows),
                "aggregate_method": "micro_by_query_count",
                "total_query_count": total_query_count,
                "total_elapsed_s": round(total_elapsed_s, 6),
                "avg_throughput_qps": round(total_query_count / max(total_elapsed_s, 1e-9), 3),
                "avg_end_to_end_ms": round(
                    _weighted_average(
                        [(row["end_to_end_avg_ms"], row["query_count"]) for row in rows]
                    ),
                    3,
                ),
                "avg_source_ms": round(
                    _weighted_average([(row["source_avg_ms"], row["query_count"]) for row in rows]),
                    3,
                ),
                "avg_retrieval_ms": round(
                    _weighted_average(
                        [(row["retrieval_avg_ms"], row["query_count"]) for row in rows]
                    ),
                    3,
                ),
                "avg_memory_ms": round(
                    _weighted_average([(row["memory_avg_ms"], row["query_count"]) for row in rows]),
                    3,
                ),
                "avg_generation_ms": round(
                    _weighted_average(
                        [(row["generation_avg_ms"], row["query_count"]) for row in rows]
                    ),
                    3,
                ),
                "avg_sink_ms": round(
                    _weighted_average([(row["sink_avg_ms"], row["query_count"]) for row in rows]),
                    3,
                ),
                "macro_avg_throughput_qps": round(mean(row["throughput_qps"] for row in rows), 3),
                "macro_avg_end_to_end_ms": round(mean(row["end_to_end_avg_ms"] for row in rows), 3),
                "macro_avg_source_ms": round(mean(row["source_avg_ms"] for row in rows), 3),
                "macro_avg_retrieval_ms": round(mean(row["retrieval_avg_ms"] for row in rows), 3),
                "macro_avg_memory_ms": round(mean(row["memory_avg_ms"] for row in rows), 3),
                "macro_avg_generation_ms": round(mean(row["generation_avg_ms"] for row in rows), 3),
                "macro_avg_sink_ms": round(mean(row["sink_avg_ms"] for row in rows), 3),
                "rows": rows,
            }
        )
    return {"variants": variants}


def _build_stage_latency_by_variant(run_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for summary in run_summaries:
        run = summary.get("run") or {}
        grouped.setdefault(
            (
                str(run.get("framework_name") or "sage"),
                str(run.get("variant_name") or "unknown"),
            ),
            [],
        ).append(summary)

    payload: dict[str, Any] = {
        "aggregate_method": "micro_by_query_count",
        "variants": {},
    }
    for (framework_name, variant_name), summaries in sorted(grouped.items()):
        query_counts = [int(summary.get("query_count") or 0) for summary in summaries]
        payload["variants"][f"{framework_name}::{variant_name}"] = {
            "framework_name": framework_name,
            "variant_name": variant_name,
            "total_query_count": sum(query_counts),
            "source": {
                "avg_ms": round(
                    _weighted_average(
                        [
                            (
                                _stage_average(summary, "source"),
                                int(summary.get("query_count") or 0),
                            )
                            for summary in summaries
                        ]
                    ),
                    3,
                ),
                "macro_avg_ms": round(
                    mean(_stage_average(summary, "source") for summary in summaries), 3
                ),
            },
            "retrieval": {
                "avg_ms": round(
                    _weighted_average(
                        [
                            (
                                _stage_average(summary, "retrieval"),
                                int(summary.get("query_count") or 0),
                            )
                            for summary in summaries
                        ]
                    ),
                    3,
                ),
                "macro_avg_ms": round(
                    mean(_stage_average(summary, "retrieval") for summary in summaries), 3
                ),
            },
            "memory": {
                "avg_ms": round(
                    _weighted_average(
                        [
                            (
                                _stage_average(summary, "memory"),
                                int(summary.get("query_count") or 0),
                            )
                            for summary in summaries
                        ]
                    ),
                    3,
                ),
                "macro_avg_ms": round(
                    mean(_stage_average(summary, "memory") for summary in summaries), 3
                ),
            },
            "generation": {
                "avg_ms": round(
                    _weighted_average(
                        [
                            (
                                _stage_average(summary, "generation"),
                                int(summary.get("query_count") or 0),
                            )
                            for summary in summaries
                        ]
                    ),
                    3,
                ),
                "macro_avg_ms": round(
                    mean(_stage_average(summary, "generation") for summary in summaries), 3
                ),
            },
            "sink": {
                "avg_ms": round(
                    _weighted_average(
                        [
                            (_stage_average(summary, "sink"), int(summary.get("query_count") or 0))
                            for summary in summaries
                        ]
                    ),
                    3,
                ),
                "macro_avg_ms": round(
                    mean(_stage_average(summary, "sink") for summary in summaries), 3
                ),
            },
        }
    return payload


def _build_fairness_audit(
    run_summaries: list[dict[str, Any]],
    *,
    framework_names: tuple[str, ...],
    workload_variant_orders: dict[str, list[str]],
    model: str | None,
    model_provider: str | None,
    generation_base_url: str | None,
) -> dict[str, Any]:
    matrix = _summary_matrix(run_summaries)
    matrix_orders: dict[tuple[str, str], list[str]] = {}
    for row in matrix:
        matrix_orders.setdefault(
            (str(row["workload_name"]), str(row["framework_name"])),
            [],
        ).append(str(row["variant_name"]))

    workloads: list[dict[str, Any]] = []
    for workload_name in sorted(workload_variant_orders):
        for framework_name in framework_names:
            matching = [
                summary
                for summary in run_summaries
                if str((summary.get("run") or {}).get("workload_name")) == workload_name
                and str((summary.get("run") or {}).get("framework_name") or "sage")
                == framework_name
            ]
            query_count = sum(int(summary.get("query_count") or 0) for summary in matching)
            workloads.append(
                {
                    "workload_name": workload_name,
                    "framework_name": framework_name,
                    "query_count": query_count,
                    "variant_execution_order": workload_variant_orders[workload_name],
                    "matrix_variant_order": matrix_orders.get((workload_name, framework_name), []),
                    "execution_order_matches_matrix": workload_variant_orders[workload_name]
                    == matrix_orders.get((workload_name, framework_name), []),
                }
            )

    return {
        "policy_version": 1,
        "shared_input_policy": "All frameworks and variants for a workload reuse the same precomputed workload bundle and query set.",
        "framework_execution_policy": "fixed_requested_order",
        "variant_execution_policy": "deterministic_rotation_by_workload_and_seed",
        "variant_aggregate_method": "micro_by_query_count",
        "stage_aggregate_method": "micro_by_query_count",
        "source_latency_semantics": {
            "comparable_metric": "source.avg_ms records per-item source processing latency.",
            "non_comparable_metric": "source_dispatch_offset_ms records batch emission position and should not be used for cross-variant fairness claims.",
        },
        "generation_backend_policy": {
            "expected_backend": _expected_generation_backend(
                model, model_provider, generation_base_url
            ),
            "mixed_backends_allowed": False,
            "enforcement": "runner raises before batch completion if a run falls back to a different backend.",
        },
        "workloads": workloads,
    }


def _run_variant(
    batch_dir: Path,
    batch_id: str,
    bundle: Any,
    framework_name: str,
    variant: ExperimentVariant,
    *,
    seed: int,
    top_k: int,
    chunk_size: int,
    chunk_overlap: int,
    max_memory_turns: int,
    model: str | None,
    model_provider: str | None,
    generation_base_url: str | None,
    generation_api_key: str | None,
    embedding_model: str | None,
    embedding_base_url: str | None,
    embedding_api_key: str | None,
    temperature: float,
    generation_parallelism: int,
    source_request_rate_qps: float | None,
) -> dict[str, Any]:
    run_dir = prepare_run_output_directory(
        batch_dir,
        bundle.dataset_name,
        variant.name,
        framework_name if framework_name != "sage" else None,
    )
    run_context = {
        "batch_id": batch_id,
        "framework_name": framework_name,
        "framework_label": FRAMEWORK_LABELS[framework_name],
        "workload_name": bundle.dataset_name,
        "family_label": str(bundle.family_spec.get("family_label") or bundle.dataset_name),
        "variant_name": variant.name,
        "variant": {
            "enable_retrieval": variant.enable_retrieval,
            "enable_memory": variant.enable_memory,
            "description": variant.description,
        },
        "seed": seed,
        "shape": bundle.shape,
        "preset": bundle.preset,
        "workload_summary": bundle.workload_summary,
        "document_count": len(bundle.documents),
        "generation_base_url": generation_base_url,
        "embedding_model": embedding_model,
        "embedding_base_url": embedding_base_url,
        "source_request_rate_qps": source_request_rate_qps,
        "run_output_dir": str(run_dir),
    }

    print(
        f"[langchain-rag] seed={seed} framework={framework_name} workload={bundle.dataset_name} variant={variant.name} start",
        flush=True,
    )

    if framework_name == "langchain_native":
        source = WorkloadQuerySource(bundle.query_items, request_rate_qps=source_request_rate_qps)
        retrieval = LangChainRetrievalStage(
            documents=bundle.documents,
            enable_retrieval=variant.enable_retrieval,
            top_k=top_k,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedding_model=embedding_model,
            embedding_base_url=embedding_base_url,
            embedding_api_key=embedding_api_key,
        )
        memory = LangChainMemoryStage(
            max_turns=max_memory_turns, enable_memory=variant.enable_memory
        )
        generation = LangChainGenerationStage(
            variant_name=variant.name,
            model=model,
            model_provider=model_provider,
            generation_base_url=generation_base_url,
            generation_api_key=generation_api_key,
            temperature=temperature,
        )
        sink = WorkloadMetricsSink(run_output_dir=str(run_dir), run_context=run_context)
        while True:
            item = source.execute()
            if item is None:
                break
            payload = retrieval.execute(item)
            payload = memory.execute(payload)
            payload = generation.execute(payload)
            sink.execute(payload)
        sink.close()
    else:
        env = LocalEnvironment(f"langchain_rag_{bundle.dataset_name}_{variant.name}")
        (
            env.from_batch(
                WorkloadQuerySource,
                query_items=bundle.query_items,
                request_rate_qps=source_request_rate_qps,
            )
            .map(
                LangChainRetrievalStage,
                documents=bundle.documents,
                enable_retrieval=variant.enable_retrieval,
                top_k=top_k,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                embedding_model=embedding_model,
                embedding_base_url=embedding_base_url,
                embedding_api_key=embedding_api_key,
            )
            .map(
                LangChainMemoryStage,
                max_turns=max_memory_turns,
                enable_memory=variant.enable_memory,
            )
            .map(
                LangChainGenerationStage,
                variant_name=variant.name,
                model=model,
                model_provider=model_provider,
                generation_base_url=generation_base_url,
                generation_api_key=generation_api_key,
                temperature=temperature,
                parallelism=generation_parallelism,
            )
            .sink(WorkloadMetricsSink, run_output_dir=str(run_dir), run_context=run_context)
        )
        env.submit(autostop=True)
    summary = _load_summary(run_dir / "summary.json")
    print(
        "[langchain-rag] "
        f"seed={seed} framework={framework_name} workload={bundle.dataset_name} variant={variant.name} completed "
        f"queries={summary.get('query_count', 0)} throughput_qps={summary.get('throughput_qps', 0)}",
        flush=True,
    )
    _validate_generation_backend(
        summary,
        model=model,
        model_provider=model_provider,
        generation_base_url=generation_base_url,
    )
    return summary


def run_shared_workload_comparison(
    *,
    output_root: str | Path | None = None,
    framework_names: tuple[str, ...] | list[str] | None = None,
    workload_names: tuple[str, ...] | list[str] | None = None,
    variant_names: tuple[str, ...] | list[str] | None = None,
    seed: int = 7,
    max_requests_per_workload: int | None = None,
    dp_size: int = 8,
    top_k: int = 3,
    chunk_size: int = 320,
    chunk_overlap: int = 48,
    max_memory_turns: int = 4,
    model: str | None = None,
    model_provider: str | None = None,
    generation_base_url: str | None = None,
    generation_api_key: str | None = None,
    embedding_model: str | None = None,
    embedding_base_url: str | None = None,
    embedding_api_key: str | None = None,
    temperature: float = 0.0,
    generation_parallelism: int = 1,
    source_request_rate_qps: float | None = None,
) -> Path:
    require_langchain()
    require_shared_workloads()

    if generation_parallelism <= 0:
        raise ValueError("generation_parallelism must be positive")
    if source_request_rate_qps is not None and source_request_rate_qps <= 0.0:
        raise ValueError("source_request_rate_qps must be positive when provided")

    resolved_frameworks = resolve_framework_names(framework_names)
    resolved_workloads = resolve_workload_names(workload_names)
    variants = resolve_variant_specs(variant_names)
    batch_dir = create_batch_output_directory(output_root)
    batch_id = batch_dir.name

    manifest = {
        "batch_id": batch_id,
        "dependency_status": dependency_status(),
        "frameworks": list(resolved_frameworks),
        "workloads": list(resolved_workloads),
        "variants": [variant.__dict__ for variant in variants],
        "framework_execution_policy": "fixed_requested_order",
        "variant_execution_policy": "deterministic_rotation_by_workload_and_seed",
        "workload_variant_orders": {},
        "seed": seed,
        "max_requests_per_workload": max_requests_per_workload,
        "dp_size": dp_size,
        "top_k": top_k,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "max_memory_turns": max_memory_turns,
        "model": model,
        "model_provider": model_provider,
        "generation_base_url": generation_base_url,
        "embedding_model": embedding_model,
        "embedding_base_url": embedding_base_url,
        "temperature": temperature,
        "generation_parallelism": generation_parallelism,
        "source_request_rate_qps": source_request_rate_qps,
        "fairness_notes": [
            "All frameworks and variants for a workload share one workload bundle and query set.",
            "Framework execution order follows the requested framework list.",
            "Variant execution order is deterministically rotated per workload and seed.",
            "Comparison aggregates use query-weighted micro averages; macro values are retained as reference only.",
            "Source dispatch offset is recorded separately and should not be used for cross-variant fairness claims.",
            "Mixed generation backends are rejected before batch completion.",
            "When generation_base_url or embedding_base_url is set, the run uses the configured remote OpenAI-compatible services instead of heuristic-local generation or keyword-hash embeddings.",
        ],
        "completed_runs": [],
        "status": "running",
        "result_root": str(batch_dir),
    }
    write_json(batch_dir / "manifest.json", manifest)

    run_summaries: list[dict[str, Any]] = []
    for workload_name in resolved_workloads:
        bundle = load_workload_bundle(
            workload_name,
            seed=seed,
            dp_size=dp_size,
            max_requests_per_workload=max_requests_per_workload,
        )
        ordered_variants = _variant_execution_order(workload_name, variants, seed)
        manifest["workload_variant_orders"][workload_name] = [
            variant.name for variant in ordered_variants
        ]
        for framework_name in resolved_frameworks:
            for variant in ordered_variants:
                run_summaries.append(
                    _run_variant(
                        batch_dir,
                        batch_id,
                        bundle,
                        framework_name,
                        variant,
                        seed=seed,
                        top_k=top_k,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        max_memory_turns=max_memory_turns,
                        model=model,
                        model_provider=model_provider,
                        generation_base_url=generation_base_url,
                        generation_api_key=generation_api_key,
                        embedding_model=embedding_model,
                        embedding_base_url=embedding_base_url,
                        embedding_api_key=embedding_api_key,
                        temperature=temperature,
                        generation_parallelism=generation_parallelism,
                        source_request_rate_qps=source_request_rate_qps,
                    )
                )
                latest_summary = run_summaries[-1]
                latest_run = latest_summary.get("run") or {}
                manifest["completed_runs"].append(
                    {
                        "framework_name": str(latest_run.get("framework_name") or framework_name),
                        "workload_name": str(latest_run.get("workload_name") or workload_name),
                        "variant_name": str(latest_run.get("variant_name") or variant.name),
                        "query_count": int(latest_summary.get("query_count") or 0),
                    }
                )
                write_json(batch_dir / "manifest.json", manifest)

    matrix = _summary_matrix(run_summaries)
    write_json(batch_dir / "comparison" / "workload_variant_matrix.json", {"rows": matrix})
    write_json(batch_dir / "comparison" / "by_workload.json", _build_by_workload(run_summaries))
    write_json(batch_dir / "comparison" / "by_variant.json", _build_by_variant(run_summaries))
    write_json(
        batch_dir / "comparison" / "stage_latency_by_variant.json",
        _build_stage_latency_by_variant(run_summaries),
    )
    write_json(
        batch_dir / "comparison" / "fairness_audit.json",
        _build_fairness_audit(
            run_summaries,
            framework_names=resolved_frameworks,
            workload_variant_orders=manifest["workload_variant_orders"],
            model=model,
            model_provider=model_provider,
            generation_base_url=generation_base_url,
        ),
    )

    manifest["status"] = "completed"
    manifest["run_count"] = len(run_summaries)
    manifest["comparison_files"] = {
        "workload_variant_matrix": str(batch_dir / "comparison" / "workload_variant_matrix.json"),
        "by_workload": str(batch_dir / "comparison" / "by_workload.json"),
        "by_variant": str(batch_dir / "comparison" / "by_variant.json"),
        "stage_latency_by_variant": str(batch_dir / "comparison" / "stage_latency_by_variant.json"),
        "fairness_audit": str(batch_dir / "comparison" / "fairness_audit.json"),
    }
    write_json(batch_dir / "manifest.json", manifest)
    return batch_dir


__all__ = [
    "DEFAULT_VARIANT_ORDER",
    "DEFAULT_FRAMEWORK_ORDER",
    "ExperimentVariant",
    "run_shared_workload_comparison",
    "supported_framework_names",
    "supported_variant_names",
    "supported_workload_names",
]
