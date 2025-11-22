"""
分析器 - 协调指标计算和结果可视化
"""

from pathlib import Path
from typing import Any

from sage.benchmark.benchmark_memory.evaluation.core.metric_interface import BaseMetric
from sage.benchmark.benchmark_memory.evaluation.core.result_loader import ResultLoader


class Analyzer:
    """实验结果分析器

    功能：
    1. 协调 ResultLoader、Metrics 和 DrawMethod
    2. 对单个或多个实验结果进行分析
    3. 生成指标报告和可视化图表

    使用流程：
    1. 加载结果：analyzer.load_results(folder_path)
    2. 注册指标：analyzer.register_metric(F1Score())
    3. 计算指标：analyzer.compute_metrics()
    4. 生成报告：analyzer.generate_report()
    5. 绘制图表：analyzer.plot_metrics()
    """

    def __init__(self, output_dir: str = "./analysis_output"):
        """初始化分析器

        Args:
            output_dir: 输出目录（报告和图表）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.loader: ResultLoader | None = None
        self.metrics: list[BaseMetric] = []
        self.results_data: list[dict[str, Any]] = []
        self.metric_results: dict[str, Any] = {}

    def load_results(self, folder_path: str) -> None:
        """加载实验结果

        Args:
            folder_path: 结果文件夹路径
        """
        print(f"\n{'=' * 60}")
        print("📂 加载实验结果")
        print(f"{'=' * 60}")

        self.loader = ResultLoader(folder_path)
        self.results_data = self.loader.get_all_results()

        summary = self.loader.get_summary()
        print(f"\n总计: {summary['total_files']} 个结果文件")
        print(f"任务: {', '.join(summary['task_ids'])}")

    def register_metric(self, metric: BaseMetric) -> None:
        """注册指标

        Args:
            metric: 指标实例（继承自 BaseMetric）
        """
        self.metrics.append(metric)
        print(f"✅ 已注册指标: {metric.name}")

    def compute_metrics(self, mode: str = "independent") -> dict[str, Any]:
        """计算指标

        Args:
            mode: 分析模式
                - "independent": 每个文件独立分析
                - "aggregate": 聚合所有文件分析（未来实现）

        Returns:
            Dict: 指标计算结果
        """
        print(f"\n{'=' * 60}")
        print(f"📊 计算指标 (模式: {mode})")
        print(f"{'=' * 60}\n")

        if mode == "independent":
            return self._compute_independent()
        elif mode == "aggregate":
            raise NotImplementedError("aggregate 模式尚未实现")
        else:
            raise ValueError(f"不支持的模式: {mode}")

    def _compute_independent(self) -> dict[str, Any]:
        """独立模式：每个文件单独计算指标"""
        results = {}

        for result_data in self.results_data:
            task_id = result_data.get("experiment_info", {}).get("task_id", "unknown")
            test_results = result_data.get("test_results", [])

            print(f"分析任务: {task_id}")

            task_metrics = {}
            for metric in self.metrics:
                # 计算每轮的指标值
                round_scores = metric.compute_all_rounds(test_results)

                # 计算整体统计
                overall_stats = metric.compute_overall(test_results)

                task_metrics[metric.name] = {
                    "round_scores": round_scores,
                    "overall": overall_stats,
                }

                print(f"  - {metric.name}: 平均 {overall_stats['mean']:.4f}")

            results[task_id] = task_metrics

        self.metric_results = results
        return results

    def generate_report(self, output_file: str = "report.txt") -> None:
        """生成文本报告

        Args:
            output_file: 报告文件名
        """
        if not self.metric_results:
            print("⚠️  请先调用 compute_metrics()")
            return

        report_path = self.output_dir / output_file

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("Memory Benchmark Analysis Report\n")
            f.write("=" * 60 + "\n\n")

            for task_id, task_metrics in self.metric_results.items():
                f.write(f"\n任务: {task_id}\n")
                f.write("-" * 60 + "\n")

                for metric_name, metric_data in task_metrics.items():
                    overall = metric_data["overall"]
                    f.write(f"\n{metric_name}:\n")
                    f.write(f"  平均值: {overall['mean']:.4f}\n")
                    f.write(f"  最大值: {overall['max']:.4f}\n")
                    f.write(f"  最小值: {overall['min']:.4f}\n")
                    f.write(f"  标准差: {overall['std']:.4f}\n")

                    # 每轮详细数据
                    round_scores = metric_data["round_scores"]
                    f.write(f"  各轮得分: {', '.join(f'{s:.4f}' for s in round_scores)}\n")

        print(f"\n📄 报告已生成: {report_path}")

    def plot_metrics(self, drawer_class=None) -> None:
        """绘制指标图表

        Args:
            drawer_class: 绘图器类（如 LineChart）
        """
        if not self.metric_results:
            print("⚠️  请先调用 compute_metrics()")
            return

        if drawer_class is None:
            from sage.benchmark.benchmark_memory.evaluation.draw_method import LineChart

            drawer_class = LineChart

        drawer = drawer_class(output_dir=str(self.output_dir))

        print(f"\n{'=' * 60}")
        print("📊 生成图表")
        print(f"{'=' * 60}\n")

        # 为每个任务生成图表
        for task_id, task_metrics in self.metric_results.items():
            # 单指标图表
            for metric_name, metric_data in task_metrics.items():
                round_scores = metric_data["round_scores"]
                drawer.plot_single_metric(
                    round_scores,
                    metric_name,
                    title=f"{task_id} - {metric_name}",
                    save_name=f"{task_id}_{metric_name}.png",
                )

            # 多指标对比图
            if len(task_metrics) > 1:
                metrics_data = {name: data["round_scores"] for name, data in task_metrics.items()}
                drawer.plot_multiple_metrics(
                    metrics_data,
                    title=f"{task_id} - 多指标对比",
                    save_name=f"{task_id}_multiple_metrics.png",
                )
