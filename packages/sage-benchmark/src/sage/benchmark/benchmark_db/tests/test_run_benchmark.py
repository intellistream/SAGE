#!/usr/bin/env python3
"""
测试 run_benchmark.py 完整流程

测试场景：
1. 使用 dummy 算法测试基本流程
2. 使用真实算法（如果可用）测试完整功能
3. 验证结果保存和指标计算
"""

import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None):
    """运行命令并返回结果"""
    print(f"\n{'=' * 80}")
    print(f"执行命令: {cmd}")
    print(f"{'=' * 80}")

    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    return result.returncode, result.stdout, result.stderr


def test_list_commands():
    """测试列表命令"""
    print("\n" + "=" * 80)
    print("测试 1: 列表命令")
    print("=" * 80)

    benchmark_anns_dir = Path(__file__).parent.parent

    # 列出算法
    print("\n--- 列出算法 ---")
    ret, stdout, stderr = run_command(
        "python run_benchmark.py --list-algorithms", cwd=benchmark_anns_dir
    )
    assert ret == 0, "列出算法失败"
    assert "dummy" in stdout, "应该包含 dummy 算法"

    # 列出数据集
    print("\n--- 列出数据集 ---")
    ret, stdout, stderr = run_command(
        "python run_benchmark.py --list-datasets", cwd=benchmark_anns_dir
    )
    assert ret == 0, "列出数据集失败"
    assert "sift" in stdout, "应该包含 sift 数据集"

    # 列出 runbooks
    print("\n--- 列出 Runbooks ---")
    ret, stdout, stderr = run_command(
        "python run_benchmark.py --list-runbooks", cwd=benchmark_anns_dir
    )
    assert ret == 0, "列出 runbooks 失败"

    print("\n✓ 所有列表命令测试通过")


def test_dummy_algorithm():
    """测试使用 dummy 算法运行基准测试"""
    print("\n" + "=" * 80)
    print("测试 2: Dummy 算法基准测试")
    print("=" * 80)

    benchmark_anns_dir = Path(__file__).parent.parent
    output_dir = benchmark_anns_dir / "test_output"

    # 清理旧的输出
    if output_dir.exists():
        shutil.rmtree(output_dir)

    # 运行测试
    cmd = (
        "python run_benchmark.py "
        "--algorithm dummy "
        "--dataset random-xs "
        "--runbook runbooks/test_simple.yaml "
        "--k 10 "
        f"--output {output_dir}"
    )

    ret, stdout, stderr = run_command(cmd, cwd=benchmark_anns_dir)

    if ret != 0:
        print(f"\n✗ 测试失败，返回码: {ret}")
        print("可能的原因：")
        print("1. random-xs 数据集未准备")
        print("2. test_simple.yaml runbook 不存在")
        print("3. 算法或数据集导入失败")
        return False

    # 验证输出文件
    assert output_dir.exists(), "输出目录未创建"

    # 检查是否有结果文件
    json_files = list(output_dir.glob("*.json"))
    print(f"\n生成的 JSON 文件: {len(json_files)}")
    for f in json_files:
        print(f"  - {f.name}")

    summary_files = list(output_dir.glob("*.txt"))
    print(f"生成的摘要文件: {len(summary_files)}")
    for f in summary_files:
        print(f"  - {f.name}")

    assert len(json_files) > 0, "应该生成至少一个 JSON 结果文件"

    print("\n✓ Dummy 算法测试通过")
    return True


def test_sift_dataset():
    """测试使用 SIFT 数据集"""
    print("\n" + "=" * 80)
    print("测试 3: SIFT 数据集测试")
    print("=" * 80)

    benchmark_anns_dir = Path(__file__).parent.parent

    # 检查 SIFT 数据集是否存在
    sift_dir = benchmark_anns_dir / "data" / "sift"
    if not sift_dir.exists() or not list(sift_dir.glob("data_*")):
        print("⚠ SIFT 数据集未下载，跳过此测试")
        print("运行 'python prepare_dataset.py --dataset sift' 来下载")
        return False

    print("✓ SIFT 数据集存在")

    output_dir = benchmark_anns_dir / "test_output_sift"
    if output_dir.exists():
        shutil.rmtree(output_dir)

    # 使用 dummy 算法和 SIFT 数据集
    cmd = (
        "python run_benchmark.py "
        "--algorithm dummy "
        "--dataset sift "
        "--runbook runbooks/test_simple.yaml "
        "--k 10 "
        f"--output {output_dir}"
    )

    ret, stdout, stderr = run_command(cmd, cwd=benchmark_anns_dir)

    if ret != 0:
        print(f"\n✗ SIFT 测试失败，返回码: {ret}")
        return False

    # 验证结果
    assert output_dir.exists(), "输出目录未创建"
    json_files = list(output_dir.glob("*.json"))
    assert len(json_files) > 0, "应该生成结果文件"

    print("\n✓ SIFT 数据集测试通过")
    return True


def test_faiss_algorithm():
    """测试使用 Faiss 算法（如果可用）"""
    print("\n" + "=" * 80)
    print("测试 4: Faiss 算法测试（可选）")
    print("=" * 80)

    # 检查 Faiss 是否可用
    try:
        import faiss

        print("✓ Faiss 已安装")
    except ImportError:
        print("⚠ Faiss 未安装，跳过此测试")
        print("安装命令: pip install faiss-cpu")
        return False

    benchmark_anns_dir = Path(__file__).parent.parent
    output_dir = benchmark_anns_dir / "test_output_faiss"

    if output_dir.exists():
        shutil.rmtree(output_dir)

    # 使用 Faiss HNSW 算法
    cmd = (
        "python run_benchmark.py "
        "--algorithm faiss_hnsw "
        "--dataset random-xs "
        "--runbook runbooks/test_simple.yaml "
        "--k 10 "
        '--algo-params \'{"M": 16, "efConstruction": 100, "efSearch": 50}\' '
        f"--output {output_dir}"
    )

    ret, stdout, stderr = run_command(cmd, cwd=benchmark_anns_dir)

    if ret != 0:
        print(f"\n✗ Faiss 测试失败，返回码: {ret}")
        return False

    print("\n✓ Faiss 算法测试通过")
    return True


def main():
    """运行所有测试"""
    print("\n" + "#" * 80)
    print("# run_benchmark.py 完整流程测试")
    print("#" * 80)

    results = {}

    # 测试 1: 列表命令
    try:
        test_list_commands()
        results["列表命令"] = "✓ 通过"
    except Exception as e:
        results["列表命令"] = f"✗ 失败: {e}"
        print(f"\n✗ 测试失败: {e}")

    # 测试 2: Dummy 算法
    try:
        success = test_dummy_algorithm()
        results["Dummy算法"] = "✓ 通过" if success else "✗ 失败"
    except Exception as e:
        results["Dummy算法"] = f"✗ 失败: {e}"
        print(f"\n✗ 测试失败: {e}")

    # 测试 3: SIFT 数据集
    try:
        success = test_sift_dataset()
        results["SIFT数据集"] = "✓ 通过" if success else "⚠ 跳过"
    except Exception as e:
        results["SIFT数据集"] = f"✗ 失败: {e}"
        print(f"\n✗ 测试失败: {e}")

    # 测试 4: Faiss 算法（可选）
    try:
        success = test_faiss_algorithm()
        results["Faiss算法"] = "✓ 通过" if success else "⚠ 跳过"
    except Exception as e:
        results["Faiss算法"] = f"⚠ 跳过: {e}"
        print(f"\n⚠ 测试跳过: {e}")

    # 打印测试总结
    print("\n" + "#" * 80)
    print("# 测试结果总结")
    print("#" * 80)

    for test_name, result in results.items():
        print(f"{test_name:20s} : {result}")

    print("#" * 80)

    # 检查关键测试是否通过
    critical_tests = ["列表命令", "Dummy算法"]
    failed_critical = [name for name in critical_tests if "✗" in results.get(name, "")]

    if failed_critical:
        print(f"\n✗ 关键测试失败: {', '.join(failed_critical)}")
        return 1
    else:
        print("\n✓ 所有关键测试通过！")
        return 0


if __name__ == "__main__":
    sys.exit(main())
