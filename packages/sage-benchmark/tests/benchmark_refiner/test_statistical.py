"""
统计检验模块单元测试
===================

测试 sage.benchmark.benchmark_refiner.analysis.statistical 模块
"""

import math

import numpy as np
import pytest

from sage.benchmark.benchmark_refiner.analysis.statistical import (
    TTestResult,
    bonferroni_correction,
    bootstrap_confidence_interval,
    cohens_d,
    compute_all_statistics,
    generate_significance_report,
    holm_bonferroni_correction,
    paired_t_test,
    wilcoxon_test,
)


class TestPairedTTest:
    """配对 t 检验测试"""

    def test_significant_difference(self):
        """测试显著差异的情况"""
        # 明显不同的两组数据
        baseline = [0.30, 0.32, 0.31, 0.33, 0.30, 0.32, 0.31, 0.33, 0.30, 0.32]
        method = [0.50, 0.52, 0.51, 0.53, 0.50, 0.52, 0.51, 0.53, 0.50, 0.52]

        result = paired_t_test(baseline, method)

        assert isinstance(result, TTestResult)
        assert result.p_value < 0.001
        assert result.significant == True  # noqa: E712
        assert result.degrees_of_freedom == 9

    def test_no_significant_difference(self):
        """测试无显著差异的情况"""
        # 几乎相同的两组数据（加入一些随机性）
        baseline = [0.35, 0.36, 0.34, 0.35, 0.36, 0.33, 0.37, 0.35]
        method = [0.36, 0.35, 0.35, 0.34, 0.35, 0.34, 0.36, 0.36]

        result = paired_t_test(baseline, method)

        assert result.p_value > 0.05
        assert result.significant == False  # noqa: E712

    def test_mismatched_lengths(self):
        """测试长度不匹配时抛出异常"""
        with pytest.raises(ValueError, match="Sample sizes must match"):
            paired_t_test([0.3, 0.4], [0.3, 0.4, 0.5])

    def test_insufficient_samples(self):
        """测试样本不足时抛出异常"""
        with pytest.raises(ValueError, match="At least 2 samples required"):
            paired_t_test([0.3], [0.4])

    def test_identical_samples(self):
        """测试完全相同的样本"""
        scores = [0.35, 0.36, 0.34, 0.35]
        result = paired_t_test(scores, scores)

        # p 值应该为 1 或接近 1（没有差异）
        # 注意：完全相同的数据可能产生 nan
        assert result.p_value >= 0.99 or math.isnan(result.p_value)


class TestBootstrapConfidenceInterval:
    """Bootstrap 置信区间测试"""

    def test_basic_ci(self):
        """测试基本置信区间计算"""
        scores = [0.35, 0.36, 0.34, 0.37, 0.35, 0.36, 0.34, 0.38, 0.33, 0.36]

        lower, upper = bootstrap_confidence_interval(scores, random_state=42)

        assert lower < upper
        assert lower > 0
        assert upper < 1

        # CI 应该包含均值
        mean = np.mean(scores)
        assert lower <= mean <= upper

    def test_reproducibility(self):
        """测试随机种子的可重复性"""
        scores = [0.35, 0.36, 0.34, 0.37, 0.35]

        ci1 = bootstrap_confidence_interval(scores, random_state=123)
        ci2 = bootstrap_confidence_interval(scores, random_state=123)

        assert ci1[0] == ci2[0]
        assert ci1[1] == ci2[1]

    def test_different_confidence_levels(self):
        """测试不同置信度"""
        scores = [0.35, 0.36, 0.34, 0.37, 0.35, 0.36, 0.34, 0.38, 0.33, 0.36]

        ci_90 = bootstrap_confidence_interval(scores, confidence=0.90, random_state=42)
        ci_95 = bootstrap_confidence_interval(scores, confidence=0.95, random_state=42)
        ci_99 = bootstrap_confidence_interval(scores, confidence=0.99, random_state=42)

        # 更高的置信度应该有更宽的区间
        assert (ci_99[1] - ci_99[0]) >= (ci_95[1] - ci_95[0])
        assert (ci_95[1] - ci_95[0]) >= (ci_90[1] - ci_90[0])

    def test_insufficient_samples(self):
        """测试样本不足时抛出异常"""
        with pytest.raises(ValueError, match="At least 2 samples required"):
            bootstrap_confidence_interval([0.35])


class TestCohensD:
    """Cohen's d 效应量测试"""

    def test_large_effect(self):
        """测试大效应"""
        baseline = [0.30, 0.32, 0.31, 0.33, 0.30]
        method = [0.50, 0.52, 0.51, 0.53, 0.50]

        d = cohens_d(baseline, method)

        assert d > 0.8  # 大效应
        assert d > 0  # method 优于 baseline

    def test_medium_effect(self):
        """测试中等效应"""
        # 调整数据以产生中等效应（d ≈ 0.5-0.8）
        # 使用更大的标准差和适当的均值差
        baseline = [0.30, 0.38, 0.42, 0.33, 0.37, 0.28, 0.40, 0.35, 0.36, 0.31]
        method = [0.33, 0.41, 0.45, 0.36, 0.40, 0.31, 0.43, 0.38, 0.39, 0.34]

        d = cohens_d(baseline, method)

        assert 0.5 <= d < 1.2  # 中等效应

    def test_small_effect(self):
        """测试小效应"""
        # 调整数据以产生小效应（d ≈ 0.2-0.5）
        # 使用更大的标准差和更小的均值差
        baseline = [0.30, 0.35, 0.40, 0.33, 0.37, 0.32, 0.38, 0.34, 0.36, 0.35]
        method = [0.32, 0.37, 0.42, 0.35, 0.39, 0.34, 0.40, 0.36, 0.38, 0.37]

        d = cohens_d(baseline, method)

        assert 0.2 <= d < 0.8  # 小到中效应

    def test_negligible_effect(self):
        """测试微小效应"""
        # 使用更大的方差和更小的均值差
        baseline = [0.30, 0.35, 0.40, 0.33, 0.37, 0.32, 0.38, 0.34, 0.36, 0.35]
        method = [0.31, 0.35, 0.40, 0.34, 0.37, 0.32, 0.38, 0.35, 0.36, 0.35]

        d = cohens_d(baseline, method)

        assert abs(d) < 0.3  # 微小效应

    def test_negative_effect(self):
        """测试负效应（method 差于 baseline）"""
        baseline = [0.50, 0.52, 0.51, 0.53, 0.50]
        method = [0.30, 0.32, 0.31, 0.33, 0.30]

        d = cohens_d(baseline, method)

        assert d < 0  # 负效应

    def test_zero_std(self):
        """测试标准差为零的边缘情况"""
        baseline = [0.35, 0.35, 0.35, 0.35]
        method = [0.35, 0.35, 0.35, 0.35]

        d = cohens_d(baseline, method)

        assert d == 0  # 完全相同

    def test_insufficient_samples(self):
        """测试样本不足"""
        with pytest.raises(ValueError):
            cohens_d([0.3], [0.4])


class TestBonferroniCorrection:
    """Bonferroni 校正测试"""

    def test_basic_correction(self):
        """测试基本校正"""
        p_values = [0.01, 0.03, 0.04]

        result = bonferroni_correction(p_values, alpha=0.05)

        # 0.05 / 3 ≈ 0.0167
        # 只有 0.01 < 0.0167
        assert result == [True, False, False]

    def test_all_significant(self):
        """测试全部显著"""
        p_values = [0.001, 0.002, 0.003]

        result = bonferroni_correction(p_values, alpha=0.05)

        assert result == [True, True, True]

    def test_none_significant(self):
        """测试全部不显著"""
        p_values = [0.1, 0.2, 0.3]

        result = bonferroni_correction(p_values, alpha=0.05)

        assert result == [False, False, False]

    def test_empty_list(self):
        """测试空列表"""
        assert bonferroni_correction([]) == []

    def test_single_comparison(self):
        """测试单次比较（无需校正）"""
        result = bonferroni_correction([0.03], alpha=0.05)
        assert result == [True]


class TestHolmBonferroniCorrection:
    """Holm-Bonferroni 校正测试"""

    def test_holm_more_powerful(self):
        """测试 Holm 方法比标准 Bonferroni 更有效"""
        p_values = [0.01, 0.02, 0.03]

        bonferroni_result = bonferroni_correction(p_values, alpha=0.05)
        holm_result = holm_bonferroni_correction(p_values, alpha=0.05)

        # Holm 方法应该检测到更多显著结果（或至少相同）
        assert sum(holm_result) >= sum(bonferroni_result)

    def test_holm_stepwise(self):
        """测试阶梯式校正"""
        p_values = [0.01, 0.025, 0.05]

        result = holm_bonferroni_correction(p_values, alpha=0.05)

        # 第一个: 0.01 < 0.05/3 = 0.0167 -> 显著
        # 第二个: 0.025 < 0.05/2 = 0.025 -> 不显著（等于不算）
        # 第三个: 停止
        assert result[0] is True


class TestGenerateSignificanceReport:
    """生成显著性报告测试"""

    def test_basic_report(self):
        """测试基本报告生成"""
        results = {
            "baseline": [0.35, 0.36, 0.34, 0.37, 0.35, 0.36, 0.34, 0.38, 0.33, 0.36],
            "longrefiner": [0.40, 0.42, 0.39, 0.41, 0.40, 0.42, 0.39, 0.43, 0.38, 0.41],
            "reform": [0.36, 0.37, 0.35, 0.38, 0.36, 0.37, 0.35, 0.39, 0.34, 0.37],
        }

        report = generate_significance_report(results)

        # 检查报告包含关键元素
        assert "Statistical Significance Report" in report
        assert "baseline" in report
        assert "longrefiner" in report
        assert "reform" in report
        assert "Cohen's d" in report
        assert "95% CI" in report

    def test_report_with_custom_baseline(self):
        """测试自定义基线"""
        results = {
            "no_compression": [0.30, 0.32, 0.31, 0.33, 0.30],
            "method_a": [0.35, 0.37, 0.36, 0.38, 0.35],
        }

        report = generate_significance_report(results, baseline_name="no_compression")

        assert "no_compression" in report
        assert "method_a" in report

    def test_missing_baseline(self):
        """测试缺少基线时抛出异常"""
        results = {"method_a": [0.35, 0.36], "method_b": [0.40, 0.41]}

        with pytest.raises(ValueError, match="Baseline .* not found"):
            generate_significance_report(results, baseline_name="baseline")


class TestComputeAllStatistics:
    """计算所有统计量测试"""

    def test_basic_stats(self):
        """测试基本统计量计算"""
        results = {
            "baseline": [0.35, 0.36, 0.34, 0.37, 0.35, 0.36, 0.34, 0.38, 0.33, 0.36],
            "method": [0.40, 0.42, 0.39, 0.41, 0.40, 0.42, 0.39, 0.43, 0.38, 0.41],
        }

        stats = compute_all_statistics(results)

        # 检查基线统计
        assert "baseline" in stats
        assert "mean" in stats["baseline"]
        assert "std" in stats["baseline"]
        assert "ci_95_lower" in stats["baseline"]
        assert "ci_95_upper" in stats["baseline"]

        # 检查方法统计
        assert "method" in stats
        assert "vs_baseline" in stats["method"]
        assert "cohens_d" in stats["method"]
        assert "relative_improvement" in stats["method"]

    def test_relative_improvement(self):
        """测试相对改进计算"""
        results = {
            "baseline": [0.40, 0.40, 0.40, 0.40, 0.40],
            "method": [0.48, 0.48, 0.48, 0.48, 0.48],
        }

        stats = compute_all_statistics(results)

        # 相对改进应该是 20%
        assert abs(stats["method"]["relative_improvement"] - 20.0) < 0.1


class TestWilcoxonTest:
    """Wilcoxon 符号秩检验测试"""

    def test_significant_difference(self):
        """测试显著差异"""
        baseline = [0.30, 0.32, 0.31, 0.33, 0.30, 0.32, 0.31, 0.33, 0.30, 0.32]
        method = [0.50, 0.52, 0.51, 0.53, 0.50, 0.52, 0.51, 0.53, 0.50, 0.52]

        result = wilcoxon_test(baseline, method)

        assert result["p_value"] < 0.05
        assert result["significant"] == True  # noqa: E712

    def test_no_difference(self):
        """测试无差异"""
        scores = [0.35, 0.36, 0.34, 0.37, 0.35, 0.36]
        result = wilcoxon_test(scores, scores)

        assert result["p_value"] == 1.0
        assert result["significant"] == False  # noqa: E712

    def test_insufficient_samples(self):
        """测试样本不足"""
        with pytest.raises(ValueError, match="At least 6 samples"):
            wilcoxon_test([0.3, 0.4], [0.4, 0.5])


class TestIntegration:
    """集成测试"""

    def test_full_analysis_workflow(self):
        """测试完整分析工作流"""
        # 模拟实验结果
        np.random.seed(42)
        n_samples = 50

        results = {
            "baseline": list(np.random.normal(0.35, 0.02, n_samples)),
            "longrefiner": list(np.random.normal(0.40, 0.02, n_samples)),
            "reform": list(np.random.normal(0.37, 0.02, n_samples)),
            "adaptive": list(np.random.normal(0.42, 0.02, n_samples)),
        }

        # 1. 计算所有统计量
        all_stats = compute_all_statistics(results)
        assert len(all_stats) == 4

        # 2. 生成报告
        report = generate_significance_report(results)
        assert "Statistical Significance Report" in report

        # 3. 验证统计显著性
        for method in ["longrefiner", "reform", "adaptive"]:
            t_result = paired_t_test(results["baseline"], results[method])
            # 由于差异明显，应该都显著
            assert t_result.p_value < 0.05

        # 4. 验证效应量排序
        d_longrefiner = cohens_d(results["baseline"], results["longrefiner"])
        d_adaptive = cohens_d(results["baseline"], results["adaptive"])
        # adaptive 改进更大，效应量应该更大
        assert d_adaptive > d_longrefiner
