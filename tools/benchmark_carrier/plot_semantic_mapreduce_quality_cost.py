#!/usr/bin/env python3
"""Generate a deterministic TikZ quality/cost figure from frozen summaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ACTION = "llm-pairwise-action-validated"
HYBRID = "hybrid-hint"
EXPECTED = {
    "budget": [4.0, 8.0, 12.0],
    "f1": [0.7791, 0.8645, 0.8571],
    "support": [0.7455, 0.8672, 0.8795],
    "baseline_f1": [0.7801, 0.7801, 0.7801],
    "latency_mean": [19.7565, 102.7286, 120.3391],
    "latency_p95": [104.81, 366.39, 547.21],
    "tokens_mean": [45.7778, 260.8593, 304.1481],
    "tokens_p95": [255.0, 975.0, 1422.0],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--budget-dir",
        action="append",
        required=True,
        help="Directory containing comparison_summary.json and stability_summary.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_point(directory: Path) -> dict[str, float]:
    budget = int(directory.name.rsplit("-", 1)[-1])
    comparison = json.loads((directory / "comparison_summary.json").read_text())
    stability = json.loads((directory / "stability_summary.json").read_text())
    by_reducer = {row["reducer"]: row for row in comparison}
    action = by_reducer[ACTION]
    hybrid = by_reducer[HYBRID]
    action_stability = stability["by_reducer"][ACTION]
    return {
        "budget": float(budget),
        "f1": action["f1_mean"],
        "support": action["support_evidence_recall_mean"],
        "baseline_f1": hybrid["f1_mean"],
        "latency_mean": action["reduce_ms_mean"],
        "latency_p95": action_stability["latency_ms_p95"],
        "tokens_mean": action["total_tokens_mean"],
        "tokens_p95": action_stability["tokens_p95"],
    }


def assert_frozen(points: list[dict[str, float]]) -> None:
    for key, expected in EXPECTED.items():
        actual = [point[key] for point in points]
        if len(actual) != len(expected) or any(
            abs(a - e) > 5e-5 for a, e in zip(actual, expected, strict=True)
        ):
            raise SystemExit(f"frozen-value mismatch for {key}: expected {expected}, got {actual}")


def coords(
    values: list[float], x0: float, y0: float, width: float, height: float, ymax: float
) -> str:
    pieces = []
    for index, value in enumerate(values):
        x = x0 + width * index / 2
        y = y0 + height * value / ymax
        pieces.append(f"({x:.3f},{y:.3f})")
    return " -- ".join(pieces)


def panel(
    *,
    x0: float,
    label: str,
    ylabel: str,
    ymax: float,
    yticks: list[float],
    series: list[tuple[str, list[float], str, str]],
    legend_x: float,
    legend_y: float,
) -> list[str]:
    y0, width, height = 0.65, 4.25, 3.25
    lines = [
        f"\\node[font=\\bfseries\\normalsize] at ({x0 - 0.28:.3f},{y0 + height + 0.32:.3f}) {{{label}}};",
    ]
    for tick in yticks:
        y = y0 + height * tick / ymax
        tick_label = f"{tick:.2f}" if ymax == 1.0 else f"{int(tick)}"
        lines.extend(
            [
                f"\\draw[gray!30, densely dashed, line width=0.25pt] ({x0:.3f},{y:.3f}) -- ({x0 + width:.3f},{y:.3f});",
                f"\\draw ({x0 - 0.07:.3f},{y:.3f}) -- ({x0:.3f},{y:.3f});",
                f"\\node[anchor=east, font=\\normalsize] at ({x0 - 0.10:.3f},{y:.3f}) {{{tick_label}}};",
            ]
        )
    lines.extend(
        [
            f"\\draw[thick] ({x0:.3f},{y0:.3f}) -- ({x0:.3f},{y0 + height:.3f});",
            f"\\draw[thick] ({x0:.3f},{y0:.3f}) -- ({x0 + width:.3f},{y0:.3f});",
        ]
    )
    for index, budget in enumerate((4, 8, 12)):
        x = x0 + width * index / 2
        lines.extend(
            [
                f"\\draw ({x:.3f},{y0:.3f}) -- ({x:.3f},{y0 - 0.07:.3f});",
                f"\\node[anchor=north, font=\\normalsize] at ({x:.3f},{y0 - 0.10:.3f}) {{{budget}}};",
            ]
        )
    lines.extend(
        [
            f"\\node[font=\\normalsize] at ({x0 + width / 2:.3f},{y0 - 0.48:.3f}) {{Candidate budget}};",
            f"\\node[rotate=90, font=\\normalsize] at ({x0 - 0.92:.3f},{y0 + height / 2:.3f}) {{{ylabel}}};",
        ]
    )
    for idx, (name, values, color, pattern) in enumerate(series):
        path = coords(values, x0, y0, width, height, ymax)
        marker = "circle" if idx == 0 else "rectangle"
        lines.extend(
            [
                f"\\draw[{color}, {pattern}, line width=1.0pt] {path};",
                *[
                    f"\\node[draw={color}, fill={color}, {marker}, inner sep=1.35pt] at ({x0 + width * j / 2:.3f},{y0 + height * value / ymax:.3f}) {{}};"
                    for j, value in enumerate(values)
                ],
                f"\\draw[{color}, {pattern}, line width=1.0pt] ({legend_x:.3f},{legend_y - 0.30 * idx:.3f}) -- ({legend_x + 0.40:.3f},{legend_y - 0.30 * idx:.3f});",
                f"\\node[anchor=west, font=\\normalsize] at ({legend_x + 0.47:.3f},{legend_y - 0.30 * idx:.3f}) {{{name}}};",
            ]
        )
    return lines


def main() -> None:
    args = parse_args()
    points = sorted((load_point(Path(p)) for p in args.budget_dir), key=lambda p: p["budget"])
    assert_frozen(points)

    def values(key: str) -> list[float]:
        return [point[key] for point in points]

    lines = [
        "% Generated by tools/benchmark_carrier/plot_semantic_mapreduce_quality_cost.py",
        "% Inputs are frozen comparison_summary.json and stability_summary.json files.",
        "\\begin{tikzpicture}[x=1cm,y=1cm]",
    ]
    lines += panel(
        x0=1.05,
        label="a",
        ylabel="Quality",
        ymax=1.0,
        yticks=[0.0, 0.25, 0.5, 0.75, 1.0],
        series=[
            ("Action F1", values("f1"), "blue!70!black", "solid"),
            ("Support recall", values("support"), "orange!90!black", "dashed"),
            ("Hybrid F1", values("baseline_f1"), "black!65", "dotted"),
        ],
        legend_x=3.25,
        legend_y=1.72,
    )
    lines += panel(
        x0=6.95,
        label="b",
        ylabel="Reducer latency (ms)",
        ymax=600.0,
        yticks=[0, 200, 400, 600],
        series=[
            ("Mean", values("latency_mean"), "blue!70!black", "solid"),
            ("p95", values("latency_p95"), "orange!90!black", "dashed"),
        ],
        legend_x=7.35,
        legend_y=3.62,
    )
    lines += panel(
        x0=12.90,
        label="c",
        ylabel="Tokens per row",
        ymax=1500.0,
        yticks=[0, 500, 1000, 1500],
        series=[
            ("Mean", values("tokens_mean"), "blue!70!black", "solid"),
            ("p95", values("tokens_p95"), "orange!90!black", "dashed"),
        ],
        legend_x=13.30,
        legend_y=3.62,
    )
    lines.append("\\end{tikzpicture}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
