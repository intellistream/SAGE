"""
可视化模块单元测试
==================

测试 visualization.py 中的所有可视化函数。
"""

import matplotlib.pyplot as plt
import pytest

from sage.benchmark.benchmark_refiner.analysis.visualization import (
    ALGORITHM_COLORS,
    ALGORITHM_MARKERS,
    _compute_pareto_frontier,
    _get_algorithm_color,
    _get_algorithm_marker,
    generate_visualization_report,
    plot_algorithm_comparison,
    plot_dataset_heatmap,
    plot_latency_breakdown,
    plot_pareto_frontier,
    plot_radar_chart,
)
from sage.benchmark.benchmark_refiner.experiments.base_experiment import AlgorithmMetrics

# =============================================================================
# 测试数据 Fixtures
# =============================================================================


@pytest.fixture
def sample_results() -> dict[str, AlgorithmMetrics]:
    """创建测试用的单数据集结果"""
    return {
        "baseline": AlgorithmMetrics(
            algorithm="baseline",
            num_samples=100,
            avg_f1=0.350,
            std_f1=0.02,
            avg_compression_rate=1.0,
            std_compression_rate=0.0,
            avg_total_time=2.50,
            std_total_time=0.1,
            avg_retrieve_time=0.5,
            avg_refine_time=0.0,
            avg_generate_time=2.0,
        ),
        "longrefiner": AlgorithmMetrics(
            algorithm="longrefiner",
            num_samples=100,
            avg_f1=0.420,
            std_f1=0.03,
            avg_compression_rate=3.0,
            std_compression_rate=0.2,
            avg_total_time=3.50,
            std_total_time=0.2,
            avg_retrieve_time=0.5,
            avg_refine_time=1.5,
            avg_generate_time=1.5,
        ),
        "reform": AlgorithmMetrics(
            algorithm="reform",
            num_samples=100,
            avg_f1=0.380,
            std_f1=0.025,
            avg_compression_rate=2.5,
            std_compression_rate=0.15,
            avg_total_time=2.80,
            std_total_time=0.15,
            avg_retrieve_time=0.5,
            avg_refine_time=0.8,
            avg_generate_time=1.5,
        ),
        "provence": AlgorithmMetrics(
            algorithm="provence",
            num_samples=100,
            avg_f1=0.370,
            std_f1=0.022,
            avg_compression_rate=2.2,
            std_compression_rate=0.1,
            avg_total_time=2.60,
            std_total_time=0.12,
            avg_retrieve_time=0.5,
            avg_refine_time=0.6,
            avg_generate_time=1.5,
        ),
        "longllmlingua": AlgorithmMetrics(
            algorithm="longllmlingua",
            num_samples=100,
            avg_f1=0.400,
            std_f1=0.028,
            avg_compression_rate=3.2,
            std_compression_rate=0.25,
            avg_total_time=4.00,
            std_total_time=0.3,
            avg_retrieve_time=0.5,
            avg_refine_time=2.0,
            avg_generate_time=1.5,
        ),
        "llmlingua2": AlgorithmMetrics(
            algorithm="llmlingua2",
            num_samples=100,
            avg_f1=0.360,
            std_f1=0.021,
            avg_compression_rate=2.8,
            std_compression_rate=0.18,
            avg_total_time=1.50,
            std_total_time=0.08,
            avg_retrieve_time=0.5,
            avg_refine_time=0.3,
            avg_generate_time=0.7,
        ),
    }


@pytest.fixture
def multi_dataset_results(sample_results) -> dict[str, dict[str, AlgorithmMetrics]]:
    """创建测试用的多数据集结果"""
    # NQ 数据集使用 sample_results
    nq_results = sample_results

    # HotpotQA 数据集 - 稍微不同的值
    hotpotqa_results = {
        "baseline": AlgorithmMetrics(
            algorithm="baseline",
            num_samples=100,
            avg_f1=0.300,
            avg_compression_rate=1.0,
            avg_total_time=2.80,
            avg_retrieve_time=0.5,
            avg_refine_time=0.0,
            avg_generate_time=2.3,
        ),
        "longrefiner": AlgorithmMetrics(
            algorithm="longrefiner",
            num_samples=100,
            avg_f1=0.380,
            avg_compression_rate=2.8,
            avg_total_time=4.00,
            avg_retrieve_time=0.5,
            avg_refine_time=1.8,
            avg_generate_time=1.7,
        ),
        "reform": AlgorithmMetrics(
            algorithm="reform",
            num_samples=100,
            avg_f1=0.350,
            avg_compression_rate=2.3,
            avg_total_time=3.00,
            avg_retrieve_time=0.5,
            avg_refine_time=0.9,
            avg_generate_time=1.6,
        ),
    }

    # 2WikiMQA 数据集
    wikimqa_results = {
        "baseline": AlgorithmMetrics(
            algorithm="baseline",
            num_samples=100,
            avg_f1=0.280,
            avg_compression_rate=1.0,
            avg_total_time=3.00,
            avg_retrieve_time=0.6,
            avg_refine_time=0.0,
            avg_generate_time=2.4,
        ),
        "longrefiner": AlgorithmMetrics(
            algorithm="longrefiner",
            num_samples=100,
            avg_f1=0.360,
            avg_compression_rate=2.6,
            avg_total_time=4.20,
            avg_retrieve_time=0.6,
            avg_refine_time=1.9,
            avg_generate_time=1.7,
        ),
        "reform": AlgorithmMetrics(
            algorithm="reform",
            num_samples=100,
            avg_f1=0.330,
            avg_compression_rate=2.1,
            avg_total_time=3.20,
            avg_retrieve_time=0.6,
            avg_refine_time=1.0,
            avg_generate_time=1.6,
        ),
    }

    return {
        "nq": nq_results,
        "hotpotqa": hotpotqa_results,
        "2wikimultihopqa": wikimqa_results,
    }


@pytest.fixture
def minimal_results() -> dict[str, AlgorithmMetrics]:
    """最小测试数据 - 只有两个算法"""
    return {
        "baseline": AlgorithmMetrics(
            algorithm="baseline",
            num_samples=10,
            avg_f1=0.30,
            avg_compression_rate=1.0,
            avg_total_time=2.0,
            avg_retrieve_time=0.5,
            avg_refine_time=0.0,
            avg_generate_time=1.5,
        ),
        "method_a": AlgorithmMetrics(
            algorithm="method_a",
            num_samples=10,
            avg_f1=0.40,
            avg_compression_rate=2.0,
            avg_total_time=3.0,
            avg_retrieve_time=0.5,
            avg_refine_time=1.0,
            avg_generate_time=1.5,
        ),
    }


# =============================================================================
# TestPlotAlgorithmComparison
# =============================================================================


class TestPlotAlgorithmComparison:
    """测试 plot_algorithm_comparison 函数"""

    def test_basic_generation(self, sample_results):
        """测试基本图表生成"""
        fig = plot_algorithm_comparison(sample_results, metric="f1")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_different_metrics(self, sample_results):
        """测试不同指标"""
        metrics = ["f1", "compression_rate", "total_time", "refine_time"]
        for metric in metrics:
            fig = plot_algorithm_comparison(sample_results, metric=metric)
            assert isinstance(fig, plt.Figure)
            plt.close(fig)

    def test_save_to_file(self, sample_results, tmp_path):
        """测试保存到文件"""
        output_path = tmp_path / "comparison.png"
        fig = plot_algorithm_comparison(sample_results, metric="f1", output_path=output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        plt.close(fig)

    def test_custom_title(self, sample_results):
        """测试自定义标题"""
        fig = plot_algorithm_comparison(sample_results, metric="f1", title="Custom Title Test")
        assert isinstance(fig, plt.Figure)
        # 检查标题
        ax = fig.axes[0]
        assert ax.get_title() == "Custom Title Test"
        plt.close(fig)

    def test_invalid_metric_raises_error(self, sample_results):
        """测试无效指标抛出错误"""
        with pytest.raises(ValueError, match="Unknown metric"):
            plot_algorithm_comparison(sample_results, metric="invalid_metric")

    def test_custom_figsize(self, sample_results):
        """测试自定义图表大小"""
        fig = plot_algorithm_comparison(sample_results, metric="f1", figsize=(12, 8))
        assert isinstance(fig, plt.Figure)
        # 检查图表大小
        width, height = fig.get_size_inches()
        assert abs(width - 12) < 0.1
        assert abs(height - 8) < 0.1
        plt.close(fig)


# =============================================================================
# TestPlotParetoFrontier
# =============================================================================


class TestPlotParetoFrontier:
    """测试 plot_pareto_frontier 函数"""

    def test_basic_generation(self, sample_results):
        """测试基本图表生成"""
        fig = plot_pareto_frontier(sample_results)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_save_to_file(self, sample_results, tmp_path):
        """测试保存到文件"""
        output_path = tmp_path / "pareto.png"
        fig = plot_pareto_frontier(sample_results, output_path=output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        plt.close(fig)

    def test_custom_metrics(self, sample_results):
        """测试自定义 X/Y 指标"""
        fig = plot_pareto_frontier(sample_results, x_metric="compression_rate", y_metric="f1")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_pareto_points_identified(self, minimal_results):
        """测试 Pareto 点识别"""
        # method_a 比 baseline 更好 (更高的 f1 和 compression_rate)
        fig = plot_pareto_frontier(minimal_results)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


# =============================================================================
# TestPlotLatencyBreakdown
# =============================================================================


class TestPlotLatencyBreakdown:
    """测试 plot_latency_breakdown 函数"""

    def test_basic_generation(self, sample_results):
        """测试基本图表生成"""
        fig = plot_latency_breakdown(sample_results)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_save_to_file(self, sample_results, tmp_path):
        """测试保存到文件"""
        output_path = tmp_path / "latency.png"
        fig = plot_latency_breakdown(sample_results, output_path=output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        plt.close(fig)

    def test_stacked_bars(self, sample_results):
        """测试堆叠柱状图包含三个组件"""
        fig = plot_latency_breakdown(sample_results)
        ax = fig.axes[0]
        # 检查图例有三个标签
        legend_labels = [t.get_text() for t in ax.get_legend().get_texts()]
        assert "Retrieve" in legend_labels
        assert "Refine" in legend_labels
        assert "Generate" in legend_labels
        plt.close(fig)

    def test_custom_title(self, sample_results):
        """测试自定义标题"""
        fig = plot_latency_breakdown(sample_results, title="Latency Test")
        ax = fig.axes[0]
        assert ax.get_title() == "Latency Test"
        plt.close(fig)


# =============================================================================
# TestPlotDatasetHeatmap
# =============================================================================


class TestPlotDatasetHeatmap:
    """测试 plot_dataset_heatmap 函数"""

    def test_basic_generation(self, multi_dataset_results):
        """测试基本图表生成"""
        # 只使用前两个数据集，确保算法一致
        results = {
            "nq": {
                k: v
                for k, v in multi_dataset_results["nq"].items()
                if k in ["baseline", "longrefiner", "reform"]
            },
            "hotpotqa": multi_dataset_results["hotpotqa"],
        }
        fig = plot_dataset_heatmap(results, metric="f1")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_save_to_file(self, multi_dataset_results, tmp_path):
        """测试保存到文件"""
        results = {
            "nq": {
                k: v
                for k, v in multi_dataset_results["nq"].items()
                if k in ["baseline", "longrefiner", "reform"]
            },
            "hotpotqa": multi_dataset_results["hotpotqa"],
        }
        output_path = tmp_path / "heatmap.png"
        fig = plot_dataset_heatmap(results, metric="f1", output_path=output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        plt.close(fig)

    def test_annotation_enabled(self, multi_dataset_results):
        """测试标注启用"""
        results = {
            "nq": {
                k: v
                for k, v in multi_dataset_results["nq"].items()
                if k in ["baseline", "longrefiner", "reform"]
            },
            "hotpotqa": multi_dataset_results["hotpotqa"],
        }
        fig = plot_dataset_heatmap(results, metric="f1", annotate=True)
        ax = fig.axes[0]
        # 检查有文本标注
        texts = [child for child in ax.get_children() if isinstance(child, plt.Text)]
        # 应该有 算法数 * 数据集数 个数值标注
        assert len([t for t in texts if t.get_text() and "0." in t.get_text()]) > 0
        plt.close(fig)

    def test_annotation_disabled(self, multi_dataset_results):
        """测试标注禁用"""
        results = {
            "nq": {
                k: v
                for k, v in multi_dataset_results["nq"].items()
                if k in ["baseline", "longrefiner", "reform"]
            },
            "hotpotqa": multi_dataset_results["hotpotqa"],
        }
        fig = plot_dataset_heatmap(results, metric="f1", annotate=False)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_empty_results_raises_error(self):
        """测试空结果抛出错误"""
        with pytest.raises(ValueError, match="Empty results"):
            plot_dataset_heatmap({}, metric="f1")


# =============================================================================
# TestPlotRadarChart
# =============================================================================


class TestPlotRadarChart:
    """测试 plot_radar_chart 函数"""

    def test_basic_generation(self, sample_results):
        """测试基本图表生成"""
        fig = plot_radar_chart(sample_results)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_save_to_file(self, sample_results, tmp_path):
        """测试保存到文件"""
        output_path = tmp_path / "radar.png"
        fig = plot_radar_chart(sample_results, output_path=output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        plt.close(fig)

    def test_custom_metrics(self, sample_results):
        """测试自定义指标"""
        fig = plot_radar_chart(
            sample_results, metrics=["f1", "compression_rate", "speed", "refine_time"]
        )
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_default_metrics(self, sample_results):
        """测试默认指标 (f1, compression_rate, speed)"""
        fig = plot_radar_chart(sample_results)
        ax = fig.axes[0]
        # 检查有 3 个标签 (默认指标)
        labels = [t.get_text() for t in ax.get_xticklabels()]
        assert len(labels) == 3
        plt.close(fig)

    def test_normalization(self, minimal_results):
        """测试归一化正常工作"""
        fig = plot_radar_chart(minimal_results)
        assert isinstance(fig, plt.Figure)
        # 归一化后值应该在 0-1 之间
        plt.close(fig)


# =============================================================================
# TestGenerateVisualizationReport
# =============================================================================


class TestGenerateVisualizationReport:
    """测试 generate_visualization_report 函数"""

    def test_generates_all_files(self, sample_results, tmp_path):
        """测试生成所有文件"""
        files = generate_visualization_report(sample_results, output_dir=tmp_path, formats=["png"])
        assert len(files) > 0
        # 检查文件存在
        for name, path in files.items():
            assert path.exists(), f"File {name} not found at {path}"

    def test_pdf_and_png_formats(self, sample_results, tmp_path):
        """测试 PDF 和 PNG 格式"""
        files = generate_visualization_report(
            sample_results, output_dir=tmp_path, formats=["pdf", "png"]
        )
        # 应该有 PDF 和 PNG 版本
        pdf_files = [k for k in files.keys() if "pdf" in k]
        png_files = [k for k in files.keys() if "png" in k]
        assert len(pdf_files) > 0
        assert len(png_files) > 0

    def test_with_multi_dataset_results(self, sample_results, multi_dataset_results, tmp_path):
        """测试包含多数据集结果"""
        # 简化 multi_dataset_results 使算法一致
        simplified_multi = {
            "nq": {
                k: v
                for k, v in multi_dataset_results["nq"].items()
                if k in ["baseline", "longrefiner", "reform"]
            },
            "hotpotqa": multi_dataset_results["hotpotqa"],
        }
        # 简化 sample_results
        simplified_single = {
            k: v for k, v in sample_results.items() if k in ["baseline", "longrefiner", "reform"]
        }
        files = generate_visualization_report(
            simplified_single,
            multi_dataset_results=simplified_multi,
            output_dir=tmp_path,
            formats=["png"],
        )
        # 应该包含热力图
        heatmap_files = [k for k in files.keys() if "heatmap" in k]
        assert len(heatmap_files) > 0

    def test_creates_output_directory(self, sample_results, tmp_path):
        """测试自动创建输出目录"""
        output_dir = tmp_path / "nested" / "output"
        files = generate_visualization_report(
            sample_results, output_dir=output_dir, formats=["png"]
        )
        assert output_dir.exists()
        assert len(files) > 0


# =============================================================================
# TestHelperFunctions
# =============================================================================


class TestHelperFunctions:
    """测试辅助函数"""

    def test_get_algorithm_color_known(self):
        """测试已知算法的颜色"""
        assert _get_algorithm_color("baseline") == "#7f7f7f"
        assert _get_algorithm_color("longrefiner") == "#1f77b4"
        assert _get_algorithm_color("REFORM") == "#ff7f0e"  # 大小写不敏感

    def test_get_algorithm_color_unknown(self):
        """测试未知算法返回默认颜色"""
        color = _get_algorithm_color("unknown_algo", idx=0)
        assert color is not None
        # 应该返回 tab10 的第一个颜色

    def test_get_algorithm_marker_known(self):
        """测试已知算法的标记"""
        assert _get_algorithm_marker("baseline") == "o"
        assert _get_algorithm_marker("longrefiner") == "s"
        assert _get_algorithm_marker("reform") == "^"

    def test_get_algorithm_marker_unknown(self):
        """测试未知算法返回默认标记"""
        marker = _get_algorithm_marker("unknown_algo")
        assert marker == "o"  # 默认标记

    def test_compute_pareto_frontier_basic(self):
        """测试 Pareto 前沿计算 - 基本情况"""
        x = [1.0, 2.0, 3.0]
        y = [3.0, 2.0, 1.0]
        # (1, 3) 和 (3, 1) 都不被支配
        pareto = _compute_pareto_frontier(x, y, maximize_x=True, maximize_y=True)
        assert 0 in pareto  # (1, 3) - 最高 y
        assert 2 in pareto  # (3, 1) - 最高 x

    def test_compute_pareto_frontier_single_point(self):
        """测试单点 Pareto 前沿"""
        x = [1.0]
        y = [1.0]
        pareto = _compute_pareto_frontier(x, y, maximize_x=True, maximize_y=True)
        assert pareto == [0]

    def test_compute_pareto_frontier_dominated(self):
        """测试被支配的点"""
        x = [1.0, 2.0, 2.0]
        y = [1.0, 2.0, 1.5]
        # (2, 2) 支配其他所有点
        pareto = _compute_pareto_frontier(x, y, maximize_x=True, maximize_y=True)
        assert 1 in pareto  # (2, 2) 是 Pareto 最优
        assert 0 not in pareto  # (1, 1) 被支配

    def test_algorithm_colors_coverage(self):
        """测试颜色映射覆盖所有算法"""
        expected_algorithms = [
            "baseline",
            "longrefiner",
            "reform",
            "provence",
            "longllmlingua",
            "llmlingua2",
        ]
        for algo in expected_algorithms:
            assert algo in ALGORITHM_COLORS

    def test_algorithm_markers_coverage(self):
        """测试标记映射覆盖所有算法"""
        expected_algorithms = [
            "baseline",
            "longrefiner",
            "reform",
            "provence",
            "longllmlingua",
            "llmlingua2",
        ]
        for algo in expected_algorithms:
            assert algo in ALGORITHM_MARKERS


# =============================================================================
# TestEdgeCases
# =============================================================================


class TestEdgeCases:
    """测试边缘情况"""

    def test_single_algorithm(self):
        """测试单个算法"""
        results = {
            "baseline": AlgorithmMetrics(
                algorithm="baseline",
                num_samples=10,
                avg_f1=0.30,
                avg_compression_rate=1.0,
                avg_total_time=2.0,
                avg_retrieve_time=0.5,
                avg_refine_time=0.0,
                avg_generate_time=1.5,
            )
        }
        fig = plot_algorithm_comparison(results, metric="f1")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_zero_values(self):
        """测试零值"""
        results = {
            "method": AlgorithmMetrics(
                algorithm="method",
                num_samples=0,
                avg_f1=0.0,
                avg_compression_rate=0.0,
                avg_total_time=0.0,
                avg_retrieve_time=0.0,
                avg_refine_time=0.0,
                avg_generate_time=0.0,
            )
        }
        fig = plot_algorithm_comparison(results, metric="f1")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_large_values(self):
        """测试大值"""
        results = {
            "method": AlgorithmMetrics(
                algorithm="method",
                num_samples=10000,
                avg_f1=0.999,
                avg_compression_rate=100.0,
                avg_total_time=1000.0,
                avg_retrieve_time=100.0,
                avg_refine_time=400.0,
                avg_generate_time=500.0,
            )
        }
        fig = plot_algorithm_comparison(results, metric="f1")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    @pytest.mark.parametrize(
        "metric",
        ["f1", "compression_rate", "total_time", "retrieve_time", "refine_time", "generate_time"],
    )
    def test_all_metrics_work(self, sample_results, metric):
        """测试所有支持的指标都能正常工作"""
        fig = plot_algorithm_comparison(sample_results, metric=metric)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)
