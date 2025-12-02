"""
Base Dataset Class

提供数据集的基础抽象接口
"""

from typing import Iterator, Optional

import numpy as np


class Dataset:
    """
    数据集基类，定义所有数据集必须实现的接口
    """

    def __init__(self):
        self.nb: int = 0  # 数据集大小
        self.nq: int = 0  # 查询数量
        self.d: int = 0  # 向量维度
        self.dtype: str = "float32"
        self.basedir: str = "raw_data/"

    def prepare(self, skip_data: bool = False) -> None:
        """
        下载并准备数据集

        Args:
            skip_data: 是否跳过数据下载（只下载查询和groundtruth）
        """
        raise NotImplementedError

    def get_dataset_fn(self) -> str:
        """
        返回数据集文件路径
        """
        raise NotImplementedError

    def get_dataset(self) -> np.ndarray:
        """
        返回完整数据集（仅用于小数据集）

        Returns:
            (nb, d) 数组
        """
        raise NotImplementedError

    def get_dataset_iterator(
        self, bs: int = 512, split: tuple[int, int] = (1, 0)
    ) -> Iterator[np.ndarray]:
        """
        返回数据集迭代器，每次返回 bs 大小的批次

        Args:
            bs: 批次大小
            split: (n, p) 将数据集分成 n 份，返回第 p 份

        Yields:
            (batch_size, d) 数组
        """
        raise NotImplementedError

    def get_queries(self) -> np.ndarray:
        """
        返回查询向量

        Returns:
            (nq, d) 数组
        """
        raise NotImplementedError

    def get_groundtruth(self, k: Optional[int] = None) -> np.ndarray:
        """
        返回 groundtruth

        Args:
            k: 返回前 k 个最近邻（None 表示全部）

        Returns:
            对于 KNN: (nq, k) 索引数组
            对于 Range: list of arrays (每个查询的结果数量可能不同)
        """
        raise NotImplementedError

    def search_type(self) -> str:
        """
        返回搜索类型: "knn", "range", "knn_filtered"
        """
        return "knn"

    def distance(self) -> str:
        """
        返回距离度量: "euclidean", "ip", "angular"
        """
        return "euclidean"

    def data_type(self) -> str:
        """
        返回数据类型: "dense", "sparse"
        """
        return "dense"

    def default_count(self) -> int:
        """
        返回默认的邻居数量（KNN）或范围半径（Range）
        """
        return 10

    def get_data_in_range(self, start: int, end: int) -> np.ndarray:
        """
        返回指定范围的数据

        Args:
            start: 起始索引（包含）
            end: 结束索引（不包含）

        Returns:
            (end-start, d) 数组
        """
        # 默认实现：加载全部数据并切片
        # 子类应该重写此方法以支持高效的范围查询
        dataset = self.get_dataset()
        return dataset[start:end]

    def short_name(self) -> str:
        """
        返回数据集的简短名称
        """
        return f"{self.__class__.__name__}-{self.nb}"

    def __str__(self) -> str:
        return (
            f"Dataset {self.__class__.__name__} in dimension {self.d}, "
            f"with distance {self.distance()}, search_type {self.search_type()}, "
            f"size: Q {self.nq} B {self.nb}"
        )
