#!/usr/bin/env python3
"""
Section 5.3.2: Scaling Analysis

测试方法在不同规模下的性能变化。

分析内容:
1. Tool Set Size Scaling - 工具数量对准确率的影响
2. LLM Size Scaling - 模型大小对性能的影响

输出:
- figures/fig5_analysis_scaling_tool_count.pdf
- figures/fig6_analysis_scaling_llm_size.pdf
- tables/table_scaling_results.tex

Usage:
    python exp_analysis_scaling.py
    python exp_analysis_scaling.py --tool-scaling
    python exp_analysis_scaling.py --llm-scaling
"""

from __future__ import annotations

import argparse
import time
from typing import Any

from .exp_utils import (
    get_figures_dir,
    load_benchmark_data,
    print_section_header,
    print_subsection_header,
    save_results,
    setup_experiment_env,
)

# =============================================================================
# Tool Set Size Scaling
# =============================================================================

TOOL_SCALE_POINTS = [10, 25, 50, 100, 200, 500]


def run_tool_scaling_experiment(
    max_samples: int = 50,
    strategies: list[str] = None,
    verbose: bool = True,
) -> dict[str, list[tuple[int, float, float]]]:
    """
    运行工具数量 Scaling 实验。

    Args:
        max_samples: 每个规模点的最大测试样本数
        strategies: 要测试的策略列表
        verbose: 是否打印详细信息

    Returns:
        {strategy: [(tool_count, accuracy, latency_ms), ...]}
    """
    print_subsection_header("Tool Set Size Scaling")

    if strategies is None:
        strategies = ["selector.keyword", "selector.embedding", "selector.hybrid"]

    # 加载基础数据
    samples = load_benchmark_data("selection", split="test", max_samples=max_samples)
    if not samples:
        print("  ❌ No selection data available")
        return {}

    # 加载或生成 noise tools
    noise_tools = _generate_noise_tools(1000)

    try:
        from sage.benchmark.benchmark_agent import get_adapter_registry

        registry = get_adapter_registry()
    except ImportError:
        print("  ❌ Failed to import adapter registry")
        return {}

    results = {s: [] for s in strategies}

    for scale in TOOL_SCALE_POINTS:
        print(f"\n    Scale: {scale} tools")

        for strategy_name in strategies:
            try:
                selector = registry.get(strategy_name)
            except Exception as e:
                print(f"      ⚠️  {strategy_name}: {e}")
                continue

            # 运行测试
            hits = 0
            total_time = 0.0

            for sample in samples:
                query = sample.get("instruction", "")
                base_tools = sample.get("candidate_tools", [])
                ground_truth = sample.get("ground_truth", [])

                # 扩展工具集到目标规模
                extended_tools = _extend_tool_set(base_tools, noise_tools, scale)

                start = time.time()
                try:
                    predictions = selector.select(query, candidate_tools=extended_tools, top_k=5)
                    pred_ids = (
                        [p.tool_id if hasattr(p, "tool_id") else str(p) for p in predictions]
                        if predictions
                        else []
                    )

                    ref_set = (
                        set(ground_truth) if isinstance(ground_truth, list) else {ground_truth}
                    )
                    if set(pred_ids[:5]) & ref_set:
                        hits += 1
                except Exception:
                    pass

                total_time += time.time() - start

            accuracy = hits / len(samples) if samples else 0
            avg_latency = total_time * 1000 / len(samples) if samples else 0

            results[strategy_name].append((scale, accuracy, avg_latency))

            if verbose:
                print(
                    f"      {strategy_name.split('.')[-1]:12s}: {accuracy * 100:5.1f}% ({avg_latency:.1f}ms)"
                )

    return results


def _generate_noise_tools(count: int) -> list[str]:
    """生成干扰工具。"""
    import random

    categories = ["search", "calendar", "email", "file", "math", "weather", "news", "social"]
    actions = ["get", "set", "create", "delete", "update", "list", "find", "check"]

    tools = []
    for i in range(count):
        cat = random.choice(categories)
        action = random.choice(actions)
        tools.append(f"noise_{cat}_{action}_{i:04d}")

    return tools


def _extend_tool_set(base_tools: list[str], noise_tools: list[str], target_size: int) -> list[str]:
    """扩展工具集到目标大小。"""
    import random

    result = list(base_tools)
    needed = target_size - len(result)

    if needed > 0:
        available_noise = [t for t in noise_tools if t not in result]
        result.extend(random.sample(available_noise, min(needed, len(available_noise))))

    return result[:target_size]


# =============================================================================
# LLM Size Scaling
# =============================================================================

# 模型列表 (按参数规模排序)
# 2x A100 80GB 可支持到 14B 模型单卡运行
LLM_MODELS = [
    # 小模型
    ("Qwen/Qwen2.5-0.5B-Instruct", "0.5B", 1),  # ~1GB VRAM
    ("Qwen/Qwen2.5-1.5B-Instruct", "1.5B", 1),  # ~3GB VRAM
    ("Qwen/Qwen2.5-3B-Instruct", "3B", 1),  # ~6GB VRAM
    # 中等模型
    ("Qwen/Qwen2.5-7B-Instruct", "7B", 1),  # ~14GB VRAM
    ("Qwen/Qwen2.5-14B-Instruct", "14B", 1),  # ~28GB VRAM
]

# 备选：如果 Qwen 下载慢，可用 Llama
LLM_MODELS_LLAMA = [
    ("meta-llama/Llama-3.2-1B-Instruct", "1B", 1),
    ("meta-llama/Llama-3.2-3B-Instruct", "3B", 1),
    ("meta-llama/Llama-3.1-8B-Instruct", "8B", 1),
]


def _start_vllm_server(model_id: str, tensor_parallel: int = 1, port: int = 8901) -> bool:
    """
    启动 vLLM 服务器。

    Args:
        model_id: HuggingFace 模型 ID
        tensor_parallel: Tensor Parallel 数量 (GPU 数)
        port: 服务端口

    Returns:
        是否成功启动
    """
    import subprocess
    import time

    import requests

    # 先停止已有服务
    _stop_vllm_server(port)
    time.sleep(2)

    print(f"      Starting vLLM server for {model_id}...")

    cmd = [
        "vllm",
        "serve",
        model_id,
        "--port",
        str(port),
        "--gpu-memory-utilization",
        "0.85",
        "--max-model-len",
        "4096",
        "--trust-remote-code",
    ]

    if tensor_parallel > 1:
        cmd.extend(["--tensor-parallel-size", str(tensor_parallel)])

    # 后台启动
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except Exception as e:
        print(f"      Failed to start vLLM: {e}")
        return False

    # 等待服务就绪 (最多 5 分钟)
    max_wait = 300
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            resp = requests.get(f"http://localhost:{port}/v1/models", timeout=5)
            if resp.status_code == 200:
                print(f"      vLLM server ready (took {time.time() - start_time:.0f}s)")
                return True
        except Exception:
            pass
        time.sleep(5)

    print("      Timeout waiting for vLLM server")
    return False


def _stop_vllm_server(port: int = 8901) -> None:
    """停止 vLLM 服务器。"""
    import subprocess

    # 通过端口找进程并杀掉
    try:
        result = subprocess.run(
            ["lsof", "-t", f"-i:{port}"],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                subprocess.run(["kill", "-9", pid], capture_output=True)
    except Exception:
        pass


def _test_llm_on_challenge(
    model_id: str,
    samples: list[dict],
    challenge: str,
    port: int = 8901,
) -> tuple[float, float]:
    """
    在指定 Challenge 上测试 LLM 性能。

    Returns:
        (accuracy, avg_latency_ms)
    """
    import time

    import requests

    base_url = f"http://localhost:{port}/v1"

    correct = 0
    total_latency = 0.0
    tested = 0

    for sample in samples:
        query = sample.get("instruction", sample.get("query", ""))
        ground_truth = sample.get("ground_truth", sample.get("label", ""))

        # 构建 prompt
        if challenge == "timing":
            prompt = f"""判断以下用户请求是否需要调用外部工具。只回答 "yes" 或 "no"。

用户请求: {query}

回答:"""
        elif challenge == "planning":
            tools = sample.get("candidate_tools", [])
            tool_str = ", ".join(tools[:10]) if tools else "search, calculate, weather"
            prompt = f"""根据用户请求，生成工具调用计划。可用工具: {tool_str}

用户请求: {query}

计划 (JSON 格式):"""
        else:  # selection
            tools = sample.get("candidate_tools", [])
            tool_str = "\n".join([f"- {t}" for t in tools[:20]])
            prompt = f"""从以下工具中选择最适合的工具来完成用户请求。

可用工具:
{tool_str}

用户请求: {query}

选择的工具 (只输出工具名):"""

        try:
            start = time.time()
            resp = requests.post(
                f"{base_url}/completions",
                json={
                    "model": model_id,
                    "prompt": prompt,
                    "max_tokens": 256,
                    "temperature": 0.1,
                },
                timeout=60,
            )
            latency = (time.time() - start) * 1000

            if resp.status_code == 200:
                result = resp.json()
                output = result.get("choices", [{}])[0].get("text", "").strip().lower()

                # 简单评估
                if challenge == "timing":
                    pred = "yes" in output or "需要" in output
                    label = (
                        ground_truth
                        if isinstance(ground_truth, bool)
                        else str(ground_truth).lower() in ["yes", "true", "1"]
                    )
                    if pred == label:
                        correct += 1
                elif challenge == "planning":
                    # 检查是否包含正确工具
                    if isinstance(ground_truth, list):
                        if any(t.lower() in output for t in ground_truth):
                            correct += 1
                    elif str(ground_truth).lower() in output:
                        correct += 1
                else:  # selection
                    if isinstance(ground_truth, list):
                        if any(t.lower() in output for t in ground_truth):
                            correct += 1
                    elif str(ground_truth).lower() in output:
                        correct += 1

                total_latency += latency
                tested += 1

        except Exception as e:
            print(f"        Error: {e}")
            continue

    accuracy = correct / tested if tested > 0 else 0.0
    avg_latency = total_latency / tested if tested > 0 else 0.0

    return accuracy, avg_latency


def run_llm_scaling_experiment(
    max_samples: int = 30,
    challenge: str = "planning",
    models: list = None,
    verbose: bool = True,
) -> dict[str, list[tuple[str, float, float]]]:
    """
    运行 LLM 大小 Scaling 实验 (真实测试)。

    Args:
        max_samples: 最大测试样本数
        challenge: 测试的 Challenge (planning 最能体现差异)
        models: 要测试的模型列表 (None 使用默认)
        verbose: 是否打印详细信息

    Returns:
        {metric: [(model_size, value, latency_ms), ...]}
    """
    print_subsection_header("LLM Size Scaling (Real Test)")

    if models is None:
        models = LLM_MODELS

    samples = load_benchmark_data(challenge, split="test", max_samples=max_samples)
    if not samples:
        print(f"  No {challenge} data available")
        return {}

    print(f"    Testing {len(models)} models on {len(samples)} samples")
    print(f"    Challenge: {challenge}")

    results = {"accuracy": [], "latency": []}
    port = 8901

    for model_id, model_size, tensor_parallel in models:
        print(f"\n    [{model_size}] {model_id}")

        # 启动 vLLM 服务
        if not _start_vllm_server(model_id, tensor_parallel, port):
            print(f"      Skipping {model_size} (failed to start)")
            continue

        try:
            # 运行测试
            accuracy, avg_latency = _test_llm_on_challenge(model_id, samples, challenge, port)

            results["accuracy"].append((model_size, accuracy, avg_latency))

            if verbose:
                print(f"      Accuracy: {accuracy * 100:.1f}%")
                print(f"      Avg Latency: {avg_latency:.0f}ms")

        finally:
            # 停止服务，释放 GPU 内存
            _stop_vllm_server(port)
            import time

            time.sleep(5)  # 等待 GPU 内存释放

    return results


# =============================================================================
# Main Experiment
# =============================================================================


def run_scaling_analysis(
    tool_scaling: bool = True,
    llm_scaling: bool = True,
    max_samples: int = 50,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    运行完整的 Scaling 分析。
    """
    setup_experiment_env(verbose=verbose)

    print_section_header("Section 5.3.2: Scaling Analysis")

    all_results = {}

    if tool_scaling:
        tool_results = run_tool_scaling_experiment(max_samples=max_samples, verbose=verbose)
        all_results["tool_scaling"] = tool_results

        # 分析结果
        if tool_results:
            print("\n    Tool Scaling Summary:")
            for strategy, data in tool_results.items():
                if data:
                    # 计算性能下降率
                    first_acc = data[0][1]
                    last_acc = data[-1][1]
                    drop_rate = (first_acc - last_acc) / first_acc if first_acc > 0 else 0
                    print(
                        f"      {strategy}: {first_acc * 100:.1f}% → {last_acc * 100:.1f}% (drop: {drop_rate * 100:.1f}%)"
                    )

    if llm_scaling:
        llm_results = run_llm_scaling_experiment(max_samples=max_samples, verbose=verbose)
        all_results["llm_scaling"] = llm_results

    # 保存结果
    output_file = save_results(all_results, "5_3_analysis", "scaling_analysis")
    print(f"\n  Results saved to: {output_file}")

    # 生成图表
    _generate_scaling_figures(all_results)

    return all_results


def _generate_scaling_figures(results: dict) -> None:
    """生成 Scaling 分析图表。"""
    try:
        from figure_generator import plot_scaling_curve

        figures_dir = get_figures_dir()

        # Tool scaling curve
        if "tool_scaling" in results and results["tool_scaling"]:
            tool_data = {}
            for strategy, data in results["tool_scaling"].items():
                tool_data[strategy.split(".")[-1]] = [(d[0], d[1]) for d in data]

            plot_scaling_curve(
                tool_data,
                x_label="Number of Candidate Tools",
                y_label="Top-5 Accuracy (%)",
                title="Tool Set Size Scaling",
                output_path=figures_dir / "fig5_analysis_scaling_tool_count.pdf",
                log_x=True,
            )
            print("  Figure saved: fig5_analysis_scaling_tool_count.pdf")

        # LLM scaling curve
        if "llm_scaling" in results and results["llm_scaling"].get("accuracy"):
            llm_data = {"planning": results["llm_scaling"]["accuracy"]}
            plot_scaling_curve(
                {"planning": [(d[0], d[1]) for d in llm_data["planning"]]},
                x_label="Model Size",
                y_label="Plan Success Rate (%)",
                title="LLM Size Scaling",
                output_path=figures_dir / "fig6_analysis_scaling_llm_size.pdf",
            )
            print("  Figure saved: fig6_analysis_scaling_llm_size.pdf")

    except Exception as e:
        print(f"  Warning: Could not generate figures: {e}")


def main():
    parser = argparse.ArgumentParser(description="Section 5.3.2: Scaling Analysis")
    parser.add_argument("--tool-scaling", action="store_true", help="Run tool scaling only")
    parser.add_argument("--llm-scaling", action="store_true", help="Run LLM scaling only")
    parser.add_argument("--max-samples", type=int, default=50, help="Maximum samples per test")
    parser.add_argument("--verbose", action="store_true", default=True, help="Verbose output")
    args = parser.parse_args()

    # 如果没有指定具体类型，运行所有
    run_tool = args.tool_scaling or not (args.tool_scaling or args.llm_scaling)
    run_llm = args.llm_scaling or not (args.tool_scaling or args.llm_scaling)

    run_scaling_analysis(
        tool_scaling=run_tool,
        llm_scaling=run_llm,
        max_samples=args.max_samples,
        verbose=args.verbose,
    )

    print("\n" + "=" * 70)
    print("📊 Scaling Analysis Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
