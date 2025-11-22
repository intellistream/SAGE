"""
折线图绘制方法 - 用于展示指标随测试轮次的变化
"""

from pathlib import Path

import matplotlib.pyplot as plt


class LineChart:
    """折线图绘制器

    功能：
    1. 绘制单个指标随测试轮次的变化（如 F1 vs 轮次）
    2. 绘制多个指标对比（如 F1、Precision、Recall 在同一张图）
    3. 支持多个实验结果对比（不同配置的横向对比）
    """

    def __init__(self, output_dir: str = "./output"):
        """初始化折线图绘制器

        Args:
            output_dir: 图表输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 设置中文字体（避免乱码）
        plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False

    def plot_single_metric(
        self,
        round_scores: list[float],
        metric_name: str,
        title: str = "",
        save_name: str = "metric_by_round.png",
    ) -> None:
        """绘制单个指标随轮次变化的折线图

        Args:
            round_scores: 每轮的指标值列表
            metric_name: 指标名称（如 "F1 Score"）
            title: 图表标题
            save_name: 保存的文件名
        """
        plt.figure(figsize=(10, 6))

        rounds = list(range(1, len(round_scores) + 1))
        plt.plot(rounds, round_scores, marker="o", linewidth=2, markersize=8)

        plt.xlabel("测试轮次", fontsize=12)
        plt.ylabel(metric_name, fontsize=12)
        plt.title(title or f"{metric_name} vs 测试轮次", fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        save_path = self.output_dir / save_name
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"📊 图表已保存: {save_path}")

    def plot_multiple_metrics(
        self,
        metrics_data: dict[str, list[float]],
        title: str = "多指标对比",
        save_name: str = "multiple_metrics.png",
    ) -> None:
        """绘制多个指标对比图

        Args:
            metrics_data: 指标数据字典 {"F1": [0.8, 0.85, ...], "Precision": [...]}
            title: 图表标题
            save_name: 保存的文件名
        """
        plt.figure(figsize=(12, 7))

        for metric_name, scores in metrics_data.items():
            rounds = list(range(1, len(scores) + 1))
            plt.plot(rounds, scores, marker="o", linewidth=2, markersize=6, label=metric_name)

        plt.xlabel("测试轮次", fontsize=12)
        plt.ylabel("指标值", fontsize=12)
        plt.title(title, fontsize=14)
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        save_path = self.output_dir / save_name
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"📊 图表已保存: {save_path}")

    def plot_experiment_comparison(
        self,
        experiments_data: dict[str, list[float]],
        metric_name: str,
        title: str = "",
        save_name: str = "experiment_comparison.png",
    ) -> None:
        """绘制不同实验配置的对比图

        Args:
            experiments_data: 实验数据 {"STM-3": [0.8, 0.85, ...], "STM-5": [...]}
            metric_name: 指标名称
            title: 图表标题
            save_name: 保存的文件名
        """
        plt.figure(figsize=(12, 7))

        for exp_name, scores in experiments_data.items():
            rounds = list(range(1, len(scores) + 1))
            plt.plot(rounds, scores, marker="o", linewidth=2, markersize=6, label=exp_name)

        plt.xlabel("测试轮次", fontsize=12)
        plt.ylabel(metric_name, fontsize=12)
        plt.title(title or f"{metric_name} - 不同配置对比", fontsize=14)
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        save_path = self.output_dir / save_name
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"📊 图表已保存: {save_path}")


if __name__ == "__main__":
    # 测试示例
    drawer = LineChart(output_dir="./test_output")

    # 测试 1: 单个指标
    f1_scores = [0.65, 0.72, 0.78, 0.82, 0.85, 0.87, 0.88, 0.89, 0.90, 0.91]
    drawer.plot_single_metric(f1_scores, "F1 Score", save_name="test_f1.png")

    # 测试 2: 多指标对比
    metrics_data = {
        "F1": f1_scores,
        "Precision": [0.70, 0.75, 0.80, 0.83, 0.86, 0.88, 0.89, 0.90, 0.91, 0.92],
        "Recall": [0.60, 0.69, 0.76, 0.81, 0.84, 0.86, 0.87, 0.88, 0.89, 0.90],
    }
    drawer.plot_multiple_metrics(metrics_data, save_name="test_multiple.png")

    # 测试 3: 实验对比
    exp_data = {
        "STM-3": f1_scores,
        "STM-5": [0.68, 0.74, 0.80, 0.84, 0.87, 0.89, 0.90, 0.91, 0.92, 0.93],
        "STM-7": [0.70, 0.76, 0.82, 0.86, 0.88, 0.90, 0.91, 0.92, 0.93, 0.94],
    }
    drawer.plot_experiment_comparison(exp_data, "F1 Score", save_name="test_comparison.png")

    print("\n✅ 测试完成，图表已生成到 ./test_output/")
