"""
Dataset Loaders

提供数据集加载和准备的工具函数
"""

import os
from typing import Optional

import numpy as np

from .base import Dataset


def xbin_mmap(filename: str, dtype: str = "float32", maxn: Optional[int] = None) -> np.ndarray:
    """
    使用内存映射读取 .bin 格式的向量文件

    文件格式: [n, d, vector_data...]
    其中 n, d 是 uint32

    Args:
        filename: 文件路径
        dtype: 数据类型
        maxn: 最大读取向量数

    Returns:
        (n, d) 数组
    """
    with open(filename, "rb") as f:
        n, d = np.fromfile(f, dtype=np.uint32, count=2)
        if maxn is not None:
            n = min(n, maxn)

        # 计算偏移量（跳过 n, d）
        offset = 2 * np.dtype(np.uint32).itemsize

        # 使用内存映射
        data = np.memmap(f.name, dtype=dtype, mode="r", offset=offset, shape=(n, d))

    return data


def load_fvecs(filename: str, maxn: Optional[int] = None) -> np.ndarray:
    """
    加载 .fvecs 格式文件

    格式: [d, vector_data] 重复 n 次
    """
    vectors = []
    with open(filename, "rb") as f:
        while True:
            d_bytes = f.read(4)
            if not d_bytes:
                break
            d = np.frombuffer(d_bytes, dtype=np.int32)[0]
            vec = np.frombuffer(f.read(d * 4), dtype=np.float32)
            vectors.append(vec)

            if maxn and len(vectors) >= maxn:
                break

    return np.array(vectors)


def load_ivecs(filename: str, maxn: Optional[int] = None) -> np.ndarray:
    """
    加载 .ivecs 格式文件（整数向量）
    """
    vectors = []
    with open(filename, "rb") as f:
        while True:
            d_bytes = f.read(4)
            if not d_bytes:
                break
            d = np.frombuffer(d_bytes, dtype=np.int32)[0]
            vec = np.frombuffer(f.read(d * 4), dtype=np.int32)
            vectors.append(vec)

            if maxn and len(vectors) >= maxn:
                break

    return np.array(vectors)


def knn_result_read(filename: str) -> tuple[np.ndarray, np.ndarray]:
    """
    读取 KNN groundtruth 文件

    文件格式支持：
    - .ibin: 二进制格式 [nq, k, indices...]
    - .ivecs: fvecs 格式的整数向量

    Returns:
        (I, D): I 是索引数组 (nq, k), D 是距离数组 (nq, k)
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Groundtruth file not found: {filename}")

    # 尝试不同的格式
    if filename.endswith(".ibin"):
        # 二进制格式
        with open(filename, "rb") as f:
            nq, k = np.fromfile(f, dtype=np.uint32, count=2)
            indices = np.fromfile(f, dtype=np.uint32).reshape(nq, k)

            # 尝试读取距离（如果有）
            remaining = f.read()
            if len(remaining) > 0:
                distances = np.frombuffer(remaining, dtype=np.float32).reshape(nq, k)
            else:
                distances = np.zeros_like(indices, dtype=np.float32)
    elif filename.endswith(".ivecs"):
        indices = load_ivecs(filename)
        distances = np.zeros_like(indices, dtype=np.float32)
    else:
        # 默认尝试 ivecs 格式
        try:
            indices = load_ivecs(filename)
            distances = np.zeros_like(indices, dtype=np.float32)
        except Exception:
            # 尝试二进制格式
            with open(filename, "rb") as f:
                nq, k = np.fromfile(f, dtype=np.uint32, count=2)
                indices = np.fromfile(f, dtype=np.uint32).reshape(nq, k)
                distances = np.zeros_like(indices, dtype=np.float32)

    return indices, distances


def range_result_read(filename: str):
    """
    读取 range search groundtruth

    Returns:
        list of arrays (每个查询的结果数量可能不同)
    """
    # 简化实现，实际可能需要根据格式调整
    results = []
    # TODO: 实现 range result 读取
    return results


def sanitize(x: np.ndarray) -> np.ndarray:
    """
    确保数组是可写的副本（不是内存映射）
    """
    if isinstance(x, np.memmap):
        return np.array(x)
    return x


def download(url: str, output_path: str) -> None:
    """
    下载文件
    """
    import shutil
    import urllib.request

    print(f"Downloading {url} to {output_path}")

    # 创建目录
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with urllib.request.urlopen(url) as response:
        with open(output_path, "wb") as out_file:
            shutil.copyfileobj(response, out_file)

    print(f"Download complete: {output_path}")


def load_dataset(dataset_name: str) -> Dataset:
    """
    根据名称加载数据集

    Args:
        dataset_name: 数据集名称

    Returns:
        Dataset 实例
    """
    from .registry import DATASETS

    if dataset_name not in DATASETS:
        raise ValueError(f"Unknown dataset: {dataset_name}")

    return DATASETS[dataset_name]()


def prepare_dataset(dataset_name: str, skip_data: bool = False) -> Dataset:
    """
    准备数据集（下载并处理）

    Args:
        dataset_name: 数据集名称
        skip_data: 是否跳过数据下载

    Returns:
        准备好的 Dataset 实例
    """
    dataset = load_dataset(dataset_name)
    dataset.prepare(skip_data=skip_data)
    return dataset
