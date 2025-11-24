"""
Memory Benchmark Data Analyzer

实验结果数据分析主程序

使用方法：
    python data_analyze.py --folder .sage/benchmarks/benchmark_memory/locomo/251121 --mode independent
    python data_analyze.py --folder .sage/benchmarks/benchmark_memory/locomo/251121 --mode aggregate
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
from sage.common.config import find_sage_project_root

project_root = find_sage_project_root()
if project_root:
    sys.path.insert(0, str(project_root))

from sage.benchmark.benchmark_memory.evaluation.accuracy import F1Score
from sage.benchmark.benchmark_memory.evaluation.core import Analyzer


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Memory Benchmark 实验结果分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 独立模式分析（每个文件单独分析）
  python data_analyze.py --folder .sage/benchmarks/benchmark_memory/locomo/251121 --mode independent

  # 聚合模式分析（所有文件汇总分析，未来支持）
  python data_analyze.py --folder .sage/benchmarks/benchmark_memory/locomo/251121 --mode aggregate

  # 指定输出目录
  python data_analyze.py --folder .sage/benchmarks/benchmark_memory/locomo/251121 --output ./my_analysis
        """,
    )

    parser.add_argument(
        "--folder", type=str, required=True, help="实验结果文件夹路径（包含 JSON 文件）"
    )

    parser.add_argument(
        "--mode",
        type=str,
        default="independent",
        choices=["independent", "aggregate"],
        help="分析模式: independent（独立分析每个文件）或 aggregate（聚合分析所有文件）",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="./analysis_output",
        help="输出目录（默认: ./analysis_output）",
    )

    parser.add_argument(
        "--metrics", type=str, nargs="+", default=["F1"], help="要计算的指标列表（默认: F1）"
    )

    parser.add_argument("--no-plot", action="store_true", help="不生成图表")

    return parser.parse_args()


def get_metric_by_name(metric_name: str):
    """根据名称获取指标实例"""
    metric_map = {
        "F1": F1Score,
        # 未来可以添加更多指标
        # "Precision": PrecisionScore,
        # "Recall": RecallScore,
    }

    metric_class = metric_map.get(metric_name)
    if metric_class is None:
        available = ", ".join(metric_map.keys())
        raise ValueError(f"未知指标: {metric_name}。可用指标: {available}")

    return metric_class()


def main():
    """主函数"""
    args = parse_arguments()

    print("\n" + "=" * 60)
    print("Memory Benchmark Data Analyzer")
    print("=" * 60)
    print(f"文件夹: {args.folder}")
    print(f"模式: {args.mode}")
    print(f"输出: {args.output}")
    print(f"指标: {', '.join(args.metrics)}")
    print("=" * 60)

    # 检查文件夹是否存在
    folder_path = Path(args.folder)
    if not folder_path.exists():
        print(f"\n❌ 错误: 文件夹不存在: {args.folder}")
        sys.exit(1)

    try:
        # 创建分析器
        analyzer = Analyzer(output_dir=args.output)

        # 加载结果
        analyzer.load_results(args.folder)

        # 注册指标
        for metric_name in args.metrics:
            metric = get_metric_by_name(metric_name)
            analyzer.register_metric(metric)

        # 计算指标
        analyzer.compute_metrics(mode=args.mode)

        # 生成报告
        analyzer.generate_report()

        # 生成图表（如果需要）
        if not args.no_plot:
            analyzer.plot_metrics()

        print(f"\n{'=' * 60}")
        print("✅ 分析完成！")
        print(f"{'=' * 60}")
        print(f"输出目录: {args.output}")
        print("  - 报告: report.txt")
        if not args.no_plot:
            print("  - 图表: *.png")

    except FileNotFoundError as e:
        print(f"\n❌ 文件错误: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ 参数错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
