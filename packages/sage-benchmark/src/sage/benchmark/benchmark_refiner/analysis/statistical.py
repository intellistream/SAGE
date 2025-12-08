"""
统计显著性检验模块
==================

用于 ICML 论文的统计检验，验证算法改进的显著性。

提供的功能：
- 配对 t 检验
- Bootstrap 置信区间
- Cohen's d 效应量
- 多重比较校正 (Bonferroni)
- 统计报告生成

依赖：scipy, numpy
"""

from typing import NamedTuple

import numpy as np
from scipy import stats


class TTestResult(NamedTuple):
    """配对 t 检验结果"""

    t_statistic: float
    p_value: float
    significant: bool
    degrees_of_freedom: int


class SignificanceResult(NamedTuple):
    """显著性检验结果"""

    method: str
    mean: float
    std: float
    ci_lower: float
    ci_upper: float
    p_value: float | None
    cohens_d: float | None
    significant: bool


def paired_t_test(
    baseline_scores: list[float],
    method_scores: list[float],
    alpha: float = 0.05,
) -> TTestResult:
    """
    配对 t 检验

    检验两组配对样本的均值差异是否显著。

    Args:
        baseline_scores: 基线方法的分数列表
        method_scores: 待比较方法的分数列表
        alpha: 显著性水平，默认 0.05

    Returns:
        TTestResult: 包含 t 统计量、p 值、是否显著、自由度

    Raises:
        ValueError: 当两组样本长度不一致或样本量不足时

    Example:
        >>> result = paired_t_test([0.3, 0.35, 0.32], [0.4, 0.42, 0.38])
        >>> result.p_value < 0.05
        True
    """
    if len(baseline_scores) != len(method_scores):
        raise ValueError(
            f"Sample sizes must match: baseline={len(baseline_scores)}, method={len(method_scores)}"
        )

    if len(baseline_scores) < 2:
        raise ValueError("At least 2 samples required for t-test")

    baseline = np.array(baseline_scores)
    method = np.array(method_scores)

    # scipy.stats.ttest_rel 执行配对 t 检验
    t_stat, p_value = stats.ttest_rel(method, baseline)

    return TTestResult(
        t_statistic=float(t_stat),
        p_value=float(p_value),
        significant=p_value < alpha,
        degrees_of_freedom=len(baseline_scores) - 1,
    )


def bootstrap_confidence_interval(
    scores: list[float],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    random_state: int | None = None,
) -> tuple[float, float]:
    """
    Bootstrap 置信区间

    使用 Bootstrap 重采样方法估计均值的置信区间。

    Args:
        scores: 分数列表
        n_bootstrap: Bootstrap 重采样次数，默认 1000
        confidence: 置信度，默认 0.95 (95% CI)
        random_state: 随机种子，用于可重复性

    Returns:
        tuple[float, float]: (下界, 上界)

    Raises:
        ValueError: 当样本量不足时

    Example:
        >>> lower, upper = bootstrap_confidence_interval([0.3, 0.35, 0.32, 0.38])
        >>> lower < upper
        True
    """
    if len(scores) < 2:
        raise ValueError("At least 2 samples required for bootstrap")

    rng = np.random.default_rng(random_state)
    scores_array = np.array(scores)
    n_samples = len(scores_array)

    # Bootstrap 重采样
    bootstrap_means = np.array(
        [rng.choice(scores_array, size=n_samples, replace=True).mean() for _ in range(n_bootstrap)]
    )

    # 计算百分位数区间
    alpha = 1 - confidence
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100

    lower_bound = float(np.percentile(bootstrap_means, lower_percentile))
    upper_bound = float(np.percentile(bootstrap_means, upper_percentile))

    return (lower_bound, upper_bound)


def cohens_d(
    baseline_scores: list[float],
    method_scores: list[float],
) -> float:
    """
    Cohen's d 效应量

    计算两组样本之间的标准化均值差异。

    解释标准：
    - |d| < 0.2: 微小效应
    - 0.2 <= |d| < 0.5: 小效应
    - 0.5 <= |d| < 0.8: 中等效应
    - |d| >= 0.8: 大效应

    Args:
        baseline_scores: 基线方法的分数列表
        method_scores: 待比较方法的分数列表

    Returns:
        float: Cohen's d 值，正值表示 method 优于 baseline

    Raises:
        ValueError: 当样本量不足时

    Example:
        >>> d = cohens_d([0.3, 0.35, 0.32], [0.5, 0.52, 0.48])
        >>> d > 0.8  # 大效应
        True
    """
    if len(baseline_scores) < 2 or len(method_scores) < 2:
        raise ValueError("At least 2 samples required for each group")

    baseline = np.array(baseline_scores)
    method = np.array(method_scores)

    # 均值差
    mean_diff = method.mean() - baseline.mean()

    # 合并标准差 (pooled standard deviation)
    n1, n2 = len(baseline), len(method)
    var1 = baseline.var(ddof=1)
    var2 = method.var(ddof=1)

    # 使用 Hedges' g 的分母计算 (考虑不等样本量)
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

    # 避免除零
    if pooled_std == 0:
        return 0.0 if mean_diff == 0 else float("inf") * np.sign(mean_diff)

    return float(mean_diff / pooled_std)


def bonferroni_correction(
    p_values: list[float],
    alpha: float = 0.05,
) -> list[bool]:
    """
    Bonferroni 多重比较校正

    通过调整显著性阈值来控制族错误率 (FWER)。

    Args:
        p_values: p 值列表
        alpha: 原始显著性水平，默认 0.05

    Returns:
        list[bool]: 每个假设是否在校正后仍然显著

    Example:
        >>> bonferroni_correction([0.01, 0.03, 0.04], alpha=0.05)
        [True, False, False]  # 只有第一个在校正后仍显著 (0.01 < 0.05/3)
    """
    if not p_values:
        return []

    n_comparisons = len(p_values)
    adjusted_alpha = alpha / n_comparisons

    return [p < adjusted_alpha for p in p_values]


def holm_bonferroni_correction(
    p_values: list[float],
    alpha: float = 0.05,
) -> list[bool]:
    """
    Holm-Bonferroni 阶梯式校正

    比标准 Bonferroni 更强大的多重比较校正方法。

    Args:
        p_values: p 值列表
        alpha: 原始显著性水平，默认 0.05

    Returns:
        list[bool]: 每个假设是否在校正后仍然显著
    """
    if not p_values:
        return []

    n = len(p_values)
    # 按 p 值排序并记录原始索引
    sorted_indices = np.argsort(p_values)
    sorted_p = np.array(p_values)[sorted_indices]

    # 计算调整后的阈值
    significant = [False] * n
    for rank, (idx, p) in enumerate(zip(sorted_indices, sorted_p)):
        adjusted_alpha = alpha / (n - rank)
        if p < adjusted_alpha:
            significant[idx] = True
        else:
            # 一旦不显著，后续都不显著
            break

    return significant


def _format_p_value(p: float) -> str:
    """格式化 p 值显示"""
    if p < 0.001:
        return "<0.001***"
    elif p < 0.01:
        return f"{p:.3f}**"
    elif p < 0.05:
        return f"{p:.3f}*"
    else:
        return f"{p:.3f}"


def _interpret_cohens_d(d: float) -> str:
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


def generate_significance_report(
    results: dict[str, list[float]],
    baseline_name: str = "baseline",
    metric_name: str = "F1",
    alpha: float = 0.05,
) -> str:
    """
    生成统计显著性报告

    Args:
        results: 各方法的分数字典，格式 {"method_name": [score1, score2, ...]}
        baseline_name: 基线方法名称
        metric_name: 指标名称，用于报告标题
        alpha: 显著性水平

    Returns:
        str: Markdown 格式的统计显著性报告

    Example:
        >>> results = {
        ...     "baseline": [0.35, 0.36, 0.34, 0.37],
        ...     "longrefiner": [0.38, 0.40, 0.39, 0.41],
        ... }
        >>> report = generate_significance_report(results)
        >>> "Statistical Significance Report" in report
        True
    """
    if baseline_name not in results:
        raise ValueError(f"Baseline '{baseline_name}' not found in results")

    baseline_scores = results[baseline_name]
    methods = [m for m in results.keys() if m != baseline_name]

    # 收集统计结果
    stats_results: list[SignificanceResult] = []

    # 添加 baseline 的结果
    baseline_mean = float(np.mean(baseline_scores))
    baseline_std = float(np.std(baseline_scores, ddof=1))
    baseline_ci = bootstrap_confidence_interval(baseline_scores)
    stats_results.append(
        SignificanceResult(
            method=baseline_name,
            mean=baseline_mean,
            std=baseline_std,
            ci_lower=baseline_ci[0],
            ci_upper=baseline_ci[1],
            p_value=None,
            cohens_d=None,
            significant=False,
        )
    )

    # 对每个方法进行检验
    p_values = []
    for method in methods:
        method_scores = results[method]
        method_mean = float(np.mean(method_scores))
        method_std = float(np.std(method_scores, ddof=1))
        method_ci = bootstrap_confidence_interval(method_scores)

        # 配对 t 检验
        try:
            t_result = paired_t_test(baseline_scores, method_scores, alpha=alpha)
            p_val = t_result.p_value
        except ValueError:
            p_val = 1.0

        # Cohen's d
        try:
            d = cohens_d(baseline_scores, method_scores)
        except ValueError:
            d = 0.0

        p_values.append(p_val)
        stats_results.append(
            SignificanceResult(
                method=method,
                mean=method_mean,
                std=method_std,
                ci_lower=method_ci[0],
                ci_upper=method_ci[1],
                p_value=p_val,
                cohens_d=d,
                significant=p_val < alpha,
            )
        )

    # Bonferroni 校正
    corrected_significance = bonferroni_correction(p_values, alpha)

    # 生成 Markdown 报告
    lines = [
        f"## Statistical Significance Report ({metric_name})",
        "",
        f"**Baseline**: {baseline_name}",
        f"**Significance level**: α = {alpha}",
        f"**Correction**: Bonferroni (adjusted α = {alpha / max(1, len(methods)):.4f})",
        "",
        "| Method | Mean | Std | 95% CI | vs Baseline p | Cohen's d | Effect | Sig. |",
        "|--------|------|-----|--------|---------------|-----------|--------|------|",
    ]

    for i, stat in enumerate(stats_results):
        if stat.method == baseline_name:
            # Baseline 行
            lines.append(
                f"| {stat.method} | {stat.mean:.4f} | {stat.std:.4f} | "
                f"[{stat.ci_lower:.3f}, {stat.ci_upper:.3f}] | - | - | - | - |"
            )
        else:
            # 其他方法
            p_str = _format_p_value(stat.p_value) if stat.p_value is not None else "-"
            d_str = f"{stat.cohens_d:.2f}" if stat.cohens_d is not None else "-"
            effect = _interpret_cohens_d(stat.cohens_d) if stat.cohens_d is not None else "-"

            # 使用 Bonferroni 校正后的显著性
            method_idx = i - 1  # 减去 baseline
            sig_after_correction = (
                corrected_significance[method_idx]
                if method_idx < len(corrected_significance)
                else False
            )
            sig_str = "Yes" if sig_after_correction else "No"

            lines.append(
                f"| {stat.method} | {stat.mean:.4f} | {stat.std:.4f} | "
                f"[{stat.ci_lower:.3f}, {stat.ci_upper:.3f}] | {p_str} | "
                f"{d_str} | {effect} | {sig_str} |"
            )

    # 添加注释
    lines.extend(
        [
            "",
            "*Notes:*",
            "- \\* p < 0.05, \\*\\* p < 0.01, \\*\\*\\* p < 0.001 (before Bonferroni correction)",
            "- Sig. column shows significance after Bonferroni correction",
            "- Effect size interpretation: negligible (<0.2), small (0.2-0.5), "
            "medium (0.5-0.8), large (≥0.8)",
        ]
    )

    return "\n".join(lines)


def compute_all_statistics(
    results: dict[str, list[float]],
    baseline_name: str = "baseline",
) -> dict[str, dict]:
    """
    计算所有统计量

    返回结构化的统计数据，适合程序化处理或导出。

    Args:
        results: 各方法的分数字典
        baseline_name: 基线方法名称

    Returns:
        dict: 包含所有统计量的字典

    Example:
        >>> stats = compute_all_statistics({"baseline": [0.3]*10, "method": [0.4]*10})
        >>> "method" in stats
        True
    """
    if baseline_name not in results:
        raise ValueError(f"Baseline '{baseline_name}' not found in results")

    baseline_scores = results[baseline_name]
    output = {}

    for method, scores in results.items():
        method_stats = {
            "mean": float(np.mean(scores)),
            "std": float(np.std(scores, ddof=1)),
            "min": float(np.min(scores)),
            "max": float(np.max(scores)),
            "median": float(np.median(scores)),
            "n_samples": len(scores),
        }

        # Bootstrap CI
        try:
            ci_lower, ci_upper = bootstrap_confidence_interval(scores)
            method_stats["ci_95_lower"] = ci_lower
            method_stats["ci_95_upper"] = ci_upper
        except ValueError:
            method_stats["ci_95_lower"] = None
            method_stats["ci_95_upper"] = None

        # 与 baseline 的比较
        if method != baseline_name:
            try:
                t_result = paired_t_test(baseline_scores, scores)
                method_stats["vs_baseline"] = {
                    "t_statistic": t_result.t_statistic,
                    "p_value": t_result.p_value,
                    "significant_005": t_result.p_value < 0.05,
                    "significant_001": t_result.p_value < 0.01,
                }
            except ValueError as e:
                method_stats["vs_baseline"] = {"error": str(e)}

            try:
                d = cohens_d(baseline_scores, scores)
                method_stats["cohens_d"] = d
                method_stats["effect_size"] = _interpret_cohens_d(d)
            except ValueError:
                method_stats["cohens_d"] = None
                method_stats["effect_size"] = None

            # 相对改进
            baseline_mean = np.mean(baseline_scores)
            if baseline_mean != 0:
                method_stats["relative_improvement"] = (
                    (method_stats["mean"] - baseline_mean) / baseline_mean * 100
                )
            else:
                method_stats["relative_improvement"] = None

        output[method] = method_stats

    return output


def wilcoxon_test(
    baseline_scores: list[float],
    method_scores: list[float],
    alpha: float = 0.05,
) -> dict:
    """
    Wilcoxon 符号秩检验

    非参数配对检验，当数据不满足正态分布假设时使用。

    Args:
        baseline_scores: 基线方法的分数列表
        method_scores: 待比较方法的分数列表
        alpha: 显著性水平

    Returns:
        dict: 包含 statistic, p_value, significant
    """
    if len(baseline_scores) != len(method_scores):
        raise ValueError("Sample sizes must match")

    if len(baseline_scores) < 6:
        raise ValueError("At least 6 samples recommended for Wilcoxon test")

    baseline = np.array(baseline_scores)
    method = np.array(method_scores)

    # 移除相等的对
    diff = method - baseline
    non_zero_mask = diff != 0
    if not np.any(non_zero_mask):
        return {"statistic": 0.0, "p_value": 1.0, "significant": False}

    statistic, p_value = stats.wilcoxon(
        method[non_zero_mask],
        baseline[non_zero_mask],
        alternative="two-sided",
    )

    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "significant": p_value < alpha,
    }


__all__ = [
    "TTestResult",
    "SignificanceResult",
    "paired_t_test",
    "bootstrap_confidence_interval",
    "cohens_d",
    "bonferroni_correction",
    "holm_bonferroni_correction",
    "generate_significance_report",
    "compute_all_statistics",
    "wilcoxon_test",
]
