"""
LaTeX 表格导出模块
==================

为 ICML 论文自动生成 LaTeX 格式的结果表格。

提供的功能：
- 主结果表格生成 (多算法、多数据集)
- 消融实验表格
- 统计显著性表格
- 压缩案例展示表格

格式要求：
- 使用 booktabs 包 (\\toprule, \\midrule, \\bottomrule)
- 最佳值加粗 (\\textbf)
- 显著性标记: $^{*}$ (p<0.05), $^{**}$ (p<0.01), $^{***}$ (p<0.001)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from sage.benchmark.benchmark_refiner.analysis.statistical import (
    bootstrap_confidence_interval,
    cohens_d,
    paired_t_test,
)
from sage.benchmark.benchmark_refiner.experiments.base_experiment import (
    AlgorithmMetrics,
)


@dataclass
class TableConfig:
    """LaTeX 表格配置"""

    caption: str = ""
    label: str = ""
    position: str = "t"  # t, b, h, p
    centering: bool = True
    font_size: str | None = None  # small, footnotesize, scriptsize
    column_sep: str = "|"  # 列分隔符
    use_booktabs: bool = True
    include_notes: bool = True


def _escape_latex(text: str) -> str:
    """
    转义 LaTeX 特殊字符

    Args:
        text: 原始文本

    Returns:
        转义后的文本
    """
    # 特殊字符映射
    special_chars = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\^{}",
        "\\": r"\textbackslash{}",
    }
    for char, escaped in special_chars.items():
        text = text.replace(char, escaped)
    return text


def _format_number(value: float, decimal_places: int = 3) -> str:
    """
    格式化数值

    Args:
        value: 数值
        decimal_places: 小数位数

    Returns:
        格式化后的字符串
    """
    if np.isnan(value) or np.isinf(value):
        return "-"
    return f"{value:.{decimal_places}f}"


def _get_significance_marker(p_value: float | None) -> str:
    """
    根据 p 值获取显著性标记

    Args:
        p_value: p 值

    Returns:
        显著性标记: $^{***}$, $^{**}$, $^{*}$, 或空字符串
    """
    if p_value is None:
        return ""
    if p_value < 0.001:
        return "$^{***}$"
    elif p_value < 0.01:
        return "$^{**}$"
    elif p_value < 0.05:
        return "$^{*}$"
    return ""


def _format_method_name(name: str) -> str:
    """
    格式化算法名称为 LaTeX 友好格式

    Args:
        name: 原始名称

    Returns:
        格式化后的名称
    """
    name_mapping = {
        "baseline": "Baseline",
        "longrefiner": "LongRefiner",
        "reform": "REFORM",
        "provence": "Provence",
        "longllmlingua": "LongLLMLingua",
        "llmlingua2": "LLMLingua-2",
    }
    return name_mapping.get(name.lower(), _escape_latex(name))


def _format_dataset_name(name: str) -> str:
    """
    格式化数据集名称

    Args:
        name: 原始名称

    Returns:
        格式化后的名称
    """
    name_mapping = {
        "nq": "NQ",
        "triviaqa": "TriviaQA",
        "hotpotqa": "HotpotQA",
        "2wikimultihopqa": "2WikiMQA",
        "musique": "Musique",
        "asqa": "ASQA",
        "popqa": "PopQA",
        "webq": "WebQ",
    }
    return name_mapping.get(name.lower(), _escape_latex(name))


def generate_main_results_table(
    results: dict[str, dict[str, AlgorithmMetrics]],
    baseline: str = "baseline",
    metrics: list[str] | None = None,
    include_significance: bool = True,
    raw_results: dict[str, dict[str, list[dict[str, Any]]]] | None = None,
    config: TableConfig | None = None,
) -> str:
    """
    生成主实验结果表格

    Args:
        results: 嵌套字典 {dataset: {algorithm: AlgorithmMetrics}}
        baseline: 基线算法名称
        metrics: 要展示的指标列表，默认 ["f1", "compression_rate", "total_time"]
        include_significance: 是否包含显著性标记
        raw_results: 原始样本结果，用于计算 p 值
                    格式: {dataset: {algorithm: [{"f1": float, ...}, ...]}}
        config: 表格配置

    Returns:
        LaTeX 表格字符串

    Example:
        >>> results = {
        ...     "nq": {
        ...         "baseline": AlgorithmMetrics(algorithm="baseline", avg_f1=0.35, ...),
        ...         "longrefiner": AlgorithmMetrics(algorithm="longrefiner", avg_f1=0.38, ...),
        ...     },
        ...     "hotpotqa": {...},
        ... }
        >>> latex = generate_main_results_table(results)
    """
    if metrics is None:
        metrics = ["f1", "compression_rate", "total_time"]

    if config is None:
        config = TableConfig(
            caption="Main Results on RAG Benchmarks. Best results are in \\textbf{bold}. "
            "$^{*}$/$^{**}$/$^{***}$ indicate statistical significance at p<0.05/0.01/0.001.",
            label="tab:main_results",
        )

    datasets = list(results.keys())
    algorithms = list(results[datasets[0]].keys()) if datasets else []

    # 指标显示名称和方向 (↑ 越大越好, ↓ 越小越好)
    metric_info = {
        "f1": ("F1 $\\uparrow$", "max", 3),
        "compression_rate": ("Comp. $\\uparrow$", "max", 1),
        "total_time": ("Time (s) $\\downarrow$", "min", 2),
        "recall": ("Recall $\\uparrow$", "max", 3),
        "rouge_l": ("ROUGE-L $\\uparrow$", "max", 3),
        "accuracy": ("Acc. $\\uparrow$", "max", 3),
    }

    # 构建表头
    n_metrics = len(metrics)
    n_datasets = len(datasets)

    # 列规格
    col_spec = "l" + ("|" + "c" * n_metrics) * n_datasets
    if not config.use_booktabs:
        col_spec = col_spec.replace("|", " ")

    lines = []

    # 表格开始
    lines.append(f"\\begin{{table}}[{config.position}]")
    if config.centering:
        lines.append("\\centering")
    if config.font_size:
        lines.append(f"\\{config.font_size}")
    if config.caption:
        lines.append(f"\\caption{{{config.caption}}}")
    if config.label:
        lines.append(f"\\label{{{config.label}}}")
    lines.append(f"\\begin{{tabular}}{{{col_spec}}}")

    # 顶部线
    if config.use_booktabs:
        lines.append("\\toprule")
    else:
        lines.append("\\hline")

    # 多行表头 - 数据集名称
    header_datasets = (
        "& "
        + " & ".join(
            [f"\\multicolumn{{{n_metrics}}}{{c}}{{{_format_dataset_name(ds)}}}" for ds in datasets]
        )
        + " \\\\"
    )
    lines.append(header_datasets)

    # cmidrule 分隔线
    if config.use_booktabs:
        cmidrules = " ".join(
            [
                f"\\cmidrule(lr){{{2 + i * n_metrics}-{1 + (i + 1) * n_metrics}}}"
                for i in range(n_datasets)
            ]
        )
        lines.append(cmidrules)

    # 指标名称行
    metric_headers = ["Method"]
    for _ in datasets:
        for m in metrics:
            info = metric_info.get(m, (m.replace("_", " ").title(), "max", 3))
            metric_headers.append(info[0])
    lines.append(" & ".join(metric_headers) + " \\\\")

    # 中间线
    if config.use_booktabs:
        lines.append("\\midrule")
    else:
        lines.append("\\hline")

    # 找出每个数据集每个指标的最佳值
    best_values: dict[str, dict[str, float]] = {}
    for ds in datasets:
        best_values[ds] = {}
        for m in metrics:
            info = metric_info.get(m, (m, "max", 3))
            direction = info[1]
            values = []
            for algo in algorithms:
                algo_metrics = results[ds].get(algo)
                if algo_metrics:
                    val = _get_metric_value(algo_metrics, m)
                    if val is not None and not np.isnan(val):
                        values.append(val)
            if values:
                best_values[ds][m] = max(values) if direction == "max" else min(values)

    # 数据行
    for algo in algorithms:
        row = [_format_method_name(algo)]
        for ds in datasets:
            algo_metrics = results[ds].get(algo)
            if not algo_metrics:
                row.extend(["-"] * n_metrics)
                continue

            for m in metrics:
                info = metric_info.get(m, (m, "max", 3))
                decimal_places = info[2]
                val = _get_metric_value(algo_metrics, m)

                if val is None or np.isnan(val):
                    row.append("-")
                    continue

                # 格式化数值
                if m == "compression_rate":
                    formatted = f"{val:.{decimal_places}f}$\\times$"
                else:
                    formatted = _format_number(val, decimal_places)

                # 检查是否是最佳值
                is_best = abs(val - best_values[ds].get(m, float("inf"))) < 1e-6

                # 添加显著性标记
                sig_marker = ""
                if include_significance and algo != baseline and raw_results:
                    p_value = _compute_p_value(raw_results, ds, baseline, algo, m)
                    sig_marker = _get_significance_marker(p_value)

                # 组合最终格式
                if is_best:
                    row.append(f"\\textbf{{{formatted}}}{sig_marker}")
                else:
                    row.append(f"{formatted}{sig_marker}")

        lines.append(" & ".join(row) + " \\\\")

    # 底部线
    if config.use_booktabs:
        lines.append("\\bottomrule")
    else:
        lines.append("\\hline")

    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)


def _get_metric_value(metrics: AlgorithmMetrics, metric_name: str) -> float | None:
    """从 AlgorithmMetrics 获取指标值"""
    mapping = {
        "f1": "avg_f1",
        "recall": "avg_recall",
        "rouge_l": "avg_rouge_l",
        "accuracy": "avg_accuracy",
        "compression_rate": "avg_compression_rate",
        "total_time": "avg_total_time",
        "retrieve_time": "avg_retrieve_time",
        "refine_time": "avg_refine_time",
        "generate_time": "avg_generate_time",
    }
    attr_name = mapping.get(metric_name, f"avg_{metric_name}")
    return getattr(metrics, attr_name, None)


def _compute_p_value(
    raw_results: dict[str, dict[str, list[dict[str, Any]]]],
    dataset: str,
    baseline: str,
    method: str,
    metric: str,
) -> float | None:
    """计算配对 t 检验的 p 值"""
    try:
        baseline_data = raw_results.get(dataset, {}).get(baseline, [])
        method_data = raw_results.get(dataset, {}).get(method, [])

        if not baseline_data or not method_data:
            return None

        baseline_scores = [d.get(metric, d.get(f"avg_{metric}", 0)) for d in baseline_data]
        method_scores = [d.get(metric, d.get(f"avg_{metric}", 0)) for d in method_data]

        if len(baseline_scores) < 2 or len(method_scores) < 2:
            return None

        # 确保长度一致 (取较短的)
        min_len = min(len(baseline_scores), len(method_scores))
        baseline_scores = baseline_scores[:min_len]
        method_scores = method_scores[:min_len]

        result = paired_t_test(baseline_scores, method_scores)
        return result.p_value
    except (ValueError, KeyError, TypeError):
        return None


def generate_ablation_table(
    results: dict[str, AlgorithmMetrics],
    components: list[str],
    baseline_full: str = "full",
    config: TableConfig | None = None,
) -> str:
    """
    生成消融实验表格

    Args:
        results: 各配置的指标 {config_name: AlgorithmMetrics}
        components: 消融组件列表 ["w/o query classifier", "w/o MMR", ...]
        baseline_full: 完整模型的名称
        config: 表格配置

    Returns:
        LaTeX 表格字符串

    Example:
        >>> results = {
        ...     "full": AlgorithmMetrics(algorithm="full", avg_f1=0.40),
        ...     "w/o classifier": AlgorithmMetrics(algorithm="w/o classifier", avg_f1=0.38),
        ... }
        >>> latex = generate_ablation_table(results, ["w/o classifier", "w/o MMR"])
    """
    if config is None:
        config = TableConfig(
            caption="Ablation Study. $\\Delta$ shows the change from the full model.",
            label="tab:ablation",
        )

    lines = []

    # 表格开始
    lines.append(f"\\begin{{table}}[{config.position}]")
    if config.centering:
        lines.append("\\centering")
    if config.font_size:
        lines.append(f"\\{config.font_size}")
    if config.caption:
        lines.append(f"\\caption{{{config.caption}}}")
    if config.label:
        lines.append(f"\\label{{{config.label}}}")
    lines.append("\\begin{tabular}{l|ccc|c}")

    # 表头
    if config.use_booktabs:
        lines.append("\\toprule")
    else:
        lines.append("\\hline")

    lines.append(
        "Configuration & F1 $\\uparrow$ & Comp. $\\uparrow$ & Time (s) $\\downarrow$ & $\\Delta$ F1 \\\\"
    )

    if config.use_booktabs:
        lines.append("\\midrule")
    else:
        lines.append("\\hline")

    # 获取完整模型的基准值
    full_metrics = results.get(baseline_full)
    full_f1 = full_metrics.avg_f1 if full_metrics else 0.0

    # 完整模型行
    if full_metrics:
        lines.append(
            f"Full Model & {full_metrics.avg_f1:.3f} & "
            f"{full_metrics.avg_compression_rate:.1f}$\\times$ & "
            f"{full_metrics.avg_total_time:.2f} & - \\\\"
        )

    if config.use_booktabs:
        lines.append("\\midrule")
    else:
        lines.append("\\hline")

    # 消融组件行
    for component in components:
        comp_metrics = results.get(component)
        if not comp_metrics:
            lines.append(f"{_escape_latex(component)} & - & - & - & - \\\\")
            continue

        delta_f1 = comp_metrics.avg_f1 - full_f1
        delta_str = f"{delta_f1:+.3f}" if delta_f1 != 0 else "0.000"

        # 如果 delta 为负，用红色标记
        if delta_f1 < -0.01:
            delta_str = f"\\textcolor{{red}}{{{delta_str}}}"

        lines.append(
            f"{_escape_latex(component)} & {comp_metrics.avg_f1:.3f} & "
            f"{comp_metrics.avg_compression_rate:.1f}$\\times$ & "
            f"{comp_metrics.avg_total_time:.2f} & {delta_str} \\\\"
        )

    # 表格结束
    if config.use_booktabs:
        lines.append("\\bottomrule")
    else:
        lines.append("\\hline")

    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)


def generate_significance_table(
    raw_results: dict[str, list[dict[str, Any]]],
    baseline: str = "baseline",
    metric: str = "f1",
    config: TableConfig | None = None,
) -> str:
    """
    生成统计显著性检验表格

    Args:
        raw_results: 各算法的原始样本结果 {algorithm: [{"f1": float, ...}, ...]}
        baseline: 基线算法名称
        metric: 要分析的指标
        config: 表格配置

    Returns:
        LaTeX 表格字符串，包含 p-value, Cohen's d, 95% CI
    """
    if config is None:
        config = TableConfig(
            caption=f"Statistical Significance Analysis ({metric.upper()}). "
            "Effect size: negligible (<0.2), small (0.2-0.5), medium (0.5-0.8), large ($\\geq$0.8).",
            label="tab:significance",
        )

    lines = []

    # 表格开始
    lines.append(f"\\begin{{table}}[{config.position}]")
    if config.centering:
        lines.append("\\centering")
    if config.font_size:
        lines.append(f"\\{config.font_size}")
    if config.caption:
        lines.append(f"\\caption{{{config.caption}}}")
    if config.label:
        lines.append(f"\\label{{{config.label}}}")
    lines.append("\\begin{tabular}{l|cccccc}")

    # 表头
    if config.use_booktabs:
        lines.append("\\toprule")
    else:
        lines.append("\\hline")

    lines.append("Method & Mean & Std & 95\\% CI & p-value & Cohen's $d$ & Effect \\\\")

    if config.use_booktabs:
        lines.append("\\midrule")
    else:
        lines.append("\\hline")

    # 提取 baseline 数据
    baseline_data = raw_results.get(baseline, [])
    baseline_scores = [d.get(metric, d.get(f"avg_{metric}", 0)) for d in baseline_data]

    # Baseline 行
    if baseline_scores:
        mean_val = float(np.mean(baseline_scores))
        std_val = float(np.std(baseline_scores, ddof=1))
        try:
            ci_lower, ci_upper = bootstrap_confidence_interval(baseline_scores)
            ci_str = f"[{ci_lower:.3f}, {ci_upper:.3f}]"
        except ValueError:
            ci_str = "-"

        lines.append(
            f"{_format_method_name(baseline)} & {mean_val:.3f} & {std_val:.3f} & "
            f"{ci_str} & - & - & - \\\\"
        )

    if config.use_booktabs:
        lines.append("\\midrule")
    else:
        lines.append("\\hline")

    # 其他方法
    for method, data in raw_results.items():
        if method == baseline:
            continue

        method_scores = [d.get(metric, d.get(f"avg_{metric}", 0)) for d in data]

        if not method_scores:
            lines.append(f"{_format_method_name(method)} & - & - & - & - & - & - \\\\")
            continue

        mean_val = float(np.mean(method_scores))
        std_val = float(np.std(method_scores, ddof=1))

        # 95% CI
        try:
            ci_lower, ci_upper = bootstrap_confidence_interval(method_scores)
            ci_str = f"[{ci_lower:.3f}, {ci_upper:.3f}]"
        except ValueError:
            ci_str = "-"

        # p-value
        try:
            min_len = min(len(baseline_scores), len(method_scores))
            t_result = paired_t_test(baseline_scores[:min_len], method_scores[:min_len])
            p_val = t_result.p_value
            p_str = _format_p_value_latex(p_val)
        except ValueError:
            p_str = "-"

        # Cohen's d
        try:
            d_val = cohens_d(baseline_scores, method_scores)
            d_str = f"{d_val:.2f}"
            effect = _interpret_effect_size(d_val)
        except ValueError:
            d_str = "-"
            effect = "-"

        lines.append(
            f"{_format_method_name(method)} & {mean_val:.3f} & {std_val:.3f} & "
            f"{ci_str} & {p_str} & {d_str} & {effect} \\\\"
        )

    # 表格结束
    if config.use_booktabs:
        lines.append("\\bottomrule")
    else:
        lines.append("\\hline")

    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)


def _format_p_value_latex(p: float) -> str:
    """格式化 p 值为 LaTeX"""
    if p < 0.001:
        return "$<$0.001$^{***}$"
    elif p < 0.01:
        return f"{p:.3f}$^{{**}}$"
    elif p < 0.05:
        return f"{p:.3f}$^{{*}}$"
    else:
        return f"{p:.3f}"


def _interpret_effect_size(d: float) -> str:
    """解释 Cohen's d 效应量"""
    abs_d = abs(d)
    if abs_d < 0.2:
        return "negligible"
    elif abs_d < 0.5:
        return "small"
    elif abs_d < 0.8:
        return "medium"
    else:
        return "large"


def generate_case_study_table(
    cases: list[dict[str, Any]],
    max_cases: int = 3,
    max_text_length: int = 100,
    config: TableConfig | None = None,
) -> str:
    """
    生成压缩案例展示表格

    Args:
        cases: 案例列表，每个案例包含:
            {
                "query": str,
                "original": str,
                "compressed": str,
                "original_tokens": int,
                "compressed_tokens": int,
                "f1_original": float,
                "f1_compressed": float,
            }
        max_cases: 最大案例数
        max_text_length: 文本最大长度 (截断)
        config: 表格配置

    Returns:
        LaTeX 表格字符串
    """
    if config is None:
        config = TableConfig(
            caption="Case Study: Compression Examples. Tokens shows original $\\rightarrow$ compressed count.",
            label="tab:case_study",
        )

    def truncate_text(text: str, max_len: int) -> str:
        """截断文本并转义"""
        text = _escape_latex(text)
        if len(text) > max_len:
            return text[: max_len - 3] + "..."
        return text

    lines = []

    # 表格开始
    lines.append(f"\\begin{{table*}}[{config.position}]")
    if config.centering:
        lines.append("\\centering")
    if config.font_size:
        lines.append(f"\\{config.font_size}")
    if config.caption:
        lines.append(f"\\caption{{{config.caption}}}")
    if config.label:
        lines.append(f"\\label{{{config.label}}}")
    lines.append("\\begin{tabular}{p{0.15\\textwidth}|p{0.35\\textwidth}|p{0.35\\textwidth}|c}")

    # 表头
    if config.use_booktabs:
        lines.append("\\toprule")
    else:
        lines.append("\\hline")

    lines.append("Query & Original Context & Compressed Context & Tokens \\\\")

    if config.use_booktabs:
        lines.append("\\midrule")
    else:
        lines.append("\\hline")

    # 案例行
    for i, case in enumerate(cases[:max_cases]):
        query = truncate_text(case.get("query", ""), 50)
        original = truncate_text(case.get("original", ""), max_text_length)
        compressed = truncate_text(case.get("compressed", ""), max_text_length)

        orig_tokens = case.get("original_tokens", 0)
        comp_tokens = case.get("compressed_tokens", 0)
        tokens_str = f"{orig_tokens} $\\rightarrow$ {comp_tokens}"

        # 使用 \parbox 处理长文本
        lines.append(
            f"{query} & \\footnotesize{{{original}}} & "
            f"\\footnotesize{{{compressed}}} & {tokens_str} \\\\"
        )

        # 案例之间加分隔线
        if i < min(len(cases), max_cases) - 1:
            if config.use_booktabs:
                lines.append("\\midrule")
            else:
                lines.append("\\hline")

    # 表格结束
    if config.use_booktabs:
        lines.append("\\bottomrule")
    else:
        lines.append("\\hline")

    lines.append("\\end{tabular}")
    lines.append("\\end{table*}")

    return "\n".join(lines)


def generate_latency_breakdown_table(
    results: dict[str, AlgorithmMetrics],
    config: TableConfig | None = None,
) -> str:
    """
    生成延迟分解表格

    Args:
        results: 各算法的指标 {algorithm: AlgorithmMetrics}
        config: 表格配置

    Returns:
        LaTeX 表格字符串
    """
    if config is None:
        config = TableConfig(
            caption="Latency Breakdown (seconds). Total = Retrieve + Refine + Generate.",
            label="tab:latency",
        )

    lines = []

    # 表格开始
    lines.append(f"\\begin{{table}}[{config.position}]")
    if config.centering:
        lines.append("\\centering")
    if config.font_size:
        lines.append(f"\\{config.font_size}")
    if config.caption:
        lines.append(f"\\caption{{{config.caption}}}")
    if config.label:
        lines.append(f"\\label{{{config.label}}}")
    lines.append("\\begin{tabular}{l|cccc}")

    # 表头
    if config.use_booktabs:
        lines.append("\\toprule")
    else:
        lines.append("\\hline")

    lines.append("Method & Retrieve & Refine & Generate & Total \\\\")

    if config.use_booktabs:
        lines.append("\\midrule")
    else:
        lines.append("\\hline")

    # 找出最快的总时间
    best_total = (
        min(m.avg_total_time for m in results.values() if m.avg_total_time > 0) if results else 0
    )

    # 数据行
    for algo, metrics in results.items():
        retrieve = _format_number(metrics.avg_retrieve_time, 2)
        refine = _format_number(metrics.avg_refine_time, 2)
        generate = _format_number(metrics.avg_generate_time, 2)
        total = _format_number(metrics.avg_total_time, 2)

        # 最快的总时间加粗
        if abs(metrics.avg_total_time - best_total) < 0.01:
            total = f"\\textbf{{{total}}}"

        lines.append(
            f"{_format_method_name(algo)} & {retrieve} & {refine} & {generate} & {total} \\\\"
        )

    # 表格结束
    if config.use_booktabs:
        lines.append("\\bottomrule")
    else:
        lines.append("\\hline")

    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)


def export_all_tables(
    results: dict[str, dict[str, AlgorithmMetrics]],
    output_dir: str | Path,
    baseline: str = "baseline",
    raw_results: dict[str, dict[str, list[dict[str, Any]]]] | None = None,
) -> dict[str, Path]:
    """
    导出所有标准表格到指定目录

    Args:
        results: 实验结果 {dataset: {algorithm: AlgorithmMetrics}}
        output_dir: 输出目录
        baseline: 基线算法名称
        raw_results: 原始样本结果

    Returns:
        生成的文件路径字典 {table_name: path}
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_files = {}

    # 1. 主结果表格
    main_table = generate_main_results_table(
        results,
        baseline=baseline,
        include_significance=True,
        raw_results=raw_results,
    )
    main_path = output_dir / "main_results.tex"
    main_path.write_text(main_table, encoding="utf-8")
    generated_files["main_results"] = main_path

    # 2. 延迟分解表格 (使用第一个数据集的结果)
    if results:
        first_dataset = list(results.keys())[0]
        latency_table = generate_latency_breakdown_table(results[first_dataset])
        latency_path = output_dir / "latency_breakdown.tex"
        latency_path.write_text(latency_table, encoding="utf-8")
        generated_files["latency_breakdown"] = latency_path

    # 3. 显著性表格 (使用第一个数据集的原始结果)
    if raw_results:
        first_dataset = list(raw_results.keys())[0]
        sig_table = generate_significance_table(
            raw_results[first_dataset],
            baseline=baseline,
        )
        sig_path = output_dir / "significance.tex"
        sig_path.write_text(sig_table, encoding="utf-8")
        generated_files["significance"] = sig_path

    return generated_files


__all__ = [
    "TableConfig",
    "generate_main_results_table",
    "generate_ablation_table",
    "generate_significance_table",
    "generate_case_study_table",
    "generate_latency_breakdown_table",
    "export_all_tables",
]
