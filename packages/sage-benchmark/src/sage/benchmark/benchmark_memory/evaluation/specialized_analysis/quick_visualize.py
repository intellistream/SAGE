"""
Quick Visualize - 快速可视化脚本

生成基础图表，观察指标随轮次的变化趋势。

使用方法：
    python quick_visualize.py --input .sage/benchmarks/benchmark_memory/locomo/251121
    python quick_visualize.py --input metrics_results.json --mode from_metrics
"""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def load_metrics_from_json(file_path: Path) -> list:
    """从explore_metrics.py生成的结果文件加载指标"""
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def load_metrics_from_raw(folder_path: Path) -> list:
    """从原始实验结果计算指标"""
    # 调用 explore_metrics 的逻辑
    from explore_metrics import analyze_single_file

    json_files = list(folder_path.rglob("*.json"))
    results = []

    for json_file in json_files:
        try:
            result = analyze_single_file(json_file)
            results.append(result)
        except Exception as e:
            print(f"跳过文件 {json_file.name}: {e}")

    return results


def plot_metric_by_rounds(metrics_data: dict, output_path: Path):
    """绘制指标随轮次变化的折线图"""
    task_id = metrics_data["task_id"]
    rounds_data = metrics_data["rounds"]

    if not rounds_data:
        print(f"跳过 {task_id}: 无数据")
        return

    test_indices = [r["test_index"] for r in rounds_data]
    f1_scores = [r["f1"] for r in rounds_data]
    em_scores = [r["exact_match"] for r in rounds_data]

    plt.figure(figsize=(10, 6))

    plt.plot(test_indices, f1_scores, marker="o", label="F1 Score", linewidth=2)
    plt.plot(test_indices, em_scores, marker="s", label="Exact Match", linewidth=2)

    plt.xlabel("Test Round", fontsize=12)
    plt.ylabel("Score", fontsize=12)
    plt.title(f"Metrics over Rounds - {task_id}", fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)

    # 保存图表
    output_file = output_path / f"{task_id}_metrics.png"
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"✅ 图表已保存: {output_file}")


def plot_overall_comparison(all_metrics: list, output_path: Path):
    """绘制不同任务的整体对比"""
    if len(all_metrics) <= 1:
        return

    task_ids = [m["task_id"] for m in all_metrics]
    avg_f1s = [m["overall"]["avg_f1"] for m in all_metrics]
    avg_ems = [m["overall"]["avg_exact_match"] for m in all_metrics]

    x = range(len(task_ids))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar([i - width / 2 for i in x], avg_f1s, width, label="Avg F1", alpha=0.8)
    ax.bar([i + width / 2 for i in x], avg_ems, width, label="Avg Exact Match", alpha=0.8)

    ax.set_xlabel("Task ID", fontsize=12)
    ax.set_ylabel("Score", fontsize=12)
    ax.set_title("Overall Metrics Comparison", fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(task_ids, rotation=45, ha="right")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    output_file = output_path / "overall_comparison.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"✅ 对比图已保存: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="快速可视化脚本")
    parser.add_argument("--input", type=str, required=True, help="输入路径（文件夹或metrics_results.json）")
    parser.add_argument(
        "--mode",
        type=str,
        default="auto",
        choices=["auto", "from_raw", "from_metrics"],
        help="加载模式",
    )
    parser.add_argument("--output", type=str, default="./results/plots", help="输出目录")
    parser.add_argument("--metric", type=str, help="只画特定指标（f1, em）")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"📈 快速可视化")
    print(f"{'=' * 60}\n")

    # 加载数据
    if args.mode == "from_metrics" or (args.mode == "auto" and input_path.is_file()):
        print(f"从指标文件加载: {input_path}")
        all_metrics = load_metrics_from_json(input_path)
    else:
        print(f"从原始结果加载: {input_path}")
        all_metrics = load_metrics_from_raw(input_path)

    if not all_metrics:
        print("❌ 未找到数据")
        return

    print(f"找到 {len(all_metrics)} 个任务的数据\n")

    # 为每个任务生成图表
    for metrics_data in all_metrics:
        plot_metric_by_rounds(metrics_data, output_path)

    # 生成整体对比图
    if len(all_metrics) > 1:
        print()
        plot_overall_comparison(all_metrics, output_path)

    print(f"\n{'=' * 60}")
    print("✨ 可视化完成")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
