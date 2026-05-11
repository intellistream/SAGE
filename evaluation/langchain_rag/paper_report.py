from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

FRAMEWORK_ORDER = ["langchain_native", "sage"]
FRAMEWORK_LABELS = {
    "langchain_native": "LangChain Native",
    "sage": "SAGE Runtime",
}
FRAMEWORK_COLORS = {
    "langchain_native": "#4e79a7",
    "sage": "#e15759",
}

VARIANT_ORDER = ["direct_generation", "retrieval_only", "full_rag"]
VARIANT_LABELS = {
    "direct_generation": "Direct Generation",
    "retrieval_only": "Retrieval Only",
    "full_rag": "Full RAG",
}
VARIANT_COLORS = {
    "direct_generation": "#1b9e77",
    "retrieval_only": "#d95f02",
    "full_rag": "#7570b3",
}
STAGE_ORDER = ["source", "retrieval", "memory", "generation", "sink"]
STAGE_COLORS = {
    "source": "#4e79a7",
    "retrieval": "#f28e2b",
    "memory": "#59a14f",
    "generation": "#e15759",
    "sink": "#76b7b2",
}


def _configure_plot_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "figure.titlesize": 13,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linestyle": "--",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.bbox": "tight",
        }
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _report_output_dir(base_dir: Path, output_dir: str | None) -> Path:
    if output_dir:
        target = Path(output_dir)
        if not target.is_absolute():
            target = base_dir / target
        return target
    timestamp = datetime.now(timezone.utc).strftime("paper-report-%Y%m%d-%H%M%S")
    return base_dir / timestamp


def _collect_batch_dirs(batch_root: Path, batch_ids: list[str] | None) -> list[Path]:
    if batch_ids:
        return [batch_root / batch_id for batch_id in batch_ids]
    return sorted(
        path for path in batch_root.iterdir() if path.is_dir() and path.name.startswith("batch-")
    )


def _load_frames(
    batch_dirs: list[Path],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    overall_records: list[dict[str, Any]] = []
    workload_records: list[dict[str, Any]] = []
    stage_records: list[dict[str, Any]] = []
    batch_records: list[dict[str, Any]] = []

    for batch_dir in batch_dirs:
        manifest = _load_json(batch_dir / "manifest.json")
        by_variant = _load_json(batch_dir / "comparison" / "by_variant.json")
        matrix = _load_json(batch_dir / "comparison" / "workload_variant_matrix.json")
        stage_latency = _load_json(batch_dir / "comparison" / "stage_latency_by_variant.json")
        fairness = _load_json(batch_dir / "comparison" / "fairness_audit.json")

        batch_records.append(
            {
                "batch_id": manifest["batch_id"],
                "seed": int(manifest["seed"]),
                "result_root": manifest["result_root"],
                "frameworks": ",".join(manifest.get("frameworks") or ["sage"]),
                "variant_execution_policy": manifest["variant_execution_policy"],
                "variant_aggregate_method": fairness["variant_aggregate_method"],
                "stage_aggregate_method": fairness["stage_aggregate_method"],
                "backend": fairness["generation_backend_policy"]["expected_backend"],
                "workload_count": len(manifest["workloads"]),
                "run_count": int(manifest["run_count"]),
            }
        )

        for record in by_variant["variants"]:
            overall_records.append(
                {
                    "batch_id": manifest["batch_id"],
                    "seed": int(manifest["seed"]),
                    **record,
                }
            )

        for row in matrix["rows"]:
            workload_records.append(
                {
                    "batch_id": manifest["batch_id"],
                    "seed": int(manifest["seed"]),
                    **row,
                }
            )

        for variant_name, payload in stage_latency["variants"].items():
            del variant_name
            for stage_name in STAGE_ORDER:
                metrics = payload[stage_name]
                stage_records.append(
                    {
                        "batch_id": manifest["batch_id"],
                        "seed": int(manifest["seed"]),
                        "framework_name": payload.get("framework_name", "sage"),
                        "variant_name": payload["variant_name"],
                        "stage": stage_name,
                        "avg_ms": float(metrics["avg_ms"]),
                        "macro_avg_ms": float(metrics["macro_avg_ms"]),
                        "total_query_count": int(payload["total_query_count"]),
                    }
                )

    return (
        pd.DataFrame(batch_records),
        pd.DataFrame(overall_records),
        pd.DataFrame(workload_records),
        pd.DataFrame(stage_records),
    )


def _variant_summary(overall_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        overall_df.groupby(["framework_name", "variant_name"], as_index=False)
        .agg(
            mean_throughput_qps=("avg_throughput_qps", "mean"),
            std_throughput_qps=("avg_throughput_qps", "std"),
            mean_end_to_end_ms=("avg_end_to_end_ms", "mean"),
            std_end_to_end_ms=("avg_end_to_end_ms", "std"),
            mean_retrieval_ms=("avg_retrieval_ms", "mean"),
            std_retrieval_ms=("avg_retrieval_ms", "std"),
            mean_memory_ms=("avg_memory_ms", "mean"),
            std_memory_ms=("avg_memory_ms", "std"),
            mean_generation_ms=("avg_generation_ms", "mean"),
            std_generation_ms=("avg_generation_ms", "std"),
            mean_sink_ms=("avg_sink_ms", "mean"),
            std_sink_ms=("avg_sink_ms", "std"),
            seeds=("seed", "nunique"),
            total_query_count=("total_query_count", "mean"),
        )
        .fillna(0.0)
    )
    summary["framework_order"] = summary["framework_name"].map(
        {name: index for index, name in enumerate(FRAMEWORK_ORDER)}
    )
    summary["variant_order"] = summary["variant_name"].map(
        {name: index for index, name in enumerate(VARIANT_ORDER)}
    )
    return summary.sort_values(["variant_order", "framework_order"]).drop(
        columns=["variant_order", "framework_order"]
    )


def _stage_summary(stage_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        stage_df.groupby(["framework_name", "variant_name", "stage"], as_index=False)
        .agg(
            mean_avg_ms=("avg_ms", "mean"),
            std_avg_ms=("avg_ms", "std"),
            mean_macro_avg_ms=("macro_avg_ms", "mean"),
            std_macro_avg_ms=("macro_avg_ms", "std"),
            seeds=("seed", "nunique"),
        )
        .fillna(0.0)
    )
    summary["framework_order"] = summary["framework_name"].map(
        {name: index for index, name in enumerate(FRAMEWORK_ORDER)}
    )
    summary["variant_order"] = summary["variant_name"].map(
        {name: index for index, name in enumerate(VARIANT_ORDER)}
    )
    summary["stage_order"] = summary["stage"].map(
        {name: index for index, name in enumerate(STAGE_ORDER)}
    )
    return summary.sort_values(["framework_order", "variant_order", "stage_order"]).drop(
        columns=["framework_order", "variant_order", "stage_order"]
    )


def _workload_summary(workload_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        workload_df.groupby(
            ["workload_name", "family_label", "framework_name", "variant_name"], as_index=False
        )
        .agg(
            mean_query_count=("query_count", "mean"),
            mean_throughput_qps=("throughput_qps", "mean"),
            std_throughput_qps=("throughput_qps", "std"),
            mean_end_to_end_ms=("end_to_end_avg_ms", "mean"),
            std_end_to_end_ms=("end_to_end_avg_ms", "std"),
            mean_retrieval_ms=("retrieval_avg_ms", "mean"),
            mean_memory_ms=("memory_avg_ms", "mean"),
            mean_generation_ms=("generation_avg_ms", "mean"),
            mean_document_count=("document_count", "mean"),
            mean_chunk_count=("chunk_count", "mean"),
            seeds=("seed", "nunique"),
        )
        .fillna(0.0)
    )
    summary["framework_order"] = summary["framework_name"].map(
        {name: index for index, name in enumerate(FRAMEWORK_ORDER)}
    )
    summary["variant_order"] = summary["variant_name"].map(
        {name: index for index, name in enumerate(VARIANT_ORDER)}
    )
    return summary.sort_values(["workload_name", "framework_order", "variant_order"]).drop(
        columns=["framework_order", "variant_order"]
    )


def _overhead_summary(workload_summary: pd.DataFrame) -> pd.DataFrame:
    pivot = workload_summary.pivot(
        index=["workload_name", "framework_name"],
        columns="variant_name",
        values="mean_end_to_end_ms",
    )
    labels = workload_summary.drop_duplicates(["workload_name", "framework_name"]).set_index(
        ["workload_name", "framework_name"]
    )["family_label"]
    fallback_labels = pd.Series([index[0] for index in pivot.index], index=pivot.index)
    overhead = pd.DataFrame(
        {
            "workload_name": [index[0] for index in pivot.index],
            "framework_name": [index[1] for index in pivot.index],
            "family_label": labels.reindex(pivot.index).fillna(fallback_labels),
            "retrieval_only_vs_direct": pivot["retrieval_only"] / pivot["direct_generation"],
            "full_rag_vs_direct": pivot["full_rag"] / pivot["direct_generation"],
        }
    ).reset_index(drop=True)
    return overhead.sort_values("full_rag_vs_direct", ascending=False)


def _save_dataframe(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    fig.savefig(output_dir / f"{stem}.pdf")
    fig.savefig(output_dir / f"{stem}.png", dpi=300)
    plt.close(fig)


def _statistics_caption(seed_count: int) -> str:
    return "single-seed observation" if seed_count <= 1 else "mean ± std over seeds"


def _format_value_with_spread(
    mean_value: float, std_value: float, seed_count: int, unit: str
) -> str:
    if seed_count <= 1:
        return f"{mean_value:.2f} {unit}".strip()
    return f"{mean_value:.2f} +/- {std_value:.2f} {unit}".strip()


def _available_frameworks(frame: pd.DataFrame) -> list[str]:
    frameworks = [name for name in FRAMEWORK_ORDER if name in set(frame["framework_name"].tolist())]
    return frameworks or ["sage"]


def _plot_overall_variant_metrics(
    variant_summary: pd.DataFrame, output_dir: Path, seed_count: int
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6))
    frameworks = _available_frameworks(variant_summary)
    labels = [VARIANT_LABELS[name] for name in VARIANT_ORDER]
    x = np.arange(len(labels))
    width = 0.8 / max(len(frameworks), 1)

    for index, framework_name in enumerate(frameworks):
        ordered = (
            variant_summary[variant_summary["framework_name"] == framework_name]
            .set_index("variant_name")
            .reindex(VARIANT_ORDER)
            .reset_index()
        )
        offset = (index - (len(frameworks) - 1) / 2.0) * width
        axes[0].bar(
            x + offset,
            ordered["mean_throughput_qps"],
            yerr=ordered["std_throughput_qps"],
            width=width,
            color=FRAMEWORK_COLORS[framework_name],
            capsize=4,
            label=FRAMEWORK_LABELS[framework_name],
        )
    axes[0].set_xticks(x, labels, rotation=12)
    axes[0].set_ylabel("Throughput (queries/s)")
    axes[0].set_title("Overall Throughput")
    axes[0].legend(frameon=False)

    for index, framework_name in enumerate(frameworks):
        ordered = (
            variant_summary[variant_summary["framework_name"] == framework_name]
            .set_index("variant_name")
            .reindex(VARIANT_ORDER)
            .reset_index()
        )
        offset = (index - (len(frameworks) - 1) / 2.0) * width
        axes[1].bar(
            x + offset,
            ordered["mean_end_to_end_ms"],
            yerr=ordered["std_end_to_end_ms"],
            width=width,
            color=FRAMEWORK_COLORS[framework_name],
            capsize=4,
            label=FRAMEWORK_LABELS[framework_name],
        )
    axes[1].set_xticks(x, labels, rotation=12)
    axes[1].set_ylabel("End-to-End Latency (ms)")
    axes[1].set_title("Overall End-to-End Latency")

    fig.suptitle(f"LangChain Native vs SAGE Runtime ({_statistics_caption(seed_count)})")
    _save_figure(fig, output_dir, "overall_variant_metrics")


def _plot_stage_breakdown(stage_summary: pd.DataFrame, output_dir: Path) -> None:
    frameworks = _available_frameworks(stage_summary)
    fig, axes = plt.subplots(
        1, len(frameworks), figsize=(4.8 * len(frameworks), 4.0), squeeze=False
    )
    for axis, framework_name in zip(axes[0], frameworks):
        ordered = stage_summary[stage_summary["framework_name"] == framework_name].copy()
        x = np.arange(len(VARIANT_ORDER))
        bottoms = np.zeros(len(VARIANT_ORDER))
        for stage_name in STAGE_ORDER:
            stage_values = (
                ordered[ordered["stage"] == stage_name]
                .set_index("variant_name")
                .reindex(VARIANT_ORDER)["mean_avg_ms"]
                .to_numpy()
            )
            axis.bar(
                x,
                stage_values,
                bottom=bottoms,
                color=STAGE_COLORS[stage_name],
                label=stage_name.capitalize(),
            )
            bottoms += stage_values
        axis.set_xticks(x, [VARIANT_LABELS[name] for name in VARIANT_ORDER], rotation=12)
        axis.set_ylabel("Latency Contribution (ms)")
        axis.set_title(FRAMEWORK_LABELS[framework_name])
    axes[0][0].legend(ncols=3, frameon=False, loc="upper center", bbox_to_anchor=(1.1, 1.18))
    fig.suptitle("Stage Latency Breakdown by Framework")
    _save_figure(fig, output_dir, "stage_latency_breakdown")


def _plot_workload_latency_heatmap(workload_summary: pd.DataFrame, output_dir: Path) -> None:
    working = workload_summary.copy()
    working["column_name"] = working.apply(
        lambda row: (
            f"{FRAMEWORK_LABELS[row['framework_name']]}\n{VARIANT_LABELS[row['variant_name']]}"
        ),
        axis=1,
    )
    pivot = working.pivot(index="family_label", columns="column_name", values="mean_end_to_end_ms")
    ordered_columns = [
        f"{FRAMEWORK_LABELS[framework_name]}\n{VARIANT_LABELS[variant_name]}"
        for framework_name in _available_frameworks(working)
        for variant_name in VARIANT_ORDER
        if f"{FRAMEWORK_LABELS[framework_name]}\n{VARIANT_LABELS[variant_name]}" in pivot.columns
    ]
    workload_order = pivot[ordered_columns[-1]].sort_values(ascending=False).index.tolist()
    pivot = pivot.reindex(index=workload_order, columns=ordered_columns)

    fig, ax = plt.subplots(figsize=(7.6, 5.8))
    image = ax.imshow(pivot.to_numpy(), aspect="auto", cmap="YlOrRd")
    ax.set_xticks(np.arange(len(ordered_columns)), ordered_columns, rotation=25)
    ax.set_yticks(np.arange(len(workload_order)), workload_order)
    ax.set_title("Workload-Level End-to-End Latency Heatmap")
    ax.set_xlabel("Variant")
    ax.set_ylabel("Workload")

    for row_index in range(pivot.shape[0]):
        for column_index in range(pivot.shape[1]):
            value = pivot.iat[row_index, column_index]
            ax.text(column_index, row_index, f"{value:.0f}", ha="center", va="center", fontsize=7)

    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("Latency (ms)")
    _save_figure(fig, output_dir, "workload_latency_heatmap")


def _plot_relative_overhead(overhead_summary: pd.DataFrame, output_dir: Path) -> None:
    frameworks = _available_frameworks(overhead_summary)
    fig, axes = plt.subplots(
        1, len(frameworks), figsize=(4.6 * len(frameworks), 5.4), squeeze=False
    )
    for axis, framework_name in zip(axes[0], frameworks):
        frame = overhead_summary[overhead_summary["framework_name"] == framework_name].sort_values(
            "full_rag_vs_direct",
            ascending=False,
        )
        y = np.arange(len(frame))
        axis.barh(
            y + 0.18,
            frame["full_rag_vs_direct"],
            height=0.34,
            color=VARIANT_COLORS["full_rag"],
            label="Full RAG / Direct",
        )
        axis.barh(
            y - 0.18,
            frame["retrieval_only_vs_direct"],
            height=0.34,
            color=VARIANT_COLORS["retrieval_only"],
            label="Retrieval Only / Direct",
        )
        axis.axvline(1.0, color="#333333", linewidth=1.0, linestyle=":")
        axis.set_yticks(y, frame["family_label"])
        axis.set_xlabel("Latency Ratio")
        axis.set_title(FRAMEWORK_LABELS[framework_name])
    axes[0][0].legend(frameon=False)
    fig.suptitle("Latency Overhead Relative to Direct Generation")
    _save_figure(fig, output_dir, "relative_latency_overhead")


def _write_latex_table(variant_summary: pd.DataFrame, output_path: Path, seed_count: int) -> None:
    ordered = variant_summary.copy()
    ordered["framework_order"] = ordered["framework_name"].map(
        {name: index for index, name in enumerate(FRAMEWORK_ORDER)}
    )
    ordered["variant_order"] = ordered["variant_name"].map(
        {name: index for index, name in enumerate(VARIANT_ORDER)}
    )
    ordered = ordered.sort_values(["framework_order", "variant_order"]).drop(
        columns=["framework_order", "variant_order"]
    )
    latex_newline = r"\\"
    lines = [
        "\\begin{tabular}{llrr}",
        "\\toprule",
        f"Framework & Variant & Throughput (q/s) & End-to-end latency (ms) {latex_newline}",
        "\\midrule",
    ]
    for _, row in ordered.iterrows():
        throughput_cell = _format_value_with_spread(
            float(row["mean_throughput_qps"]),
            float(row["std_throughput_qps"]),
            seed_count,
            "",
        ).strip()
        latency_cell = _format_value_with_spread(
            float(row["mean_end_to_end_ms"]),
            float(row["std_end_to_end_ms"]),
            seed_count,
            "",
        ).strip()
        lines.append(
            f"{FRAMEWORK_LABELS[row['framework_name']]} & "
            f"{VARIANT_LABELS[row['variant_name']]} & "
            f"{throughput_cell} & "
            f"{latency_cell} {latex_newline}"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_markdown_summary(
    batch_df: pd.DataFrame,
    variant_summary: pd.DataFrame,
    overhead_summary: pd.DataFrame,
    output_path: Path,
) -> None:
    seed_count = int(batch_df["seed"].nunique())
    fastest = variant_summary.sort_values("mean_throughput_qps", ascending=False).iloc[0]
    lowest_latency = variant_summary.sort_values("mean_end_to_end_ms", ascending=True).iloc[0]
    hardest = overhead_summary.iloc[0]

    lines = [
        "# LangChain + SAGE RAG Paper Report",
        "",
        "## Experimental Setup",
        "",
        f"- Batches: {len(batch_df)}",
        f"- Seeds: {', '.join(str(value) for value in sorted(batch_df['seed'].tolist()))}",
        f"- Backend: {batch_df['backend'].iloc[0]}",
        f"- Frameworks: {batch_df['frameworks'].iloc[0]}",
        f"- Variant execution policy: {batch_df['variant_execution_policy'].iloc[0]}",
        f"- Aggregate method: {batch_df['variant_aggregate_method'].iloc[0]}",
        f"- Statistics view: {_statistics_caption(seed_count)}",
        "",
        "## Key Findings",
        "",
        f"- Highest throughput: {FRAMEWORK_LABELS[fastest['framework_name']]} / {VARIANT_LABELS[fastest['variant_name']]} at {_format_value_with_spread(float(fastest['mean_throughput_qps']), float(fastest['std_throughput_qps']), seed_count, 'q/s')}.",
        f"- Lowest end-to-end latency: {FRAMEWORK_LABELS[lowest_latency['framework_name']]} / {VARIANT_LABELS[lowest_latency['variant_name']]} at {_format_value_with_spread(float(lowest_latency['mean_end_to_end_ms']), float(lowest_latency['std_end_to_end_ms']), seed_count, 'ms')}.",
        f"- Largest Full RAG latency overhead appears on {FRAMEWORK_LABELS[hardest['framework_name']]} / {hardest['family_label']} with a {hardest['full_rag_vs_direct']:.2f}x ratio relative to direct generation.",
        "",
        "## Artifacts",
        "",
        "- overall_variant_metrics.pdf / .png",
        "- stage_latency_breakdown.pdf / .png",
        "- workload_latency_heatmap.pdf / .png",
        "- relative_latency_overhead.pdf / .png",
        "- variant_summary.csv",
        "- workload_summary.csv",
        "- stage_summary.csv",
        "- variant_summary.tex",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_paper_report(
    batch_root: str | Path,
    *,
    output_dir: str | None = None,
    batch_ids: list[str] | None = None,
) -> Path:
    _configure_plot_style()
    batch_root_path = Path(batch_root)
    batch_dirs = _collect_batch_dirs(batch_root_path, batch_ids)
    if not batch_dirs:
        raise ValueError(f"no batch directories found under {batch_root_path}")

    report_dir = _report_output_dir(batch_root_path, output_dir)
    figures_dir = report_dir / "figures"
    tables_dir = report_dir / "tables"
    figures_dir.mkdir(parents=True, exist_ok=False)
    tables_dir.mkdir(parents=True, exist_ok=False)

    batch_df, overall_df, workload_df, stage_df = _load_frames(batch_dirs)
    seed_count = int(batch_df["seed"].nunique())
    variant_summary = _variant_summary(overall_df)
    workload_summary = _workload_summary(workload_df)
    stage_summary = _stage_summary(stage_df)
    overhead_summary = _overhead_summary(workload_summary)

    _save_dataframe(batch_df, tables_dir / "batch_inventory.csv")
    _save_dataframe(overall_df, tables_dir / "overall_seed_records.csv")
    _save_dataframe(workload_df, tables_dir / "workload_seed_records.csv")
    _save_dataframe(stage_df, tables_dir / "stage_seed_records.csv")
    _save_dataframe(variant_summary, tables_dir / "variant_summary.csv")
    _save_dataframe(workload_summary, tables_dir / "workload_summary.csv")
    _save_dataframe(stage_summary, tables_dir / "stage_summary.csv")
    _save_dataframe(overhead_summary, tables_dir / "overhead_summary.csv")

    _write_latex_table(variant_summary, tables_dir / "variant_summary.tex", seed_count)
    _write_markdown_summary(batch_df, variant_summary, overhead_summary, report_dir / "report.md")

    _plot_overall_variant_metrics(variant_summary, figures_dir, seed_count)
    _plot_stage_breakdown(stage_summary, figures_dir)
    _plot_workload_latency_heatmap(workload_summary, figures_dir)
    _plot_relative_overhead(overhead_summary, figures_dir)

    report_manifest = {
        "batch_root": str(batch_root_path),
        "batch_ids": batch_df["batch_id"].tolist(),
        "seeds": sorted(int(value) for value in batch_df["seed"].tolist()),
        "backend": batch_df["backend"].iloc[0],
        "figure_directory": str(figures_dir),
        "table_directory": str(tables_dir),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (report_dir / "report_manifest.json").write_text(
        json.dumps(report_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate paper-ready tables and figures from LangChain RAG batch outputs."
    )
    parser.add_argument("--batch-root", required=True, help="Directory containing batch-* outputs.")
    parser.add_argument("--output-dir", default=None, help="Optional report output directory.")
    parser.add_argument(
        "--batch-ids", default=None, help="Optional comma-separated batch IDs to include."
    )
    args = parser.parse_args()

    batch_ids = None
    if args.batch_ids:
        batch_ids = [value.strip() for value in args.batch_ids.split(",") if value.strip()]

    report_dir = generate_paper_report(
        args.batch_root,
        output_dir=args.output_dir,
        batch_ids=batch_ids,
    )
    print(report_dir)
    return 0


__all__ = ["generate_paper_report", "main"]
