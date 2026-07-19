#!/usr/bin/env python3
"""Generate the deterministic strong-baseline comparison used in the paper."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

SCENARIOS = (
    "single-service",
    "cascade",
    "shared-bottleneck",
    "concurrent",
    "false-correlation",
    "partial-evidence",
    "ambiguous-overmerge",
    "ambiguous-disconnected-merge",
    "ambiguous-temporal-split",
)
SEEDS_10 = (7, 11, 13, 17, 19, 23, 29, 31, 37, 41)
MATCHED_SEEDS = (7, 11, 13)
ACTION = "llm-pairwise-action-validated"
HYBRID = "hybrid-hint"
CONSTRAINED = "constrained-agglomerative"
PANEL_A_REDUCERS = (
    "map-only",
    "window-aggregate",
    HYBRID,
    CONSTRAINED,
)
DISPLAY = {
    "map-only": "Map-only",
    "window-aggregate": "Window",
    HYBRID: "Hybrid",
    CONSTRAINED: "Constrained",
    ACTION: "Bounded action",
}
SCENARIO_DISPLAY = {
    "single-service": "Single service",
    "cascade": "Cascade",
    "shared-bottleneck": "Shared bottleneck",
    "concurrent": "Concurrent",
    "false-correlation": "False correlation",
    "partial-evidence": "Partial evidence",
    "ambiguous-overmerge": "Overmerge",
    "ambiguous-disconnected-merge": "Disconnected",
    "ambiguous-temporal-split": "Temporal split",
}
EXPECTED_AGGREGATE = {
    "map-only": 0.0705,
    "window-aggregate": 0.4916,
    HYBRID: 0.7796,
    CONSTRAINED: 0.9287,
    ACTION: 0.8645,
    "matched-hybrid": 0.7801,
    "matched-constrained": 0.9028,
}
BOOTSTRAP_SEED = 20260718
BOOTSTRAP_DRAWS = 10_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-summary", required=True, type=Path)
    parser.add_argument("--online-case-summary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--data-output", type=Path)
    return parser.parse_args()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _assert_unique(
    rows: list[dict[str, str]], keys: tuple[str, ...], expected_count: int, label: str
) -> None:
    identities = [tuple(row[key] for key in keys) for row in rows]
    if len(rows) != expected_count or len(set(identities)) != expected_count:
        raise SystemExit(
            f"{label} must contain {expected_count} unique rows by {keys}; "
            f"got {len(rows)} rows and {len(set(identities))} identities"
        )


def load_evidence(
    offline_summary: Path, online_case_summary: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    offline_raw = _read_csv(offline_summary)
    _assert_unique(
        offline_raw,
        ("scenario", "seed", "sample_id", "reducer"),
        9 * 10 * 6,
        "offline matrix",
    )
    offline = [
        {
            "scenario": row["scenario"],
            "seed": int(row["seed"]),
            "reducer": row["reducer"],
            "f1": float(row["f1"]),
        }
        for row in offline_raw
    ]
    if set(row["scenario"] for row in offline) != set(SCENARIOS):
        raise SystemExit("offline scenario inventory drift")
    if set(row["seed"] for row in offline) != set(SEEDS_10):
        raise SystemExit("offline seed inventory drift")
    for reducer in PANEL_A_REDUCERS:
        if sum(row["reducer"] == reducer for row in offline) != 90:
            raise SystemExit(f"offline reducer coverage drift: {reducer}")

    online_raw = [
        row
        for row in _read_csv(online_case_summary)
        if row["reducer"] in {HYBRID, ACTION}
    ]
    _assert_unique(
        online_raw,
        ("scenario", "seed", "sample_id", "reducer"),
        9 * 3 * 5 * 2,
        "online action/hybrid matrix",
    )
    if set(row["scenario"] for row in online_raw) != set(SCENARIOS):
        raise SystemExit("online scenario inventory drift")
    if set(int(row["seed"]) for row in online_raw) != set(MATCHED_SEEDS):
        raise SystemExit("online seed inventory drift")

    grouped: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    for row in online_raw:
        grouped[(row["scenario"], int(row["seed"]), row["reducer"])].append(
            float(row["f1"])
        )
    online = []
    for (scenario, seed, reducer), values in sorted(grouped.items()):
        if len(values) != 5:
            raise SystemExit(f"online repeat coverage drift: {scenario}/{seed}/{reducer}")
        online.append(
            {
                "scenario": scenario,
                "seed": seed,
                "reducer": reducer,
                "f1": statistics.fmean(values),
            }
        )
    return offline, online


def summarize(
    offline: list[dict[str, Any]], online: list[dict[str, Any]]
) -> dict[str, Any]:
    aggregate = {
        reducer: statistics.fmean(
            row["f1"] for row in offline if row["reducer"] == reducer
        )
        for reducer in PANEL_A_REDUCERS
    }
    matched_constrained = [
        row
        for row in offline
        if row["reducer"] == CONSTRAINED and row["seed"] in MATCHED_SEEDS
    ]
    aggregate["matched-constrained"] = statistics.fmean(
        row["f1"] for row in matched_constrained
    )
    aggregate["matched-hybrid"] = statistics.fmean(
        row["f1"] for row in online if row["reducer"] == HYBRID
    )
    aggregate[ACTION] = statistics.fmean(
        row["f1"] for row in online if row["reducer"] == ACTION
    )
    for name, expected in EXPECTED_AGGREGATE.items():
        actual = round(aggregate[name], 4)
        if actual != expected:
            raise SystemExit(
                f"frozen aggregate mismatch for {name}: expected {expected}, got {actual}"
            )

    action_by_unit = {
        (row["scenario"], row["seed"]): row["f1"]
        for row in online
        if row["reducer"] == ACTION
    }
    constrained_by_unit = {
        (row["scenario"], row["seed"]): row["f1"]
        for row in matched_constrained
    }
    deltas = [
        action_by_unit[unit] - constrained_by_unit[unit]
        for unit in sorted(constrained_by_unit)
    ]
    rng = random.Random(BOOTSTRAP_SEED)
    bootstrap_means = sorted(
        statistics.fmean(rng.choices(deltas, k=len(deltas)))
        for _ in range(BOOTSTRAP_DRAWS)
    )

    def percentile(values: list[float], quantile: float) -> float:
        index = (len(values) - 1) * quantile
        lower = int(index)
        upper = min(lower + 1, len(values) - 1)
        fraction = index - lower
        return values[lower] * (1 - fraction) + values[upper] * fraction

    paired = {
        "target": ACTION,
        "baseline": CONSTRAINED,
        "independent_unit": "scenario_seed_mean_across_repeated_samples",
        "unit_count": len(deltas),
        "f1_delta_mean": round(statistics.fmean(deltas), 4),
        "f1_delta_paired_bootstrap_95ci": [
            round(percentile(bootstrap_means, 0.025), 4),
            round(percentile(bootstrap_means, 0.975), 4),
        ],
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "wins_ties_losses": {
            "wins": sum(delta > 1e-12 for delta in deltas),
            "ties": sum(abs(delta) <= 1e-12 for delta in deltas),
            "losses": sum(delta < -1e-12 for delta in deltas),
        },
    }
    family_delta_means = [
        statistics.fmean(
            action_by_unit[(scenario, seed)]
            - constrained_by_unit[(scenario, seed)]
            for seed in MATCHED_SEEDS
        )
        for scenario in SCENARIOS
    ]
    family_rng = random.Random(BOOTSTRAP_SEED)
    family_bootstrap_means = sorted(
        statistics.fmean(
            family_rng.choices(family_delta_means, k=len(family_delta_means))
        )
        for _ in range(BOOTSTRAP_DRAWS)
    )
    paired["f1_delta_family_clustered_bootstrap_95ci"] = [
        round(percentile(family_bootstrap_means, 0.025), 4),
        round(percentile(family_bootstrap_means, 0.975), 4),
    ]
    paired["family_cluster_count"] = len(SCENARIOS)
    paired["family_cluster_definition"] = (
        "scenario_family_with_three_seed_rows_preserved"
    )
    if paired["f1_delta_mean"] != -0.0384 or paired[
        "f1_delta_paired_bootstrap_95ci"
    ] != [-0.1019, 0.0268]:
        raise SystemExit(f"frozen paired comparison mismatch: {paired}")

    family: dict[str, dict[str, float]] = {}
    for scenario in SCENARIOS:
        family[scenario] = {
            CONSTRAINED: statistics.fmean(
                row["f1"]
                for row in matched_constrained
                if row["scenario"] == scenario
            ),
            HYBRID: statistics.fmean(
                row["f1"]
                for row in online
                if row["scenario"] == scenario and row["reducer"] == HYBRID
            ),
            ACTION: statistics.fmean(
                row["f1"]
                for row in online
                if row["scenario"] == scenario and row["reducer"] == ACTION
            ),
        }
    return {
        "status": "working-diagnostic-not-final-submission-figure",
        "comparison_regime": {
            "legacy_action_implementation": "merge-only semantic-reduce/v1",
            "legacy_action_h0": "semantic-graph",
            "hybrid_role": "comparison and configured fallback; not action H0",
            "constrained_permission": "full-evidence global reclustering",
            "fair_shared_catalog_peer_comparison": False,
        },
        "evidence_labels": {
            "offline_matrix": "simulation/model",
            "online_matrix": "real-online",
            "figure": "derived-artifact",
        },
        "units": {
            "offline_per_reducer": 90,
            "matched_per_reducer": 27,
            "online_repeats_per_unit": 5,
        },
        "aggregate_f1": {key: round(value, 6) for key, value in aggregate.items()},
        "paired_action_vs_constrained": paired,
        "family_f1": {
            scenario: {key: round(value, 6) for key, value in values.items()}
            for scenario, values in family.items()
        },
    }


def _jitter(identity: str) -> float:
    raw = int(hashlib.sha256(identity.encode("utf-8")).hexdigest()[:8], 16)
    return ((raw % 2001) / 1000.0 - 1.0) * 0.17


def _panel_a(offline: list[dict[str, Any]], summary: dict[str, Any]) -> list[str]:
    x0, y0, width, height = 1.12, 0.70, 7.10, 4.25
    lines = [
        f"\\node[font=\\bfseries\\normalsize] at ({x0 - 0.36:.2f},{y0 + height + 0.30:.2f}) {{a}};",
        f"\\node[font=\\normalsize] at ({x0 + width / 2:.2f},{y0 + height + 0.30:.2f}) {{Controlled matrix (90 units/method)}};",
    ]
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = y0 + height * tick
        lines.extend(
            [
                f"\\draw[gray!25,densely dashed,line width=0.25pt] ({x0:.2f},{y:.3f}) -- ({x0 + width:.2f},{y:.3f});",
                f"\\node[anchor=east,font=\\normalsize] at ({x0 - 0.10:.2f},{y:.3f}) {{{tick:.2f}}};",
            ]
        )
    lines.extend(
        [
            f"\\draw[thick] ({x0:.2f},{y0:.2f}) -- ({x0:.2f},{y0 + height:.2f});",
            f"\\node[rotate=90,font=\\normalsize] at ({x0 - 0.78:.2f},{y0 + height / 2:.2f}) {{F1}};",
        ]
    )
    spacing = width / len(PANEL_A_REDUCERS)
    for index, reducer in enumerate(PANEL_A_REDUCERS):
        x = x0 + spacing * (index + 0.5)
        rows = [row for row in offline if row["reducer"] == reducer]
        for row in rows:
            point_x = x + _jitter(f"{reducer}/{row['scenario']}/{row['seed']}")
            point_y = y0 + height * row["f1"]
            lines.append(
                f"\\fill[blue!45,opacity=0.42] ({point_x:.3f},{point_y:.3f}) circle (0.55pt);"
            )
        mean_y = y0 + height * summary["aggregate_f1"][reducer]
        lines.extend(
            [
                f"\\draw[black,line width=1.25pt] ({x - 0.30:.3f},{mean_y:.3f}) -- ({x + 0.30:.3f},{mean_y:.3f});",
                f"\\node[anchor=north,align=center,font=\\normalsize] at ({x:.3f},{y0 - 0.10:.3f}) {{{DISPLAY[reducer]}}};",
                f"\\node[anchor=south,font=\\normalsize] at ({x:.3f},{mean_y + 0.06:.3f}) {{{summary['aggregate_f1'][reducer]:.4f}}};",
            ]
        )
    return lines


def _panel_b(summary: dict[str, Any]) -> list[str]:
    x0, y0, width, row_gap = 10.62, 0.70, 7.45, 0.47
    height = row_gap * (len(SCENARIOS) - 1)
    lines = [
        f"\\node[font=\\bfseries\\normalsize] at ({x0 - 2.00:.2f},{y0 + height + 0.62:.2f}) {{b}};",
        f"\\node[font=\\normalsize] at ({x0 + width / 2:.2f},{y0 + height + 0.62:.2f}) {{Matched three-seed family means}};",
    ]
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = x0 + width * tick
        lines.extend(
            [
                f"\\draw[gray!25,densely dashed,line width=0.25pt] ({x:.3f},{y0 - 0.15:.2f}) -- ({x:.3f},{y0 + height + 0.15:.2f});",
                f"\\node[anchor=north,font=\\normalsize] at ({x:.3f},{y0 - 0.20:.2f}) {{{tick:.2f}}};",
            ]
        )
    for index, scenario in enumerate(reversed(SCENARIOS)):
        y = y0 + row_gap * index
        lines.append(
            f"\\node[anchor=east,font=\\normalsize] at ({x0 - 0.13:.2f},{y:.3f}) {{{SCENARIO_DISPLAY[scenario]}}};"
        )
        values = summary["family_f1"][scenario]
        for reducer, shape, color, fill in (
            (HYBRID, "circle", "gray!65", "white"),
            (CONSTRAINED, "rectangle", "blue!70!black", "blue!70!black"),
            (ACTION, "circle", "orange!90!black", "orange!90!black"),
        ):
            x = x0 + width * values[reducer]
            lines.append(
                f"\\node[draw={color},fill={fill},{shape},inner sep=1.45pt] at ({x:.3f},{y:.3f}) {{}};"
            )
    legend_y = y0 + height + 0.27
    for index, (reducer, shape, color, fill) in enumerate(
        (
            (HYBRID, "circle", "gray!65", "white"),
            (CONSTRAINED, "rectangle", "blue!70!black", "blue!70!black"),
            (ACTION, "circle", "orange!90!black", "orange!90!black"),
        )
    ):
        legend_x = x0 + 0.25 + index * 2.40
        lines.extend(
            [
                f"\\node[draw={color},fill={fill},{shape},inner sep=1.45pt] at ({legend_x:.3f},{legend_y:.3f}) {{}};",
                f"\\node[anchor=west,font=\\normalsize] at ({legend_x + 0.14:.3f},{legend_y:.3f}) {{{DISPLAY[reducer]}}};",
            ]
        )
    lines.append(
        f"\\node[font=\\normalsize] at ({x0 + width / 2:.2f},{y0 - 0.62:.2f}) {{Mean F1}};"
    )
    return lines


def render(offline: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    lines = [
        "% Generated by tools/benchmark_carrier/plot_semantic_mapreduce_baseline_comparison.py",
        "% Inputs: clean controlled summary.csv and frozen real-online case_seed_summary.csv.",
        "% Working diagnostic: legacy merge-only action and constrained reference have unequal permissions.",
        "\\begin{tikzpicture}[x=1cm,y=1cm]",
        *_panel_a(offline, summary),
        *_panel_b(summary),
        "\\end{tikzpicture}",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    offline, online = load_evidence(args.offline_summary, args.online_case_summary)
    summary = summarize(offline, online)
    summary["source_files"] = {
        "controlled_matrix_summary_csv": {
            "sha256": _sha256(args.offline_summary),
            "evidence_label": "simulation/model",
        },
        "historical_online_case_seed_summary_csv": {
            "sha256": _sha256(args.online_case_summary),
            "evidence_label": "real-online",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(offline, summary), encoding="utf-8")
    if args.data_output:
        args.data_output.parent.mkdir(parents=True, exist_ok=True)
        args.data_output.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
