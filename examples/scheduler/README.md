# Scheduler Examples - 调度器示例

这个目录包含了演示 SAGE 调度器功能的示例代码。

## 📁 文件说明

### 1. `remote_environment_simple.py`
**RemoteEnvironment 基础示例**

演示如何在 RemoteEnvironment 中使用不同的调度器：
- 使用默认调度器（FIFO）
- 使用字符串指定调度器
- 使用调度器实例
- 查看调度器性能指标

**运行前提：**
- 需要启动 JobManager daemon
- 确保 Ray 已正确安装

**运行命令：**
```bash
# 1. 启动 JobManager daemon
python -m sage.kernel.daemon.start

# 2. 运行示例
python examples/scheduler/remote_environment_simple.py
```

### 2. `scheduler_comparison.py`
**调度器性能对比示例**

对比不同调度策略的性能：
- FIFO 调度器
- LoadAware 调度器
- Local vs Remote 环境

展示如何：
- 为不同实验配置不同调度器
- 收集和对比性能指标
- 分析调度策略对性能的影响

**运行命令：**
```bash
python examples/scheduler/scheduler_comparison.py
```

## 🎯 核心概念

### 用户视角：无感知

用户只需要在创建 Environment 时可选地指定调度策略：

```python
from sage.kernel.api.remote_environment import RemoteEnvironment

# 方式 1: 使用默认调度器
env = RemoteEnvironment()

# 方式 2: 字符串指定
env = RemoteEnvironment(scheduler="fifo")
env = RemoteEnvironment(scheduler="load_aware")

# 方式 3: 传入调度器实例
from sage.kernel.scheduler.impl import LoadAwareScheduler
scheduler = LoadAwareScheduler(max_concurrent=20)
env = RemoteEnvironment(scheduler=scheduler)
```

### 并行度：Operator 级别

并行度在定义 transformation 时指定，而不是在调度器配置中：

```python
(env.from_source(MySource)
    .map(HeavyProcessor, parallelism=4)   # 这个 operator 有 4 个并行实例
    .filter(LightFilter, parallelism=2)   # 这个 operator 有 2 个并行实例
    .sink(MySink))
```

### 调度策略：应用级别

调度器在 Environment 级别配置，影响整个应用的调度行为：
- 自动处理所有任务的调度
- 尊重每个 operator 的 parallelism 设置
- 提供性能指标供分析

## 📊 可用的调度器

### FIFOScheduler (默认)
- **策略**: 先进先出
- **特点**: 简单、可预测
- **适用**: 负载均匀的应用

```python
env = RemoteEnvironment(scheduler="fifo")
```

### LoadAwareScheduler
- **策略**: 负载感知
- **特点**: 动态控制并发，避免过载
- **适用**: 资源受限、负载波动的场景

```python
env = RemoteEnvironment(scheduler="load_aware")
# 或自定义参数
from sage.kernel.scheduler.impl import LoadAwareScheduler
env = RemoteEnvironment(scheduler=LoadAwareScheduler(max_concurrent=15))
```

## 🔍 查看调度器指标

所有调度器都提供 `get_metrics()` 方法返回性能指标：

```python
env = RemoteEnvironment(scheduler="load_aware")

# 构建和运行 pipeline
(env.from_source(Source)
    .map(Processor, parallelism=4)
    .sink(Sink))

env.submit(autostop=True)

# 查看指标
metrics = env.scheduler.get_metrics()
print(metrics)

# 示例输出:
# {
#     'scheduler_type': 'LoadAware',
#     'total_scheduled': 1000,
#     'avg_latency_ms': 3.2,
#     'active_tasks': 15,
#     'max_concurrent': 20,
#     'avg_resource_utilization': 0.75,
#     'platform': 'remote'
# }
```

## 💡 开发者指南

### 对比不同调度策略

```python
from sage.kernel.scheduler.impl import FIFOScheduler, LoadAwareScheduler

schedulers = [
    ("FIFO", FIFOScheduler()),
    ("LoadAware", LoadAwareScheduler(max_concurrent=20)),
]

for name, scheduler in schedulers:
    env = RemoteEnvironment(scheduler=scheduler)
    # 构建相同的 pipeline
    build_pipeline(env)
    env.submit(autostop=True)
    
    # 对比指标
    metrics = env.scheduler.get_metrics()
    print(f"{name}: {metrics}")
```

### 实现自定义调度器

参考 `packages/sage-kernel/src/sage/kernel/scheduler/README.md` 了解如何实现自定义调度器。

## 🚀 快速开始

1. **安装依赖**
   ```bash
   pip install sage-stream
   ```

2. **启动 JobManager daemon（如果使用 RemoteEnvironment）**
   ```bash
   python -m sage.kernel.daemon.start
   ```

3. **运行简单示例**
   ```bash
   python examples/scheduler/remote_environment_simple.py
   ```

4. **运行性能对比**
   ```bash
   python examples/scheduler/scheduler_comparison.py
   ```

## 📚 相关文档

- [调度器模块文档](../../packages/sage-kernel/src/sage/kernel/scheduler/README.md)
- [SAGE 核心 API 文档](../tutorials/core-api/)
- [Transformation API 文档](../tutorials/transformation-api/)

## ❓ 常见问题

### Q: 如何选择调度器？

A: 
- **默认情况**: 不需要选择，使用默认的 FIFO 即可
- **资源受限**: 使用 LoadAwareScheduler 控制并发
- **自定义需求**: 实现自己的调度器

### Q: 调度器会影响并行度吗？

A: 不会。并行度由 `parallelism` 参数控制，调度器只决定何时调度任务。

### Q: LocalEnvironment 也支持调度器吗？

A: 是的！所有示例都同时支持 LocalEnvironment 和 RemoteEnvironment。

```python
from sage.kernel.api.local_environment import LocalEnvironment
env = LocalEnvironment(scheduler="load_aware")
```

## 🎓 学习路径

1. 先运行 `remote_environment_simple.py` 了解基本用法
2. 然后运行 `scheduler_comparison.py` 了解性能对比
3. 阅读调度器模块文档了解如何实现自定义调度器
4. 在实际应用中选择合适的调度策略

---

**Happy Scheduling! 🚀**
