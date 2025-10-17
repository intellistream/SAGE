# Scheduler Module

SAGE 调度器模块 - 负责任务和服务的智能调度与资源感知放置。

## 📖 完整文档

请查看 **[SCHEDULER_GUIDE.md](./SCHEDULER_GUIDE.md)** 获取完整的调度器文档，包括：

1. **设计原则与架构** - 了解调度器的核心设计理念
2. **快速开始** - 5分钟上手调度器
3. **调度器类型** - FIFO vs LoadAware
4. **资源感知调度** - NodeSelector 和调度策略（Balanced/Pack/Spread）
5. **服务调度** - 长期运行服务的特殊处理
6. **API 参考** - 完整的 API 文档
7. **开发指南** - 自定义调度器、性能对比、调试技巧

## 🚀 快速示例

```python
from sage.kernel import LocalEnvironment

# 使用负载感知调度器
env = LocalEnvironment(scheduler="load_aware")

# 构建 pipeline（operator 级别指定并行度）
(env.from_source(MySource)
    .map(MyOperator, parallelism=4)   # 4 个并行实例
    .filter(MyFilter, parallelism=2)  # 2 个并行实例
    .sink(MySink))

# 提交执行（调度器自动工作）
env.submit()
```

## 📂 文件结构

```
scheduler/
├── SCHEDULER_GUIDE.md          # 📖 完整文档（从这里开始）
├── README.md                   # 本文件
├── api.py                      # BaseScheduler 接口
├── decision.py                 # PlacementDecision 数据类
├── node_selector.py            # NodeSelector 资源监控
├── placement.py                # PlacementExecutor 执行器
├── examples_node_placement.py  # 使用示例
└── impl/
    ├── simple_scheduler.py     # FIFOScheduler
    └── resource_aware_scheduler.py  # LoadAwareScheduler
```

## 🔑 核心概念

### 职责分离

- **Scheduler（决策者）**：分析任务需求，选择最优节点，返回 `PlacementDecision`
- **NodeSelector（监控者）**：监控集群资源，提供节点选择算法
- **PlacementExecutor（执行者）**：根据决策执行物理放置，创建 Ray Actor
- **Dispatcher（协调者）**：协调 Scheduler 和 PlacementExecutor

### 调度流程

```
Dispatcher → Scheduler.make_decision() → PlacementDecision
          ↓
          PlacementExecutor.place_task() → Ray Actor
```

## 💡 何时使用哪种调度器？

| 场景 | 推荐调度器 | 理由 |
|------|-----------|------|
| 开发测试 | `FIFOScheduler` | 简单快速 |
| 生产环境（通用） | `LoadAwareScheduler(strategy="balanced")` | 负载均衡 |
| 弹性集群 | `LoadAwareScheduler(strategy="pack")` | 节省资源 |
| 高可用服务 | `LoadAwareScheduler(strategy="spread")` | 避免单点故障 |

## 🔗 相关链接

- [完整文档](./SCHEDULER_GUIDE.md)
- [使用示例](./examples_node_placement.py)
- [Dispatcher 源码](../runtime/dispatcher.py)

---

**开始使用**：阅读 [SCHEDULER_GUIDE.md](./SCHEDULER_GUIDE.md) 🚀
