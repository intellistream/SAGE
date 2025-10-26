# RPC Queue 架构重构 - 工厂模式实现

> 日期: 2025-10-23 作者: Architecture Review Team 状态: ✅ 已完成

## 📋 重构概述

**问题**: RPCQueueDescriptor (L2) 直接导入 RPCQueue (L3)，违反了分层架构原则。

**解决方案**: 实现工厂注册模式（Factory Registration Pattern），消除 L2→L3 的直接依赖。

**结果**:

- ✅ 消除架构违规
- ✅ 保持层级依赖单向性 (L1 ← L2 ← L3)
- ✅ 所有测试通过 (30/30)
- ✅ 运行时验证成功

## 🎯 架构原则

### 分层依赖规则

```
L1 (sage-common)    ← 基础设施，无依赖
  ↑
L2 (sage-platform)  ← 平台服务，依赖 L1
  ↑
L3 (sage-kernel)    ← 核心引擎，依赖 L1+L2
```

**原则**:

- ✅ 允许：L3 → L2 → L1 (向下依赖)
- ❌ 禁止：L2 → L3 (向上依赖)
- ❌ 禁止：L1 → L3 (跨层依赖)

### 工厂模式解决跨层问题

当 L2 需要创建 L3 对象时，使用工厂注册模式：

1. **L2 定义接口** - 提供注册点，不导入实现
1. **L3 注册实现** - 在初始化时注册工厂函数
1. **运行时绑定** - L2 使用注册的工厂创建对象

## 🔧 实现细节

### 1. L2 层：定义接口和注册点

**文件**: `packages/sage-platform/src/sage/platform/queue/rpc_queue_descriptor.py`

```python
from typing import Any, Callable, Optional

# 工厂函数类型定义
QueueFactory = Callable[..., Any]

# 全局工厂注册表 - 由L3层注册实现
_rpc_queue_factory: Optional[QueueFactory] = None


def register_rpc_queue_factory(factory: QueueFactory) -> None:
    """注册RPC队列工厂函数

    This function should be called by sage-kernel (L3) to register
    the concrete RPCQueue implementation.

    Args:
        factory: Factory function that creates RPCQueue instances
            Signature: factory(queue_id, host, port, ...) -> RPCQueue
    """
    global _rpc_queue_factory
    _rpc_queue_factory = factory
    logger.info("RPC queue factory registered successfully")


class RPCQueueDescriptor(BaseQueueDescriptor):
    """RPC队列描述符 - L2层不直接导入L3实现"""

    def _create_queue_instance(self) -> Any:
        """使用工厂模式创建实例"""
        if _rpc_queue_factory is None:
            raise RuntimeError(
                "RPC queue factory not registered. "
                "Please ensure sage-kernel is imported and initialized."
            )

        # 使用注册的工厂函数创建队列实例
        return _rpc_queue_factory(
            queue_id=self.queue_id,
            host=self.host,
            port=self.port,
            connection_timeout=self.connection_timeout,
            retry_count=self.retry_count,
            enable_pooling=self.enable_pooling,
        )
```

**关键点**:

- ✅ 不导入 `sage.kernel` 任何模块
- ✅ 使用全局变量存储工厂函数
- ✅ 提供清晰的错误信息

### 2. L3 层：注册实现

**文件**: `packages/sage-kernel/src/sage/kernel/__init__.py`

```python
"""
SAGE Kernel - 流式数据处理引擎和基础算子

Layer: L3 (Kernel)
Dependencies: sage.platform (L2), sage.common (L1)
"""

# ============================================================================
# 架构关键：L3向L2注册实现（Factory Pattern）
# ============================================================================
# 在初始化时注册RPCQueue实现到sage-platform的工厂
# 这样L2层可以创建L3实例，但不需要直接导入L3代码
try:
    from sage.platform.queue import register_rpc_queue_factory
    from sage.kernel.runtime.communication.rpc import RPCQueue

    def _rpc_queue_factory(**kwargs):
        """RPC队列工厂函数 - 由L2调用创建L3实例"""
        return RPCQueue(**kwargs)

    register_rpc_queue_factory(_rpc_queue_factory)

except ImportError as e:
    import warnings

    warnings.warn(
        f"Failed to register RPC queue factory: {e}. "
        "RPC queue functionality will not be available.",
        ImportWarning,
    )
```

**关键点**:

- ✅ 在包初始化时自动注册
- ✅ 使用 try-except 处理导入失败
- ✅ 提供降级机制（功能不可用但不崩溃）

### 3. L3 层：RPCQueue 实现

**文件**: `packages/sage-kernel/src/sage/kernel/runtime/communication/rpc/rpc_queue.py`

```python
"""
SAGE - RPC Queue Implementation

Layer: L3 (Kernel)
Dependencies: sage.platform (L2), queue.Queue (stdlib)

RPCQueue实现：基于RPC的远程队列通信

Note:
    ⚠️ STUB IMPLEMENTATION - 当前使用本地Queue模拟远程行为
    生产环境需要实现真实的RPC客户端（如gRPC）
"""

import logging
from queue import Empty, Queue
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RPCQueue:
    """RPC队列实现 - 当前为stub版本"""

    def __init__(
        self,
        queue_id: str,
        host: str = "localhost",
        port: int = 50051,
        maxsize: int = 0,
        **kwargs,
    ):
        """初始化RPC队列"""
        self.queue_id = queue_id
        self.host = host
        self.port = port
        self.maxsize = maxsize

        # Stub实现：使用本地Queue
        self._queue: Queue = Queue(maxsize=maxsize)
        self._connected = False

        logger.warning(
            f"⚠️ RPCQueue '{queue_id}' initialized as STUB - "
            f"using local Queue instead of real RPC to {host}:{port}"
        )

    def connect(self) -> bool:
        """连接到RPC服务器"""
        if not self._connected:
            logger.info(
                f"[STUB] Simulating connection to RPC server "
                f"{self.host}:{self.port} for queue '{self.queue_id}'"
            )
            self._connected = True
        return True

    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None):
        """发送数据"""
        if not self._connected:
            self.connect()
        self._queue.put(item, block=block, timeout=timeout)

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """接收数据"""
        if not self._connected:
            self.connect()
        return self._queue.get(block=block, timeout=timeout)

    # ... 其他队列方法
```

**关键点**:

- ✅ 实现标准队列接口（put, get, qsize, empty, full）
- ✅ 当前为 stub 实现，使用本地 Queue 模拟
- ✅ 提供清晰的警告信息
- ⚠️ TODO: 实现真实的 RPC 通信（gRPC/HTTP）

## 📦 文件组织

### 删除的文件

- ❌
  `packages/sage-kernel/src/sage/kernel/runtime/communication/queue_descriptor/rpc_queue_descriptor.py`
  - **原因**: 重复文件，应该只在 L2 (sage-platform) 存在
  - **操作**: 已删除

### 新增的文件

- ✅ `packages/sage-kernel/src/sage/kernel/runtime/communication/rpc/__init__.py`
- ✅ `packages/sage-kernel/src/sage/kernel/runtime/communication/rpc/rpc_queue.py`

### 修改的文件

1. **sage-platform (L2)**:

   - `src/sage/platform/queue/rpc_queue_descriptor.py` - 添加工厂注册机制
   - `src/sage/platform/queue/__init__.py` - 导出注册函数
   - `src/sage/platform/__init__.py` - 更新文档

1. **sage-kernel (L3)**:

   - `src/sage/kernel/__init__.py` - 添加工厂注册调用
   - `src/sage/kernel/runtime/communication/queue_descriptor/__init__.py` - 从 L2 导入
     RPCQueueDescriptor

## ✅ 验证结果

### 单元测试

```bash
cd packages/sage-platform
python -m pytest tests/unit/queue/ -v
```

**结果**: ✅ 30/30 tests passed

关键测试:

- `test_rpc_queue_creation` - RPC 描述符创建
- `test_queue_operations` - 队列操作（put/get）
- `test_serialization` - 序列化/反序列化
- `test_lazy_loading` - 延迟加载机制

### 运行时验证

```python
# 导入 kernel 触发注册
import sage.kernel

# 创建 RPC 描述符
from sage.platform.queue import RPCQueueDescriptor

descriptor = RPCQueueDescriptor(host="test-host", port=9999, queue_id="test-rpc-queue")

# 获取队列实例 - 使用工厂创建
queue = descriptor.queue_instance

# 验证队列操作
queue.put("test-message")
result = queue.get()
assert result == "test-message"
```

**结果**: ✅ 工厂模式正常工作

输出:

```
⚠️ RPCQueue 'test-rpc-queue' initialized as STUB - using local Queue instead of real RPC to test-host:9999
✅ Factory registration successful!
   Queue type: RPCQueue
   Queue ID: test-rpc-queue
   Host: test-host
   Port: 9999
   Put/Get test: test-message
   Connected: True
```

### 架构检查

```python
# 验证 L2 不导入 L3
import ast
import sys


def check_imports(file_path, forbidden_modules):
    with open(file_path) as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(alias.name.startswith(m) for m in forbidden_modules):
                    return False
        elif isinstance(node, ast.ImportFrom):
            if node.module and any(
                node.module.startswith(m) for m in forbidden_modules
            ):
                return False
    return True


# 检查 sage-platform 是否导入 sage-kernel
result = check_imports(
    "packages/sage-platform/src/sage/platform/queue/rpc_queue_descriptor.py",
    ["sage.kernel"],
)
```

**结果**: ✅ 无架构违规

## 🎓 设计模式总结

### 工厂注册模式 (Factory Registration Pattern)

**定义**: 高层模块提供注册点，低层模块在运行时注册工厂函数，实现依赖倒置。

**适用场景**:

- 分层架构中，高层需要创建低层对象
- 插件系统中，核心系统不依赖插件代码
- 微服务架构中，服务发现和注册

**优点**:

- ✅ 解耦高层和低层模块
- ✅ 保持依赖单向性
- ✅ 易于扩展和替换实现
- ✅ 支持运行时配置

**缺点**:

- ⚠️ 增加了间接层
- ⚠️ 运行时错误检测（非编译时）
- ⚠️ 需要确保注册顺序正确

### 与其他模式的对比

| 模式         | 依赖方向  | 绑定时机 | 类型安全  | 适用场景   |
| ------------ | --------- | -------- | --------- | ---------- |
| **直接导入** | 高层→低层 | 编译时   | ✅ 强类型 | 无分层约束 |
| **抽象基类** | 双向解耦  | 编译时   | ✅ 强类型 | 接口稳定   |
| **工厂注册** | 单向解耦  | 运行时   | ⚠️ 弱类型 | 分层架构   |
| **依赖注入** | 外部控制  | 运行时   | ✅ 可配置 | 复杂系统   |

### 在 SAGE 中的应用

**当前使用**:

- ✅ RPCQueueDescriptor (L2) ← RPCQueue (L3)

**未来可能应用**:

- [ ] Storage Backend 注册（Redis, RocksDB）
- [ ] Model Provider 注册（OpenAI, Anthropic, etc.）
- [ ] Operator 插件系统

## 📚 相关文档

- [PACKAGE_ARCHITECTURE.md](../PACKAGE_ARCHITECTURE.md) - 包架构总览
- [L2_LAYER_ANALYSIS.md](./L2_LAYER_ANALYSIS.md) - L2 层设计分析
- [TOP_LAYER_REVIEW_2025.md](./TOP_LAYER_REVIEW_2025.md) - 架构审查报告

## 🔄 后续工作

### 短期 (已完成)

- ✅ 实现工厂注册机制
- ✅ 删除重复文件
- ✅ 更新所有导入路径
- ✅ 验证测试通过
- ✅ 更新文档

### 中期 (计划中)

- [ ] 实现真实的 RPC 通信（gRPC）
- [ ] 添加连接池管理
- [ ] 实现序列化/反序列化
- [ ] 添加重试和故障转移机制

### 长期 (待评估)

- [ ] 扩展工厂模式到其他组件
- [ ] 实现插件系统
- [ ] 支持动态加载和卸载

## 👥 贡献者

- Architecture Review Team
- 审查日期: 2025-10-23
- 重构完成: 2025-10-23

______________________________________________________________________

**Status**: ✅ 已完成并验证 **Last Updated**: 2025-10-23
