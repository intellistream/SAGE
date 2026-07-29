""" "
Fault Tolerance Module - 分布式容错

Layer: L3 (Kernel - Fault Tolerance)
Dependencies: sage.platform (L2), sage.common (L1)

容错对应用用户是透明的 - 用户只需在 Environment 配置中声明容错策略即可。
容错对开发者是可扩展的 - 开发者可以实现自己的容错策略。

## 对应用用户（Application User）

用户在创建 Environment 时声明容错需求，系统自动处理：

```python
from sage.kernel.api.local_environment import LocalEnvironment

# 使用 checkpoint 容错策略
env = LocalEnvironment(
    "my_app",
    config={
        "fault_tolerance": {
            "strategy": "checkpoint",
            "checkpoint_interval": 60.0,
            "max_recovery_attempts": 3
        }
    }
)

# 或使用 restart 容错策略
env = LocalEnvironment(
    "my_app",
    config={
        "fault_tolerance": {
            "strategy": "restart",
            "restart_strategy": "exponential",
            "max_attempts": 5
        }
    }
)

# 正常定义和提交 DAG，容错由系统自动处理
query_stream = env.from_source(...).map(...).sink(...)
env.submit()
```

## 对开发者（Developer）

开发者可以实现自定义容错策略：

```python
from sage.kernel.fault_tolerance.base import BaseFaultHandler

class MyCustomFaultHandler(BaseFaultHandler):
    def handle_failure(self, task_id, error):
        # 自定义容错逻辑
        pass

    def can_recover(self, task_id):
        # 自定义恢复判断
        pass

    def recover(self, task_id):
        # 自定义恢复实现
        pass
```

然后在代码中注册：

```python
# 在 impl/__init__.py 中添加导出
# 在需要的地方使用自定义策略
```

## 模块导出

仅导出开发者扩展所需的基类和实现接口：
- BaseFaultHandler: 容错处理器抽象基类（开发者继承）
- impl: 实现层模块（内含各种策略实现）
"""

# 导出实现层供开发者参考和扩展
from sage.kernel.fault_tolerance import impl

# 只导出开发者扩展需要的基类
from sage.kernel.fault_tolerance.base import BaseFaultHandler

__all__ = [
    "BaseFaultHandler",  # 开发者继承此类实现自定义策略
    "impl",  # 实现层模块，包含所有内置策略
]
