# Fault Tolerance Module

分布式系统容错模块，提供多种容错策略的实现。

## 设计理念

**容错对应用用户是透明的，对开发者是可扩展的。**

- **应用用户（Application User）**：只需在 Environment 配置中声明容错策略，无需编写任何容错相关代码
- **开发者（Developer）**：可以实现自定义容错策略，扩展系统功能

## 架构设计

```
fault_tolerance/
├── base.py                     # BaseFaultHandler - 容错处理器抽象基类
├── factory.py                  # 从配置创建容错策略的工厂（内部使用）
├── __init__.py                 # 只导出开发者扩展需要的接口
│
└── impl/                       # 实现层 - 内置容错策略
    ├── checkpoint_recovery.py   # Checkpoint 容错策略
    ├── restart_recovery.py      # 重启容错策略
    ├── checkpoint_impl.py       # Checkpoint 管理实现
    ├── lifecycle_impl.py        # 生命周期管理实现
    └── restart_strategy.py      # 重启策略（Fixed, Exponential, FailureRate）
```

### 核心组件

1. **BaseFaultHandler** (base.py)
   - 容错处理器抽象基类
   - 开发者继承此类实现自定义容错策略

2. **factory** (factory.py)
   - 内部使用的工厂模块
   - 从 Environment 配置创建容错处理器实例
   - Dispatcher/JobManager 自动调用

3. **impl** (实现层)
   - 包含所有内置容错策略实现
   - 开发者可参考这些实现来创建自定义策略

## 应用用户使用指南

### 1. 基本使用 - 在 Environment 配置中声明

用户只需在创建 Environment 时声明容错策略，系统会自动处理一切：

```python
from sage.kernel.api.local_environment import LocalEnvironment
from sage.libs.io.source import FileSource
from sage.libs.io.sink import TerminalSink

# 使用 Checkpoint 容错策略
env = LocalEnvironment(
    "my_app",
    config={
        "fault_tolerance": {
            "strategy": "checkpoint",
            "checkpoint_interval": 60.0,      # 每60秒保存一次checkpoint
            "max_recovery_attempts": 3,        # 最多尝试恢复3次
            "checkpoint_dir": ".checkpoints"   # checkpoint存储目录
        }
    }
)

# 正常定义和提交 DAG - 容错由系统自动处理
stream = env.from_source(FileSource, {...}).map(...).sink(TerminalSink, {...})
env.submit()
```

### 2. 使用重启策略

```python
# 使用固定延迟重启策略
env = LocalEnvironment(
    "my_app",
    config={
        "fault_tolerance": {
            "strategy": "restart",
            "restart_strategy": "fixed",
            "delay": 5.0,            # 每次重启等待5秒
            "max_attempts": 3        # 最多重启3次
        }
    }
)

# 或使用指数退避策略
env = LocalEnvironment(
    "my_app",
    config={
        "fault_tolerance": {
            "strategy": "restart",
            "restart_strategy": "exponential",
            "initial_delay": 1.0,     # 初始延迟1秒
            "max_delay": 60.0,        # 最大延迟60秒
            "multiplier": 2.0,        # 每次延迟翻倍
            "max_attempts": 5         # 最多重启5次
        }
    }
)

# 或使用基于失败率的策略
env = LocalEnvironment(
    "my_app",
    config={
        "fault_tolerance": {
            "strategy": "restart",
            "restart_strategy": "failure_rate",
            "max_failures_per_interval": 3,  # 时间窗口内最多失败3次
            "interval_seconds": 60.0,         # 时间窗口60秒
            "delay": 5.0                      # 重启延迟5秒
        }
    }
)

# 正常定义和提交 DAG
stream = env.from_source(...).map(...).sink(...)
env.submit()
```

### 3. 不使用容错（默认行为）

```python
# 不指定 fault_tolerance 配置，使用默认的简单重启策略
env = LocalEnvironment("my_app")

# 或者显式禁用容错
env = LocalEnvironment("my_app", config={})
```

### 完整示例

```python
from sage.kernel.api.local_environment import LocalEnvironment
from sage.libs.io.source import FileSource
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.io.sink import TerminalSink

def main():
    # 创建环境并配置容错策略
    env = LocalEnvironment(
        "qa_pipeline",
        config={
            "fault_tolerance": {
                "strategy": "checkpoint",
                "checkpoint_interval": 30.0,
                "max_recovery_attempts": 5
            },
            "source": {"file_path": "questions.txt"},
            "promptor": {...},
            "generator": {...},
            "sink": {}
        }
    )

    # 定义 DAG - 用户不需要关心容错
    pipeline = (
        env.from_source(FileSource, env.config["source"])
           .map(QAPromptor, env.config["promptor"])
           .map(OpenAIGenerator, env.config["generator"])
           .sink(TerminalSink, env.config["sink"])
    )

    # 提交作业 - 容错由系统自动处理
    env.submit()

if __name__ == "__main__":
    main()
```

## 开发者扩展指南

开发者可以实现自定义容错策略来满足特定需求。

### 1. 实现自定义容错策略

```python
# my_custom_fault_tolerance.py
from sage.kernel.fault_tolerance.base import BaseFaultHandler

class ReplicationBasedRecovery(BaseFaultHandler):
    """
    基于副本的容错策略

    为每个任务创建多个副本，一个失败时切换到另一个。
    """

    def __init__(self, num_replicas=3):
        self.num_replicas = num_replicas
        self.replicas = {}
        self.active_replicas = {}
        self.logger = None

    def handle_failure(self, task_id: str, error: Exception) -> bool:
        """处理任务失败 - 切换到备用副本"""
        if self.logger:
            self.logger.warning(f"Task {task_id} failed: {error}")

        if self.can_recover(task_id):
            return self.recover(task_id)
        else:
            if self.logger:
                self.logger.error(f"No available replicas for {task_id}")
            return False

    def can_recover(self, task_id: str) -> bool:
        """检查是否有可用的备用副本"""
        available_replicas = [
            r for r in self.replicas.get(task_id, [])
            if r != self.active_replicas.get(task_id)
        ]
        return len(available_replicas) > 0

    def recover(self, task_id: str) -> bool:
        """切换到健康的副本"""
        available_replicas = [
            r for r in self.replicas.get(task_id, [])
            if r != self.active_replicas.get(task_id)
        ]

        if available_replicas:
            new_replica = available_replicas[0]
            self.active_replicas[task_id] = new_replica

            if self.logger:
                self.logger.info(f"Switched task {task_id} to replica {new_replica}")

            return True

        return False
```

### 2. 将自定义策略集成到系统

将自定义策略添加到 `impl` 目录：

```bash
# 将文件放到 impl 目录
cp my_custom_fault_tolerance.py packages/sage-kernel/src/sage/kernel/fault_tolerance/impl/
```

更新 `impl/__init__.py`：

```python
# impl/__init__.py
from sage.kernel.fault_tolerance.impl.checkpoint_recovery import CheckpointBasedRecovery
from sage.kernel.fault_tolerance.impl.restart_recovery import RestartBasedRecovery
from sage.kernel.fault_tolerance.impl.my_custom_fault_tolerance import ReplicationBasedRecovery

__all__ = [
    "CheckpointBasedRecovery",
    "RestartBasedRecovery",
    "ReplicationBasedRecovery",  # 添加自定义策略
    ...
]
```

更新 `factory.py` 以支持新策略：

```python
# factory.py
from sage.kernel.fault_tolerance.impl.my_custom_fault_tolerance import ReplicationBasedRecovery

def create_fault_handler_from_config(config):
    strategy = config.get("strategy", "restart")

    if strategy == "replication":
        num_replicas = config.get("num_replicas", 3)
        return ReplicationBasedRecovery(num_replicas=num_replicas)
    # ... 其他策略
```

### 3. 应用用户使用自定义策略

```python
env = LocalEnvironment(
    "my_app",
    config={
        "fault_tolerance": {
            "strategy": "replication",  # 使用自定义策略
            "num_replicas": 3
        }
    }
)
```

## 内置容错策略对比

| 策略 | 适用场景 | 优点 | 缺点 | 配置示例 |
|-----|---------|------|------|---------|
| **Checkpoint** | 长时间运行的有状态任务 | 减少重新计算，节省资源 | 需要额外存储，保存开销 | `{"strategy": "checkpoint", "checkpoint_interval": 60.0}` |
| **Restart** | 无状态或短任务 | 简单直接，无额外开销 | 失败时需要完全重新执行 | `{"strategy": "restart", "restart_strategy": "exponential"}` |

## 配置参数详解

### Checkpoint 策略参数

```python
{
    "fault_tolerance": {
        "strategy": "checkpoint",
        "checkpoint_interval": 60.0,       # Checkpoint保存间隔（秒）
        "max_recovery_attempts": 3,        # 最大恢复尝试次数
        "checkpoint_dir": ".checkpoints"   # Checkpoint存储目录
    }
}
```

### Restart 策略参数

**固定延迟（Fixed）：**
```python
{
    "fault_tolerance": {
        "strategy": "restart",
        "restart_strategy": "fixed",
        "delay": 5.0,           # 固定延迟时间（秒）
        "max_attempts": 3       # 最大重启次数
    }
}
```

**指数退避（Exponential）：**
```python
{
    "fault_tolerance": {
        "strategy": "restart",
        "restart_strategy": "exponential",
        "initial_delay": 1.0,   # 初始延迟（秒）
        "max_delay": 60.0,      # 最大延迟（秒）
        "multiplier": 2.0,      # 延迟倍数
        "max_attempts": 5       # 最大重启次数
    }
}
```

**失败率（Failure Rate）：**
```python
{
    "fault_tolerance": {
        "strategy": "restart",
        "restart_strategy": "failure_rate",
        "max_failures_per_interval": 3,  # 时间窗口内最多失败次数
        "interval_seconds": 60.0,         # 时间窗口大小（秒）
        "delay": 5.0                      # 重启延迟（秒）
    }
}
```

## 工作原理

1. **用户声明容错需求**：在 Environment 的 `config["fault_tolerance"]` 中配置
2. **系统自动创建处理器**：Dispatcher 初始化时从配置创建容错处理器
3. **自动故障处理**：任务失败时，Dispatcher 自动调用容错处理器进行恢复
4. **用户无感知**：整个过程对用户透明，用户只需关注业务逻辑

## 参考实现

查看 `impl/` 目录下的实现以了解如何编写容错策略：

- `checkpoint_recovery.py` - Checkpoint 策略实现
- `restart_recovery.py` - 重启策略实现
- `restart_strategy.py` - 各种重启策略实现
