# Bench 模块

Bench 模块是 SAGE-DB-Bench 的核心组件，提供了流式向量索引的基准测试框架。

## 📁 目录结构

```
bench/
├── __init__.py
├── algorithms/          # 算法实现目录
├── cache_profiler.py    # Cache miss 性能分析工具
├── io_utils.py          # 结果导出工具
├── maintenance.py       # 索引维护操作
├── metrics.py           # 性能指标数据结构
├── runner.py            # Benchmark 运行器
└── worker.py            # 工作线程管理
```

## 🚀 快速开始

### 基本用法

```python
from bench.runner import BenchmarkRunner
from bench.algorithms import get_algorithm
from datasets import get_dataset

# 获取算法和数据集
algo = get_algorithm('faiss_HNSW', metric='euclidean')
dataset = get_dataset('sift')

# 创建 runner
runner = BenchmarkRunner(
    algorithm=algo,
    dataset=dataset,
    k=10,
    output_dir='results'
)

# 运行 benchmark
metrics = runner.run_runbook('general_experiment')
```

## 🔧 算法实现（Algorithm Implementations）

本目录包含所有 ANN 算法的 Python 封装实现，提供统一的流式索引接口。

### 已实现算法

#### CANDY 系列

- **candy_lshapg** - LSH + Approximate Proximity Graph
- **candy_mnru** - Most Nearly Recently Used
- **candy_sptag** - Space Partition Tree And Graph

#### Faiss 系列

- **faiss_HNSW** - Hierarchical NSW
- **faiss_HNSW_Optimized** - 优化版 HNSW
- **faiss_IVFPQ** - IVF + Product Quantization
- **faiss_lsh** - Locality Sensitive Hashing
- **faiss_NSW** - Navigable Small World
- **faiss_pq** - Product Quantization
- **faiss_fast_scan** - Fast Scan variant
- **faiss_onlinepq** - Online PQ with buffering

#### 其他算法

- **diskann** / **ipdiskann** - DiskANN 系列
- **puck** - Puck 索引
- **gti** - Graph-based Tree Index
- **plsh** - Partition-based LSH
- **cufe** / **pyanns** - 其他实现

### 通过注册表获取算法

```python
from bench.algorithms import get_algorithm, ALGORITHMS

# 获取算法实例
algo = get_algorithm('faiss_HNSW', metric='euclidean')

# 初始化
algo.setup(dtype='float32', max_pts=100000, ndim=128)

# 插入数据
algo.insert(vectors, ids)

# 查询
algo.set_query_arguments({'efSearch': 100})
results = algo.query(query_vectors, k=10)

# 列出所有已注册算法
print(list(ALGORITHMS.keys()))
```

### 添加新算法

1. **创建算法目录和文件**

```bash
mkdir bench/algorithms/my_algorithm/
touch bench/algorithms/my_algorithm/my_algorithm.py
touch bench/algorithms/my_algorithm/config.yaml
```

2. **实现算法类**

```python
# my_algorithm.py
from bench.algorithms.base import BaseStreamingANN
import numpy as np

class MyAlgorithm(BaseStreamingANN):
    def __init__(self, **params):
        super().__init__()
        self.params = params

    def setup(self, dtype: str, max_pts: int, ndim: int) -> None:
        """初始化索引"""
        self.ndim = ndim
        self.max_pts = max_pts

    def insert(self, X: np.ndarray, ids: np.ndarray) -> None:
        """插入向量"""
        pass

    def delete(self, ids: np.ndarray) -> None:
        """删除向量"""
        pass

    def query(self, X: np.ndarray, k: int):
        """查询 k 近邻，返回 (indices, distances)"""
        return np.array([]), np.array([])

    def set_query_arguments(self, query_args):
        """设置查询参数"""
        pass
```

3. **创建配置文件**

```yaml
# config.yaml
random-xs:
  my_algorithm:
    module: bench.algorithms.my_algorithm.my_algorithm
    constructor: MyAlgorithm
    base-args: ["@metric"]
    run-groups:
      base:
        args: |
          [{"param1": 10, "param2": 100}]
        query-args: |
          [{"query_param": 50}]
```

算法会在模块加载时自动注册，无需手动修改 `registry.py`。

### 接口规范

所有算法必须继承 `BaseStreamingANN` 并实现：

| 方法                          | 说明         | 必需 |
| ----------------------------- | ------------ | ---- |
| `setup(dtype, max_pts, ndim)` | 初始化索引   | ✅   |
| `insert(X, ids)`              | 插入向量     | ✅   |
| `delete(ids)`                 | 删除向量     | ✅   |
| `query(X, k)`                 | 查询 k 近邻  | ✅   |
| `set_query_arguments(args)`   | 设置查询参数 | ✅   |
| `fit(X)`                      | 批量建索引   | ⚪   |
| `get_memory_usage()`          | 获取内存使用 | ⚪   |

## 📊 Cache Miss Profiling 功能

### 功能概述

Cache miss profiling 使用 Linux `perf` 工具来监测向量索引操作的 cache miss 行为。该功能会在每个批次插入操作时测量以下指标：

- **Cache Misses**: 总 cache miss 次数（L1 + LLC）
- **Cache References**: cache 访问总次数
- **Cache Miss Rate**: cache miss 率（cache_misses / cache_references）
- **L1 D-cache Loads/Misses**: L1 数据缓存加载和 miss 统计
- **LLC Loads/Misses**: Last Level Cache 加载和 miss 统计
- **Instructions/Cycles**: 指令数和 CPU 周期数

### 系统要求

#### 1. 安装 perf 工具

**Ubuntu/Debian:**

```bash
sudo apt-get install linux-tools-common linux-tools-generic
```

**RHEL/CentOS:**

```bash
sudo yum install perf
```

**WSL2 (Windows Subsystem for Linux):**

```bash
# 安装对应内核版本的 perf 工具
sudo apt-get install linux-tools-$(uname -r)

# 如果上面命令失败，安装通用版本
sudo apt-get install linux-tools-generic
```

#### 2. 配置 perf 权限

在 Linux 或 WSL 中，需要调整 `perf_event_paranoid` 参数以允许非 root 用户使用 perf：

**临时配置（重启后失效）:**

```bash
sudo sysctl -w kernel.perf_event_paranoid=-1
```

**永久配置:**

```bash
echo 'kernel.perf_event_paranoid=-1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

**WSL2 特殊说明:**

- WSL2 需要内核版本 >= 5.10.16.3 才能正常使用 perf
- 检查内核版本: `uname -r`
- 如果版本过低，需要更新 WSL2 内核

#### 3. 验证 perf 可用性

运行以下命令测试 perf 是否正常工作：

```bash
cd bench
python cache_profiler.py
```

如果输出显示 "perf 工具可用"，说明配置成功。

### 使用方法

#### 在 BenchmarkRunner 中启用 cache profiling

修改你的 benchmark 脚本，在创建 `BenchmarkRunner` 时设置 `enable_cache_profiling=True`：

```python
from bench.runner import BenchmarkRunner

# 创建 runner 时启用 cache profiling
runner = BenchmarkRunner(
    algorithm=algo,
    dataset=dataset,
    k=10,
    enable_cache_profiling=True,  # 启用 cache miss 监测
    output_dir='results'
)

# 运行 benchmark
metrics = runner.run_runbook(runbook)
```

#### 查看输出结果

运行 benchmark 后，cache miss 数据会被保存到以下文件：

1. **{algorithm}\_batch_cache_miss.csv**

   - 位置: `results/{dataset}/{algorithm}/`
   - 格式:
     ```csv
     batch_idx,cache_misses,cache_references,cache_miss_rate
     0,1234567,12345678,0.10
     1,1345678,13456789,0.10
     ...
     ```

1. **{algorithm}_{dataset}_{runbook}\_final_results.csv**（通过 export_results.py 导出）

   - 包含 cache miss 与其他性能指标的综合数据
   - 列包括: batch_idx, recall, insert_qps, query_qps, query_latency_ms, cache_misses,
     cache_references, cache_miss_rate

#### 导出最终结果

使用 `export_results.py` 导出包含 cache miss 的综合结果：

```bash
python export_results.py \
    --dataset sift \
    --algorithm faiss_HNSW \
    --runbook general_experiment \
    --output-dir results
```

### 性能影响

启用 cache profiling 会对性能产生一定影响：

- **CPU 开销**: perf 工具会增加约 5-10% 的 CPU 开销
- **延迟影响**: 每个批次的启动/停止 profiler 会增加约 100-200 微秒的延迟
- **建议**: 仅在需要分析 cache 行为时启用该功能，日常 benchmark 可以关闭

### 示例输出

启用 cache profiling 后，benchmark 运行时会输出类似如下的信息：

```
[1/5] 执行操作: batch_insert
  批量插入: 50000 条数据
    [10] 10000~12500 querying all 10000 queries (进度: 25.0%)
    [20] 20000~22500 querying all 10000 queries (进度: 50.0%)
    批次延迟统计:
      端到端: 平均=15.23ms, P99=28.45ms
      索引插入: 平均=12.34ms
      队列等待: 平均=2.89ms
    Cache miss 统计:
      平均 cache misses: 1,234,567
      平均 cache miss 率: 12.34%
  ✓ 批量插入完成: 5.23s, 9560 ops/s, 20 个批次
```

### 故障排除

#### 问题: perf 工具不可用

**症状**: 运行时提示 "perf 工具未安装" 或 "perf 权限不足"

**解决方案**:

1. 检查 perf 是否已安装: `which perf`
1. 如果未安装，参考上面的安装说明
1. 检查权限配置: `cat /proc/sys/kernel/perf_event_paranoid`
   - 值应该为 -1 或更小
   - 如果不是，运行: `sudo sysctl -w kernel.perf_event_paranoid=-1`

#### 问题: WSL2 中 perf 无法正常工作

**症状**: 提示 "Permission denied" 或 "perf_event_paranoid"

**解决方案**:

1. 检查 WSL2 内核版本: `uname -r`
   - 需要 >= 5.10.16.3
1. 更新 WSL2 内核:
   ```bash
   wsl --update
   wsl --shutdown
   # 重新启动 WSL
   ```
1. 在 Windows PowerShell 中设置 WSL 配置 (`.wslconfig`):
   ```ini
   [wsl2]
   kernelCommandLine = perf_event_paranoid=-1
   ```

#### 问题: cache miss 数据全为 0

**症状**: CSV 文件中 cache_misses 和 cache_references 都是 0

**可能原因**:

1. perf 监测的事件不支持（某些虚拟化环境）
1. 监测时间太短，没有足够的采样数据
1. 进程绑定问题

**解决方案**:

1. 运行测试脚本验证: `python bench/cache_profiler.py`
1. 尝试增加 batch_size 以延长单个批次的执行时间
1. 检查是否在虚拟机中运行（虚拟机可能不支持硬件性能计数器）

### 技术细节

#### 监测原理

`CacheProfiler` 使用 `perf stat` 命令监测目标进程的硬件性能计数器：

```bash
perf stat -e cache-misses,cache-references,L1-dcache-loads,L1-dcache-load-misses,LLC-loads,LLC-load-misses,instructions,cycles -p <pid> -o <output_file>
```

#### 数据采集时机

- **启动**: 在 `algo.insert(batch_data, batch_ids)` 调用之前
- **停止**: 在插入操作完成后立即停止
- **粒度**: 每个 batch 一次测量

#### 数据存储流程

1. `CacheProfiler.stop()` → 返回 `CacheMissStats`
1. `BenchmarkRunner._execute_batch_insert()` → 收集每批次的统计数据
1. `BenchmarkMetrics.cache_miss_per_batch` → 存储到 metrics
1. `save_run_results()` → 导出到 CSV 文件
1. `export_results.py` → 合并到最终结果

## 📂 相关文件

- `bench/cache_profiler.py`: Cache profiling 核心实现
- `bench/metrics.py`: Metrics 数据结构定义
- `bench/runner.py`: Benchmark 运行器（集成 profiling）
- `bench/io_utils.py`: 结果导出工具
- `bench/algorithms/base.py`: 算法基类接口
- `bench/algorithms/registry.py`: 自动注册机制
- `export_results.py`: 最终结果导出脚本

## 🔗 参考资料

- [Linux perf 文档](https://perf.wiki.kernel.org/index.php/Main_Page)
- [WSL2 内核更新指南](https://docs.microsoft.com/en-us/windows/wsl/kernel-release-notes)
- [CPU Cache 性能分析](https://www.brendangregg.com/perf.html)
