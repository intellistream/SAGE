"""
Datasets Module for Benchmark ANNS

This module provides dataset management functionality.
"""

from .base import Dataset
from .loaders import (
    knn_result_read,
    load_dataset,
    load_fvecs,
    load_ivecs,
    prepare_dataset,
    sanitize,
    xbin_mmap,
)
from .registry import (
    COCO,
    DATASETS,
    SIFT,
    SIFT100M,
    WTE,
    # 文本/词向量数据集
    Glove,
    Msong,
    MSTuring,
    # 图像数据集
    OpenImagesStreaming,
    # 测试数据集
    RandomDataset,
    # SIFT 系列
    SIFTSmall,
    Sun,
    get_dataset,
    register_dataset,
)

__all__ = [
    "Dataset",
    "load_dataset",
    "prepare_dataset",
    "DATASETS",
    "register_dataset",
    "get_dataset",
    # Dataset classes
    "SIFTSmall",
    "SIFT",
    "SIFT100M",
    "OpenImagesStreaming",
    "Sun",
    "COCO",
    "Glove",
    "Msong",
    "MSTuring",
    "WTE",
    "RandomDataset",
    # Loaders
    "xbin_mmap",
    "load_fvecs",
    "load_ivecs",
    "knn_result_read",
    "sanitize",
]
