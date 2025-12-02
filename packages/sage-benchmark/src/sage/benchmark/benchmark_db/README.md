# Benchmark ANNS - 流式向量索引基准测试框架

一个完整的流式索引基准测试框架，专注于评估向量索引在动态数据场景下的性能。

**特点**: 包含所有必需的第三方库源代码，开箱即用。

## 📁 项目结构

```
benchmark_anns/
├── datasets/           # 数据集管理
│   ├── base.py        # 数据集基类
│   ├── loaders.py     # 数据加载器
│   └── registry.py    # 数据集注册（SIFT, Glove, 随机数据等）
│
├── bench/              # 核心测试框架
│   ├── runner.py      # 测试运行器
│   ├── worker.py      # 工作线程（支持拥塞丢弃）
│   ├── metrics.py     # 性能指标计算
│   ├── maintenance.py # 索引维护策略
│   └── algorithms/    # 算法接口
│       ├── base.py    # BaseANN, BaseStreamingANN
│       └── registry.py # 算法注册表
│
├── algorithms_impl/    # 算法实现与第三方库
│   ├── faiss/         # Faiss 完整源码
│   ├── DiskANN/       # DiskANN 完整源码
│   ├── puck/          # Puck 完整源码
│   ├── SPTAG/         # SPTAG 完整源码
│   ├── candy/         # CANDY 源码
│   ├── bindings/      # Python 绑定（PyCANDY）
│   ├── build.sh       # 编译脚本
│   └── README.md      # 详细编译说明
│
├── runbooks/           # 实验配置文件
│   ├── simple.yaml    # 简单示例
│   ├── baseline.yaml  # 基准测试
│   └── experiments/   # 各类实验场景
│
├── tests/              # 测试套件
│   ├── test_streaming.py  # 流式测试
│   └── test_datasets.py   # 数据集测试
│
└── utils/              # 工具函数
    ├── io.py          # 文件 I/O
    ├── system.py      # 系统工具
    └── timestamp.py   # 时间戳处理
```

## 🚀 快速开始

### 方式1: 自动安装（推荐）

```bash
# 克隆仓库
git clone --recursive https://github.com/intellistream/SAGE-DB-Bench.git
cd SAGE-DB-Bench

# 运行安装脚本
./install.sh

# 激活环境
source venv/bin/activate
```

### 方式2: Docker（快速体验）

```bash
# 构建并运行
docker-compose up sage-bench-dev

# 或使用Docker
docker build -t sage-db-bench .
docker run -it -v $(pwd)/results:/app/results sage-db-bench
```

**⚠️ 注意**: Docker适合功能测试和开发，**不推荐用于精确的性能测试**（cache miss、CPU性能等会受容器影响）。

### 方式3: 手动安装

详见 [INSTALL.md](INSTALL.md) 获取完整安装指南。

```bash
# 1. 克隆仓库
git clone --recursive https://github.com/intellistream/SAGE-DB-Bench.git
cd SAGE-DB-Bench

# 2. 安装Python依赖
pip install -r requirements.txt

# 3. 编译算法库（可选，用于C++算法）
cd algorithms_impl
./build.sh

# 4. 运行测试
python tests/test_streaming.py
```

### 运行基准测试

```bash
# 使用简单配置
python __main__.py --config runbooks/simple.yaml --output results/test1

# 使用基准配置
python __main__.py --config runbooks/baseline.yaml --output results/baseline
```

## 📊 支持的实验场景

在 `runbooks/` 目录下提供了多种实验配置：

### 基础场景

- **baseline.yaml** - 基准性能测试
- **simple.yaml** - 简单示例

### 高级场景（experiments/ 子目录）

- **stress_tests/** - 压力测试
- **batch_sizes/** - 批次大小影响
- **event_rates/** - 不同事件率测试
- **data_volumes/** - 数据规模测试
- **search_patterns/** - 查询模式测试
- **deletion_patterns/** - 删除模式测试
- **concept_drift/** - 数据漂移场景
- **out_of_order/** - 乱序数据处理
- **random_contamination/** - 随机污染
- **random_drop/** - 随机丢弃

## 📝 Runbook 配置示例

```yaml
name: "my_test"
description: "流式索引测试"

# 数据集配置
dataset:
  name: "sift-small"  # 可选: sift, glove, random-xs 等

# 算法配置
algorithm:
  name: "faiss_hnsw"
  parameters:
    M: 16
    efConstruction: 200
    efSearch: 100

# 测试参数
test:
  k: 10                # 查询返回数量
  num_workers: 1       # 工作线程数

# 流式操作序列
operations:
  - type: initial_load
    count: 10000

  - type: batch_insert
    count: 50000
    batch_size: 1000
    event_rate: 1000   # 每秒事件数

  - type: search
    num_queries: 1000

  - type: maintenance_rebuild

# 输出配置
output:
  output_dir: "results/my_test"
  save_timestamps: true
  save_metrics: true
```

## 🔧 核心功能

### 支持的操作类型

1. **initial_load** - 初始数据加载
1. **batch_insert** - 批量流式插入
1. **search** - 搜索性能测试
1. **batch_delete** - 批量删除
1. **maintenance_rebuild** - 索引重建
1. **replace** - 数据替换

### 流式特性

- ✅ **事件时间戳模拟** - 真实的时间序列数据流
- ✅ **并发查询** - 在插入过程中持续查询
- ✅ **拥塞丢弃** - 当系统过载时自动丢弃数据
- ✅ **维护策略** - 支持定期重建和增量更新
- ✅ **内存监控** - 实时追踪内存使用
- ✅ **乱序处理** - 模拟乱序数据到达
- ✅ **数据污染** - 测试对噪声数据的鲁棒性

## 📈 性能指标

框架会自动计算以下指标：

- **延迟 (Latency)**: P50, P95, P99 延迟
- **吞吐量 (Throughput)**: 每秒处理的事件数
- **Drop Rate**: 数据丢弃率
- **Recall@k**: 查询召回率
- **QPS**: 每秒查询数
- **内存使用**: 峰值和平均内存占用

## 🎯 集成新算法

### 1. 实现算法接口

```python
from benchmark_anns.bench.algorithms import BaseStreamingANN

class MyAlgorithm(BaseStreamingANN):
    def __init__(self, **params):
        super().__init__()
        # 初始化算法

    def insert(self, vectors, ids):
        # 实现插入逻辑
        pass

    def delete(self, ids):
        # 实现删除逻辑
        pass

    def query(self, vectors, k):
        # 实现查询逻辑
        pass
```

### 2. 注册算法

```python
# 在 bench/algorithms/registry.py 中
from .my_algorithm import MyAlgorithm

def register_algorithm(name, algorithm_class, **default_params):
    ALGORITHMS[name] = {
        'class': algorithm_class,
        'params': default_params
    }

# 注册
register_algorithm('my_algo', MyAlgorithm, param1=10, param2='value')
```

### 3. 创建配置文件

在 `runbooks/` 下创建 YAML 配置文件，指定 `algorithm.name: "my_algo"`。

## 📚 支持的算法

### Python 实现

- **DummyStreamingANN** - 测试用虚拟算法

### C++ 实现（需编译）

- **Faiss HNSW** - 高性能近似最近邻搜索
- **Faiss IVFPQ** - 倒排文件 + 乘积量化
- **DiskANN** - 基于磁盘的大规模索引
- **Puck** - 高效向量检索
- **CANDY** - 拥塞感知动态索引系列
  - CANDY-MNRU
  - CANDY-LSHAPG
  - CANDY-SPTAG

## 🗃️ 支持的数据集

### 内置数据集

- **sift** - SIFT 1M 数据集
- **sift-small** - SIFT 100K 数据集
- **glove** - GloVe 词向量
- **msong** - Million Song Dataset
- **coco** - COCO 图像特征
- **random-xs/s/m/l** - 随机生成数据（不同规模）

### 添加自定义数据集

```python
# 在 datasets/registry.py 中
from .base import Dataset

class MyDataset(Dataset):
    def __init__(self):
        super().__init__()
        self.nb = 100000  # 基础数据量
        self.nq = 1000    # 查询数量
        self.d = 128      # 向量维度

    def prepare(self):
        # 加载或生成数据
        pass

    def get_dataset(self):
        # 返回基础数据 (nb, d)
        pass

    def get_queries(self):
        # 返回查询数据 (nq, d)
        pass

# 注册
DATASETS['my-dataset'] = lambda: MyDataset()
```

## 🔍 查看结果

测试结果会保存在指定的输出目录下：

```
results/my_test/
├── metrics.json       # 性能指标
├── timestamps.csv     # 详细时间戳数据
├── config.yaml        # 运行配置副本
└── visualizations/    # 可视化图表（如果启用）
```

## 🛠️ 开发指南

### 项目架构

- **数据层** (`datasets/`) - 负责数据加载和管理
- **算法层** (`bench/algorithms/`) - 定义算法接口
- **执行层** (`bench/`) - 测试流程控制和指标计算
- **实现层** (`algorithms_impl/`) - 具体算法实现

### 运行测试

```bash
# 运行所有测试
python tests/test_streaming.py
python tests/test_datasets.py

# 验证项目结构
bash tests/test_verify_project.sh
```

## 📊 批次级别指标（Batch Metrics）

框架会在每个批次操作时生成详细的性能指标，保存在 CSV 文件中：

### 插入操作指标（\*\_inserts.csv）

- **timestamp**: 批次开始时间
- **batch_size**: 批次大小
- **batch_duration**: 批次耗时（秒）
- **insert_qps**: 插入QPS（向量数/秒）
- **num_queries**: 并发查询数
- **query_qps**: 查询QPS（查询数/秒）
- **query_latency_p50/p95/p99**: 查询延迟分位数（秒）

### 查询操作指标（\*\_queries.csv）

- **timestamp**: 查询时间戳
- **num_queries**: 查询数量
- **query_duration**: 查询总耗时
- **query_qps**: 查询QPS
- **query_latency_p50/p95/p99**: 延迟分位数

### 使用场景

1. **性能分析** - 查看插入吞吐量随时间变化
1. **并发影响** - 分析插入与查询的相互影响
1. **延迟监控** - 追踪查询延迟的变化趋势
1. **瓶颈识别** - 发现性能瓶颈和异常批次

## 🎯 计算真值（Ground Truth）

### 基本用法

```bash
# 计算数据集的真值
python compute_gt.py --dataset sift --runbook runbooks/general_experiment.yaml

# 参数说明：
# --dataset: 数据集名称（如 sift, glove）
# --runbook: runbook 配置文件路径
# --k: 近邻数量（默认 100）
```

### 真值文件

计算完成后会在 `raw_data/{dataset}/{size}/{runbook_name}/` 下生成：

- `.gt100` - 真值索引文件
- `.tags` - ID 映射文件
- `.data` - 临时数据文件

### 注意事项

1. **DiskANN 依赖** - 使用 DiskANN 的 `compute_groundtruth` 工具
1. **内存需求** - 大数据集需要足够内存
1. **重要实验** - 框架会自动为标记为重要的实验生成所有阶段的真值

## 📤 结果导出

### 召回率计算

运行完测试后，使用以下命令计算召回率：

```bash
python -c "from bench.runner import StreamingANNRunner; \
    StreamingANNRunner('path/to/output_dir').compute_and_export_recall()"
```

### 导出文件

- **results_with_recall.csv** - 包含召回率的完整结果
- 包含字段：
  - operation_type: 操作类型
  - timestamp: 时间戳
  - recall@k: 召回率
  - latency_p50/p95/p99: 延迟分位数
  - qps: 查询吞吐量

### 批量导出

对多个实验结果统一计算召回率：

```bash
for dir in results/*/; do
    python -c "from bench.runner import StreamingANNRunner; \
        StreamingANNRunner('$dir').compute_and_export_recall()"
done
```

## ⚠️ 已知问题（Known Issues）

### runner.py 待修复问题

1. **真值路径问题**

   - 问题：搜索操作时真值文件路径不正确
   - 影响：无法正确计算召回率
   - 临时方案：手动指定真值文件路径

1. **initial_load vs fit 混淆**

   - 问题：`initial_load` 操作调用了 `fit()` 方法，但很多算法没实现 `fit()`
   - 影响：导致运行时错误
   - 临时方案：在算法中实现 `fit()` 方法或改用 `batch_insert`

1. **真值文件加载**

   - 问题：真值文件加载逻辑需要改进
   - 影响：某些场景下无法正确加载真值
   - 建议：重构真值文件管理逻辑

1. **步骤级真值**

   - 问题：需要支持每个操作步骤的独立真值文件
   - 影响：无法准确评估每个阶段的性能
   - 计划：支持 `step_0.gt100`, `step_1.gt100` 等格式

## 📖 更多文档

- `algorithms_impl/README.md` - 算法编译和实现详细说明
- `runbooks/README.md` - Runbook 配置详细说明
- `datasets/README.md` - 数据集说明

## 🤝 贡献

欢迎贡献新的算法实现、数据集支持和实验场景！

## 📄 许可证

遵循项目原始许可证。
