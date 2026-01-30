#!/usr/bin/env python3
"""
Workload 4 执行脚本
==================

用法:
    # 使用默认配置
    python run_workload4.py

    # 使用命令行参数
    python run_workload4.py --num-tasks 100 --duration 1200 --query-qps 40 --doc-qps 25

    # 使用配置文件
    python run_workload4.py --config workload4_config.yaml

    # 指定调度器
    python run_workload4.py --scheduler load_aware --num-tasks 200

    # 调试模式（小规模）
    python run_workload4.py --debug
"""

import argparse
import logging
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# 添加 SAGE 到路径
SAGE_ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(SAGE_ROOT / "packages" / "sage-kernel" / "src"))
sys.path.insert(0, str(SAGE_ROOT / "packages" / "sage-common" / "src"))
sys.path.insert(0, str(SAGE_ROOT / "packages" / "sage-libs" / "src"))
sys.path.insert(0, str(SAGE_ROOT / "packages" / "sage-benchmark" / "src"))

from workload4.config import Workload4Config
from workload4.pipeline import Workload4Pipeline

# =============================================================================
# 日志配置
# =============================================================================


def setup_logging(verbose: bool = False, log_file: str | None = None) -> None:
    """配置日志系统"""
    log_level = logging.DEBUG if verbose else logging.INFO

    # 日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )


# =============================================================================
# 命令行参数解析
# =============================================================================


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Run Workload 4 Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_workload4.py --num-tasks 100 --duration 1200
  python run_workload4.py --config workload4.yaml --verbose
  python run_workload4.py --debug  # 快速调试模式
        """,
    )

    # === 配置文件 ===
    parser.add_argument("--config", "-c", type=str, help="配置文件路径（YAML 格式）")

    # === 基础配置 ===
    parser.add_argument("--num-tasks", "-n", type=int, default=100, help="任务数量（默认: 100）")

    parser.add_argument(
        "--duration", "-d", type=int, default=1200, help="运行时长（秒，默认: 1200 = 20分钟）"
    )

    parser.add_argument(
        "--use-remote", action="store_true", default=True, help="使用分布式环境（默认: True）"
    )

    parser.add_argument("--num-nodes", type=int, default=8, help="分布式节点数量（默认: 8）")

    # === 双流配置 ===
    parser.add_argument("--query-qps", type=float, default=40.0, help="查询流 QPS（默认: 40.0）")

    parser.add_argument("--doc-qps", type=float, default=25.0, help="文档流 QPS（默认: 25.0）")

    # === Join 配置 ===
    parser.add_argument("--join-window", type=int, default=60, help="Join 窗口大小（秒，默认: 60）")

    parser.add_argument(
        "--join-threshold", type=float, default=0.70, help="Join 相似度阈值（默认: 0.70）"
    )

    parser.add_argument("--join-parallelism", type=int, default=16, help="Join 并行度（默认: 16）")

    # === VDB 配置 ===
    parser.add_argument("--vdb-top-k", type=int, default=20, help="VDB 检索 top-k（默认: 20）")

    # === 调度器配置 ===
    parser.add_argument(
        "--scheduler",
        "-s",
        type=str,
        default="load_aware",
        choices=["fifo", "load_aware", "priority", "adaptive"],
        help="调度策略（默认: load_aware）",
    )

    parser.add_argument(
        "--scheduler-strategy", type=str, default="adaptive", help="调度器策略（默认: adaptive）"
    )

    # === 输出配置 ===
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="/tmp/sage_metrics_workload4",
        help="指标输出目录（默认: /tmp/sage_metrics_workload4）",
    )

    parser.add_argument("--log-file", type=str, help="日志文件路径（可选）")

    # === 调试和监控 ===
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出（DEBUG 日志）")

    parser.add_argument("--debug", action="store_true", help="调试模式（小规模快速测试）")

    parser.add_argument("--no-profiling", action="store_true", help="禁用性能分析")

    parser.add_argument("--dry-run", action="store_true", help="仅显示配置，不实际运行")

    # === 服务端点配置 ===
    parser.add_argument(
        "--llm-url",
        type=str,
        default="http://11.11.11.7:8904/v1",
        help="LLM 服务 URL（默认: http://11.11.11.7:8904/v1）",
    )

    parser.add_argument(
        "--embedding-url",
        type=str,
        default="http://11.11.11.7:8090/v1",
        help="Embedding 服务 URL（默认: http://11.11.11.7:8090/v1）",
    )

    return parser.parse_args()


# =============================================================================
# 配置加载和验证
# =============================================================================


def load_config(args: argparse.Namespace) -> Workload4Config:
    """加载配置

    优先级: 配置文件 > 命令行参数 > 默认值
    """
    config_dict: dict[str, Any] = {}

    # 1. 从配置文件加载（如果提供）
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path) as f:
            config_dict = yaml.safe_load(f) or {}

        logging.info(f"从配置文件加载: {config_path}")

    # 2. 命令行参数覆盖（如果提供了非默认值）
    if args.debug:
        # 调试模式：小规模快速测试
        config_dict.update(
            {
                "num_tasks": 10,
                "duration": 60,
                "query_qps": 2.0,
                "doc_qps": 1.5,
                "join_window_seconds": 30,
                "num_nodes": 2,
                "enable_profiling": False,
            }
        )
        logging.info("使用调试模式配置")
    else:
        # 正常模式：使用命令行参数
        config_dict.update(
            {
                "num_tasks": args.num_tasks,
                "duration": args.duration,
                "use_remote": args.use_remote,
                "num_nodes": args.num_nodes,
                "query_qps": args.query_qps,
                "doc_qps": args.doc_qps,
                "join_window_seconds": args.join_window,
                "join_threshold": args.join_threshold,
                "join_parallelism": args.join_parallelism,
                "vdb1_top_k": args.vdb_top_k,
                "vdb2_top_k": args.vdb_top_k,
                "scheduler_type": args.scheduler,
                "scheduler_strategy": args.scheduler_strategy,
                "metrics_output_dir": args.output_dir,
                "enable_profiling": not args.no_profiling,
                "llm_base_url": args.llm_url,
                "embedding_base_url": args.embedding_url,
            }
        )

    # 3. 创建配置对象
    config = Workload4Config(**config_dict)

    # 4. 验证配置
    config.validate()

    return config


# =============================================================================
# 实时监控和显示
# =============================================================================


class ProgressMonitor:
    """进度监控器"""

    def __init__(self, total_tasks: int, duration: int):
        self.total_tasks = total_tasks
        self.duration = duration
        self.start_time = time.time()
        self.last_update = time.time()

    def print_header(self) -> None:
        """打印表头"""
        print("\n" + "=" * 80)
        print("Workload 4 Benchmark - 实时监控")
        print("=" * 80)
        print(f"{'时间':^12} | {'已运行':^10} | {'进度':^10} | {'状态':^30}")
        print("-" * 80)

    def update(self, status: str = "运行中") -> None:
        """更新进度显示"""
        now = time.time()

        # 每5秒更新一次
        if now - self.last_update < 5:
            return

        elapsed = now - self.start_time
        progress = min(100, (elapsed / self.duration) * 100)

        timestamp = datetime.now().strftime("%H:%M:%S")
        elapsed_str = f"{int(elapsed)}s"
        progress_str = f"{progress:.1f}%"

        print(f"{timestamp:^12} | {elapsed_str:^10} | {progress_str:^10} | {status:^30}")

        self.last_update = now

    def print_footer(self, success: bool = True) -> None:
        """打印结束信息"""
        elapsed = time.time() - self.start_time
        print("-" * 80)
        if success:
            print(f"✓ Benchmark 完成！总耗时: {elapsed:.2f}s")
        else:
            print(f"✗ Benchmark 失败！运行时间: {elapsed:.2f}s")
        print("=" * 80 + "\n")


def print_config_summary(config: Workload4Config) -> None:
    """打印配置摘要"""
    print("\n" + "=" * 80)
    print("Workload 4 配置摘要")
    print("=" * 80)

    print("\n【基础配置】")
    print(f"  任务数量:        {config.num_tasks}")
    print(f"  运行时长:        {config.duration}s ({config.duration // 60}分钟)")
    print(f"  分布式节点:      {config.num_nodes}")
    print(f"  调度策略:        {config.scheduler_type} ({config.scheduler_strategy})")

    print("\n【双流配置】")
    print(f"  查询流 QPS:      {config.query_qps}")
    print(f"  文档流 QPS:      {config.doc_qps}")
    print(f"  预计查询数:      {int(config.query_qps * config.duration)}")
    print(f"  预计文档数:      {int(config.doc_qps * config.duration)}")

    print("\n【Semantic Join】")
    print(f"  窗口大小:        {config.join_window_seconds}s")
    print(f"  相似度阈值:      {config.join_threshold}")
    print(f"  并行度:          {config.join_parallelism}")
    print(f"  窗口文档数:      ~{int(config.doc_qps * config.join_window_seconds)}")

    print("\n【VDB 检索】")
    print(f"  VDB1 top-k:      {config.vdb1_top_k}")
    print(f"  VDB2 top-k:      {config.vdb2_top_k}")
    print(f"  过滤阈值:        {config.vdb_filter_threshold}")
    print(f"  并行度:          {config.vdb_parallelism}")

    print("\n【图遍历】")
    print(f"  最大深度:        {config.graph_max_depth}")
    print(f"  最大节点数:      {config.graph_max_nodes}")
    print(f"  Beam 宽度:       {config.graph_bfs_beam_width}")

    print("\n【聚类去重】")
    print(f"  算法:            {config.clustering_algorithm.upper()}")
    print(f"  DBSCAN eps:      {config.dbscan_eps}")
    print(f"  最小样本数:      {config.dbscan_min_samples}")

    print("\n【重排序】")
    print(f"  Top-K:           {config.rerank_top_k}")
    print("  评分权重:")
    for dim, weight in config.rerank_score_weights.items():
        print(f"    - {dim:12s}: {weight:.2f}")
    print(f"  MMR lambda:      {config.mmr_lambda}")

    print("\n【批处理】")
    print(f"  Category 批大小: {config.category_batch_size}")
    print(f"  Category 超时:   {config.category_batch_timeout_ms}ms")
    print(f"  Global 批大小:   {config.global_batch_size}")
    print(f"  Global 超时:     {config.global_batch_timeout_ms}ms")

    print("\n【服务端点】")
    print(f"  LLM:             {config.llm_base_url}")
    print(f"  LLM Model:       {config.llm_model}")
    print(f"  Embedding:       {config.embedding_base_url}")
    print(f"  Embedding Model: {config.embedding_model}")

    print("\n【输出配置】")
    print(f"  指标目录:        {config.metrics_output_dir}")
    print(f"  性能分析:        {'启用' if config.enable_profiling else '禁用'}")

    print("=" * 80 + "\n")


def print_metrics_summary(metrics_dir: Path) -> None:
    """打印指标摘要"""
    if not metrics_dir.exists():
        logging.warning(f"指标目录不存在: {metrics_dir}")
        return

    # 查找 CSV 文件
    csv_files = list(metrics_dir.glob("*.csv"))
    if not csv_files:
        logging.warning(f"未找到指标文件: {metrics_dir}")
        return

    print("\n" + "=" * 80)
    print("指标文件摘要")
    print("=" * 80)

    for csv_file in sorted(csv_files):
        size_kb = csv_file.stat().st_size / 1024
        print(f"  {csv_file.name:40s}  {size_kb:>10.2f} KB")

    print("\n分析指标请运行:")
    print(f"  python analyze_detailed_with_csv.py {metrics_dir.name}")
    print("=" * 80 + "\n")


# =============================================================================
# 主函数
# =============================================================================


def main() -> int:
    """主函数"""
    try:
        # 1. 解析参数
        args = parse_args()

        # 2. 配置日志
        log_file = args.log_file
        if not log_file and not args.dry_run:
            # 自动生成日志文件
            log_dir = Path(args.output_dir) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = str(log_dir / f"workload4_{timestamp}.log")

        setup_logging(verbose=args.verbose, log_file=log_file)

        logging.info("=" * 80)
        logging.info("Workload 4 Benchmark 启动")
        logging.info("=" * 80)

        # 3. 加载配置
        config = load_config(args)
        print_config_summary(config)

        # 4. Dry run 模式
        if args.dry_run:
            logging.info("Dry run 模式 - 仅显示配置，不执行")
            return 0

        # 5. 检查环境变量
        required_vars = ["OPENAI_API_KEY", "HF_TOKEN"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logging.warning(f"缺少环境变量: {', '.join(missing_vars)}")
            logging.warning("某些功能可能无法正常工作")

        # 6. 构建 pipeline
        logging.info("正在构建 Workload 4 Pipeline...")
        pipeline = Workload4Pipeline(config)
        pipeline.build(name="workload4_benchmark")
        logging.info("✓ Pipeline 构建完成")

        # 7. 运行 benchmark
        logging.info("开始运行 Benchmark...")

        monitor = ProgressMonitor(config.num_tasks, config.duration)
        monitor.print_header()

        start_time = time.time()

        try:
            # 运行 pipeline
            metrics = pipeline.run()

            elapsed = time.time() - start_time
            monitor.print_footer(success=True)

            # 8. 打印结果摘要
            logging.info(f"Benchmark 完成！总耗时: {elapsed:.2f}s")

            if metrics:
                logging.info("=" * 80)
                logging.info("性能指标摘要")
                logging.info("=" * 80)
                logging.info(f"端到端延迟: {metrics.end_to_end_time:.2f}s")
                logging.info(f"CPU 时间:    {metrics.cpu_time:.2f}s")
                logging.info(f"内存峰值:    {metrics.memory_peak_mb:.2f}MB")
                logging.info("=" * 80)

            # 9. 打印指标文件摘要
            metrics_dir = Path(config.metrics_output_dir)
            print_metrics_summary(metrics_dir)

            logging.info("✓ 所有任务完成")
            return 0

        except KeyboardInterrupt:
            logging.warning("用户中断 Benchmark")
            monitor.print_footer(success=False)
            return 130  # SIGINT exit code

        except Exception as e:
            logging.error(f"运行时错误: {e}")
            logging.debug(traceback.format_exc())
            monitor.print_footer(success=False)
            return 1

    except Exception as e:
        logging.error(f"初始化失败: {e}")
        logging.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
