#!/usr/bin/env python3
"""
Export Results with Recall Calculation

计算批次级别的召回率并导出最终结果
参考 big-ann-benchmarks/data_export.py 和 benchmark/plotting/utils.py

用法:
    python export_results.py --dataset sift --algorithm faiss_HNSW --runbook general_experiment
    python export_results.py --dataset sift --algorithm faiss_HNSW --runbook general_experiment --output final_results.csv
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

import h5py
import numpy as np
import pandas as pd
from datasets.registry import DATASETS, get_dataset
from utils.runbook import load_runbook


def knn_result_read(filepath: str) -> tuple[np.ndarray, np.ndarray]:
    """
    读取真值文件（.gt100 格式）

    参考 big-ann-benchmarks/benchmark/dataset_io.py

    Returns:
        (ids, distances): 真值的ID和距离数组
    """
    with open(filepath, "rb") as f:
        # 读取头部：nq(查询数), k(邻居数)
        nq = np.fromfile(f, dtype=np.uint32, count=1)[0]
        k = np.fromfile(f, dtype=np.uint32, count=1)[0]

        # 读取数据
        ids = np.fromfile(f, dtype=np.uint32, count=nq * k).reshape(nq, k)
        distances = np.fromfile(f, dtype=np.float32, count=nq * k).reshape(nq, k)

    return ids, distances


def compute_recall(
    true_ids: np.ndarray, true_dists: np.ndarray, run_ids: np.ndarray, k: int
) -> tuple[float, np.ndarray]:
    """
    计算召回率

    参考 big-ann-benchmarks/benchmark/plotting/metrics.py 的实现

    Args:
        true_ids: 真值ID数组 (nq, k_gt)
        true_dists: 真值距离数组 (nq, k_gt)
        run_ids: 查询结果ID数组 (nq, k)
        k: 需要的邻居数

    Returns:
        (mean_recall, recalls): 平均召回率和每个查询的召回率
    """
    nq = run_ids.shape[0]
    recalls = np.zeros(nq)

    for i in range(nq):
        # 简单版本：计算交集大小
        correct = len(set(true_ids[i, :k]) & set(run_ids[i]))
        recalls[i] = correct / k

    return np.mean(recalls), recalls


def load_groundtruth_for_batch_inserts(
    dataset, runbook: dict, dataset_name: str, runbook_path: str
) -> list[list[tuple]]:
    """
    加载所有 batch_insert 操作的真值

    参考 big-ann-benchmarks/benchmark/plotting/utils.py 的 compute_metrics_all_runs

    Returns:
        List of [List of (ids, distances)] for each batch_insert operation
    """
    # 获取真值目录
    runbook_filename = os.path.basename(runbook_path)
    gt_dir = os.path.join(dataset.basedir, str(dataset.nb), runbook_filename)

    if not os.path.exists(gt_dir):
        raise FileNotFoundError(f"Ground truth directory not found: {gt_dir}")

    # 解析 runbook 找到所有 batch_insert 操作
    operations = []
    if dataset_name in runbook:
        dataset_config = runbook[dataset_name]
        # 只处理整数键（步骤编号）
        for key in sorted([k for k in dataset_config.keys() if isinstance(k, int)]):
            operations.append(dataset_config[key])
    else:
        raise ValueError(f"Dataset {dataset_name} not found in runbook")

    # 加载每个 batch_insert 的真值
    true_nn_across_batches = []
    num_batch_insert = 0

    for step, entry in enumerate(operations):
        if entry["operation"] == "batch_insert" or entry["operation"] == "batch_insert_delete":
            batch_gts = []
            start = entry["start"]
            end = entry["end"]
            batch_size = entry.get("batchSize", 2500)

            # 计算批次数量
            num_batches = (end - start + batch_size - 1) // batch_size

            # continuous_query_interval: 每插入总数据量的 1/100 执行一次查询
            total_data = end - start
            continuous_query_interval = total_data // 100

            continuous_counter = 0
            for batch_idx in range(num_batches):
                continuous_counter += batch_size

                # 每插入 total_data/100 就查询一次
                if continuous_counter >= continuous_query_interval:
                    gt_filename = f"batch{num_batch_insert}_{batch_idx}.gt100"
                    gt_path = os.path.join(gt_dir, gt_filename)

                    if os.path.exists(gt_path):
                        true_ids, true_dists = knn_result_read(gt_path)
                        batch_gts.append((true_ids, true_dists))
                        print(f"  加载真值: {gt_filename} (shape: {true_ids.shape})")
                    else:
                        print(f"  ⚠️  真值文件缺失: {gt_filename}")

                    continuous_counter = 0

            true_nn_across_batches.append(batch_gts)
            num_batch_insert += 1

    return true_nn_across_batches


def compute_batch_recalls(
    result_hdf5: str, groundtruth_batches: list[list[tuple]], k: int = 10
) -> tuple[list[float], list[list[float]]]:
    """
    计算每个批次的召回率

    Args:
        result_hdf5: 结果HDF5文件路径
        groundtruth_batches: 真值数据 (每个batch_insert包含多个查询批次)
        k: kNN的k值

    Returns:
        (mean_recalls, all_recalls): 每个查询批次的平均召回率和详细召回率
    """
    # 读取查询结果
    with h5py.File(result_hdf5, "r") as f:
        if "neighbors_continuous" not in f:
            raise ValueError("HDF5 file does not contain 'neighbors_continuous' dataset")

        neighbors_continuous = np.array(f["neighbors_continuous"])
        print(f"查询结果形状: {neighbors_continuous.shape}")

    # 展平所有真值（因为真值是按batch_insert分组的）
    all_groundtruth = []
    for batch_gts in groundtruth_batches:
        all_groundtruth.extend(batch_gts)

    print(f"真值批次数: {len(all_groundtruth)}")

    # 计算每个批次的召回率
    mean_recalls = []
    all_recalls = []

    query_idx = 0
    dataset_nq = None  # 每批次的查询数量

    for gt_idx, (true_ids, true_dists) in enumerate(all_groundtruth):
        nq = true_ids.shape[0]
        if dataset_nq is None:
            dataset_nq = nq

        # 提取对应的查询结果
        if query_idx + nq > neighbors_continuous.shape[0]:
            print(f"  ⚠️  查询结果不足: 需要 {query_idx + nq}, 实际 {neighbors_continuous.shape[0]}")
            break

        run_ids = neighbors_continuous[query_idx : query_idx + nq, :k]

        # 计算召回率
        mean_recall, recalls = compute_recall(true_ids, true_dists, run_ids, k)
        mean_recalls.append(mean_recall)
        all_recalls.append(recalls.tolist())

        query_idx += nq

        print(f"  批次 {gt_idx}: 召回率 = {mean_recall:.4f}")

    return mean_recalls, all_recalls


def export_results(
    dataset_name: str,
    algorithm: str,
    runbook_name: str,
    output_dir: str = "results",
    output_file: Optional[str] = None,
):
    """
    导出带召回率的最终结果

    Args:
        dataset_name: 数据集名称
        algorithm: 算法名称
        runbook_name: Runbook名称
        output_dir: 结果目录
        output_file: 输出CSV文件名（可选）
    """
    print(f"\n{'=' * 80}")
    print(f"导出结果: {algorithm} @ {dataset_name} / {runbook_name}")
    print(f"{'=' * 80}\n")

    # 1. 加载数据集和runbook
    print("[1/5] 加载数据集和Runbook...")
    dataset = get_dataset(dataset_name)

    runbook_path = f"runbooks/{runbook_name}/{runbook_name}.yaml"
    if not os.path.exists(runbook_path):
        runbook_path = f"runbooks/{runbook_name}.yaml"

    if not os.path.exists(runbook_path):
        raise FileNotFoundError(f"Runbook not found: {runbook_path}")

    # 加载 runbook（使用正确的签名）
    max_pts, runbook_config = load_runbook(dataset_name, dataset.nb, runbook_path)

    # 将 runbook_config 转换为字典格式（用于后续处理）
    import yaml

    with open(runbook_path) as f:
        runbook = yaml.safe_load(f)

    print(f"  ✓ 数据集: {dataset_name}")
    print(f"  ✓ Runbook: {runbook_path}")

    # 2. 定位结果文件
    print("\n[2/5] 定位结果文件...")
    result_dir = Path(output_dir) / dataset_name / algorithm
    result_base = f"{algorithm}_sift_{runbook_name}" if dataset_name == "sift" else f"{algorithm}"

    hdf5_file = result_dir / f"{result_base}.hdf5"
    csv_file = result_dir / f"{result_base}.csv"
    batch_insert_qps_file = result_dir / f"{result_base}_batch_insert_qps.csv"
    batch_query_qps_file = result_dir / f"{result_base}_batch_query_qps.csv"
    batch_query_latency_file = result_dir / f"{result_base}_batch_query_latency.csv"

    if not hdf5_file.exists():
        # 尝试简化的文件名
        hdf5_file = result_dir / f"{algorithm}.hdf5"
        csv_file = result_dir / f"{algorithm}.csv"
        batch_insert_qps_file = result_dir / f"{algorithm}_batch_insert_qps.csv"
        batch_query_qps_file = result_dir / f"{algorithm}_batch_query_qps.csv"
        batch_query_latency_file = result_dir / f"{algorithm}_batch_query_latency.csv"

    if not hdf5_file.exists():
        raise FileNotFoundError(f"Result HDF5 file not found: {hdf5_file}")

    print(f"  ✓ HDF5: {hdf5_file}")
    print(f"  ✓ CSV: {csv_file}")

    # 3. 加载真值
    print("\n[3/5] 加载真值...")
    groundtruth_batches = load_groundtruth_for_batch_inserts(
        dataset, runbook, dataset_name, runbook_path
    )
    print(f"  ✓ 加载了 {len(groundtruth_batches)} 个 batch_insert 操作的真值")

    # 4. 计算召回率
    print("\n[4/5] 计算召回率...")
    k = 10  # 默认 k=10
    mean_recalls, all_recalls = compute_batch_recalls(str(hdf5_file), groundtruth_batches, k)

    # 5. 导出结果
    print("\n[5/5] 导出结果...")

    # 5.1 读取现有的批次数据
    data = {"batch_idx": list(range(len(mean_recalls))), "recall": mean_recalls}

    # 5.2 合并插入QPS
    if batch_insert_qps_file.exists():
        insert_qps_df = pd.read_csv(batch_insert_qps_file)
        if len(insert_qps_df) == len(mean_recalls):
            data["insert_qps"] = insert_qps_df["insert_qps"].values
        else:
            print(f"  ⚠️  插入QPS数量不匹配: {len(insert_qps_df)} vs {len(mean_recalls)}")

    # 5.3 查询QPS和延迟
    if batch_query_qps_file.exists():
        query_qps_df = pd.read_csv(batch_query_qps_file)
        # 对齐batch_idx
        query_qps_dict = dict(zip(query_qps_df["batch_idx"], query_qps_df["query_qps"]))
        data["query_qps"] = [query_qps_dict.get(i, np.nan) for i in data["batch_idx"]]

    # 5.4 查询延迟
    if batch_query_latency_file.exists():
        query_latency_df = pd.read_csv(batch_query_latency_file)
        # 对齐batch_idx
        query_latency_dict = dict(
            zip(query_latency_df["batch_idx"], query_latency_df["query_latency_ms"])
        )
        data["query_latency_ms"] = [query_latency_dict.get(i, np.nan) for i in data["batch_idx"]]

    # 5.5 Cache Miss 统计
    batch_cache_miss_file = result_dir / f"{algorithm}_batch_cache_miss.csv"
    if batch_cache_miss_file.exists():
        cache_miss_df = pd.read_csv(batch_cache_miss_file)
        # 对齐batch_idx
        cache_miss_dict = dict(zip(cache_miss_df["batch_idx"], cache_miss_df["cache_misses"]))
        cache_refs_dict = dict(zip(cache_miss_df["batch_idx"], cache_miss_df["cache_references"]))
        cache_rate_dict = dict(zip(cache_miss_df["batch_idx"], cache_miss_df["cache_miss_rate"]))

        data["cache_misses"] = [cache_miss_dict.get(i, np.nan) for i in data["batch_idx"]]
        data["cache_references"] = [cache_refs_dict.get(i, np.nan) for i in data["batch_idx"]]
        data["cache_miss_rate"] = [cache_rate_dict.get(i, np.nan) for i in data["batch_idx"]]

    # 5.6 创建DataFrame并保存
    df = pd.DataFrame(data)

    if output_file is None:
        output_file = result_dir / f"{result_base}_final_results.csv"
    else:
        output_file = Path(output_file)

    df.to_csv(output_file, index=False)
    print(f"  ✓ 最终结果已保存: {output_file}")

    # 5.6 打印统计信息
    print(f"\n{'=' * 80}")
    print("统计摘要")
    print(f"{'=' * 80}")
    print(f"批次数量: {len(mean_recalls)}")
    print(f"平均召回率: {np.mean(mean_recalls):.4f}")
    print(f"最小召回率: {np.min(mean_recalls):.4f}")
    print(f"最大召回率: {np.max(mean_recalls):.4f}")

    if "insert_qps" in data:
        print(f"平均插入QPS: {np.nanmean(data['insert_qps']):.2f} ops/s")
    if "query_qps" in data:
        print(f"平均查询QPS: {np.nanmean(data['query_qps']):.2f} queries/s")
    if "query_latency_ms" in data:
        print(f"平均查询延迟: {np.nanmean(data['query_latency_ms']):.2f} ms")
    if "cache_misses" in data and not all(pd.isna(data["cache_misses"])):
        print(f"平均 Cache Misses: {np.nanmean(data['cache_misses']):,.0f}")
    if "cache_miss_rate" in data and not all(pd.isna(data["cache_miss_rate"])):
        print(f"平均 Cache Miss 率: {np.nanmean(data['cache_miss_rate']):.2%}")

    print(f"{'=' * 80}\n")

    return df


def main():
    parser = argparse.ArgumentParser(
        description="Export results with recall calculation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--dataset", required=True, help="Dataset name (e.g., sift)")
    parser.add_argument("--algorithm", required=True, help="Algorithm name (e.g., faiss_HNSW)")
    parser.add_argument("--runbook", required=True, help="Runbook name (e.g., general_experiment)")
    parser.add_argument(
        "--output-dir", default="results", help="Results directory (default: results)"
    )
    parser.add_argument("--output-file", help="Output CSV file path (optional)")
    parser.add_argument("--list-datasets", action="store_true", help="List available datasets")

    args = parser.parse_args()

    if args.list_datasets:
        print("Available datasets:")
        for name in DATASETS.keys():
            print(f"  - {name}")
        return

    try:
        export_results(
            dataset_name=args.dataset,
            algorithm=args.algorithm,
            runbook_name=args.runbook,
            output_dir=args.output_dir,
            output_file=args.output_file,
        )
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
