"""
数据集准备示例代码

展示如何使用 big-ann-benchmarks 的完整下载和预处理流程
"""

import os

from sage.benchmark.benchmark_db.datasets.download_utils import download_dataset
from sage.benchmark.benchmark_db.datasets.registry import load_data, sample_vectors, save_data

# 示例：完整的数据集 prepare() 方法实现


def prepare_with_download(self, skip_data=False):
    """
    完整的数据集准备流程（参考 big-ann-benchmarks）

    包含以下步骤：
    1. 创建目录
    2. 检查并下载数据
    3. 预处理数据（采样、转换格式等）
    """
    import os

    from .download_utils import download_dataset
    from .registry import load_data, sample_vectors, save_data

    # 步骤 1: 创建目录
    os.makedirs(self.basedir, exist_ok=True)

    # 步骤 2: 检查并下载
    download_flag = False
    for item in os.listdir(self.basedir):
        item_path = os.path.join(self.basedir, item)
        if os.path.isdir(item_path) or os.path.isfile(item_path):
            print(f"✓ {self.__class__.__name__} has already been installed!")
            download_flag = True
            break

    if not download_flag:
        # 使用 short_name() 作为数据集标识符
        dataset_key = self.short_name()
        download_dataset(dataset_key, self.basedir)

    # 步骤 3: 预处理检查
    preprocess_flag = False
    data_file_path = os.path.join(self.basedir, self.ds_fn)
    queries_file_path = os.path.join(self.basedir, self.qs_fn)

    if os.path.exists(data_file_path) and os.path.exists(queries_file_path):
        print("✓ Preprocessed data already exists. Skipping data generation.")
        preprocess_flag = True

    # 步骤 4: 执行预处理（如果需要）
    if not preprocess_flag and not skip_data:
        print("Preprocessing data...")
        try:
            # 加载原始数据
            num, dim, vectors = load_data(os.path.join(self.basedir, f"data_{self.nb}_{self.d}"))

            # 采样生成基础向量和查询向量
            index_vectors, query_vectors = sample_vectors(vectors, self.nb, self.nq)

            # 保存处理后的数据
            save_data(index_vectors, type="data", basedir=self.basedir)
            save_data(query_vectors, type="queries", basedir=self.basedir)

            print("✓ Preprocessing completed!")
        except Exception as e:
            print(f"⚠ Preprocessing failed: {e}")
            print("  You may need to preprocess the data manually")


# 各数据集的完整 prepare() 实现模板：


# ============================================================================
# SIFT-Small
# ============================================================================
def prepare_sift_small(self, skip_data=False):
    os.makedirs(self.basedir, exist_ok=True)

    if any(os.listdir(self.basedir)):
        print("✓ SIFT-Small has already been installed!")
        return

    download_dataset("sift-small", self.basedir)


# ============================================================================
# SIFT
# ============================================================================
def prepare_sift(self, skip_data=False):
    os.makedirs(self.basedir, exist_ok=True)

    # 下载检查
    if any(os.listdir(self.basedir)):
        print("✓ SIFT has already been installed!")
    else:
        download_dataset("sift", self.basedir)

    # 预处理检查
    data_file = os.path.join(self.basedir, self.ds_fn)
    queries_file = os.path.join(self.basedir, self.qs_fn)

    if os.path.exists(data_file) and os.path.exists(queries_file):
        print("✓ Preprocessed data already exists.")
        return

    # 预处理
    print("Preprocessing data...")
    try:
        num, dim, vectors = load_data(os.path.join(self.basedir, "data_1000000_128"))
        index_vectors, _ = sample_vectors(vectors, self.nb, self.nq)
        save_data(index_vectors, type="data", basedir=self.basedir)

        num, dim, vectors = load_data(os.path.join(self.basedir, "queries_10000_128"))
        _, query_vectors = sample_vectors(vectors, 0, self.nq)
        save_data(query_vectors, type="queries", basedir=self.basedir)
        print("✓ Preprocessing completed!")
    except Exception as e:
        print(f"⚠ Preprocessing failed: {e}")


# ============================================================================
# OpenImages
# ============================================================================
def prepare_openimages(self, skip_data=False):
    os.makedirs(self.basedir, exist_ok=True)

    if any(os.listdir(self.basedir)):
        print("✓ OpenImages has already been installed!")
    else:
        download_dataset("openimages", self.basedir)

    data_file = os.path.join(self.basedir, self.ds_fn)
    queries_file = os.path.join(self.basedir, self.qs_fn)

    if os.path.exists(data_file) and os.path.exists(queries_file):
        print("✓ Preprocessed data already exists.")
        return

    print("Preprocessing data...")
    try:
        num, dim, vectors = load_data(os.path.join(self.basedir, "data_1000000_512"))
        index_vectors, _ = sample_vectors(vectors, self.nb, self.nq)
        save_data(index_vectors, type="data", basedir=self.basedir)

        num, dim, vectors = load_data(os.path.join(self.basedir, "queries_10000_512"))
        _, query_vectors = sample_vectors(vectors, 0, self.nq)
        save_data(query_vectors, type="queries", basedir=self.basedir)
        print("✓ Preprocessing completed!")
    except Exception as e:
        print(f"⚠ Preprocessing failed: {e}")


# ============================================================================
# Sun
# ============================================================================
def prepare_sun(self, skip_data=False):
    os.makedirs(self.basedir, exist_ok=True)

    if any(os.listdir(self.basedir)):
        print("✓ Sun has already been installed!")
    else:
        download_dataset("sun", self.basedir)

    data_file = os.path.join(self.basedir, self.ds_fn)
    queries_file = os.path.join(self.basedir, self.qs_fn)

    if os.path.exists(data_file) and os.path.exists(queries_file):
        print("✓ Preprocessed data already exists.")
        return

    print("Preprocessing data...")
    try:
        num, dim, vectors = load_data(os.path.join(self.basedir, "data_79106_512"))
        index_vectors, query_vectors = sample_vectors(vectors, self.nb, self.nq)
        save_data(index_vectors, type="data", basedir=self.basedir)
        save_data(query_vectors, type="queries", basedir=self.basedir)
        print("✓ Preprocessing completed!")
    except Exception as e:
        print(f"⚠ Preprocessing failed: {e}")


# ============================================================================
# Glove
# ============================================================================
def prepare_glove(self, skip_data=False):
    os.makedirs(self.basedir, exist_ok=True)

    if any(os.listdir(self.basedir)):
        print("✓ Glove has already been installed!")
    else:
        download_dataset("glove", self.basedir)

    data_file = os.path.join(self.basedir, self.ds_fn)
    queries_file = os.path.join(self.basedir, self.qs_fn)

    if os.path.exists(data_file) and os.path.exists(queries_file):
        print("✓ Preprocessed data already exists.")
        return

    print("Preprocessing data...")
    try:
        num, dim, vectors = load_data(os.path.join(self.basedir, "data_1192514_100"))
        index_vectors, query_vectors = sample_vectors(vectors, self.nb, self.nq)
        save_data(index_vectors, type="data", basedir=self.basedir)
        save_data(query_vectors, type="queries", basedir=self.basedir)
        print("✓ Preprocessing completed!")
    except Exception as e:
        print(f"⚠ Preprocessing failed: {e}")


# 使用说明：
#
# 1. 每个数据集类的 prepare() 方法应该按照上面的模板实现
# 2. 关键步骤：检查已下载 → 下载 → 检查已预处理 → 预处理
# 3. 使用 download_dataset() 函数统一处理下载逻辑
# 4. 预处理包括：加载原始数据、采样、保存标准格式
