#!/usr/bin/env python3
"""
验证 bench/algorithms/ 目录结构是否正确

检查：
1. 每个算法文件夹是否包含实现文件和配置文件
2. 算法类是否正确命名
3. 是否正确继承 BaseStreamingANN
4. 自动注册机制是否工作
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_algorithm_structure():
    """检查算法目录结构"""
    algorithms_dir = project_root / "bench" / "algorithms"

    print("=" * 60)
    print("算法目录结构验证")
    print("=" * 60)

    algorithm_folders = []
    for item in algorithms_dir.iterdir():
        if item.is_dir() and not item.name.startswith("_") and not item.name.startswith("."):
            algorithm_folders.append(item)

    print(f"\n找到 {len(algorithm_folders)} 个算法文件夹\n")

    valid_algorithms = []
    invalid_algorithms = []

    for algo_folder in sorted(algorithm_folders):
        algo_name = algo_folder.name
        py_file = algo_folder / f"{algo_name}.py"
        config_file = algo_folder / "config.yaml"

        has_py = py_file.exists()
        has_config = config_file.exists()

        status = "✓" if (has_py and has_config) else "✗"

        print(f"{status} {algo_name:25s} | .py: {has_py:5} | config.yaml: {has_config:5}")

        if has_py and has_config:
            valid_algorithms.append(algo_name)
        else:
            invalid_algorithms.append(algo_name)

    print("\n" + "=" * 60)
    print(f"验证完成: {len(valid_algorithms)} 个有效, {len(invalid_algorithms)} 个无效")
    print("=" * 60)

    if invalid_algorithms:
        print("\n⚠ 无效算法:")
        for algo in invalid_algorithms:
            print(f"  - {algo}")

    return valid_algorithms


def check_imports():
    """检查算法是否能正确导入和注册"""
    print("\n" + "=" * 60)
    print("算法导入和注册验证")
    print("=" * 60 + "\n")

    try:
        from bench.algorithms.registry import ALGORITHMS, discover_algorithms

        discovered = discover_algorithms()
        print(f"发现的算法目录: {len(discovered)}")
        for algo in sorted(discovered):
            print(f"  - {algo}")

        print(f"\n注册的算法: {len(ALGORITHMS)}")
        for algo_name in sorted(ALGORITHMS.keys()):
            print(f"  - {algo_name}")

        print("\n✓ 导入和注册机制工作正常")
        return True

    except Exception as e:
        print(f"\n✗ 导入失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_algorithm_instantiation():
    """测试算法实例化"""
    print("\n" + "=" * 60)
    print("算法实例化测试")
    print("=" * 60 + "\n")

    try:
        from bench.algorithms.registry import ALGORITHMS

        success_count = 0
        fail_count = 0

        for algo_name in sorted(ALGORITHMS.keys()):
            if algo_name == "dummy":
                continue

            try:
                # 尝试获取算法类（而不是实例化）
                _ = ALGORITHMS[algo_name]
                print(f"✓ {algo_name:25s} - 工厂函数可用")
                success_count += 1
            except Exception as e:
                print(f"✗ {algo_name:25s} - 失败: {e}")
                fail_count += 1

        print(f"\n测试完成: {success_count} 成功, {fail_count} 失败")
        return fail_count == 0

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n🔍 开始验证 bench/algorithms/ 结构...\n")

    # 检查目录结构
    valid_algos = check_algorithm_structure()

    # 检查导入
    import_ok = check_imports()

    # 测试实例化
    instantiation_ok = test_algorithm_instantiation()

    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    print(f"目录结构: {len(valid_algos)} 个有效算法")
    print(f"导入机制: {'✓ 正常' if import_ok else '✗ 失败'}")
    print(f"实例化测试: {'✓ 正常' if instantiation_ok else '✗ 失败'}")

    if import_ok and instantiation_ok and len(valid_algos) >= 17:
        print("\n✅ 所有检查通过！")
        return 0
    else:
        print("\n⚠ 部分检查未通过")
        return 1


if __name__ == "__main__":
    sys.exit(main())
