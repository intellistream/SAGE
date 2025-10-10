# Scheduler Module - 调度器模块

## 设计原则

### 1. 用户无感知
用户只需在创建 Environment 时指定调度策略，无需关心调度细节。

### 2. 并行度是 operator 级别的
每个 transformation 可以指定自己的并行度（parallelism）。

### 3. 调度策略是应用级别的
在 Environment 初始化时配置，影响整个 application 的调度行为。

## 用户使用方式

### 基础用法

```python
from sage.kernel.api.local_environment import LocalEnvironment

# 使用默认调度器（FIFO）
env = LocalEnvironment()

# 或指定调度器类型
env = LocalEnvironment(scheduler="fifo")  # FIFO 策略
env = LocalEnvironment(scheduler="load_aware")  # 负载感知策略

# 构建 pipeline（operator 级别的并行度）
(env.from_source(MySource)
    .map(MyOperator, parallelism=4)   # 这个 operator 有 4 个并行实例
    .filter(MyFilter, parallelism=2)  # 这个 operator 有 2 个并行实例
    .sink(MySink))

# 提交执行（调度器自动工作）
env.submit()
```

### 实际例子（参考 examples/）

```python
from sage.kernel.api.remote_environment import RemoteEnvironment

# RAG 应用示例
env = RemoteEnvironment(scheduler="fifo")

(env.from_source(QuestionSource)
    .map(Retriever, parallelism=4)    # 4 个并行检索器
    .map(Promptor)                     # 默认并行度 1
    .map(Generator, parallelism=2)    # 2 个并行生成器
    .sink(TerminalSink))

env.submit()
```

## 开发者使用方式

### 对比不同调度策略

```python
from sage.kernel.scheduler.impl import FIFOScheduler, LoadAwareScheduler

# 实验 1: FIFO 策略
env1 = LocalEnvironment(scheduler=FIFOScheduler())
build_pipeline(env1)
env1.submit()
metrics1 = env1.scheduler.get_metrics()

# 实验 2: 负载感知策略
env2 = LocalEnvironment(scheduler=LoadAwareScheduler(max_concurrent=20))
build_pipeline(env2)
env2.submit()
metrics2 = env2.scheduler.get_metrics()

# 对比结果
print(f"FIFO latency: {metrics1['avg_latency_ms']:.2f}ms")
print(f"LoadAware latency: {metrics2['avg_latency_ms']:.2f}ms")
print(f"LoadAware utilization: {metrics2['avg_resource_utilization']:.2f}")
```

## 目录结构

```
scheduler/
├── api.py                    # 核心 API 定义
│   └── BaseScheduler         # 调度器基类
│
├── __init__.py               # 模块导出
│
├── impl/                     # 调度器实现（供开发者对比）
│   ├── simple_scheduler.py      # FIFOScheduler (baseline)
│   ├── resource_aware_scheduler.py  # LoadAwareScheduler
│   ├── template_scheduler.py    # 实现模板
│   └── [your_scheduler].py     # 你的调度器
│
└── README.md                 # 本文件
```

## 核心 API

### BaseScheduler

所有调度器必须继承的基类：

```python
from sage.kernel.scheduler.api import BaseScheduler

class MyScheduler(BaseScheduler):
    def schedule_task(self, node, runtime_ctx=None):
        """
        根据 node.transformation.parallelism 和调度策略
        决定如何调度任务
        """
        # 获取并行度
        parallelism = node.transformation.parallelism
        
        # 实现调度逻辑
        # ...
        
        # 创建任务
        ctx = runtime_ctx or node.ctx
        return node.task_factory.create_task(node.name, ctx)
    
    def schedule_service(self, node, runtime_ctx=None):
        """调度服务节点"""
        ctx = runtime_ctx or node.ctx
        return node.service_task_factory.create_service_task(ctx)
    
    def get_metrics(self):
        """返回性能指标"""
        return {"scheduler_type": "MyScheduler", ...}
```

## 已实现的调度策略

### 1. FIFOScheduler (simple_scheduler.py)

最简单的 FIFO（先进先出）调度策略：

```python
from sage.kernel.scheduler.impl import FIFOScheduler

# 方式 1: 字符串
env = LocalEnvironment(scheduler="fifo")

# 方式 2: 实例
env = LocalEnvironment(scheduler=FIFOScheduler())
```

**特点：**
- 按任务到达顺序调度
- 简单、可预测
- 适合作为 baseline
- 尊重 operator 的 parallelism 设置

**适用场景：**
- 负载均匀的应用
- 对调度顺序不敏感的任务
- 作为对照实验的 baseline

### 2. LoadAwareScheduler (resource_aware_scheduler.py)

负载感知调度策略：

```python
from sage.kernel.scheduler.impl import LoadAwareScheduler

# 指定最大并发数
env = LocalEnvironment(scheduler=LoadAwareScheduler(max_concurrent=20))
```

**特点：**
- 监控系统当前负载
- 动态控制并发任务数
- 避免资源过载
- 平衡资源利用率

**适用场景：**
- 资源受限的环境
- 负载波动较大的应用
- 需要控制并发度的场景

## 实现自定义调度器

### 步骤 1: 复制模板

```bash
cd impl/
cp template_scheduler.py priority_scheduler.py
```

### 步骤 2: 实现调度逻辑

```python
from sage.kernel.scheduler.api import BaseScheduler

class PriorityScheduler(BaseScheduler):
    def __init__(self, platform="local"):
        self.platform = platform
        self.priority_queue = []
    
    def schedule_task(self, task_node, runtime_ctx=None):
        # 获取 transformation 信息
        transformation = task_node.transformation
        parallelism = transformation.parallelism
        
        # 你的优先级逻辑
        # 例如：根据 operator 类型或其他元数据决定优先级
        
        # 创建任务
        ctx = runtime_ctx or task_node.ctx
        task = task_node.task_factory.create_task(task_node.name, ctx)
        return task
    
    def schedule_service(self, service_node, runtime_ctx=None):
        ctx = runtime_ctx or service_node.ctx
        return service_node.service_task_factory.create_service_task(ctx)
    
    def get_metrics(self):
        return {"scheduler_type": "Priority", ...}
```

### 步骤 3: 导出调度器

在 `impl/__init__.py` 中添加：

```python
from sage.kernel.scheduler.impl.priority_scheduler import PriorityScheduler

__all__ = [
    # ...
    "PriorityScheduler",
]
```

### 步骤 4: 使用调度器

```python
from sage.kernel.scheduler.impl import PriorityScheduler

env = LocalEnvironment(scheduler=PriorityScheduler())
# 构建 pipeline...
env.submit()
```

## 调度器对比指标

所有调度器都提供 `get_metrics()` 方法返回性能指标：

```python
metrics = env.scheduler.get_metrics()

# FIFOScheduler 返回:
{
    "scheduler_type": "FIFO",
    "total_scheduled": 1000,
    "avg_latency_ms": 2.5,
    "platform": "local"
}

# LoadAwareScheduler 返回:
{
    "scheduler_type": "LoadAware",
    "total_scheduled": 1000,
    "avg_latency_ms": 3.2,
    "active_tasks": 15,
    "max_concurrent": 20,
    "avg_resource_utilization": 0.75,
    "platform": "local"
}
```

## 建议实现的 Baseline 策略

- [x] **FIFOScheduler** - 先进先出（已实现）
- [x] **LoadAwareScheduler** - 负载感知（已实现）
- [ ] **RoundRobinScheduler** - 轮询调度
- [ ] **PriorityScheduler** - 优先级调度
- [ ] **CostOptimizedScheduler** - 成本优化

## 与 SAGE 架构的集成

### Environment 层面

```python
class BaseEnvironment:
    def __init__(self, scheduler=None):
        # 初始化调度器
        if scheduler is None:
            self.scheduler = FIFOScheduler()
        elif isinstance(scheduler, str):
            self.scheduler = get_scheduler_by_name(scheduler)
        else:
            self.scheduler = scheduler
```

### Transformation 层面

```python
# 用户定义 operator 时指定并行度
env.from_source(MySource).map(
    MyOperator,
    parallelism=4  # operator 级别的并行度
)
```

### Runtime 层面

```python
# Runtime 使用 scheduler 调度任务
task = self.scheduler.schedule_task(task_node, runtime_ctx)
```

## 常见问题

### Q: 调度器在哪里配置？

在创建 Environment 时配置：
```python
env = LocalEnvironment(scheduler="fifo")
```

### Q: 并行度在哪里指定？

在定义 transformation 时指定：
```python
.map(MyOperator, parallelism=4)
```

### Q: 如何对比不同调度策略？

创建多个 Environment，分别使用不同调度器，对比 metrics：
```python
env1 = LocalEnvironment(scheduler="fifo")
env2 = LocalEnvironment(scheduler="load_aware")

# 运行并对比
metrics1 = env1.scheduler.get_metrics()
metrics2 = env2.scheduler.get_metrics()
```

### Q: 用户需要了解调度器吗？

**不需要！** 用户只需：
1. 创建 Environment 时可选指定调度策略（默认 FIFO）
2. 为每个 operator 指定并行度
3. 调度器自动工作，用户无感知

## 最佳实践

### 对于用户

```python
# 简单应用 - 使用默认调度器
env = LocalEnvironment()

# 复杂应用 - 指定调度策略
env = RemoteEnvironment(scheduler="load_aware")

# 构建 pipeline - 指定并行度
(env.from_source(MySource)
    .map(HeavyProcessor, parallelism=8)  # 资源密集型
    .filter(SimpleFilter, parallelism=2)  # 轻量级
    .sink(MySink))

env.submit()
```

### 对于开发者

```python
# 实现新调度器
class MyScheduler(BaseScheduler):
    def schedule_task(self, node, runtime_ctx=None):
        # 考虑 node.transformation.parallelism
        # 实现调度逻辑
        pass

# 对比实验
schedulers = [FIFOScheduler(), LoadAwareScheduler(), MyScheduler()]
for sched in schedulers:
    env = LocalEnvironment(scheduler=sched)
    run_experiment(env)
    print(sched.get_metrics())
```

## 总结

- ✅ **用户无感知** - 在 Environment 级别配置调度策略
- ✅ **并行度是 operator 级别的** - 每个 transformation 独立配置
- ✅ **调度策略是应用级别的** - 影响整个 application
- ✅ **开发者可对比** - 轻松实现和对比不同策略
- ✅ **清晰分离** - API 与实现分离
- ✅ **易于扩展** - 简单添加新策略
