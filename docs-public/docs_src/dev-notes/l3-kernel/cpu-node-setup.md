# CPU版本SAGE节点设置指南

## 概述

SAGE框架完全支持CPU-only计算节点，允许您在没有GPU的环境中运行分布式任务。本文档详细说明如何配置、启动和使用CPU版本的SAGE节点。

## 核心组件

CPU节点支持依赖以下核心组件（无需额外安装）：

- **JobManager**: 作业管理器，负责任务调度和生命周期管理
- **NodeSelector**: 节点选择器，根据资源需求选择最优CPU节点
- **RemoteEnvironment**: 远程环境，将任务提交到JobManager
- **Resource-Aware Scheduler**: 资源感知调度器，支持CPU/GPU/内存需求规范

## 快速开始

### 1. 启动JobManager

JobManager是SAGE分布式任务执行的核心服务：

```bash
# 方式1: 使用CLI命令（推荐）
sage jobmanager start

# 方式2: 手动启动
python -m sage.kernel.runtime.job_manager --host 127.0.0.1 --port 19001

# 检查状态
sage jobmanager status
```

**输出示例**:

```
🚀 Starting SAGE JobManager...
✅ JobManager service started successfully
📍 Listening on 127.0.0.1:19001
```

### 2. 配置Ray集群（可选）

JobManager会自动初始化单机Ray环境。如果需要多节点部署：

```bash
# 在主节点（Head Node）
ray start --head --port=6379

# 在CPU工作节点（Worker Node）
ray start \
  --address=<head_node_ip>:6379 \
  --num-cpus=8 \
  --num-gpus=0 \
  --memory=16000000000  # 16GB in bytes
```

**重要参数说明**:

- `--num-cpus`: CPU核心数
- `--num-gpus`: GPU数量（CPU节点设为0）
- `--memory`: 可用内存（字节）
- `--address`: 头节点地址

### 3. 提交CPU任务

创建并运行CPU任务示例：

```python
from sage.kernel.api.remote_environment import RemoteEnvironment
from sage.common.core.functions import SourceFunction, MapFunction, SinkFunction

# 创建远程环境
env = RemoteEnvironment(name="cpu_task_demo")

# 构建数据流（自动选择CPU节点）
(env.from_source(MySource)
    .map(MyCPUProcessor, parallelism=4)
    .sink(MySink))

# 提交任务（autostop=True 表示任务完成后自动清理）
env.submit(autostop=True)
```

## 资源需求规范

### Operator级别资源声明

在CPU Operator中明确声明资源需求：

```python
class CPUComputeProcessor(MapFunction):
    """CPU密集型处理器"""

    # 资源需求声明（由调度器使用）
    cpu_required = 2        # 需要2个CPU核心
    memory_required = "2GB" # 需要2GB内存
    gpu_required = 0        # 明确不需要GPU

    def execute(self, data):
        # CPU密集型计算
        result = heavy_cpu_computation(data)
        return result
```

### 调度器自动识别

Resource-Aware Scheduler会自动：

1. 读取Operator的资源需求
1. 通过NodeSelector选择满足条件的CPU节点
1. 将任务分配到选定节点

## 自定义CPU调度策略

### 创建CPU专用调度器

```python
from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.decision import PlacementDecision
from sage.kernel.scheduler.node_selector import NodeSelector

class CPUOnlyScheduler(BaseScheduler):
    """CPU专用调度器 - 确保只选择CPU节点"""

    def __init__(self):
        super().__init__()
        self.node_selector = NodeSelector()

    def make_decision(self, task_node):
        # 提取CPU资源需求
        cpu = getattr(task_node.transformation, "cpu_required", 1)
        memory = getattr(task_node.transformation, "memory_required", "1GB")

        # 选择CPU节点（明确指定 gpu_required=0）
        target_node = self.node_selector.select_best_node(
            cpu_required=cpu,
            gpu_required=0,  # 不需要GPU
            strategy="balanced",  # 负载均衡
        )

        decision = PlacementDecision(
            target_node=target_node,
            resource_requirements={
                "cpu": cpu,
                "memory": memory,
                "gpu": 0,
            },
            placement_strategy="cpu_only",
        )

        return decision
```

### 使用自定义调度器

```python
# 创建使用CPU调度器的环境
cpu_scheduler = CPUOnlyScheduler()
env = RemoteEnvironment(
    name="cpu_scheduled_task",
    scheduler=cpu_scheduler,
)

# 构建和提交任务
(env.from_source(MySource)
    .map(MyCPUProcessor, parallelism=4)
    .sink(MySink))

env.submit(autostop=True)

# 查看调度统计
metrics = cpu_scheduler.get_metrics()
print(f"调度任务数: {metrics['scheduled_count']}")
```

## 节点选择策略

NodeSelector支持多种CPU节点选择策略：

### 1. 负载均衡（Balanced）

选择CPU使用率最低的节点：

```python
node_id = node_selector.select_best_node(
    cpu_required=2,
    gpu_required=0,
    strategy="balanced",  # 默认策略
)
```

### 2. 紧凑放置（Pack）

优先填满使用率高的节点（节能模式）：

```python
node_id = node_selector.select_best_node(
    cpu_required=2,
    gpu_required=0,
    strategy="pack",
)
```

### 3. 分散放置（Spread）

将任务均匀分散到所有节点：

```python
node_id = node_selector.select_best_node(
    cpu_required=2,
    gpu_required=0,
    strategy="spread",
)
```

## 集群监控和检查

### 获取集群资源统计

```python
from sage.kernel.scheduler.node_selector import NodeSelector

selector = NodeSelector()
stats = selector.get_cluster_stats()

print(f"节点数量: {stats['node_count']}")
print(f"总CPU核心: {stats['total_cpu']}")
print(f"可用CPU: {stats['available_cpu']}")
print(f"CPU使用率: {stats['avg_cpu_usage']:.1%}")
print(f"总内存: {stats['total_memory'] / (1024**3):.2f} GB")
```

### 查看单个节点信息

```python
# 获取所有节点
nodes = selector.get_all_nodes()

for node in nodes:
    print(f"节点: {node.hostname}")
    print(f"  CPU: {node.available_cpu}/{node.total_cpu}")
    print(f"  内存: {node.available_memory / (1024**3):.2f} GB")
    print(f"  任务数: {node.task_count}")
```

### 监控JobManager

```python
# 检查JobManager健康状态
env = RemoteEnvironment()
health = env.health_check()
print(health)  # {'status': 'healthy', 'timestamp': '...', 'jobs_count': 0}

# 获取作业状态
status = env.get_job_status()
print(status)
```

## 日志和调试

### 日志位置

所有任务执行日志保存在：

```
.sage/logs/jobmanager/
├── session_YYYYMMDD_HHMMSS/
│   ├── jobmanager.log          # JobManager主日志
│   ├── error.log                # 错误日志
│   └── env_<name>_<session>/    # 环境专用日志
│       ├── Environment.log      # 环境执行日志
│       └── Error.log            # 环境错误日志
```

### 查看实时日志

```bash
# JobManager日志
tail -f .sage/logs/jobmanager/session_*/jobmanager.log

# 环境日志
tail -f .sage/logs/jobmanager/session_*/env_*/Environment.log

# 错误日志
tail -f .sage/logs/jobmanager/session_*/error.log
```

### 调试模式

在RemoteEnvironment中设置日志级别：

```python
env = RemoteEnvironment(
    name="debug_task",
    config={"log_level": "DEBUG"}
)
```

## 性能优化

### CPU任务并行度配置

```python
# 根据可用CPU核心数调整并行度
import os
cpu_count = os.cpu_count()

(env.from_source(MySource)
    .map(MyCPUProcessor, parallelism=cpu_count)  # 充分利用CPU
    .sink(MySink))
```

### 批处理优化

```python
class BatchCPUProcessor(MapFunction):
    """批处理CPU任务以减少开销"""

    def __init__(self, batch_size=100, **kwargs):
        super().__init__(**kwargs)
        self.batch_size = batch_size
        self.batch = []

    def execute(self, data):
        self.batch.append(data)

        if len(self.batch) >= self.batch_size:
            # 批量处理
            results = process_batch(self.batch)
            self.batch = []
            return results

        return None  # 等待更多数据
```

## 常见问题

### Q1: CPU节点如何与GPU节点共存？

A: NodeSelector会根据`gpu_required`参数自动区分：

- `gpu_required=0`: 选择CPU节点
- `gpu_required>0`: 选择GPU节点

```python
# CPU任务
cpu_node = selector.select_best_node(cpu_required=4, gpu_required=0)

# GPU任务
gpu_node = selector.select_best_node(cpu_required=2, gpu_required=1)
```

### Q2: 如何确保任务只在CPU节点执行？

A: 有两种方式：

1. **使用CPU专用调度器**（推荐）：

```python
env = RemoteEnvironment(scheduler=CPUOnlyScheduler())
```

2. **在Operator中声明**：

```python
class MyCPUOperator(MapFunction):
    gpu_required = 0  # 明确不需要GPU
```

### Q3: 多个CPU节点如何负载均衡？

A: NodeSelector的`balanced`策略会自动选择负载最低的节点：

```python
node_selector = NodeSelector()
for task in tasks:
    node = node_selector.select_best_node(
        cpu_required=2,
        strategy="balanced",  # 负载均衡
    )
```

### Q4: 如何监控CPU节点性能？

A: 使用NodeSelector获取实时统计：

```python
stats = node_selector.get_cluster_stats()
for node in stats['nodes']:
    print(f"{node['hostname']}: CPU={node['cpu_usage']:.1%}")
```

## 完整示例

参考示例代码：

```bash
# 基础CPU节点示例
examples/tutorials/L3-kernel/cpu_node_demo.py

# 远程环境示例
examples/tutorials/L2-platform/environment/remote_env.py

# 批处理示例
examples/tutorials/L3-kernel/batch/hello_remote_batch.py
```

运行示例：

```bash
# 1. 启动JobManager
sage jobmanager start

# 2. 运行CPU节点演示
cd examples/tutorials/L3-kernel
python cpu_node_demo.py

# 3. 查看日志
ls -la ~/.sage/logs/jobmanager/
```

## 架构参考

CPU节点支持的关键文件：

```
packages/sage-kernel/src/sage/kernel/
├── runtime/
│   ├── job_manager.py          # 作业管理器
│   └── jobmanager_client.py    # 客户端接口
├── scheduler/
│   ├── node_selector.py        # 节点选择器
│   └── impl/
│       └── resource_aware_scheduler.py  # 资源感知调度
└── api/
    └── remote_environment.py   # 远程环境
```

## 总结

SAGE框架对CPU节点的支持特点：

✅ **开箱即用**: 无需额外配置，默认支持CPU节点\
✅ **资源感知**: 自动根据CPU/内存需求选择节点\
✅ **灵活调度**: 支持多种调度策略（负载均衡、紧凑放置等）\
✅ **完整监控**: 提供任务执行日志和集群资源统计\
✅ **易于扩展**: 支持自定义调度器和节点选择策略\
✅ **无缝集成**: 与GPU节点共存，自动区分

如有问题，请查看：

- 示例代码: `examples/tutorials/L3-kernel/cpu_node_demo.py`
- API文档: `docs/dev-notes/l3-kernel/`
- Issue跟踪: GitHub Issue #573
