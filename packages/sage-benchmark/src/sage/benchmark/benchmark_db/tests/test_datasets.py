#!/usr/bin/env python3
"""
测试数据集实现

验证各个数据集类的基本功能
"""

import sys
from pathlib import Path

# 添加项目根目录到 sys.path
# 从 tests/ 目录运行时，需要添加父目录（benchmark_anns 根目录）
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from datasets.registry import DATASETS


def test_dataset_registry():
    """测试数据集注册表"""
    print("=" * 60)
    print("Testing Dataset Registry")
    print("=" * 60)

    print(f"\nTotal datasets registered: {len(DATASETS)}")
    print("\nAvailable datasets:")
    for name in sorted(DATASETS.keys()):
        print(f"  - {name}")

    return True


def test_dataset_creation():
    """测试数据集创建"""
    print("\n" + "=" * 60)
    print("Testing Dataset Creation")
    print("=" * 60)

    test_datasets = [
        "sift-small",
        "sift",
        "openimages-streaming",
        "sun",
        "glove",
        "msong",
        "coco",
        "wte-0.05",
    ]

    for ds_name in test_datasets:
        try:
            print(f"\n✓ Creating {ds_name}...", end=" ")
            ds = load_dataset(ds_name)
            print("OK")
            print(f"  - nb={ds.nb}, nq={ds.nq}, d={ds.d}")
            print(f"  - dtype={ds.dtype}, distance={ds.distance()}")
            print(f"  - basedir={ds.basedir}")
        except Exception as e:
            print(f"FAILED: {e}")
            return False

    return True


def test_dataset_interface():
    """测试数据集接口"""
    print("\n" + "=" * 60)
    print("Testing Dataset Interface")
    print("=" * 60)

    # 使用随机数据集测试
    print("\nTesting with random-xs dataset...")
    ds = load_dataset("random-xs")

    # 准备数据集
    print("  - prepare()...", end=" ")
    ds.prepare()
    print("OK")

    # 获取数据集
    print("  - get_dataset()...", end=" ")
    data = ds.get_dataset()
    print(f"OK (shape={data.shape})")
    assert data.shape == (ds.nb, ds.d), f"Expected shape ({ds.nb}, {ds.d}), got {data.shape}"

    # 获取查询
    print("  - get_queries()...", end=" ")
    queries = ds.get_queries()
    print(f"OK (shape={queries.shape})")
    assert queries.shape == (ds.nq, ds.d), f"Expected shape ({ds.nq}, {ds.d}), got {queries.shape}"

    # 获取 groundtruth
    print("  - get_groundtruth(k=10)...", end=" ")
    gt = ds.get_groundtruth(k=10)
    print(f"OK (shape={gt.shape})")
    assert gt.shape == (ds.nq, 10), f"Expected shape ({ds.nq}, 10), got {gt.shape}"

    # 测试迭代器
    print("  - get_dataset_iterator(bs=100)...", end=" ")
    count = 0
    for batch in ds.get_dataset_iterator(bs=100):
        count += len(batch)
    print(f"OK (total={count})")
    assert count == ds.nb, f"Expected {ds.nb} vectors, got {count}"

    # 测试其他方法
    print("  - search_type()...", end=" ")
    search_type = ds.search_type()
    print(f"OK ({search_type})")

    print("  - data_type()...", end=" ")
    data_type = ds.data_type()
    print(f"OK ({data_type})")

    print("  - default_count()...", end=" ")
    default_k = ds.default_count()
    print(f"OK ({default_k})")

    print("  - short_name()...", end=" ")
    short_name = ds.short_name()
    print(f"OK ({short_name})")

    return True


def test_dataset_comparison():
    """比较数据集参数与 big-ann-benchmarks 的一致性"""
    print("\n" + "=" * 60)
    print("Dataset Parameters Comparison")
    print("=" * 60)

    # 预期的数据集参数（来自 big-ann-benchmarks）
    expected_params = {
        "sift": (1000000, 10000, 128),
        "sift-100m": (100000000, 1000, 128),
        "openimages-streaming": (1000000, 10000, 512),
        "sun": (79106, 200, 512),
        "msong": (992272, 200, 420),
        "coco": (100000, 500, 768),
        "glove": (1192514, 200, 100),
    }

    all_match = True
    for ds_name, (expected_nb, expected_nq, expected_d) in expected_params.items():
        ds = load_dataset(ds_name)
        match = ds.nb == expected_nb and ds.nq == expected_nq and ds.d == expected_d
        status = "✓" if match else "✗"

        print(f"\n{status} {ds_name}:")
        print(f"  Expected: nb={expected_nb}, nq={expected_nq}, d={expected_d}")
        print(f"  Actual:   nb={ds.nb}, nq={ds.nq}, d={ds.d}")

        if not match:
            all_match = False

    return all_match


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("BENCHMARK_ANNS DATASETS TEST SUITE")
    print("=" * 60)

    tests = [
        ("Registry", test_dataset_registry),
        ("Creation", test_dataset_creation),
        ("Interface", test_dataset_interface),
        ("Parameters", test_dataset_comparison),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test {test_name} failed with exception: {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    # 总结
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(r for _, r in results)

    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
