from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .corpus import build_workload_documents
from .dependencies import (
    DEFAULT_WORKLOAD_DATASET_ORDER,
    WORKLOAD_BENCHMARK_SHAPE_CATALOG,
    WORKLOAD_FAMILY_SPECS,
    WORKLOAD_PRESET_CATALOG,
    generate_repo_local_workload_requests,
    normalize_repo_local_metadata,
    require_shared_workloads,
    summarize_repo_local_workload,
)

_SHAPE_REQUIRED_KEYS = {
    "num_groups",
    "prompts_per_group",
    "system_prompt_len",
    "question_len",
    "output_len",
}


class WhitespaceTokenizer:
    def encode(self, text: str, add_special_tokens: bool = False) -> list[str]:
        del add_special_tokens
        return text.split()


@dataclass(frozen=True)
class SharedWorkloadBundle:
    dataset_name: str
    family_spec: dict[str, Any]
    shape: dict[str, Any]
    preset: dict[str, Any]
    workload_summary: dict[str, Any]
    query_items: list[dict[str, Any]]
    documents: list[dict[str, str]]


def supported_workload_names() -> tuple[str, ...]:
    require_shared_workloads()
    return tuple(DEFAULT_WORKLOAD_DATASET_ORDER)


def resolve_workload_names(workload_names: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    require_shared_workloads()
    if not workload_names:
        return supported_workload_names()

    normalized = tuple(name.strip() for name in workload_names if name and name.strip())
    if not normalized or normalized == ("all",):
        return supported_workload_names()

    unknown = sorted(set(normalized) - set(DEFAULT_WORKLOAD_DATASET_ORDER))
    if unknown:
        raise ValueError(f"unknown workload names: {', '.join(unknown)}")
    return normalized


def _shape_kwargs(shape: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in shape.items() if key not in _SHAPE_REQUIRED_KEYS}


def _metadata_dict(metadata: Any) -> dict[str, Any]:
    return {
        "workload_family": metadata.workload_family,
        "family_label": metadata.family_label,
        "deployment_story": metadata.deployment_story,
        "anchor_strategy": metadata.anchor_strategy,
        "locality_activation_rationale": metadata.locality_activation_rationale,
        "primary_anchor_id": metadata.primary_anchor_id,
        "secondary_anchor_ids": list(metadata.secondary_anchor_ids),
        "primary_anchor_kind": metadata.primary_anchor_kind,
        "secondary_anchor_kind": metadata.secondary_anchor_kind,
        "home_rank": metadata.home_rank,
        "anchor_index": metadata.anchor_index,
        "turn_index": metadata.turn_index,
        "extras": dict(metadata.extras),
    }


def _query_items_from_rows(dataset_name: str, rows: list[Any]) -> list[dict[str, Any]]:
    query_items: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows, start=1):
        metadata = normalize_repo_local_metadata(getattr(row, "repo_local_metadata", {}))
        session_id = (
            metadata.primary_anchor_id
            or getattr(row, "routing_key", None)
            or f"{dataset_name}-session-{metadata.anchor_index}"
        )
        query_items.append(
            {
                "query_id": f"{dataset_name}-q{row_index}",
                "session_id": str(session_id),
                "question": str(getattr(row, "prompt", "")),
                "prompt_len": int(getattr(row, "prompt_len", 0)),
                "expected_output_len": int(getattr(row, "output_len", 0)),
                "routing_key": getattr(row, "routing_key", None),
                "workload_metadata": _metadata_dict(metadata),
            }
        )
    return query_items


def load_workload_bundle(
    dataset_name: str,
    *,
    seed: int,
    dp_size: int = 8,
    max_requests_per_workload: int | None = None,
) -> SharedWorkloadBundle:
    require_shared_workloads()
    if dataset_name not in WORKLOAD_BENCHMARK_SHAPE_CATALOG:
        raise ValueError(f"unknown workload dataset: {dataset_name}")

    shape = dict(WORKLOAD_BENCHMARK_SHAPE_CATALOG[dataset_name])
    row_count = int(shape["num_groups"]) * int(shape["prompts_per_group"])
    rows = generate_repo_local_workload_requests(
        dataset_name=dataset_name,
        tokenizer=WhitespaceTokenizer(),
        dp_size=dp_size,
        num_prompts=row_count,
        num_groups=int(shape["num_groups"]),
        system_prompt_len=int(shape["system_prompt_len"]),
        question_len=int(shape["question_len"]),
        output_len=int(shape["output_len"]),
        seed=seed,
        **_shape_kwargs(shape),
    )
    if max_requests_per_workload is not None:
        rows = rows[: max(1, int(max_requests_per_workload))]

    workload_summary = summarize_repo_local_workload(rows)
    if workload_summary is None:
        raise ValueError(f"shared workload {dataset_name} did not emit repo-local metadata")

    family_spec = dict(WORKLOAD_FAMILY_SPECS[dataset_name].__dict__)
    preset = dict(WORKLOAD_PRESET_CATALOG.get(dataset_name, {}))
    query_items = _query_items_from_rows(dataset_name, rows)
    documents = build_workload_documents(
        dataset_name,
        rows,
        family_spec=family_spec,
        shape=shape,
        preset=preset,
        workload_summary=workload_summary,
    )
    return SharedWorkloadBundle(
        dataset_name=dataset_name,
        family_spec=family_spec,
        shape=shape,
        preset=preset,
        workload_summary=workload_summary,
        query_items=query_items,
        documents=documents,
    )


__all__ = [
    "SharedWorkloadBundle",
    "WhitespaceTokenizer",
    "load_workload_bundle",
    "resolve_workload_names",
    "supported_workload_names",
]
