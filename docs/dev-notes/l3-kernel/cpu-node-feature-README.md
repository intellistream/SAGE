# CPU版本SAGE节点支持

## 概述

本功能为SAGE框架添加完整的CPU-only计算节点支持，允许在无GPU环境中运行分布式任务。

## 功能特性

✅ **完整支持**: 通过JobManager将任务分配给CPU SAGE节点  
✅ **智能调度**: 资源感知的节点选择（CPU、内存需求）  
✅ **灵活策略**: 支持负载均衡、紧凑放置、分散放置等调度策略  
✅ **监控日志**: 完整的任务执行监控和日志记录能力  
✅ **易于使用**: 无需额外配置，开箱即用  

## 验收标准（Issue #573）

- [x] 可以通过JobManager将任务分配给CPU SAGE节点
- [x] 节点能够正常执行并返回结果
- [x] 任务执行过程中具备基本的监控和日志记录能力
- [x] 提供完整的文档和示例代码
- [x] 单元测试覆盖核心功能

## 快速开始

### 1. 启动JobManager

```bash
sage jobmanager start
```

### 2. 运行CPU任务示例

```bash
cd examples/tutorials/L3-kernel
python cpu_node_demo.py
```

### 3. 查看执行日志

```bash
ls -la .sage/logs/jobmanager/
tail -f .sage/logs/jobmanager/session_*/jobmanager.log
```

## 代码示例

### 基础CPU任务

```python
from sage.kernel.api.remote_environment import RemoteEnvironment
from sage.common.core.functions import MapFunction

class CPUProcessor(MapFunction):
    # 声明资源需求
    cpu_required = 2
    memory_required = "2GB"
    gpu_required = 0  # 不需要GPU

    def execute(self, data):
        # CPU计算逻辑
        return process_on_cpu(data)

# 创建环境并提交任务
env = RemoteEnvironment(name="cpu_task")
(env.from_source(MySource)
    .map(CPUProcessor, parallelism=4)
    .sink(MySink))

env.submit(autostop=True)
```

### 使用CPU专用调度器

```python
from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.node_selector import NodeSelector
from sage.kernel.scheduler.decision import PlacementDecision

class CPUOnlyScheduler(BaseScheduler):
    def __init__(self):
        super().__init__()
        self.node_selector = NodeSelector()

    def make_decision(self, task_node):
        cpu = getattr(task_node.transformation, "cpu_required", 1)

        # 选择CPU节点（gpu_required=0）
        target_node = self.node_selector.select_best_node(
            cpu_required=cpu,
            gpu_required=0,
            strategy="balanced",
        )

        return PlacementDecision(
            target_node=target_node,
            resource_requirements={"cpu": cpu, "gpu": 0},
            placement_strategy="cpu_only",
        )

# 使用自定义调度器
env = RemoteEnvironment(scheduler=CPUOnlyScheduler())
```

## 文件结构

```
SAGE/
├── examples/tutorials/L3-kernel/
│   └── cpu_node_demo.py              # CPU节点完整演示
├── docs/dev-notes/l3-kernel/
│   └── cpu-node-setup.md             # CPU节点设置指南
├── packages/sage-kernel/
│   ├── src/sage/kernel/
│   │   ├── runtime/
│   │   │   ├── job_manager.py        # 作业管理器
│   │   │   └── jobmanager_client.py  # 客户端接口
│   │   ├── scheduler/
│   │   │   ├── node_selector.py      # 节点选择器（核心）
│   │   │   └── impl/
│   │   │       └── resource_aware_scheduler.py
│   │   └── api/
│   │       └── remote_environment.py # 远程环境
│   └── tests/unit/kernel/scheduler/
│       └── test_cpu_node_selection.py # CPU节点单元测试
```

## 核心组件

### NodeSelector（节点选择器）

负责根据资源需求选择最优CPU节点：

- 监控集群资源状态（CPU、内存、GPU）
- 支持多种调度策略（balanced、pack、spread）
- 跟踪节点任务分配历史
- 提供集群统计信息

位置: `packages/sage-kernel/src/sage/kernel/scheduler/node_selector.py`

### JobManager（作业管理器）

管理任务生命周期和调度：

- 接收远程任务提交
- 协调调度器和执行器
- 提供监控和日志功能
- 支持任务启停控制

位置: `packages/sage-kernel/src/sage/kernel/runtime/job_manager.py`

### RemoteEnvironment（远程环境）

客户端接口，提交任务到JobManager：

- 序列化环境和任务
- 通过TCP连接JobManager
- 支持自动停止（autostop）
- 获取任务状态和指标

位置: `packages/sage-kernel/src/sage/kernel/api/remote_environment.py`

## 技术实现

### 资源需求规范

在Operator级别声明资源需求：

```python
class CPUComputeProcessor(MapFunction):
    cpu_required = 2        # CPU核心数
    memory_required = "2GB" # 内存需求
    gpu_required = 0        # 不需要GPU
```

### 节点选择流程

1. **提取需求**: Scheduler从Operator提取资源需求
2. **过滤节点**: NodeSelector过滤满足条件的节点
3. **排序选择**: 根据策略（balanced/pack/spread）排序
4. **返回决策**: 生成PlacementDecision返回给Dispatcher

### 调度策略

- **Balanced（负载均衡）**: 选择使用率最低的节点
- **Pack（紧凑放置）**: 优先填满使用率高的节点（节能）
- **Spread（分散放置）**: 均匀分散到所有节点

## 测试

### 运行单元测试

```bash
# 所有调度器测试
pytest packages/sage-kernel/tests/unit/kernel/scheduler/ -v

# CPU节点测试
pytest packages/sage-kernel/tests/unit/kernel/scheduler/test_cpu_node_selection.py -v

# 完整测试套件
sage-dev project test --quick
```

### 运行示例

```bash
# 基础示例
python examples/tutorials/L3-kernel/cpu_node_demo.py

# 远程环境示例
python examples/tutorials/L2-platform/environment/remote_env.py

# 批处理示例
python examples/tutorials/L3-kernel/batch/hello_remote_batch.py
```

## 监控和调试

### 查看集群状态

```python
from sage.kernel.scheduler.node_selector import NodeSelector

selector = NodeSelector()
stats = selector.get_cluster_stats()

print(f"节点数量: {stats['node_count']}")
print(f"总CPU: {stats['total_cpu']}")
print(f"可用CPU: {stats['available_cpu']}")
print(f"CPU使用率: {stats['avg_cpu_usage']:.1%}")
```

### 日志位置

```
.sage/logs/jobmanager/
├── session_YYYYMMDD_HHMMSS/
│   ├── jobmanager.log          # JobManager主日志
│   ├── error.log                # 错误日志
│   └── env_<name>_<session>/    # 环境日志
│       ├── Environment.log
│       └── Error.log
```

### 实时日志监控

```bash
# JobManager日志
tail -f .sage/logs/jobmanager/session_*/jobmanager.log

# 环境日志
tail -f .sage/logs/jobmanager/session_*/env_*/Environment.log
```

## 配置Ray集群

### 单机模式（默认）

JobManager自动初始化单机Ray环境，无需手动配置。

### 多节点模式

```bash
# 头节点
ray start --head --port=6379

# CPU工作节点
ray start \
  --address=<head_node_ip>:6379 \
  --num-cpus=8 \
  --num-gpus=0 \
  --memory=16000000000
```

## 性能优化

### 并行度配置

```python
import os
cpu_count = os.cpu_count()

# 根据CPU核心数调整并行度
env.from_source(MySource).map(
    CPUProcessor,
    parallelism=cpu_count  # 充分利用CPU
).sink(MySink)
```

### 批处理

```python
class BatchProcessor(MapFunction):
    def __init__(self, batch_size=100, **kwargs):
        super().__init__(**kwargs)
        self.batch_size = batch_size
        self.batch = []

    def execute(self, data):
        self.batch.append(data)
        if len(self.batch) >= self.batch_size:
            results = process_batch(self.batch)
            self.batch = []
            return results
        return None
```

## 相关资源

- **文档**: `docs/dev-notes/l3-kernel/cpu-node-setup.md`
- **示例**: `examples/tutorials/L3-kernel/cpu_node_demo.py`
- **测试**: `packages/sage-kernel/tests/unit/kernel/scheduler/test_cpu_node_selection.py`
- **Issue**: [#573](https://github.com/intellistream/SAGE/issues/573)

## 贡献者

- 开发: SAGE Development Assistant
- 审查: IntelliStream Team
- 分支: `copilot/add-cpu-version-sage-node`

## 许可证

遵循SAGE项目许可证（LICENSE文件）
