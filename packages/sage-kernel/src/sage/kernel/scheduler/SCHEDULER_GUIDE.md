# Scheduler Module - 调度器完整文档

本文档是 SAGE 调度器模块的完整参考指南，涵盖架构设计、使用方法、资源感知调度和服务调度。

______________________________________________________________________

## 目录

1. [设计原则与架构](#1-%E8%AE%BE%E8%AE%A1%E5%8E%9F%E5%88%99%E4%B8%8E%E6%9E%B6%E6%9E%84)
1. [快速开始](#2-%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B)
1. [调度器类型](#3-%E8%B0%83%E5%BA%A6%E5%99%A8%E7%B1%BB%E5%9E%8B)
1. [资源感知调度](#4-%E8%B5%84%E6%BA%90%E6%84%9F%E7%9F%A5%E8%B0%83%E5%BA%A6)
1. [服务调度](#5-%E6%9C%8D%E5%8A%A1%E8%B0%83%E5%BA%A6)
1. [API 参考](#6-api-%E5%8F%82%E8%80%83)
1. [开发指南](#7-%E5%BC%80%E5%8F%91%E6%8C%87%E5%8D%97)

______________________________________________________________________

## 1. 设计原则与架构

### 1.1 核心设计原则

#### 用户无感知

用户只需在创建 Environment 时指定调度策略，无需关心调度细节。

#### 并行度是 operator 级别的

每个 transformation 可以指定自己的并行度（parallelism）。

#### 调度策略是应用级别的

在 Environment 初始化时配置，影响整个 application 的调度行为。

### 1.2 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        Dispatcher                            │
│                      (协调者/中介者)                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 接收任务图 (TaskGraph)                                   │
│  2. 调用 Scheduler 获取调度决策                               │
│  3. 将决策交给 PlacementExecutor 执行物理放置                 │
│  4. 管理任务生命周期                                          │
│                                                              │
└───────────┬─────────────────────────────┬───────────────────┘
            │                             │
            ▼                             ▼
    ┌──────────────┐            ┌──────────────────┐
    │   Scheduler  │            │ PlacementExecutor│
    │  (决策者)     │            │   (执行者)        │
    ├──────────────┤            ├──────────────────┤
    │              │            │                  │
    │ 分析任务需求 │            │ 根据决策执行     │
    │ 评估系统状态 │            │ 创建 Ray Actor   │
    │ 选择最优节点 │            │ 配置资源         │
    │              │            │ 指定节点         │
    │ 返回决策     │            │                  │
    │ PlacementDecision        │ 返回 Task        │
    └──────────────┘            └──────────────────┘
            │
            ▼
    ┌──────────────┐
    │ NodeSelector │
    │ (资源监控)    │
    ├──────────────┤
    │              │
    │ 监控集群资源 │
    │ 选择最优节点 │
    │ 跟踪任务分配 │
    │              │
    └──────────────┘
```

### 1.3 职责分离

| 组件                  | 职责                   | 输入                 | 输出              |
| --------------------- | ---------------------- | -------------------- | ----------------- |
| **Dispatcher**        | 协调调度和执行         | TaskGraph            | 运行中的任务      |
| **Scheduler**         | 制定调度决策（决策者） | TaskNode/ServiceNode | PlacementDecision |
| **NodeSelector**      | 资源监控和节点选择     | 资源需求             | 最优节点 ID       |
| **PlacementExecutor** | 执行物理放置（执行者） | PlacementDecision    | Ray Actor         |

### 1.4 完整流程

```python
# Dispatcher.submit():
for task_node in graph.nodes:
    # 1. Scheduler 制定决策
    decision = scheduler.make_decision(task_node)
    # → decision.target_node = "worker-node-2"
    # → decision.resource_requirements = {"cpu": 4, "gpu": 1}

    # 2. 根据决策等待（如果需要）
    if decision.delay > 0:
        time.sleep(decision.delay)

    # 3. PlacementExecutor 执行放置
    task = placement_executor.place_task(task_node, decision)

    # 4. 启动任务
    task.start_running()
```

______________________________________________________________________

## 2. 快速开始

### 2.1 基础用法

```python
from sage.kernel import LocalEnvironment

# 使用默认调度器（FIFO）
env = LocalEnvironment()

# 或指定调度器类型
env = LocalEnvironment(scheduler="fifo")  # FIFO 策略
env = LocalEnvironment(scheduler="load_aware")  # 负载感知策略

# 构建 pipeline（operator 级别的并行度）
(
    env.from_source(MySource)
    .map(MyOperator, parallelism=4)  # 这个 operator 有 4 个并行实例
    .filter(MyFilter, parallelism=2)  # 这个 operator 有 2 个并行实例
    .sink(MySink)
)

# 提交执行（调度器自动工作）
env.submit()
```

### 2.2 指定资源需求

```python
# 在 Operator 类中定义资源需求
class GPUOperator:
    cpu_required = 4  # 需要 4 个 CPU 核心
    gpu_required = 1  # 需要 1 个 GPU
    memory_required = "8GB"  # 需要 8GB 内存

    def process(self, data):
        # GPU 计算
        return data


# 使用负载感知调度器
from sage.kernel.scheduler.impl import LoadAwareScheduler

scheduler = LoadAwareScheduler(
    max_concurrent=10, strategy="balanced"  # balanced, pack, 或 spread
)

env = LocalEnvironment(name="gpu_demo", platform="remote", scheduler=scheduler)

# 调度器会自动：
# 1. 提取资源需求：cpu=4, gpu=1, memory=8GB
# 2. 选择有 GPU 且负载最低的节点
# 3. 将任务放置到该节点
env.from_source(source).map(GPUOperator, parallelism=2).sink(sink)
env.submit()
```

______________________________________________________________________

## 3. 调度器类型

### 3.1 FIFOScheduler - 基准调度器

**特点**：

- 最简单的调度策略
- 按任务到达顺序调度
- 不考虑负载和资源
- 使用 Ray 默认负载均衡

**适用场景**：

- 资源充足
- 负载均匀
- 作为性能对比的 baseline

**使用方式**：

```python
# 方式 1: 字符串指定
env = LocalEnvironment(scheduler="fifo")

# 方式 2: 实例化指定
from sage.kernel.scheduler.impl import FIFOScheduler

env = LocalEnvironment(scheduler=FIFOScheduler())
```

**性能指标**：

```python
metrics = scheduler.get_metrics()
# {
#     "scheduler_type": "FIFO",
#     "total_scheduled": 100,
#     "avg_latency_ms": 2.5,
#     "decisions": 100
# }
```

### 3.2 LoadAwareScheduler - 负载感知调度器

**特点**：

- 监控集群资源状态（CPU、GPU、内存）
- 根据任务需求选择最优节点
- 支持多种调度策略（balanced/pack/spread）
- 跟踪任务分配历史

**适用场景**：

- 资源受限
- 负载波动
- 需要资源感知调度
- 多租户环境

**使用方式**：

```python
from sage.kernel.scheduler.impl import LoadAwareScheduler

# 创建负载感知调度器
scheduler = LoadAwareScheduler(
    max_concurrent=10, strategy="balanced"  # 最大并发任务数  # 调度策略
)

env = LocalEnvironment(scheduler=scheduler)
```

**性能指标**：

```python
metrics = scheduler.get_metrics()
# {
#     "scheduler_type": "LoadAware",
#     "total_scheduled": 100,
#     "avg_latency_ms": 5.8,
#     "active_tasks": 8,
#     "max_concurrent": 10,
#     "avg_resource_utilization": 0.75,
#     "cluster": {
#         "node_count": 5,
#         "total_cpu": 80,
#         "available_cpu": 32,
#         "avg_cpu_usage": 0.60,
#         "nodes": [...]
#     }
# }
```

______________________________________________________________________

## 4. 资源感知调度

### 4.1 核心组件

#### NodeSelector - 资源感知核心

**功能**：

1. **实时监控集群资源**

   - CPU、GPU、内存使用情况
   - 每个节点的负载状态
   - 自定义资源

1. **智能节点选择**

   - 根据任务需求匹配节点
   - 支持多种调度策略
   - 考虑资源可用性和负载

1. **任务分配跟踪**

   - 记录任务分配到哪个节点
   - 跟踪每个节点的任务数
   - 用于负载均衡决策

**核心方法**：

```python
class NodeSelector:
    def select_best_node(
        self,
        cpu_required: float = 0,
        gpu_required: float = 0,
        memory_required: int = 0,
        custom_resources: Optional[Dict] = None,
        strategy: str = "balanced",
    ) -> Optional[str]:
        """根据资源需求和策略选择最优节点"""
        # 1. 获取所有节点资源信息
        # 2. 过滤满足资源需求的节点
        # 3. 根据策略计算得分
        # 4. 返回最优节点 ID
```

### 4.2 调度策略

#### Balanced - 负载均衡（推荐）

**特点**：

- 选择综合使用率最低的节点
- 考虑 CPU、GPU、内存使用率
- 适合大多数场景

**评分公式**：

```python
score = cpu_usage * 0.4 + gpu_usage * 0.4 + memory_usage * 0.2
# 使用率越低，得分越低，越优先
```

**示例**：

```python
scheduler = LoadAwareScheduler(strategy="balanced")
```

#### Pack - 紧凑放置

**特点**：

- 选择使用率最高但能容纳任务的节点
- 尽量填满现有节点
- 节省资源，适合弹性集群

**评分公式**：

```python
score = -(cpu_usage * 0.4 + gpu_usage * 0.4 + memory_usage * 0.2)
# 使用率越高，得分越低（负数），越优先
```

**适用场景**：

- 弹性集群（可以释放空闲节点）
- 需要最大化资源利用率
- 成本敏感的场景

**示例**：

```python
scheduler = LoadAwareScheduler(strategy="pack")
```

#### Spread - 分散放置

**特点**：

- 选择任务数最少的节点
- 任务均匀分布
- 适合需要隔离的场景

**评分公式**：

```python
score = task_count
# 任务数越少，得分越低，越优先
```

**适用场景**：

- 需要任务隔离
- 避免单点故障
- 服务调度（高可用）

**示例**：

```python
scheduler = LoadAwareScheduler(strategy="spread")
```

### 4.3 资源需求定义

在 Operator 类中定义资源需求：

```python
class MyOperator:
    # 资源需求定义
    cpu_required = 4  # 需要 4 个 CPU 核心
    gpu_required = 1  # 需要 1 个 GPU
    memory_required = "8GB"  # 需要 8GB 内存
    custom_resources = {"special_hardware": 1}  # 自定义资源

    def process(self, data):
        # 处理逻辑
        return data
```

调度器会自动提取这些信息：

```python
# LoadAwareScheduler.make_decision() 自动提取：
cpu_required = task_node.transformation.cpu_required  # → 4
gpu_required = task_node.transformation.gpu_required  # → 1
memory_required = parse_memory(
    task_node.transformation.memory_required  # → 8589934592 bytes
)
```

### 4.4 完整示例

```python
from sage.kernel import LocalEnvironment
from sage.kernel.scheduler.impl import LoadAwareScheduler


# 定义需要 GPU 的任务
class GPUTask:
    cpu_required = 4
    gpu_required = 1
    memory_required = "8GB"

    def process(self, data):
        # GPU 计算
        return data


# 创建负载均衡调度器
scheduler = LoadAwareScheduler(max_concurrent=10, strategy="balanced")

# 创建 Environment
env = LocalEnvironment(name="gpu_demo", platform="remote", scheduler=scheduler)

# 构建 Pipeline
# 调度器会：
# 1. 提取资源需求：cpu=4, gpu=1, memory=8GB
# 2. 查找有 GPU 且负载最低的节点
# 3. 返回决策：target_node="worker-node-2"
# 4. PlacementExecutor 将任务放置到 worker-node-2
env.from_source(source).map(GPUTask, parallelism=4).sink(sink)

env.submit()
```

### 4.5 监控和调试

#### 获取调度指标

```python
# 获取调度器指标
metrics = scheduler.get_metrics()

print(f"总调度任务数: {metrics['total_scheduled']}")
print(f"活跃任务数: {metrics['active_tasks']}")
print(f"平均延迟: {metrics['avg_latency_ms']}ms")

# 获取集群资源统计
cluster = metrics["cluster"]
print(f"节点数: {cluster['node_count']}")
print(f"总 CPU: {cluster['total_cpu']}")
print(f"可用 CPU: {cluster['available_cpu']}")
print(f"平均 CPU 使用率: {cluster['avg_cpu_usage']:.1%}")

# 每个节点的详细信息
for node in cluster["nodes"]:
    print(
        f"  {node['hostname']}: CPU={node['cpu_usage']:.1%}, "
        f"GPU={node['gpu_usage']:.1%}, tasks={node['task_count']}"
    )
```

#### 查看决策历史

```python
# 查看所有调度决策
for i, decision in enumerate(scheduler.decision_history, 1):
    print(f"{i}. {decision}")

# 输出：
# 1. PlacementDecision(target_node=worker-node-2, resources={'cpu': 4, 'gpu': 1}, reason='...')
# 2. PlacementDecision(target_node=worker-node-1, resources={'cpu': 2}, reason='...')
```

______________________________________________________________________

## 5. 服务调度

### 5.1 服务 vs 任务

|              | 任务（Task）              | 服务（Service）           |
| ------------ | ------------------------- | ------------------------- |
| **运行时长** | 短期（处理完即退出）      | 长期（持续运行）          |
| **调度策略** | Balanced/Pack（负载均衡） | Spread（分散）            |
| **故障影响** | 单个任务失败影响小        | 服务失败影响大            |
| **资源需求** | 动态变化                  | 相对固定                  |
| **方法**     | `make_decision()`         | `make_service_decision()` |

### 5.2 API 定义

#### 基类默认实现

```python
# sage/kernel/scheduler/api.py
class BaseScheduler(ABC):
    def make_service_decision(self, service_node: "ServiceNode") -> "PlacementDecision":
        """
        制定服务调度决策

        默认实现：立即使用默认配置调度
        子类可以重写此方法提供自定义逻辑
        """
        from sage.kernel.scheduler.decision import PlacementDecision

        return PlacementDecision.immediate_default(
            reason=f"Service placement: {service_node.service_name}"
        )
```

#### FIFOScheduler 实现

```python
class FIFOScheduler(BaseScheduler):
    def make_service_decision(self, service_node: "ServiceNode") -> PlacementDecision:
        """FIFO 服务调度：按到达顺序立即调度"""
        self.scheduled_count += 1

        decision = PlacementDecision.immediate_default(
            reason=f"FIFO service: {service_node.service_name} (#{self.scheduled_count})"
        )

        self.decision_history.append(decision)
        return decision
```

#### LoadAwareScheduler 实现

```python
class LoadAwareScheduler(BaseScheduler):
    def make_service_decision(self, service_node: "ServiceNode") -> PlacementDecision:
        """
        负载感知的服务调度

        服务特殊处理：
        1. 提取服务的资源需求
        2. 选择资源充足且负载低的节点
        3. 优先使用 spread 策略避免单点故障
        """
        # 1. 提取资源需求
        cpu_required = getattr(service_node.service_class, "cpu_required", 1.0)
        gpu_required = getattr(service_node.service_class, "gpu_required", 0.0)
        memory_required = self._parse_memory(
            getattr(service_node.service_class, "memory_required", 0)
        )

        # 2. 使用 NodeSelector 选择节点（spread 策略）
        target_node = self.node_selector.select_best_node(
            cpu_required=cpu_required,
            gpu_required=gpu_required,
            memory_required=memory_required,
            strategy="spread",  # 服务使用 spread 策略
        )

        # 3. 跟踪服务分配
        if target_node:
            self.node_selector.track_task_placement(
                service_node.service_name, target_node
            )

        # 4. 返回决策
        return PlacementDecision(
            target_node=target_node,
            resource_requirements={
                "cpu": cpu_required,
                "gpu": gpu_required,
                "memory": memory_required,
            },
            placement_strategy="spread",
            reason=f"LoadAware Service: {service_node.service_name}",
        )
```

### 5.3 为什么服务使用 Spread 策略？

#### Spread 策略的优势

1. **高可用性**：服务分散到不同节点，避免单点故障

   ```
   Node 1: [ServiceA]
   Node 2: [ServiceB]
   Node 3: [ServiceC]
   ```

1. **负载均衡**：服务均匀分布，不会集中在某个节点

   ```
   ❌ 不好：Node 1: [ServiceA, ServiceB, ServiceC]
           Node 2: []
           Node 3: []

   ✅ 良好：Node 1: [ServiceA]
           Node 2: [ServiceB]
           Node 3: [ServiceC]
   ```

1. **资源隔离**：服务之间不会竞争同一节点的资源

### 5.4 使用示例

```python
from sage.kernel import LocalEnvironment
from sage.kernel.scheduler.impl import LoadAwareScheduler


# 定义一个缓存服务
class CacheService:
    cpu_required = 2
    memory_required = "4GB"

    def __init__(self):
        self.cache = {}

    def get(self, key):
        return self.cache.get(key)

    def set(self, key, value):
        self.cache[key] = value


# 创建负载感知调度器
scheduler = LoadAwareScheduler(strategy="balanced")

# 创建 Environment（服务会被自动注册和调度）
env = LocalEnvironment(name="cache_demo", platform="remote", scheduler=scheduler)

# 构建 Pipeline（Dispatcher 会调用 make_service_decision 调度服务）
env.from_source(source).map(operator).sink(sink)
env.submit()
```

______________________________________________________________________

## 6. API 参考

### 6.1 BaseScheduler

```python
class BaseScheduler(ABC):
    """调度器抽象基类"""

    @abstractmethod
    def make_decision(self, task_node: "TaskNode") -> "PlacementDecision":
        """制定任务调度决策"""
        pass

    def make_service_decision(self, service_node: "ServiceNode") -> "PlacementDecision":
        """制定服务调度决策（有默认实现）"""
        pass

    def get_metrics(self) -> Dict[str, Any]:
        """获取调度器性能指标"""
        pass

    def shutdown(self):
        """关闭调度器，释放资源"""
        pass
```

### 6.2 PlacementDecision

```python
@dataclass
class PlacementDecision:
    """调度决策数据类"""

    target_node: Optional[str] = None  # 目标节点 ID
    resource_requirements: Optional[Dict] = None  # 资源需求
    delay: float = 0.0  # 延迟时间（秒）
    immediate: bool = True  # 是否立即调度
    placement_strategy: Optional[str] = None  # 放置策略
    affinity: Optional[Dict] = None  # 亲和性配置
    reason: str = ""  # 决策原因

    @classmethod
    def immediate_default(cls, reason: str = "") -> "PlacementDecision":
        """创建立即调度到默认节点的决策"""
        return cls(immediate=True, reason=reason)

    @classmethod
    def with_resources(
        cls, cpu: float, gpu: float = 0, memory: int = 0, **kwargs
    ) -> "PlacementDecision":
        """创建带资源需求的决策"""
        return cls(
            resource_requirements={"cpu": cpu, "gpu": gpu, "memory": memory}, **kwargs
        )

    @classmethod
    def with_node(cls, node_id: str, **kwargs) -> "PlacementDecision":
        """创建指定节点的决策"""
        return cls(target_node=node_id, **kwargs)
```

### 6.3 NodeSelector

```python
class NodeSelector:
    """节点选择器 - 资源监控和节点选择"""

    def __init__(self, cache_ttl: float = 1.0, enable_tracking: bool = False):
        """初始化节点选择器"""
        pass

    def select_best_node(
        self,
        cpu_required: float = 0,
        gpu_required: float = 0,
        memory_required: int = 0,
        custom_resources: Optional[Dict] = None,
        strategy: str = "balanced",
    ) -> Optional[str]:
        """选择最优节点"""
        pass

    def get_all_nodes(self) -> List[NodeResources]:
        """获取所有节点信息"""
        pass

    def get_node(self, node_id: str) -> Optional[NodeResources]:
        """获取指定节点信息"""
        pass

    def track_task_placement(self, task_name: str, node_id: str):
        """跟踪任务分配"""
        pass

    def untrack_task(self, task_name: str):
        """取消任务跟踪"""
        pass

    def get_cluster_stats(self) -> Dict[str, Any]:
        """获取集群统计信息"""
        pass
```

### 6.4 FIFOScheduler

```python
class FIFOScheduler(BaseScheduler):
    """FIFO 调度器"""

    def __init__(self, platform: str = "local"):
        """初始化 FIFO 调度器"""
        pass

    def make_decision(self, task_node: "TaskNode") -> PlacementDecision:
        """FIFO 调度决策：立即使用默认配置调度"""
        pass

    def make_service_decision(self, service_node: "ServiceNode") -> PlacementDecision:
        """FIFO 服务调度决策"""
        pass
```

### 6.5 LoadAwareScheduler

```python
class LoadAwareScheduler(BaseScheduler):
    """负载感知调度器"""

    def __init__(
        self,
        max_concurrent: int = 100,
        platform: str = "local",
        strategy: str = "balanced",
    ):
        """
        初始化负载感知调度器

        Args:
            max_concurrent: 最大并发任务数
            platform: 平台类型 ('local' 或 'remote')
            strategy: 调度策略 ('balanced', 'pack', 'spread')
        """
        pass

    def make_decision(self, task_node: "TaskNode") -> PlacementDecision:
        """负载感知调度决策"""
        pass

    def make_service_decision(self, service_node: "ServiceNode") -> PlacementDecision:
        """负载感知服务调度决策"""
        pass

    def task_completed(self, task_name: str):
        """任务完成时调用，释放资源"""
        pass
```

______________________________________________________________________

## 7. 开发指南

### 7.1 创建自定义调度器

```python
from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.decision import PlacementDecision


class MyScheduler(BaseScheduler):
    """自定义调度器"""

    def __init__(self, **config):
        super().__init__()
        # 初始化配置
        self.config = config

    def make_decision(self, task_node: "TaskNode") -> PlacementDecision:
        """实现调度决策逻辑"""
        # 1. 分析任务需求
        parallelism = task_node.transformation.parallelism

        # 2. 评估系统状态
        # ...

        # 3. 制定决策
        decision = PlacementDecision(
            target_node="my-target-node",
            resource_requirements={"cpu": 2},
            reason="My custom logic",
        )

        # 4. 记录历史
        self.scheduled_count += 1
        self.decision_history.append(decision)

        return decision

    def get_metrics(self) -> Dict[str, Any]:
        """返回调度器指标"""
        return {
            "scheduler_type": "MyScheduler",
            "scheduled_count": self.scheduled_count,
            **self.config,
        }
```

### 7.2 使用自定义调度器

```python
from sage.kernel import LocalEnvironment

# 创建自定义调度器实例
my_scheduler = MyScheduler(param1="value1", param2="value2")

# 使用自定义调度器
env = LocalEnvironment(scheduler=my_scheduler)

# 构建和提交 pipeline
env.from_source(source).map(operator).sink(sink)
env.submit()
```

### 7.3 对比不同调度策略

```python
import time
from sage.kernel import LocalEnvironment
from sage.kernel.scheduler.impl import FIFOScheduler, LoadAwareScheduler


def benchmark_scheduler(scheduler, name):
    """测试调度器性能"""
    env = LocalEnvironment(scheduler=scheduler)

    # 构建相同的 pipeline
    env.from_source(source).map(operator, parallelism=10).sink(sink)

    # 计时
    start = time.time()
    env.submit()
    elapsed = time.time() - start

    # 获取指标
    metrics = scheduler.get_metrics()

    print(f"\n{name} 调度器:")
    print(f"  执行时间: {elapsed:.2f}s")
    print(f"  平均调度延迟: {metrics['avg_latency_ms']:.2f}ms")
    print(f"  总调度任务: {metrics['total_scheduled']}")


# 对比测试
benchmark_scheduler(FIFOScheduler(), "FIFO")
benchmark_scheduler(LoadAwareScheduler(strategy="balanced"), "LoadAware (Balanced)")
benchmark_scheduler(LoadAwareScheduler(strategy="pack"), "LoadAware (Pack)")
```

### 7.4 调试技巧

#### 启用详细日志

```python
import logging

# 启用调度器日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("sage.kernel.scheduler")
logger.setLevel(logging.DEBUG)
```

#### 检查决策历史

```python
# 运行后检查所有决策
for i, decision in enumerate(scheduler.decision_history):
    print(f"决策 {i+1}:")
    print(f"  目标节点: {decision.target_node}")
    print(f"  资源需求: {decision.resource_requirements}")
    print(f"  原因: {decision.reason}")
```

#### 监控资源使用

```python
# 定期获取集群统计
import time


def monitor_cluster(scheduler, interval=5):
    while True:
        metrics = scheduler.get_metrics()
        if "cluster" in metrics:
            cluster = metrics["cluster"]
            print(
                f"节点数: {cluster['node_count']}, "
                f"CPU使用: {cluster['avg_cpu_usage']:.1%}, "
                f"活跃任务: {metrics.get('active_tasks', 0)}"
            )
        time.sleep(interval)


# 在后台线程运行
import threading

monitor_thread = threading.Thread(target=monitor_cluster, args=(scheduler,))
monitor_thread.daemon = True
monitor_thread.start()
```

______________________________________________________________________

## 附录

### A. 调度策略对比

| 策略         | 目标     | 优点         | 缺点         | 适用场景           |
| ------------ | -------- | ------------ | ------------ | ------------------ |
| **FIFO**     | 按序调度 | 简单、快速   | 不考虑负载   | 资源充足、负载均匀 |
| **Balanced** | 负载均衡 | 综合考虑资源 | 调度开销稍大 | 通用场景（推荐）   |
| **Pack**     | 紧凑放置 | 节省资源     | 可能热点     | 弹性集群、成本敏感 |
| **Spread**   | 分散放置 | 高可用、隔离 | 资源利用率低 | 服务调度、需要隔离 |

### B. 常见问题

#### Q1: 如何选择调度策略？

**A**:

- 开发测试：使用 FIFO（简单快速）
- 生产环境（通用）：使用 LoadAware + Balanced
- 弹性集群：使用 LoadAware + Pack
- 高可用服务：使用 LoadAware + Spread

#### Q2: 资源需求如何定义？

**A**: 在 Operator 类中定义：

```python
class MyOperator:
    cpu_required = 4
    gpu_required = 1
    memory_required = "8GB"
```

#### Q3: 如何监控调度性能？

**A**: 使用 `get_metrics()` 方法：

```python
metrics = scheduler.get_metrics()
print(metrics)
```

#### Q4: 并行度在哪里指定？

**A**: 在构建 pipeline 时指定：

```python
env.from_source(source).map(MyOperator, parallelism=4).sink(sink)
```

#### Q5: 如何实现自定义调度策略？

**A**: 继承 `BaseScheduler` 并实现 `make_decision()` 方法（参见 7.1 节）。

### C. 相关文件

- **核心 API**: `api.py` - BaseScheduler 接口
- **决策数据类**: `decision.py` - PlacementDecision
- **节点选择器**: `node_selector.py` - NodeSelector
- **放置执行器**: `placement.py` - PlacementExecutor
- **FIFO 调度器**: `impl/simple_scheduler.py` - FIFOScheduler
- **负载感知调度器**: `impl/resource_aware_scheduler.py` - LoadAwareScheduler
- **Dispatcher**: `../runtime/dispatcher.py` - 协调者

______________________________________________________________________

**最后更新**: 2025-10-13 **版本**: 1.0.0 **维护者**: SAGE Team
