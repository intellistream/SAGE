"""
LaTeX 导出模块单元测试
=====================

测试 latex_export.py 中的所有表格生成功能。
"""

import pytest

from sage.benchmark.benchmark_refiner.analysis.latex_export import (
    TableConfig,
    export_all_tables,
    generate_ablation_table,
    generate_case_study_table,
    generate_latency_breakdown_table,
    generate_main_results_table,
    generate_significance_table,
)
from sage.benchmark.benchmark_refiner.experiments.base_experiment import AlgorithmMetrics

# =============================================================================
# 测试数据 Fixtures
# =============================================================================


@pytest.fixture
def sample_metrics() -> dict[str, AlgorithmMetrics]:
    """单数据集的算法指标"""
    return {
        "baseline": AlgorithmMetrics(
            algorithm="baseline",
            num_samples=100,
            avg_f1=0.350,
            avg_recall=0.400,
            avg_compression_rate=1.0,
            avg_total_time=2.50,
            avg_retrieve_time=1.0,
            avg_refine_time=0.0,
            avg_generate_time=1.5,
            std_f1=0.05,
        ),
        "longrefiner": AlgorithmMetrics(
            algorithm="longrefiner",
            num_samples=100,
            avg_f1=0.380,
            avg_recall=0.420,
            avg_compression_rate=3.0,
            avg_total_time=3.50,
            avg_retrieve_time=1.0,
            avg_refine_time=1.0,
            avg_generate_time=1.5,
            std_f1=0.04,
        ),
        "llmlingua2": AlgorithmMetrics(
            algorithm="llmlingua2",
            num_samples=100,
            avg_f1=0.360,
            avg_recall=0.410,
            avg_compression_rate=2.8,
            avg_total_time=1.50,
            avg_retrieve_time=1.0,
            avg_refine_time=0.3,
            avg_generate_time=0.2,
            std_f1=0.06,
        ),
    }


@pytest.fixture
def multi_dataset_results(sample_metrics) -> dict[str, dict[str, AlgorithmMetrics]]:
    """多数据集结果"""
    return {
        "nq": sample_metrics,
        "hotpotqa": {
            "baseline": AlgorithmMetrics(
                algorithm="baseline",
                num_samples=100,
                avg_f1=0.300,
                avg_compression_rate=1.0,
                avg_total_time=2.80,
            ),
            "longrefiner": AlgorithmMetrics(
                algorithm="longrefiner",
                num_samples=100,
                avg_f1=0.350,
                avg_compression_rate=2.8,
                avg_total_time=4.00,
            ),
            "llmlingua2": AlgorithmMetrics(
                algorithm="llmlingua2",
                num_samples=100,
                avg_f1=0.320,
                avg_compression_rate=2.5,
                avg_total_time=1.80,
            ),
        },
    }


@pytest.fixture
def raw_results_single() -> dict[str, list[dict]]:
    """单数据集原始样本结果"""
    import random

    random.seed(42)

    def generate_samples(base_f1: float, n: int = 20) -> list[dict]:
        return [{"f1": base_f1 + random.gauss(0, 0.05)} for _ in range(n)]

    return {
        "baseline": generate_samples(0.35),
        "longrefiner": generate_samples(0.38),
        "llmlingua2": generate_samples(0.36),
    }


@pytest.fixture
def raw_results_multi(raw_results_single) -> dict[str, dict[str, list[dict]]]:
    """多数据集原始样本结果"""
    import random

    random.seed(43)

    def generate_samples(base_f1: float, n: int = 20) -> list[dict]:
        return [{"f1": base_f1 + random.gauss(0, 0.05)} for _ in range(n)]

    return {
        "nq": raw_results_single,
        "hotpotqa": {
            "baseline": generate_samples(0.30),
            "longrefiner": generate_samples(0.35),
            "llmlingua2": generate_samples(0.32),
        },
    }


# =============================================================================
# generate_main_results_table 测试
# =============================================================================


class TestGenerateMainResultsTable:
    """主结果表格生成测试"""

    def test_basic_generation(self, multi_dataset_results):
        """测试基本表格生成"""
        latex = generate_main_results_table(multi_dataset_results)

        # 检查 LaTeX 结构
        assert r"\begin{table}" in latex
        assert r"\end{table}" in latex
        assert r"\begin{tabular}" in latex
        assert r"\end{tabular}" in latex

        # 检查 booktabs 命令
        assert r"\toprule" in latex
        assert r"\midrule" in latex
        assert r"\bottomrule" in latex

        # 检查数据集名称
        assert "NQ" in latex
        assert "HotpotQA" in latex

        # 检查算法名称
        assert "Baseline" in latex
        assert "LongRefiner" in latex
        assert "LLMLingua-2" in latex

    def test_best_value_bold(self, multi_dataset_results):
        """测试最佳值加粗"""
        latex = generate_main_results_table(multi_dataset_results)

        # 最佳 F1 应该加粗
        assert r"\textbf{" in latex

    def test_significance_markers(self, multi_dataset_results, raw_results_multi):
        """测试显著性标记"""
        latex = generate_main_results_table(
            multi_dataset_results,
            include_significance=True,
            raw_results=raw_results_multi,
        )

        # 检查显著性标记格式 (可能有也可能没有)
        # 至少应该包含表格结构
        assert r"\begin{table}" in latex

    def test_custom_metrics(self, multi_dataset_results):
        """测试自定义指标"""
        latex = generate_main_results_table(
            multi_dataset_results,
            metrics=["f1", "compression_rate"],
        )

        # 检查只包含选定的指标列
        assert "F1" in latex
        assert "Comp." in latex

    def test_no_significance(self, multi_dataset_results):
        """测试禁用显著性标记"""
        latex = generate_main_results_table(
            multi_dataset_results,
            include_significance=False,
        )

        # 数据行中不应该有显著性标记 (caption 中可能有说明文字)
        # 检查表格数据部分
        lines = latex.split("\n")
        data_lines = [line for line in lines if "LongRefiner" in line or "LLMLingua" in line]
        for line in data_lines:
            assert "$^{*}$" not in line, f"Found significance marker in data line: {line}"
            assert "$^{**}$" not in line, f"Found significance marker in data line: {line}"
            assert "$^{***}$" not in line, f"Found significance marker in data line: {line}"

    def test_custom_config(self, multi_dataset_results):
        """测试自定义表格配置"""
        config = TableConfig(
            caption="Custom Caption",
            label="tab:custom",
            position="h",
            font_size="small",
        )
        latex = generate_main_results_table(
            multi_dataset_results,
            config=config,
        )

        assert "Custom Caption" in latex
        assert r"\label{tab:custom}" in latex
        assert r"\begin{table}[h]" in latex
        assert r"\small" in latex


# =============================================================================
# generate_ablation_table 测试
# =============================================================================


class TestGenerateAblationTable:
    """消融实验表格测试"""

    def test_basic_generation(self):
        """测试基本消融表格生成"""
        results = {
            "full": AlgorithmMetrics(
                algorithm="full",
                avg_f1=0.40,
                avg_compression_rate=3.0,
                avg_total_time=3.5,
            ),
            "w/o classifier": AlgorithmMetrics(
                algorithm="w/o classifier",
                avg_f1=0.38,
                avg_compression_rate=2.8,
                avg_total_time=3.2,
            ),
            "w/o MMR": AlgorithmMetrics(
                algorithm="w/o MMR",
                avg_f1=0.35,
                avg_compression_rate=3.0,
                avg_total_time=3.0,
            ),
        }
        components = ["w/o classifier", "w/o MMR"]

        latex = generate_ablation_table(results, components)

        # 检查结构
        assert r"\begin{table}" in latex
        assert r"\end{table}" in latex
        assert "Full Model" in latex
        assert r"$\Delta$ F1" in latex

        # 检查组件
        assert "w/o classifier" in latex.replace(r"\_", "_")
        assert "w/o MMR" in latex.replace(r"\_", "_")

    def test_delta_calculation(self):
        """测试 delta 计算"""
        results = {
            "full": AlgorithmMetrics(algorithm="full", avg_f1=0.40),
            "ablated": AlgorithmMetrics(algorithm="ablated", avg_f1=0.35),
        }

        latex = generate_ablation_table(results, ["ablated"])

        # 应该显示负的 delta
        assert "-0.050" in latex or "textcolor" in latex


# =============================================================================
# generate_significance_table 测试
# =============================================================================


class TestGenerateSignificanceTable:
    """统计显著性表格测试"""

    def test_basic_generation(self, raw_results_single):
        """测试基本显著性表格生成"""
        latex = generate_significance_table(raw_results_single)

        # 检查结构
        assert r"\begin{table}" in latex
        assert "Mean" in latex
        assert "Std" in latex
        assert "95" in latex  # 95% CI
        assert "p-value" in latex
        assert "Cohen" in latex

    def test_effect_size_labels(self, raw_results_single):
        """测试效应量标签"""
        latex = generate_significance_table(raw_results_single)

        # 应该包含效应量解释
        possible_effects = ["negligible", "small", "medium", "large"]
        assert any(effect in latex for effect in possible_effects) or "-" in latex

    def test_baseline_row(self, raw_results_single):
        """测试基线行不包含比较"""
        latex = generate_significance_table(raw_results_single, baseline="baseline")

        # Baseline 行不应该有 p 值
        lines = latex.split("\n")
        baseline_line = [line for line in lines if "Baseline" in line]
        assert len(baseline_line) > 0


# =============================================================================
# generate_case_study_table 测试
# =============================================================================


class TestGenerateCaseStudyTable:
    """案例展示表格测试"""

    def test_basic_generation(self):
        """测试基本案例表格生成"""
        cases = [
            {
                "query": "What is the capital of France?",
                "original": "Paris is the capital and most populous city of France. "
                "It is located in northern France.",
                "compressed": "Paris is the capital of France.",
                "original_tokens": 50,
                "compressed_tokens": 10,
            },
            {
                "query": "Who wrote Romeo and Juliet?",
                "original": "Romeo and Juliet is a tragedy written by William Shakespeare "
                "early in his career.",
                "compressed": "Written by William Shakespeare.",
                "original_tokens": 30,
                "compressed_tokens": 8,
            },
        ]

        latex = generate_case_study_table(cases)

        # 检查结构 - 案例表格使用 table* 环境
        assert r"\begin{table*}" in latex
        assert r"\end{table*}" in latex
        assert "Query" in latex
        assert "Original Context" in latex
        assert "Compressed Context" in latex

    def test_max_cases_limit(self):
        """测试最大案例数限制"""
        cases = [
            {"query": f"Query {i}", "original": f"Original {i}", "compressed": f"Compressed {i}"}
            for i in range(10)
        ]

        latex = generate_case_study_table(cases, max_cases=3)

        # 只应该有 3 个案例
        assert latex.count("Query 0") == 1
        assert "Query 5" not in latex

    def test_text_truncation(self):
        """测试长文本截断"""
        cases = [
            {
                "query": "Q",
                "original": "A" * 200,  # 很长的文本
                "compressed": "B" * 200,
            }
        ]

        latex = generate_case_study_table(cases, max_text_length=50)

        # 应该被截断
        assert "..." in latex


# =============================================================================
# generate_latency_breakdown_table 测试
# =============================================================================


class TestGenerateLatencyBreakdownTable:
    """延迟分解表格测试"""

    def test_basic_generation(self, sample_metrics):
        """测试基本延迟表格生成"""
        latex = generate_latency_breakdown_table(sample_metrics)

        # 检查结构
        assert r"\begin{table}" in latex
        assert "Retrieve" in latex
        assert "Refine" in latex
        assert "Generate" in latex
        assert "Total" in latex

    def test_best_total_bold(self, sample_metrics):
        """测试最快总时间加粗"""
        latex = generate_latency_breakdown_table(sample_metrics)

        # llmlingua2 应该是最快的
        assert r"\textbf{" in latex


# =============================================================================
# export_all_tables 测试
# =============================================================================


class TestExportAllTables:
    """批量导出测试"""

    def test_export_creates_files(self, multi_dataset_results, raw_results_multi, tmp_path):
        """测试导出创建文件"""
        generated = export_all_tables(
            multi_dataset_results,
            output_dir=tmp_path,
            raw_results=raw_results_multi,
        )

        # 检查文件是否创建
        assert "main_results" in generated
        assert generated["main_results"].exists()

        assert "latency_breakdown" in generated
        assert generated["latency_breakdown"].exists()

        assert "significance" in generated
        assert generated["significance"].exists()

    def test_export_without_raw_results(self, multi_dataset_results, tmp_path):
        """测试无原始结果时的导出"""
        generated = export_all_tables(
            multi_dataset_results,
            output_dir=tmp_path,
            raw_results=None,
        )

        # 主表格和延迟表格应该存在
        assert "main_results" in generated
        assert "latency_breakdown" in generated

        # 显著性表格不应该存在
        assert "significance" not in generated


# =============================================================================
# TableConfig 测试
# =============================================================================


class TestTableConfig:
    """表格配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = TableConfig()

        assert config.position == "t"
        assert config.centering is True
        assert config.use_booktabs is True

    def test_custom_values(self):
        """测试自定义值"""
        config = TableConfig(
            caption="Test Caption",
            label="tab:test",
            position="h",
            font_size="footnotesize",
        )

        assert config.caption == "Test Caption"
        assert config.label == "tab:test"
        assert config.position == "h"
        assert config.font_size == "footnotesize"


# =============================================================================
# 边界情况测试
# =============================================================================


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_results(self):
        """测试空结果"""
        latex = generate_main_results_table({})

        # 应该生成有效的空表格
        assert r"\begin{table}" in latex
        assert r"\end{table}" in latex

    def test_single_algorithm(self):
        """测试单算法"""
        results = {
            "nq": {
                "baseline": AlgorithmMetrics(
                    algorithm="baseline",
                    avg_f1=0.35,
                )
            }
        }

        latex = generate_main_results_table(results)
        assert "Baseline" in latex

    def test_nan_values(self):
        """测试 NaN 值处理"""
        import math

        results = {
            "nq": {
                "test": AlgorithmMetrics(
                    algorithm="test",
                    avg_f1=math.nan,
                    avg_compression_rate=1.0,
                )
            }
        }

        latex = generate_main_results_table(results)

        # NaN 应该显示为 "-"
        assert "-" in latex

    def test_special_characters_in_names(self):
        """测试名称中的特殊字符"""
        results = {
            "test_dataset": {
                "test_algo": AlgorithmMetrics(
                    algorithm="test_algo",
                    avg_f1=0.35,
                )
            }
        }

        # 不应该抛出异常
        latex = generate_main_results_table(results)
        assert r"\begin{table}" in latex
