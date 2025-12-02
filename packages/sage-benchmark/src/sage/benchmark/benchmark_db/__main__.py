"""
Main entry point for running benchmarks
"""

import argparse

import yaml
from bench import BenchmarkRunner, StressTestConfig, get_algorithm
from bench.visualize import plot_results

# benchmark_anns 是独立项目，使用相对导入
from datasets import prepare_dataset


def load_config(config_path: str) -> dict:
    """加载 YAML 配置文件"""
    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Benchmark ANNS - Streaming Index Benchmark")
    parser.add_argument("--config", type=str, required=True, help="Path to config YAML file")
    parser.add_argument("--output", type=str, default=None, help="Output directory")
    parser.add_argument("--plot", action="store_true", help="Generate plots")

    args = parser.parse_args()

    # 加载配置
    print(f"Loading configuration from {args.config}")
    config = load_config(args.config)

    # 准备数据集
    dataset_name = config["dataset"]["name"]
    print(f"\nPreparing dataset: {dataset_name}")
    dataset = prepare_dataset(dataset_name)
    print(f"Dataset: {dataset}")

    # 获取算法
    algo_config = config["algorithm"]
    algo_name = algo_config["name"]
    algo_params = algo_config.get("parameters", {})
    print(f"\nInitializing algorithm: {algo_name}")
    algorithm = get_algorithm(algo_name, **algo_params)
    print(f"Algorithm: {algorithm}")

    # 创建测试配置
    test_config = config["test"]
    stress_config = StressTestConfig.from_dict(config.get("stress_test", {}))

    # 创建 runner
    print("\nCreating benchmark runner...")
    runner = BenchmarkRunner(
        algorithm=algorithm,
        dataset=dataset,
        config=stress_config,
        k=test_config.get("k", 10),
        num_workers=test_config.get("num_workers", 1),
    )

    # 运行测试
    print("\nStarting benchmark...")
    metrics = runner.run_stress_test()

    # 保存结果
    output_config = config.get("output", {})
    output_dir = args.output or output_config.get("output_dir", "results")

    import os

    os.makedirs(output_dir, exist_ok=True)

    if output_config.get("save_timestamps", True):
        timestamp_file = os.path.join(output_dir, "timestamps.csv")
        runner.save_results(timestamp_file)

    if output_config.get("save_results", True):
        from benchmark_anns.utils.io import save_results

        results_file = os.path.join(output_dir, "metrics.json")
        results = {
            "config": config,
            "metrics": {
                "throughput": metrics.throughput,
                "latency_p50": metrics.latency_p50,
                "latency_p95": metrics.latency_p95,
                "latency_p99": metrics.latency_p99,
                "drop_rate": metrics.drop_rate,
                "recall": metrics.recall,
            },
        }
        save_results(results, results_file)

    # 生成图表
    if args.plot or output_config.get("plot_results", False):
        timestamp_file = os.path.join(output_dir, "timestamps.csv")
        if os.path.exists(timestamp_file):
            plot_file = os.path.join(output_dir, "results.png")
            print("\nGenerating plots...")
            plot_results(timestamp_file, plot_file)

    print(f"\n✓ Benchmark complete! Results saved to {output_dir}")


if __name__ == "__main__":
    main()
