#!/usr/bin/env python3
"""
数据集准备工具

用于下载和准备基准测试所需的数据集

用法示例：
    # 下载 SIFT 1M 数据集
    python prepare_dataset.py --dataset sift

    # 下载 SIFT Small 数据集（10K，用于快速测试）
    python prepare_dataset.py --dataset sift-small

    # 列出所有可用数据集
    python prepare_dataset.py --list

    # 跳过数据下载，仅创建目录结构
    python prepare_dataset.py --dataset sift --skip-data
"""

import argparse
import sys

# benchmark_anns 是独立项目，使用相对导入
from datasets import DATASETS, prepare_dataset


def list_datasets():
    """列出所有可用的数据集及其信息"""
    print("\n" + "=" * 80)
    print("可用数据集列表")
    print("=" * 80)

    # 按类别分组
    categories = {
        "SIFT 系列": ["sift-small", "sift", "sift100m"],
        "图像数据集": ["openimages", "sun", "coco"],
        "文本/词向量": ["glove", "msong", "msturing", "wte"],
        "测试数据集": ["random-xs", "random-s", "random-m"],
    }

    for category, dataset_names in categories.items():
        print(f"\n【{category}】")
        for name in dataset_names:
            if name in DATASETS:
                ds = DATASETS[name]()
                size_info = f"{ds.nb:,}" if hasattr(ds, "nb") else "动态"
                dim_info = f"{ds.d}" if hasattr(ds, "d") else "N/A"
                print(f"  • {name:<20} - {size_info:>12} 向量, {dim_info:>4} 维")
            elif name.startswith("random-"):
                print(f"  • {name:<20} - 随机生成数据集")

    print("\n" + "=" * 80)
    print("提示：")
    print("  - sift-small (10K) 适合快速测试")
    print("  - sift (1M) 是常用的基准数据集")
    print("  - sift100m (100M) 用于大规模测试")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="数据集准备工具 - 下载和准备基准测试数据集",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 下载 SIFT 1M 数据集（最常用）
  python prepare_dataset.py --dataset sift

  # 下载 SIFT Small 用于快速测试
  python prepare_dataset.py --dataset sift-small

  # 列出所有可用数据集
  python prepare_dataset.py --list

  # 准备多个数据集
  python prepare_dataset.py --dataset sift --dataset glove
        """,
    )

    parser.add_argument(
        "--dataset", "-d", type=str, action="append", help="要准备的数据集名称（可多次指定）"
    )

    parser.add_argument("--list", "-l", action="store_true", help="列出所有可用的数据集")

    parser.add_argument("--skip-data", action="store_true", help="跳过数据下载，仅创建目录结构")

    args = parser.parse_args()

    # 列出数据集
    if args.list:
        list_datasets()
        return

    # 检查是否指定了数据集
    if not args.dataset:
        parser.print_help()
        print("\n错误：请使用 --dataset 指定要准备的数据集，或使用 --list 查看可用数据集")
        sys.exit(1)

    # 准备数据集
    print("\n" + "=" * 80)
    print("数据集准备工具")
    print("=" * 80)

    success_count = 0
    failed_datasets = []

    for dataset_name in args.dataset:
        print(f"\n{'─' * 80}")
        print(f"准备数据集: {dataset_name}")
        print(f"{'─' * 80}")

        try:
            # 检查数据集是否存在
            if dataset_name not in DATASETS:
                print(f"✗ 错误：未知数据集 '{dataset_name}'")
                print("  使用 --list 查看所有可用数据集")
                failed_datasets.append(dataset_name)
                continue

            # 准备数据集
            dataset = prepare_dataset(dataset_name, skip_data=args.skip_data)

            # 显示数据集信息
            print("\n✓ 数据集准备完成！")
            print(f"  名称: {dataset_name}")
            print(f"  路径: {dataset.basedir}")
            if hasattr(dataset, "nb"):
                print(f"  向量数: {dataset.nb:,}")
            if hasattr(dataset, "d"):
                print(f"  维度: {dataset.d}")
            if hasattr(dataset, "nq"):
                print(f"  查询数: {dataset.nq:,}")

            success_count += 1

        except Exception as e:
            print(f"\n✗ 准备失败: {e}")
            import traceback

            traceback.print_exc()
            failed_datasets.append(dataset_name)

    # 汇总结果
    print("\n" + "=" * 80)
    print("准备完成")
    print("=" * 80)
    print(f"成功: {success_count}/{len(args.dataset)}")

    if failed_datasets:
        print(f"失败: {', '.join(failed_datasets)}")
        sys.exit(1)
    else:
        print("所有数据集准备成功！")
        print("\n下一步：")
        print(
            f"  python run_benchmark.py --algorithm <算法> --dataset {args.dataset[0]} --runbook <runbook>"
        )
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
