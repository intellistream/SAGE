# 分布式 Pipeline

> **目标**：学习如何构建可扩展的分布式流式处理应用

## 概述

SAGE 基于 Ray 构建分布式执行能力，支持在多节点集群上运行大规模流式处理任务。

## 示例上手三件套

| 项           | 内容                                                                                                                                                             |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **源码入口** | `examples/tutorials/L3-kernel/advanced/parallelism_remote_validation.py`                                                                                         |
| **运行命令** | `python examples/tutorials/L3-kernel/advanced/parallelism_remote_validation.py`                                                                                  |
| **预期日志** | 终端会打印 `REMOTE ENVIRONMENT - SINGLE STREAM PARALLELISM VALIDATION`、多条 `⚙️  DistProcessor[...]`/`✅ Filter[...]`/`🎯 SINK[...]`，并输出 Ray 节点并行度统计 |

脚本默认会连接当前 JobManager 已配置的 Ray 集群；执行前建议运行 `sage-dev quality --check-only` 和必要的 `sage cluster status`
检查，以便排除环境问题。

## 分布式环境配置

### 启动 Ray 集群

```bash
# 启动 Head 节点
sage cluster start --head

# 在其他机器上启动 Worker 节点
sage cluster start --worker --head-address=<head-node-ip>:10001
```

### 配置分布式环境

```python
from sage.kernel.api.remote_environment import RemoteEnvironment

# 创建远程分布式执行环境
env = RemoteEnvironment(
    name="distributed_app",
    host="127.0.0.1",      # JobManager 服务地址
    port=19001,              # JobManager 服务端口
    config={
        "ray": {
            "address": "ray://localhost:10001",  # Ray 集群地址
            "num_cpus": 16,
            "num_gpus": 4,
        }
    },
)
```

> **注意**：分布式执行需要使用 `RemoteEnvironment`，它会将作业提交到远程的 JobManager 服务。

## 并行处理

### 设置并行度

```python
# 摘自 examples/tutorials/L3-kernel/advanced/parallelism_remote_validation.py
class DistributedProcessor(BaseFunction):
    def __init__(self, processor_name="DistProcessor"):
        super().__init__()
        self.processor_name = processor_name
        self.instance_id = id(self)

    def execute(self, data):
        result = f"{self.processor_name}[{self.instance_id}]: {data}"
        print(f"⚙️  {result}")
        return result


class DistributedFilter(BaseFunction):
    def execute(self, data):
        passes = isinstance(data, int) and data % 3 == 0
        print(f"{'✅' if passes else '❌'} Filter: {data}")
        return passes


(
    env.from_collection(NumberListSource, list(range(1, 31)))
    .map(DistributedProcessor, "DistMapper", parallelism=4)
    .filter(DistributedFilter, parallelism=3)
    .sink(DistributedSink, parallelism=2)
)

env.submit(autostop=True)
```

> `NumberListSource` 与 `DistributedSink` 等配套类同样位于该示例脚本中，可直接运行脚本或复制到自定义工程中复用。

### 资源分配

> **⚠️ 功能开发中**：当前版本的 `map()` 方法仅支持 `parallelism` 参数。
>
> 细粒度的资源分配功能（如 `num_cpus`、`memory`、`num_gpus`）正在开发中。
>
> 相关 Issue: [#TODO: 添加算子级别的资源配置支持](https://github.com/intellistream/SAGE/issues/)

当前可用的并行度配置：

```python
# 当前支持：设置并行度
stream = (
    env.from_source(source)
    .map(HeavyComputeOperator(), parallelism=4)   # 4 个并行实例
    .map(GPUInferenceOperator(), parallelism=2)   # 2 个并行实例
    .sink(sink)
)
```

**未来计划支持的资源配置**（开发中）：

```python
# 计划支持：细粒度资源分配
stream = (
    env.from_source(source)
    .map(
        HeavyComputeOperator(),
        parallelism=4,
        resources={
            "num_cpus": 4,      # 每个实例 4 核
            "memory": "8GB"      # 每个实例 8GB 内存
        }
    )
    .map(
        GPUInferenceOperator(),
        parallelism=2,
        resources={
            "num_gpus": 1       # 每个实例 1 个 GPU
        }
    )
    .sink(sink)
)
```

## 分布式 RAG Pipeline

### 并行 Embedding

示例脚本中也包含 RAG 相关算子占位，可根据自身环境替换为 `examples/tutorials/L3-libs/rag/*.py` 中的 VDB/Chroma 操作，并沿用相同的
RemoteEnvironment 配置。

### 并行检索和生成

```python
from sage.middleware.operators.rag import ChromaRetrieverOperator, OpenAIGeneratorOperator

# 高并发查询处理
stream = (
    env.from_source(QuerySource())
    .map(
        ChromaRetrieverOperator(collection="docs", top_k=5),
        parallelism=4  # 4 个并行检索实例
    )
    .map(
        OpenAIGeneratorOperator(model="gpt-4"),
        parallelism=8  # 8 个并行生成实例
    )
    .sink(ResponseSink())
)

env.execute()
```

## 数据分区策略

### Key-Based 分区

```python
# 按 key 分区，确保相同 key 的数据到同一个实例
stream = (
    env.from_source(source)
    .key_by(lambda record: record["user_id"])  # 按用户 ID 分区
    .map(UserSessionOperator(), parallelism=4)
    .sink(sink)
)
```

### 自定义分区

```python
from sage.kernel.api.partitioner import Partitioner

class CustomPartitioner(Partitioner):
    def partition(self, record, num_partitions):
        # 自定义分区逻辑
        hash_value = hash(record["key"])
        return hash_value % num_partitions

stream = (
    env.from_source(source)
    .partition_custom(CustomPartitioner(), parallelism=4)
    .map(operator)
    .sink(sink)
)
```

## 监控和调试

### 查看集群状态

```bash
# 查看 Ray 集群状态
sage cluster status

# 查看作业状态
sage job list
sage job status <job-id>
```

### 资源使用监控

```python
# 在代码中获取资源使用情况
from sage.kernel.api.runtime import RuntimeContext

class MonitoredOperator(MapFunction):
    def open(self, context: RuntimeContext):
        self.metrics = context.get_metrics()

    def map(self, record):
        # 记录处理时间
        start = time.time()
        result = self.process(record)
        duration = time.time() - start

        self.metrics.record("processing_time", duration)
        return result
```

## 最佳实践

### ✅ 推荐做法

- **合理设置并行度** - 根据数据量和资源情况设置，避免过度并行
- **资源预估** - 提前评估每个算子的资源需求
- **数据分区** - 使用 key_by 保证有状态操作的正确性
- **监控指标** - 持续监控资源使用和处理延迟

### ❌ 避免的问题

- 并行度设置过高导致调度开销增加
- 未考虑数据倾斜导致部分节点过载
- GPU 资源分配不均导致利用率低
- 忽略网络传输开销

## 故障排查

### 常见问题

**问题 1：任务启动慢**

- 检查 Ray 集群连接状态
- 确认资源配置是否合理
- 查看是否有资源争用

**问题 2：部分节点空闲**

- 检查数据分区是否均衡
- 调整并行度配置
- 使用 key-based 分区避免数据倾斜

**问题 3：内存溢出**

- 减少单个算子实例的并行度
- 增加每个实例的内存配置
- 优化算子的内存使用（见[性能调优](performance-tuning.md)）

## 相关阅读

- [Kernel 用户指南](../../guides/packages/sage-kernel/README.md) - 执行引擎详解
- [性能调优](performance-tuning.md) - 优化分布式性能
- [容错与可靠性](fault-tolerance.md) - 分布式容错机制

______________________________________________________________________

**下一步**：学习 [自定义算子](custom-operators.md) 封装业务逻辑
