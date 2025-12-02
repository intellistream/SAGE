"""
Dataset Registry

注册所有可用的数据集

设计参考 big-ann-benchmarks，每个数据集在 raw_data/ 目录下有独立的子文件夹：
- raw_data/sift-small/     - SIFT Small 数据集
- raw_data/sift/           - SIFT 1M 数据集
- raw_data/random-xs/      - 随机测试数据集
...

每个数据集文件夹包含：
- data_*.bin          - 基础向量数据
- queries_*.bin       - 查询向量
- gt_*.bin           - Ground truth 结果
"""

import os
from typing import Callable

import numpy as np

from .base import Dataset
from .download_utils import download_dataset
from .loaders import knn_result_read, load_fvecs, load_ivecs, sanitize, xbin_mmap

# 数据集根目录 - 所有数据集都存储在这里的子目录中
BASEDIR = "raw_data/"


# ============================================================================
# 辅助函数 - 用于数据下载和预处理
# ============================================================================


def load_data(path: str):
    """
    从二进制文件加载数据

    文件格式：[nb, d] (int32) + vectors (float32)
    """
    with open(path, "rb") as f:
        nb_d = np.fromfile(f, dtype=np.int32, count=2)
        nb, d = nb_d[0], nb_d[1]
        vectors = np.fromfile(f, dtype=np.float32).reshape((nb, d))
    return nb, d, vectors


def sample_vectors(vectors: np.ndarray, nb: int, nq: int):
    """
    从向量集中采样出基础向量和查询向量

    Args:
        vectors: 原始向量数据
        nb: 需要的基础向量数量
        nq: 需要的查询向量数量

    Returns:
        (index_vectors, query_vectors) 元组
    """
    num = vectors.shape[0]
    if num >= nb + nq:
        indices = np.random.permutation(nb + nq)
        index_vectors = vectors[indices[:nb]]
        query_vectors = vectors[indices[nb : nb + nq]]
        return index_vectors, query_vectors
    else:
        indices = np.random.permutation(num)
        query_vectors = vectors[indices[:nq]]
        return vectors, query_vectors


def save_data(vectors_index: np.ndarray, type: str, basedir: str):
    """
    保存向量数据到二进制文件

    Args:
        vectors_index: 要保存的向量数据
        type: 文件类型 ('data' 或 'queries')
        basedir: 保存目录

    Returns:
        保存的文件路径
    """
    nb = vectors_index.shape[0]
    d = vectors_index.shape[1]

    path = os.path.join(basedir, f"{type}_{nb}_{d}")
    with open(path, "wb") as f:
        np.array([nb, d], dtype="uint32").tofile(f)
        vectors_index.tofile(f)

    return path


class SIFTSmall(Dataset):
    """
    SIFT Small 数据集 (10K 向量)

    数据存储在: raw_data/sift-small/
    下载地址: https://drive.google.com/drive/folders/1XbvrSjlP-oUZ5cixVpfSTn0zE-Cim0NK
    """

    def __init__(self):
        super().__init__()
        self.nb = 10000
        self.nq = 100
        self.d = 128
        self.dtype = "float32"
        self.basedir = os.path.join(BASEDIR, "sift-small")
        self.ds_fn = f"data_{self.nb}_{self.d}"
        self.qs_fn = f"queries_{self.nq}_{self.d}"
        self.gt_fn = f"gt_{self.nb}_{self.nq}_{self.d}"

    def prepare(self, skip_data: bool = False) -> None:
        """下载并准备数据集"""
        os.makedirs(self.basedir, exist_ok=True)

        # 检查是否已经下载
        if any(os.listdir(self.basedir)):
            print("✓ SIFT-Small has already been installed!")
            return

        # 从 Google Drive 下载
        download_dataset("sift-small", self.basedir)
        print(f"✓ Dataset directory: {self.basedir}")

        # 检查文件是否存在
        required_files = [self.ds_fn, self.qs_fn, self.gt_fn]
        missing = [f for f in required_files if not os.path.exists(os.path.join(self.basedir, f))]

        if missing:
            print(f"⚠ Missing files in {self.basedir}:")
            for f in missing:
                print(f"  - {f}")
            print("Please download SIFT Small dataset and place files in the directory above.")

    def get_dataset_fn(self) -> str:
        return os.path.join(self.basedir, self.ds_fn)

    def get_dataset(self) -> np.ndarray:
        return sanitize(load_fvecs(self.get_dataset_fn(), maxn=self.nb))

    def get_dataset_iterator(self, bs: int = 512, split=(1, 0)):
        nsplit, rank = split
        data = self.get_dataset()
        i0 = len(data) * rank // nsplit
        i1 = len(data) * (rank + 1) // nsplit

        for j0 in range(i0, i1, bs):
            j1 = min(j0 + bs, i1)
            yield data[j0:j1]

    def get_queries(self) -> np.ndarray:
        filename = os.path.join(self.basedir, self.qs_fn)
        return sanitize(load_fvecs(filename))

    def get_groundtruth(self, k=None) -> np.ndarray:
        filename = os.path.join(self.basedir, self.gt_fn)
        I = load_ivecs(filename)
        if k is not None:
            I = I[:, :k]
        return I

    def distance(self) -> str:
        return "euclidean"

    def short_name(self) -> str:
        return "sift-small"


class RandomDataset(Dataset):
    """
    随机生成的数据集（用于测试）

    数据存储在: raw_data/random-{size}/
    """

    def __init__(self, nb: int = 10000, nq: int = 100, d: int = 128):
        super().__init__()
        self.nb = nb
        self.nq = nq
        self.d = d
        self.dtype = "float32"
        # 根据大小命名目录
        size_suffix = self._get_size_suffix()
        self.basedir = os.path.join(BASEDIR, f"random-{size_suffix}")
        self._data = None
        self._queries = None
        self._groundtruth = None

    def _get_size_suffix(self) -> str:
        """根据数据集大小返回合适的后缀"""
        if self.nb <= 10000:
            return "xs"  # extra small
        elif self.nb <= 100000:
            return "s"  # small
        elif self.nb <= 1000000:
            return "m"  # medium
        else:
            return "l"  # large

    def prepare(self, skip_data: bool = False) -> None:
        """准备随机数据集 - 创建目录"""
        os.makedirs(self.basedir, exist_ok=True)
        print(f"✓ Random dataset: {self.nb} vectors, {self.d} dims → {self.basedir}")

    def get_dataset_fn(self) -> str:
        return os.path.join(self.basedir, f"data_{self.nb}_{self.d}.bin")

    def get_dataset(self) -> np.ndarray:
        if self._data is None:
            # 使用固定种子保证可重复性
            np.random.seed(42)
            self._data = np.random.randn(self.nb, self.d).astype(np.float32)
            # 归一化到单位向量（可选）
            # norms = np.linalg.norm(self._data, axis=1, keepdims=True)
            # self._data = self._data / (norms + 1e-10)
        return self._data
        return self._data

    def get_dataset_iterator(self, bs: int = 512, split=(1, 0)):
        nsplit, rank = split
        data = self.get_dataset()
        i0 = len(data) * rank // nsplit
        i1 = len(data) * (rank + 1) // nsplit

        for j0 in range(i0, i1, bs):
            j1 = min(j0 + bs, i1)
            yield data[j0:j1]

    def get_queries(self) -> np.ndarray:
        if self._queries is None:
            np.random.seed(123)  # 不同的种子以避免重复
            self._queries = np.random.randn(self.nq, self.d).astype(np.float32)
        return self._queries

    def get_groundtruth(self, k=None) -> np.ndarray:
        """计算 groundtruth（暴力搜索，仅用于小数据集）"""
        if k is None:
            k = 10

        if self._groundtruth is None or self._groundtruth.shape[1] != k:
            data = self.get_dataset()
            queries = self.get_queries()

            # 计算欧氏距离矩阵
            distances = np.linalg.norm(data[np.newaxis, :, :] - queries[:, np.newaxis, :], axis=2)

            # 返回最近的 k 个索引
            self._groundtruth = np.argsort(distances, axis=1)[:, :k]

        return self._groundtruth

    def distance(self) -> str:
        return "euclidean"

    def short_name(self) -> str:
        return f"random-{self._get_size_suffix()}"


class SIFT(Dataset):
    """
    SIFT 数据集 (1M 向量)

    数据存储在: raw_data/sift/
    下载地址: https://drive.google.com/drive/folders/1PngXRH9jnN86T8RNiU-QyGqOillfQE_p
    """

    def __init__(self):
        super().__init__()
        self.nb = 1000000
        self.nq = 10000
        self.d = 128
        self.dtype = "float32"
        self.basedir = os.path.join(BASEDIR, "sift")
        self.ds_fn = f"data_{self.nb}_{self.d}"
        self.qs_fn = f"queries_{self.nq}_{self.d}"
        self.gt_fn = f"gt_{self.nb}_{self.nq}_{self.d}"

    def prepare(self, skip_data: bool = False) -> None:
        os.makedirs(self.basedir, exist_ok=True)

        # 检查是否已经下载
        if any(os.listdir(self.basedir)):
            print("✓ SIFT has already been installed!")
        else:
            # 下载数据集
            download_dataset("sift", self.basedir)

        # 检查是否需要预处理
        data_file = os.path.join(self.basedir, self.ds_fn)
        queries_file = os.path.join(self.basedir, self.qs_fn)

        if os.path.exists(data_file) and os.path.exists(queries_file):
            print("✓ Preprocessed data already exists.")
            return

        # 预处理数据
        print("Preprocessing data...")
        try:
            num, dim, vectors = load_data(os.path.join(self.basedir, f"data_{self.nb}_{self.d}"))
            index_vectors, _ = sample_vectors(vectors, self.nb, self.nq)
            save_data(index_vectors, type="data", basedir=self.basedir)

            num, dim, vectors = load_data(os.path.join(self.basedir, f"queries_{self.nq}_{self.d}"))
            _, query_vectors = sample_vectors(vectors, 0, self.nq)
            save_data(query_vectors, type="queries", basedir=self.basedir)
            print("✓ Preprocessing completed!")
        except Exception as e:
            print(f"⚠ Preprocessing skipped: {e}")

    def get_dataset_fn(self) -> str:
        return os.path.join(self.basedir, self.ds_fn)

    def get_dataset(self) -> np.ndarray:
        """仅用于小数据集测试"""
        assert self.nb <= 10**7, "Dataset too large, use iterator"
        return sanitize(xbin_mmap(self.get_dataset_fn(), dtype=self.dtype, maxn=self.nb))

    def get_dataset_iterator(self, bs: int = 512, split=(1, 0)):
        nsplit, rank = split
        filename = self.get_dataset_fn()
        x = xbin_mmap(filename, dtype=self.dtype, maxn=self.nb)
        i0 = self.nb * rank // nsplit
        i1 = self.nb * (rank + 1) // nsplit

        for j0 in range(i0, i1, bs):
            j1 = min(j0 + bs, i1)
            yield sanitize(x[j0:j1])

    def get_queries(self) -> np.ndarray:
        filename = os.path.join(self.basedir, self.qs_fn)
        return sanitize(xbin_mmap(filename, dtype=self.dtype))

    def get_groundtruth(self, k=None) -> np.ndarray:
        filename = os.path.join(self.basedir, self.gt_fn)
        I, D = knn_result_read(filename)
        if k is not None:
            I = I[:, :k]
        return I

    def distance(self) -> str:
        return "euclidean"

    def short_name(self) -> str:
        return "sift"


class SIFT100M(Dataset):
    """
    SIFT 100M 数据集

    数据存储在: raw_data/sift-100m/
    """

    def __init__(self):
        super().__init__()
        self.nb = 100000000
        self.nq = 1000
        self.d = 128
        self.dtype = "float32"
        self.basedir = os.path.join(BASEDIR, "sift-100m")
        self.ds_fn = f"base.{self.nb}.u8bin"
        self.qs_fn = "query.public.10K.u8bin"
        self.gt_fn = "gt.public.10K.bin"

    def prepare(self, skip_data: bool = False) -> None:
        os.makedirs(self.basedir, exist_ok=True)
        print(f"✓ SIFT100M dataset directory: {self.basedir}")
        print("  Note: Very large dataset (100M vectors). Ensure sufficient storage space.")

        if not skip_data and not os.path.exists(self.get_dataset_fn()):
            print("  Download from: https://big-ann-benchmarks.com/")

    def get_dataset_fn(self) -> str:
        return os.path.join(self.basedir, self.ds_fn)

    def get_dataset_iterator(self, bs: int = 512, split=(1, 0)):
        """大数据集仅支持迭代器访问"""
        nsplit, rank = split
        filename = self.get_dataset_fn()
        x = xbin_mmap(filename, dtype=self.dtype, maxn=self.nb)
        i0 = self.nb * rank // nsplit
        i1 = self.nb * (rank + 1) // nsplit

        for j0 in range(i0, i1, bs):
            j1 = min(j0 + bs, i1)
            yield sanitize(x[j0:j1])

    def get_queries(self) -> np.ndarray:
        filename = os.path.join(self.basedir, self.qs_fn)
        return sanitize(xbin_mmap(filename, dtype=self.dtype))

    def get_groundtruth(self, k=None) -> np.ndarray:
        filename = os.path.join(self.basedir, self.gt_fn)
        I, D = knn_result_read(filename)
        if k is not None:
            I = I[:, :k]
        return I

    def distance(self) -> str:
        return "euclidean"

    def short_name(self) -> str:
        return "sift-100m"


class OpenImagesStreaming(Dataset):
    """
    OpenImages Streaming 数据集

    数据存储在: raw_data/openimages/
    """

    def __init__(self):
        super().__init__()
        self.nb = 1000000
        self.nq = 10000
        self.d = 512
        self.dtype = "float32"
        self.basedir = os.path.join(BASEDIR, "openimages")
        self.ds_fn = "base.1M.fbin"
        self.qs_fn = "query.public.10K.fbin"
        self.gt_fn = "gt.public.10K.bin"

    def prepare(self, skip_data: bool = False) -> None:
        os.makedirs(self.basedir, exist_ok=True)
        print(f"✓ OpenImages dataset directory: {self.basedir}")

    def get_dataset_fn(self) -> str:
        return os.path.join(self.basedir, self.ds_fn)

    def get_dataset_iterator(self, bs: int = 512, split=(1, 0)):
        nsplit, rank = split
        filename = self.get_dataset_fn()
        x = xbin_mmap(filename, dtype=self.dtype, maxn=self.nb)
        i0 = self.nb * rank // nsplit
        i1 = self.nb * (rank + 1) // nsplit

        for j0 in range(i0, i1, bs):
            j1 = min(j0 + bs, i1)
            yield sanitize(x[j0:j1])

    def get_queries(self) -> np.ndarray:
        filename = os.path.join(self.basedir, self.qs_fn)
        return sanitize(xbin_mmap(filename, dtype=self.dtype))

    def get_groundtruth(self, k=None) -> np.ndarray:
        filename = os.path.join(self.basedir, self.gt_fn)
        I, D = knn_result_read(filename)
        if k is not None:
            I = I[:, :k]
        return I

    def distance(self) -> str:
        return "euclidean"

    def short_name(self) -> str:
        return "openimages"


class Sun(Dataset):
    """
    SUN 数据集

    数据存储在: raw_data/sun/
    """

    def __init__(self):
        super().__init__()
        self.nb = 79106
        self.nq = 200
        self.d = 512
        self.dtype = "float32"
        self.basedir = os.path.join(BASEDIR, "sun")
        self.ds_fn = "base.fbin"
        self.qs_fn = "query.fbin"
        self.gt_fn = "gt.bin"

    def prepare(self, skip_data: bool = False) -> None:
        os.makedirs(self.basedir, exist_ok=True)
        print(f"✓ SUN dataset directory: {self.basedir}")

    def get_dataset_fn(self) -> str:
        return os.path.join(self.basedir, self.ds_fn)

    def get_dataset(self) -> np.ndarray:
        return sanitize(xbin_mmap(self.get_dataset_fn(), dtype=self.dtype, maxn=self.nb))

    def get_dataset_iterator(self, bs: int = 512, split=(1, 0)):
        nsplit, rank = split
        data = self.get_dataset()
        i0 = len(data) * rank // nsplit
        i1 = len(data) * (rank + 1) // nsplit

        for j0 in range(i0, i1, bs):
            j1 = min(j0 + bs, i1)
            yield data[j0:j1]

    def get_queries(self) -> np.ndarray:
        filename = os.path.join(self.basedir, self.qs_fn)
        return sanitize(xbin_mmap(filename, dtype=self.dtype))

    def get_groundtruth(self, k=None) -> np.ndarray:
        filename = os.path.join(self.basedir, self.gt_fn)
        I, D = knn_result_read(filename)
        if k is not None:
            I = I[:, :k]
        return I

    def distance(self) -> str:
        return "euclidean"

    def short_name(self) -> str:
        return "sun"


class Msong(Dataset):
    """
    Million Song 数据集

    数据存储在: raw_data/msong/
    """

    def __init__(self):
        super().__init__()
        self.nb = 992272
        self.nq = 200
        self.d = 420
        self.dtype = "float32"
        self.basedir = os.path.join(BASEDIR, "msong")
        self.ds_fn = "base.fbin"
        self.qs_fn = "query.fbin"
        self.gt_fn = "gt.bin"

    def prepare(self, skip_data: bool = False) -> None:
        os.makedirs(self.basedir, exist_ok=True)
        print(f"✓ MSONG dataset directory: {self.basedir}")

    def get_dataset_fn(self) -> str:
        return os.path.join(self.basedir, self.ds_fn)

    def get_dataset_iterator(self, bs: int = 512, split=(1, 0)):
        nsplit, rank = split
        filename = self.get_dataset_fn()
        x = xbin_mmap(filename, dtype=self.dtype, maxn=self.nb)
        i0 = self.nb * rank // nsplit
        i1 = self.nb * (rank + 1) // nsplit

        for j0 in range(i0, i1, bs):
            j1 = min(j0 + bs, i1)
            yield sanitize(x[j0:j1])

    def get_queries(self) -> np.ndarray:
        filename = os.path.join(self.basedir, self.qs_fn)
        return sanitize(xbin_mmap(filename, dtype=self.dtype))

    def get_groundtruth(self, k=None) -> np.ndarray:
        filename = os.path.join(self.basedir, self.gt_fn)
        I, D = knn_result_read(filename)
        if k is not None:
            I = I[:, :k]
        return I

    def distance(self) -> str:
        return "euclidean"

    def short_name(self) -> str:
        return "msong"


class COCO(Dataset):
    """
    COCO 数据集

    数据存储在: raw_data/coco/
    """

    def __init__(self):
        super().__init__()
        self.nb = 100000
        self.nq = 500
        self.d = 768
        self.dtype = "float32"
        self.basedir = os.path.join(BASEDIR, "coco")
        self.ds_fn = "base.fbin"
        self.qs_fn = "query.fbin"
        self.gt_fn = "gt.bin"

    def prepare(self, skip_data: bool = False) -> None:
        os.makedirs(self.basedir, exist_ok=True)
        print(f"✓ COCO dataset directory: {self.basedir}")

    def get_dataset_fn(self) -> str:
        return os.path.join(self.basedir, self.ds_fn)

    def get_dataset_iterator(self, bs: int = 512, split=(1, 0)):
        nsplit, rank = split
        filename = self.get_dataset_fn()
        x = xbin_mmap(filename, dtype=self.dtype, maxn=self.nb)
        i0 = self.nb * rank // nsplit
        i1 = self.nb * (rank + 1) // nsplit

        for j0 in range(i0, i1, bs):
            j1 = min(j0 + bs, i1)
            yield sanitize(x[j0:j1])

    def get_queries(self) -> np.ndarray:
        filename = os.path.join(self.basedir, self.qs_fn)
        return sanitize(xbin_mmap(filename, dtype=self.dtype))

    def get_groundtruth(self, k=None) -> np.ndarray:
        filename = os.path.join(self.basedir, self.gt_fn)
        I, D = knn_result_read(filename)
        if k is not None:
            I = I[:, :k]
        return I

    def distance(self) -> str:
        return "euclidean"

    def short_name(self) -> str:
        return "coco"


class Glove(Dataset):
    """
    GloVe 数据集

    数据存储在: raw_data/glove/
    """

    def __init__(self):
        super().__init__()
        self.nb = 1192514
        self.nq = 200
        self.d = 100
        self.dtype = "float32"
        self.basedir = os.path.join(BASEDIR, "glove")
        self.ds_fn = "base.fbin"
        self.qs_fn = "query.fbin"
        self.gt_fn = "gt.bin"

    def prepare(self, skip_data: bool = False) -> None:
        os.makedirs(self.basedir, exist_ok=True)
        print(f"✓ GloVe dataset directory: {self.basedir}")

    def get_dataset_fn(self) -> str:
        return os.path.join(self.basedir, self.ds_fn)

    def get_dataset_iterator(self, bs: int = 512, split=(1, 0)):
        nsplit, rank = split
        filename = self.get_dataset_fn()
        x = xbin_mmap(filename, dtype=self.dtype, maxn=self.nb)
        i0 = self.nb * rank // nsplit
        i1 = self.nb * (rank + 1) // nsplit

        for j0 in range(i0, i1, bs):
            j1 = min(j0 + bs, i1)
            yield sanitize(x[j0:j1])

    def get_queries(self) -> np.ndarray:
        filename = os.path.join(self.basedir, self.qs_fn)
        return sanitize(xbin_mmap(filename, dtype=self.dtype))

    def get_groundtruth(self, k=None) -> np.ndarray:
        filename = os.path.join(self.basedir, self.gt_fn)
        I, D = knn_result_read(filename)
        if k is not None:
            I = I[:, :k]
        return I

    def distance(self) -> str:
        return "euclidean"

    def short_name(self) -> str:
        return "glove"


class MSTuring(Dataset):
    """
    MS Turing 数据集 (100M)

    数据存储在: raw_data/msturing-100m/
    """

    def __init__(self):
        super().__init__()
        self.nb = 100000000  # 100M
        self.nq = 100
        self.d = 100
        self.dtype = "float32"
        self.basedir = os.path.join(BASEDIR, "msturing-100m")
        self.ds_fn = "base.100M.fbin"
        self.qs_fn = "query.fbin"
        self.gt_fn = "gt.bin"

    def prepare(self, skip_data: bool = False) -> None:
        os.makedirs(self.basedir, exist_ok=True)
        print(f"✓ MSTuring dataset directory: {self.basedir}")
        print("  Note: Large dataset (100M vectors). Ensure sufficient storage space.")

    def get_dataset_fn(self) -> str:
        return os.path.join(self.basedir, self.ds_fn)

    def get_dataset_iterator(self, bs: int = 512, split=(1, 0)):
        nsplit, rank = split
        filename = self.get_dataset_fn()
        x = xbin_mmap(filename, dtype=self.dtype, maxn=self.nb)
        i0 = self.nb * rank // nsplit
        i1 = self.nb * (rank + 1) // nsplit

        for j0 in range(i0, i1, bs):
            j1 = min(j0 + bs, i1)
            yield sanitize(x[j0:j1])

    def get_queries(self) -> np.ndarray:
        filename = os.path.join(self.basedir, self.qs_fn)
        return sanitize(xbin_mmap(filename, dtype=self.dtype))

    def get_groundtruth(self, k=None) -> np.ndarray:
        filename = os.path.join(self.basedir, self.gt_fn)
        I, D = knn_result_read(filename)
        if k is not None:
            I = I[:, :k]
        return I

    def distance(self) -> str:
        return "euclidean"

    def short_name(self) -> str:
        return "msturing-100m"


class WTE(Dataset):
    """
    Word Translation Embeddings 数据集

    数据存储在: raw_data/wte-{drift}/
    """

    def __init__(self, drift: float = -0.05):
        """
        Args:
            drift: 漂移参数 (-0.05, -0.1, -0.2, -0.4, -0.6, -0.8)
        """
        super().__init__()
        self.drift = drift
        self.nb = 100000
        self.nq = 1000
        self.d = 768
        self.dtype = "float32"
        # 使用小写和正数表示漂移
        drift_str = str(abs(drift)).replace(".", "")
        self.basedir = os.path.join(BASEDIR, f"wte-{drift_str}")
        self.ds_fn = "base.fbin"
        self.qs_fn = "query.fbin"
        self.gt_fn = "gt.bin"

    def prepare(self, skip_data: bool = False) -> None:
        os.makedirs(self.basedir, exist_ok=True)
        print(f"✓ WTE (drift={self.drift}) dataset directory: {self.basedir}")

    def get_dataset_fn(self) -> str:
        return os.path.join(self.basedir, self.ds_fn)

    def get_dataset_iterator(self, bs: int = 512, split=(1, 0)):
        nsplit, rank = split
        filename = self.get_dataset_fn()
        x = xbin_mmap(filename, dtype=self.dtype, maxn=self.nb)
        i0 = self.nb * rank // nsplit
        i1 = self.nb * (rank + 1) // nsplit

        for j0 in range(i0, i1, bs):
            j1 = min(j0 + bs, i1)
            yield sanitize(x[j0:j1])

    def get_queries(self) -> np.ndarray:
        filename = os.path.join(self.basedir, self.qs_fn)
        return sanitize(xbin_mmap(filename, dtype=self.dtype))

    def get_groundtruth(self, k=None) -> np.ndarray:
        filename = os.path.join(self.basedir, self.gt_fn)
        I, D = knn_result_read(filename)
        if k is not None:
            I = I[:, :k]
        return I

    def distance(self) -> str:
        return "euclidean"

    def short_name(self) -> str:
        drift_str = str(abs(self.drift)).replace(".", "")
        return f"wte-{drift_str}"


# 数据集注册表
DATASETS: dict[str, Callable[[], Dataset]] = {
    # SIFT 系列
    "sift-small": lambda: SIFTSmall(),
    "sift": lambda: SIFT(),
    "sift-100m": lambda: SIFT100M(),
    # 图像数据集
    "openimages": lambda: OpenImagesStreaming(),
    "sun": lambda: Sun(),
    "coco": lambda: COCO(),
    # 文本/词向量数据集
    "glove": lambda: Glove(),
    "msong": lambda: Msong(),
    "msturing-100m": lambda: MSTuring(),
    # WTE 系列（不同漂移参数）
    "wte-0.05": lambda: WTE(-0.05),
    "wte-0.1": lambda: WTE(-0.1),
    "wte-0.2": lambda: WTE(-0.2),
    "wte-0.4": lambda: WTE(-0.4),
    "wte-0.6": lambda: WTE(-0.6),
    "wte-0.8": lambda: WTE(-0.8),
    # 随机数据集（用于测试）
    "random-xs": lambda: RandomDataset(10000, 1000, 20),
    "random-s": lambda: RandomDataset(100000, 1000, 50),
    "random-m": lambda: RandomDataset(500000, 1000, 128),
}


def register_dataset(name: str, factory: Callable[[], Dataset]) -> None:
    """
    注册新的数据集

    Args:
        name: 数据集名称
        factory: 返回 Dataset 实例的工厂函数
    """
    DATASETS[name] = factory


def get_dataset(name: str) -> Dataset:
    """
    根据名称获取数据集实例

    Args:
        name: 数据集名称

    Returns:
        Dataset 实例

    Raises:
        ValueError: 如果数据集不存在
    """
    if name not in DATASETS:
        available = ", ".join(sorted(DATASETS.keys()))
        raise ValueError(f"Unknown dataset: '{name}'. Available datasets: {available}")

    return DATASETS[name]()
