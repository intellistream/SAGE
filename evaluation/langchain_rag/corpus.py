from __future__ import annotations

from collections import defaultdict
from typing import Any

from .dependencies import normalize_repo_local_metadata, require_shared_workloads


def _prompt_snippet(prompt: str, token_limit: int = 96) -> str:
    tokens = str(prompt).split()
    if len(tokens) <= token_limit:
        return " ".join(tokens)
    return " ".join(tokens[:token_limit]) + " ..."


def _family_overview_text(
    dataset_name: str,
    family_spec: dict[str, Any],
    shape: dict[str, Any],
    preset: dict[str, Any],
    workload_summary: dict[str, Any],
) -> str:
    summary_lines = [
        f"dataset_name: {dataset_name}",
        f"family_label: {family_spec.get('family_label', dataset_name)}",
        f"deployment_story: {family_spec.get('deployment_story', '')}",
        f"anchor_strategy: {family_spec.get('anchor_strategy', '')}",
        f"locality_activation_rationale: {family_spec.get('locality_activation_rationale', '')}",
        f"primary_anchor_kind: {family_spec.get('primary_anchor_kind', '')}",
        f"secondary_anchor_kind: {family_spec.get('secondary_anchor_kind', '')}",
        f"scenario_tags: {', '.join(family_spec.get('scenario_tags', ())) or 'none'}",
        f"request_count: {workload_summary.get('request_count', 0)}",
        f"primary_anchor_count: {workload_summary.get('primary_anchor_count', 0)}",
        f"secondary_anchor_count: {workload_summary.get('secondary_anchor_count', 0)}",
        f"anchor_rank_coverage: {workload_summary.get('anchor_rank_coverage', 0)}",
        f"recommended_request_rate: {preset.get('recommended_request_rate', 'unknown')}",
        f"shape: {shape}",
    ]
    return "\n".join(summary_lines)


def build_workload_documents(
    dataset_name: str,
    rows: list[Any],
    family_spec: dict[str, Any],
    shape: dict[str, Any],
    preset: dict[str, Any],
    workload_summary: dict[str, Any],
) -> list[dict[str, str]]:
    require_shared_workloads()

    documents: list[dict[str, str]] = [
        {
            "source_id": f"{dataset_name}-overview",
            "title": f"{family_spec.get('family_label', dataset_name)} overview",
            "text": _family_overview_text(
                dataset_name, family_spec, shape, preset, workload_summary
            ),
        }
    ]

    primary_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    secondary_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row_index, row in enumerate(rows, start=1):
        metadata = normalize_repo_local_metadata(getattr(row, "repo_local_metadata", {}))
        record = {
            "row_index": row_index,
            "primary_anchor_id": metadata.primary_anchor_id or f"anchor-{row_index}",
            "secondary_anchor_ids": metadata.secondary_anchor_ids,
            "home_rank": metadata.home_rank,
            "turn_index": metadata.turn_index,
            "prompt_len": int(getattr(row, "prompt_len", 0)),
            "output_len": int(getattr(row, "output_len", 0)),
            "snippet": _prompt_snippet(getattr(row, "prompt", "")),
        }
        primary_groups[record["primary_anchor_id"]].append(record)
        for secondary_anchor_id in record["secondary_anchor_ids"]:
            secondary_groups[secondary_anchor_id].append(record)

    for primary_anchor_id, records in sorted(primary_groups.items()):
        ordered = sorted(records, key=lambda item: (item["turn_index"], item["row_index"]))
        snippets = "\n".join(
            f"turn_{item['turn_index']}: {item['snippet']}" for item in ordered[:3]
        )
        secondary_anchor_ids = sorted(
            {
                secondary_anchor_id
                for item in ordered
                for secondary_anchor_id in item["secondary_anchor_ids"]
            }
        )
        documents.append(
            {
                "source_id": f"{dataset_name}-primary-{primary_anchor_id}",
                "title": f"Primary anchor {primary_anchor_id}",
                "text": (
                    f"dataset_name: {dataset_name}\n"
                    f"primary_anchor_id: {primary_anchor_id}\n"
                    f"primary_anchor_kind: {family_spec.get('primary_anchor_kind', '')}\n"
                    f"home_ranks: {sorted({item['home_rank'] for item in ordered})}\n"
                    f"secondary_anchor_ids: {secondary_anchor_ids}\n"
                    f"prompt_examples:\n{snippets}"
                ),
            }
        )

    for secondary_anchor_id, records in sorted(secondary_groups.items()):
        ordered = sorted(records, key=lambda item: (item["turn_index"], item["row_index"]))
        primary_anchor_ids = sorted({item["primary_anchor_id"] for item in ordered})
        snippets = "\n".join(
            f"anchor_{item['primary_anchor_id']}: {item['snippet']}" for item in ordered[:3]
        )
        documents.append(
            {
                "source_id": f"{dataset_name}-secondary-{secondary_anchor_id}",
                "title": f"Secondary anchor {secondary_anchor_id}",
                "text": (
                    f"dataset_name: {dataset_name}\n"
                    f"secondary_anchor_id: {secondary_anchor_id}\n"
                    f"secondary_anchor_kind: {family_spec.get('secondary_anchor_kind', '')}\n"
                    f"linked_primary_anchor_ids: {primary_anchor_ids}\n"
                    f"shared_prompt_examples:\n{snippets}"
                ),
            }
        )

    return documents


__all__ = ["build_workload_documents"]
