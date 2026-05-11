from __future__ import annotations

import math
from statistics import mean
from typing import Any

STAGE_ORDER = ("source", "retrieval", "memory", "generation", "sink")


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * fraction
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _metric_summary(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {
            "count": 0,
            "avg": 0.0,
            "min": 0.0,
            "max": 0.0,
            "p50": 0.0,
            "p95": 0.0,
        }
    return {
        "count": len(values),
        "avg": round(sum(values) / len(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "p50": round(_percentile(values, 0.50), 3),
        "p95": round(_percentile(values, 0.95), 3),
    }


def _base_query_record(stage_name: str, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "query_id": str(item.get("query_id") or ""),
        "session_id": str(item.get("session_id") or ""),
        "duration_ms": round(float((item.get("latency_ms") or {}).get(stage_name, 0.0)), 3),
        "prompt_len": int(item.get("prompt_len") or 0),
        "expected_output_len": int(item.get("expected_output_len") or 0),
    }


def build_stage_report(
    stage_name: str,
    results: list[dict[str, Any]],
    run_context: dict[str, Any],
) -> dict[str, Any]:
    query_records: list[dict[str, Any]] = []
    for item in results:
        record = _base_query_record(stage_name, item)
        if stage_name == "source":
            source_metrics = item.get("source_metrics") or {}
            record["source_dispatch_offset_ms"] = round(
                float(source_metrics.get("source_dispatch_offset_ms") or 0.0),
                3,
            )
            record["pacing_sleep_ms"] = round(
                float(source_metrics.get("pacing_sleep_ms") or 0.0),
                3,
            )
        elif stage_name == "retrieval":
            retrieval = item.get("retrieval") or {}
            record["retrieved_count"] = int(retrieval.get("retrieved_count") or 0)
            record["index_build_ms"] = round(float(retrieval.get("index_build_ms") or 0.0), 3)
        elif stage_name == "memory":
            memory = item.get("memory") or {}
            record["turns_before"] = int(memory.get("turns_before") or 0)
            record["turns_after"] = int(memory.get("turns_after") or 0)
        elif stage_name == "generation":
            generation = item.get("generation") or {}
            record["prompt_tokens_est"] = int(generation.get("prompt_tokens_est") or 0)
            record["answer_tokens_est"] = int(generation.get("answer_tokens_est") or 0)
            record["generator_backend"] = str(item.get("generator_backend") or "unknown")
        query_records.append(record)

    summary = _metric_summary([float(record["duration_ms"]) for record in query_records])
    summary["enabled_query_count"] = sum(
        1 for record in query_records if record["duration_ms"] > 0.0
    )

    if stage_name == "source" and results:
        source_metrics = results[0].get("source_metrics") or {}
        emission_times = [float(item.get("source_emitted_at") or 0.0) for item in results]
        emission_span_s = 0.0
        if len(emission_times) > 1:
            emission_span_s = max(emission_times) - min(emission_times)
        summary["source_load_ms"] = round(float(source_metrics.get("source_load_ms") or 0.0), 3)
        summary["query_count"] = int(source_metrics.get("query_count") or len(results))
        summary["target_request_rate_qps"] = (
            round(float(source_metrics["target_request_rate_qps"]), 3)
            if source_metrics.get("target_request_rate_qps") is not None
            else None
        )
        summary["target_inter_request_delay_ms"] = round(
            float(source_metrics.get("target_inter_request_delay_ms") or 0.0),
            3,
        )
        summary["pacing_sleep_avg_ms"] = round(
            mean(
                float((item.get("source_metrics") or {}).get("pacing_sleep_ms") or 0.0)
                for item in results
            ),
            3,
        )
        summary["source_emission_span_ms"] = round(emission_span_s * 1000.0, 3)
        summary["achieved_request_rate_qps"] = round(
            ((len(results) - 1) / emission_span_s)
            if len(results) > 1 and emission_span_s > 0.0
            else 0.0,
            3,
        )
        summary["mean_prompt_len"] = round(
            mean(int(item.get("prompt_len") or 0) for item in results), 3
        )
        summary["mean_output_len"] = round(
            mean(int(item.get("expected_output_len") or 0) for item in results), 3
        )
    elif stage_name == "retrieval" and results:
        retrieval = results[0].get("retrieval") or {}
        summary["document_count"] = int(retrieval.get("document_count") or 0)
        summary["chunk_count"] = int(retrieval.get("chunk_count") or 0)
        summary["index_build_ms"] = round(float(retrieval.get("index_build_ms") or 0.0), 3)
        summary["retrieved_count_avg"] = round(
            mean(
                int((item.get("retrieval") or {}).get("retrieved_count") or 0) for item in results
            ),
            3,
        )
    elif stage_name == "memory" and results:
        summary["turns_before_avg"] = round(
            mean(int((item.get("memory") or {}).get("turns_before") or 0) for item in results), 3
        )
        summary["turns_after_max"] = max(
            int((item.get("memory") or {}).get("turns_after") or 0) for item in results
        )
    elif stage_name == "generation" and results:
        summary["prompt_tokens_est_avg"] = round(
            mean(
                int((item.get("generation") or {}).get("prompt_tokens_est") or 0)
                for item in results
            ),
            3,
        )
        summary["answer_tokens_est_avg"] = round(
            mean(
                int((item.get("generation") or {}).get("answer_tokens_est") or 0)
                for item in results
            ),
            3,
        )
        summary["generator_backends"] = sorted(
            {str(item.get("generator_backend") or "unknown") for item in results}
        )

    return {
        "stage": stage_name,
        "run": run_context,
        "summary": summary,
        "queries": query_records,
    }


def build_stage_reports(
    results: list[dict[str, Any]],
    run_context: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        stage_name: build_stage_report(stage_name, results, run_context)
        for stage_name in STAGE_ORDER
    }


def build_run_summary(
    results: list[dict[str, Any]],
    run_context: dict[str, Any],
    elapsed_s: float,
    stage_reports: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    end_to_end_values = [
        float((item.get("latency_ms") or {}).get("end_to_end", 0.0)) for item in results
    ]
    retrieval = results[0].get("retrieval") if results else {}
    return {
        "run": run_context,
        "query_count": len(results),
        "elapsed_s": round(elapsed_s, 6),
        "throughput_qps": round(len(results) / max(elapsed_s, 1e-9), 3),
        "end_to_end_latency_ms": _metric_summary(end_to_end_values),
        "stage_latency_ms": {
            stage_name: report["summary"] for stage_name, report in stage_reports.items()
        },
        "retrieval_context": {
            "document_count": int((retrieval or {}).get("document_count") or 0),
            "chunk_count": int((retrieval or {}).get("chunk_count") or 0),
            "index_build_ms": round(float((retrieval or {}).get("index_build_ms") or 0.0), 3),
        },
    }


def comparison_row(summary: dict[str, Any]) -> dict[str, Any]:
    run = summary.get("run") or {}
    stage_latency = summary.get("stage_latency_ms") or {}
    return {
        "framework_name": str(run.get("framework_name") or "sage"),
        "workload_name": str(run.get("workload_name") or ""),
        "family_label": str(run.get("family_label") or ""),
        "variant_name": str(run.get("variant_name") or ""),
        "query_count": int(summary.get("query_count") or 0),
        "throughput_qps": round(float(summary.get("throughput_qps") or 0.0), 3),
        "end_to_end_avg_ms": round(
            float((summary.get("end_to_end_latency_ms") or {}).get("avg") or 0.0), 3
        ),
        "source_avg_ms": round(float((stage_latency.get("source") or {}).get("avg") or 0.0), 3),
        "source_load_ms": round(
            float((stage_latency.get("source") or {}).get("source_load_ms") or 0.0), 3
        ),
        "retrieval_avg_ms": round(
            float((stage_latency.get("retrieval") or {}).get("avg") or 0.0), 3
        ),
        "memory_avg_ms": round(float((stage_latency.get("memory") or {}).get("avg") or 0.0), 3),
        "generation_avg_ms": round(
            float((stage_latency.get("generation") or {}).get("avg") or 0.0), 3
        ),
        "sink_avg_ms": round(float((stage_latency.get("sink") or {}).get("avg") or 0.0), 3),
        "document_count": int((summary.get("retrieval_context") or {}).get("document_count") or 0),
        "chunk_count": int((summary.get("retrieval_context") or {}).get("chunk_count") or 0),
    }


__all__ = [
    "STAGE_ORDER",
    "build_run_summary",
    "build_stage_reports",
    "comparison_row",
]
