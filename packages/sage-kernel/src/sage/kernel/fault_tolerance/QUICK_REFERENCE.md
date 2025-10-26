# Fault Tolerance 快速参考

## 应用用户 - 5秒上手

### Checkpoint 策略

```python
env = LocalEnvironment(
    "app",
    config={"fault_tolerance": {"strategy": "checkpoint", "checkpoint_interval": 60.0}},
)
```

### Restart 策略

```python
env = LocalEnvironment(
    "app",
    config={
        "fault_tolerance": {"strategy": "restart", "restart_strategy": "exponential"}
    },
)
```

就这么简单！系统会自动处理容错。

______________________________________________________________________

## 开发者 - 3步扩展

### 步骤 1: 实现处理器

```python
from sage.kernel.fault_tolerance.base import BaseFaultHandler


class MyHandler(BaseFaultHandler):
    def handle_failure(self, task_id, error): ...
    def can_recover(self, task_id): ...
    def recover(self, task_id): ...
```

### 步骤 2: 注册到 factory.py

```python
# 在 create_fault_handler_from_config() 添加
if strategy == "my_strategy":
    return MyHandler(...)
```

### 步骤 3: 用户使用

```python
env = LocalEnvironment("app", config={"fault_tolerance": {"strategy": "my_strategy"}})
```

______________________________________________________________________

## 配置参数速查

| 策略           | 参数                        | 说明                                 |
| -------------- | --------------------------- | ------------------------------------ |
| **checkpoint** | `checkpoint_interval`       | Checkpoint保存间隔（秒）             |
|                | `max_recovery_attempts`     | 最大恢复次数                         |
|                | `checkpoint_dir`            | 存储目录                             |
| **restart**    | `restart_strategy`          | `fixed`/`exponential`/`failure_rate` |
| (fixed)        | `delay`                     | 固定延迟（秒）                       |
|                | `max_attempts`              | 最大重试次数                         |
| (exponential)  | `initial_delay`             | 初始延迟（秒）                       |
|                | `max_delay`                 | 最大延迟（秒）                       |
|                | `multiplier`                | 延迟倍数                             |
|                | `max_attempts`              | 最大重试次数                         |
| (failure_rate) | `max_failures_per_interval` | 窗口内最大失败数                     |
|                | `interval_seconds`          | 时间窗口（秒）                       |
|                | `delay`                     | 重启延迟（秒）                       |

______________________________________________________________________

## 文件导航

- **用户文档**: `README.md`
- **代码示例**: `examples.py`
- **重构总结**: `REFACTORING_SUMMARY.md`
- **实现参考**: `impl/`目录
- **基类定义**: `base.py`
