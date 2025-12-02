# Datasets Module

数据集管理模块，参考 big-ann-benchmarks 设计，提供统一的数据集下载、预处理和访问接口。

## 核心特性

- **自动下载**: 支持从 Google Drive 自动下载数据集
- **统一接口**: 所有数据集提供一致的访问方法
- **内存优化**: 大数据集使用迭代器避免内存溢出
- **标准格式**: 统一的目录结构和文件格式

## 快速开始

### 安装依赖

```bash
pip install numpy gdown
```

### 基本使用

```python
from benchmark_anns.datasets import DATASETS

# 获取数据集实例
dataset = DATASETS['sift']()

# 自动下载和准备（首次使用）
dataset.prepare()

# 访问数据
queries = dataset.get_queries()
groundtruth = dataset.get_groundtruth(k=10)

# 大数据集使用迭代器
for batch in dataset.get_dataset_iterator(bs=10000):
    # 处理批次
    pass
```

## 目录结构

```
raw_data/
├── sift-small/           # SIFT Small (10K vectors, 128d)
├── sift/                 # SIFT 1M (1M vectors, 128d)
├── sift-100m/            # SIFT 100M (100M vectors, 128d)
├── openimages/           # OpenImages (1M vectors, 512d)
├── sun/                  # SUN Scene (79K vectors, 512d)
├── msong/                # Million Song (992K vectors, 420d)
├── coco/                 # COCO (100K vectors, 768d)
├── glove/                # GloVe (1.19M vectors, 100d)
├── msturing-100m/        # MS Turing 100M (100M vectors, 100d)
├── wte-*/                # Word Translation Embeddings (各种 drift 参数)
└── random-*/             # 随机测试数据集
```

每个数据集目录包含：

- `base.{format}` - 基础向量数据
- `query.{format}` - 查询向量
- `gt.{format}` - Ground truth 结果

## 支持的数据集

### SIFT 系列

- **sift-small**: 10K vectors, 128d - 测试用小数据集
- **sift**: 1M vectors, 128d - 标准 SIFT 数据集
- **sift-100m**: 100M vectors, 128d - 大规模数据集

### 图像特征数据集

- **openimages**: 1M vectors, 512d
- **sun**: 79K vectors, 512d
- **coco**: 100K vectors, 768d

### 文本/词向量数据集

- **glove**: 1.19M vectors, 100d - GloVe 词向量
- **msong**: 992K vectors, 420d - Million Song Dataset
- **msturing-100m**: 100M vectors, 100d - MS Turing 大规模数据集

### 其他数据集

- **wte-**\*: Word Translation Embeddings (drift 参数: -0.05, -0.1, -0.2, -0.4, -0.6, -0.8)
- **random-xs/s/m**: 随机生成的测试数据集

## 数据集下载

### 自动下载（推荐）

```python
# 数据集会自动从 Google Drive 下载
dataset = DATASETS['sift']()
dataset.prepare()
```

### 下载链接

| 数据集     | 大小   | 下载链接                                                                                 |
| ---------- | ------ | ---------------------------------------------------------------------------------------- |
| SIFT-Small | ~50MB  | [Google Drive](https://drive.google.com/drive/folders/1XbvrSjlP-oUZ5cixVpfSTn0zE-Cim0NK) |
| SIFT       | ~500MB | [Google Drive](https://drive.google.com/drive/folders/1PngXRH9jnN86T8RNiU-QyGqOillfQE_p) |
| OpenImages | ~2GB   | [Google Drive](https://drive.google.com/drive/folders/1ZkWOrja-0A6C9yh3ysFoCP6w5u7oWjQx) |
| Sun        | ~160MB | [Google Drive](https://drive.google.com/drive/folders/1gNK1n-do-7d5N-Z1tuAoXe5Xq3I8fZIH) |
| COCO       | ~300MB | [Google Drive](https://drive.google.com/drive/folders/1Hp6SI8YOFPdWbmC1a4_-1dZWxZH3CHMS) |
| Glove      | ~500MB | [Google Drive](https://drive.google.com/drive/folders/1m06VVmXmklHr7QZzdz6w8EtYmuRGIl9s) |
| Msong      | ~1.6GB | [Google Drive](https://drive.google.com/drive/folders/1TnLNJNVqyFrEzKGfQVdvUC8Al-tmjVg0) |

**注意**:

- SIFT-100M 和 MSTuring-100M 是超大数据集（各约 50GB），需手动下载
- 下载可能需要较长时间，Google Drive 可能有配额限制

## API 参考

### 数据集注册表

所有数据集通过 `DATASETS` 字典访问：

```python
from benchmark_anns.datasets import DATASETS

# 获取可用数据集列表
print(DATASETS.keys())

# 创建数据集实例
dataset = DATASETS['sift']()
```

### Dataset 基类方法

每个数据集都提供以下方法：

```python
# 准备数据集（下载、创建目录）
dataset.prepare()

# 获取数据（小数据集）
base_vectors = dataset.get_dataset()

# 获取数据迭代器（大数据集推荐）
for batch in dataset.get_dataset_iterator(bs=10000):
    process(batch)

# 获取查询向量
queries = dataset.get_queries()

# 获取 ground truth
gt = dataset.get_groundtruth(k=10)

# 获取数据集属性
dataset.nb           # 基础向量数量
dataset.nq           # 查询向量数量
dataset.d            # 向量维度
dataset.distance()   # 距离度量 ('euclidean', 'cosine', etc.)
dataset.short_name() # 数据集短名称
```

## 文件格式

### `.fvecs` / `.ivecs` 格式（SIFT-Small）

传统 SIFT 格式，每个向量：`[dim: int32][data: float32/int32 × dim]`

### `.bin` / `.u8bin` / `.fbin` 格式（Big-ANN）

- 文件头: `[n: uint32][d: uint32]`
- 数据: `[vectors: dtype × n × d]`

### Ground Truth 格式

二进制整数索引，包含最近邻索引和距离

## 添加新数据集

1. 在 `registry.py` 中创建数据集类：

```python
class MyDataset(Dataset):
    def __init__(self):
        super().__init__()
        self.nb = 10000      # 基础向量数
        self.nq = 100        # 查询向量数
        self.d = 64          # 向量维度
        self.basedir = os.path.join(BASEDIR, "mydataset")
        self.ds_fn = "base.fbin"
        self.qs_fn = "query.fbin"
        self.gt_fn = "gt.bin"

    def prepare(self, skip_data=False):
        os.makedirs(self.basedir, exist_ok=True)
        if any(os.listdir(self.basedir)):
            print("✓ Dataset already installed!")
            return
        download_dataset('mydataset', self.basedir)

    def short_name(self):
        return "mydataset"

    def distance(self):
        return "euclidean"
```

2. 注册数据集：

```python
DATASETS['mydataset'] = lambda: MyDataset()
```

3. 在 `download_utils.py` 中添加下载链接（如需自动下载）

## 注意事项

- 大数据集（sift-100m, msturing-100m）需要大量存储空间（各约 50GB）
- 使用迭代器而非直接加载来处理大数据集
- Random 数据集在内存中动态生成，不需要下载
- 首次使用数据集时会自动下载，请确保网络连接稳定

## 参考

- [big-ann-benchmarks](https://github.com/harsha-simhadri/big-ann-benchmarks)
- [Google Drive Python API (gdown)](https://github.com/wkentaro/gdown)
