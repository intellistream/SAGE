# SAGE Platform

> 平台服务层 (L2) - SAGE 基础设施抽象

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../../LICENSE)

## 📋 概述

**SAGE Platform** 提供核心基础设施抽象，位于基础层（`sage-common`）和执行引擎（`sage-kernel`）之间。这个第二层平台服务提供：

## 🧭 Governance / 团队协作制度

- `docs/governance/TEAM.md`

- `docs/governance/MAINTAINERS.md`

- `docs/governance/DEVELOPER_GUIDE.md`

- `docs/governance/PR_CHECKLIST.md`

- `docs/governance/SELF_HOSTED_RUNNER.md`

- `docs/governance/TODO.md`

- **队列抽象**：Python、Ray 和 RPC 队列的统一接口

- **存储抽象**：可插拔的键值存储后端

- **服务基类**：构建 SAGE 服务的基础

- **平台接口**：分布式系统的通用模式

该包使应用程序代码能够在本地和分布式执行模式之间无缝切换。

## ✨ 核心特性

- **多态队列**：Python Queue、Ray Queue 和 RPC Queue 的单一 API
- **可插拔存储**：内存、Redis 和自定义存储后端
- **服务框架**：构建平台服务的基类
- **类型安全**：完整的类型提示和运行时验证
- **零开销**：本地执行的最小抽象成本

## 组件

### 🔄 队列 (`sage.platform.queue`)

支持多种后端的多态队列描述符：

```python
from sage.platform.queue import (
    BaseQueueDescriptor,
    PythonQueueDescriptor,
    RayQueueDescriptor,
    RPCQueueDescriptor,
)

# 创建 Ray 队列
queue_desc = RayQueueDescriptor(maxsize=1000, queue_id="my_queue")
queue = queue_desc.queue_instance

# 使用队列操作
queue_desc.put(item)
item = queue_desc.get()
```

**特性**：

- 延迟初始化
- 序列化支持
- 跨进程通信
- 后端无关的 API

### 💾 存储 (`sage.platform.storage`)

键值存储抽象：

```python
from sage.platform.storage.kv_backend import BaseKVBackend, DictKVBackend

# 使用内存后端
backend = DictKVBackend()
backend.set("key", "value")
value = backend.get("key")


# 使用自定义后端扩展
class RedisKVBackend(BaseKVBackend):
    # 实现抽象方法
    ...
```

**支持的操作**：

- `get(key)`, `set(key, value)`, `delete(key)`
- `has(key)`, `clear()`, `get_all_keys()`
- 磁盘持久化：`store_data_to_disk()`, `load_data_to_memory()`

### 🔌 服务 (`sage.platform.service`)

SAGE 服务的基类：

```python
from sage.platform.service import BaseService


class MyService(BaseService):
    def __init__(self, config):
        super().__init__(name="my_service")
        self.config = config

    def process(self, request):
        # 服务逻辑
        return response
```

## 📦 包结构

```
sage-platform/
├── src/
│   └── sage/
│       └── platform/
│           ├── __init__.py
│           ├── queue/              # 队列抽象
│           │   ├── base.py
│           │   ├── python_queue.py
│           │   ├── ray_queue.py
│           │   └── rpc_queue.py
│           ├── storage/            # 存储后端
│           │   └── kv_backend.py
│           └── service/            # 服务基类
│               └── base.py
├── tests/
├── pyproject.toml
└── README.md
```

## 🚀 安装

### 基础安装

```bash
pip install isage-platform
```

### 开发安装

```bash
cd packages/sage-platform
pip install -e .
```

### 安装可选依赖

```bash
# 安装 Ray 支持（分布式队列）
pip install isage-platform[ray]

# 安装 Redis 支持（分布式存储）
pip install isage-platform[redis]

# 完整安装
pip install isage-platform[all]
```

## 📖 快速开始

### 使用队列

```python
from sage.platform.queue import RayQueueDescriptor

# 创建分布式队列
queue_desc = RayQueueDescriptor(maxsize=1000, queue_id="my_distributed_queue")

# 生产者
queue_desc.put({"task": "process_data", "data": [1, 2, 3]})

# 消费者
task = queue_desc.get()
print(f"处理中: {task}")

# 检查队列状态
print(f"队列大小: {queue_desc.qsize()}")
print(f"是否为空: {queue_desc.empty()}")
```

### 使用存储

```python
from sage.platform.storage.kv_backend import DictKVBackend

# 创建存储后端
storage = DictKVBackend()

# 存储数据
storage.set("user:1", {"name": "Alice", "age": 30})
storage.set("user:2", {"name": "Bob", "age": 25})

# 检索数据
user = storage.get("user:1")
print(f"用户: {user}")

# 列出所有键
keys = storage.get_all_keys()
print(f"所有键: {keys}")

# 持久化到磁盘
storage.store_data_to_disk("storage.pkl")
```

### 创建服务

```python
from sage.platform.service import BaseService


class DataProcessingService(BaseService):
    def __init__(self, config):
        super().__init__(name="data_processing")
        self.config = config
        self.initialize()

    def initialize(self):
        """初始化服务资源"""
        self.logger.info(f"初始化 {self.name}")

    def process(self, request):
        """处理传入请求"""
        self.logger.debug(f"处理请求: {request}")
        result = self._transform_data(request["data"])
        return {"status": "success", "result": result}

    def _transform_data(self, data):
        # 服务逻辑
        return [x * 2 for x in data]


# 使用服务
service = DataProcessingService({"param": "value"})
result = service.process({"data": [1, 2, 3]})
print(result)  # {"status": "success", "result": [2, 4, 6]}
```

## 🔧 配置

服务可以通过环境变量或配置文件进行配置：

```yaml
# platform_config.yaml
platform:
  queue:
    backend: ray  # 或 python, rpc
    maxsize: 1000

  storage:
    backend: dict  # 或 redis
    persist: true
    save_path: ./storage
```

## 架构位置

```
L1: sage-common         ← 基础层
L2: sage-platform       ← 当前层
L3: sage-kernel         ← 执行引擎
    sage-libs
L4: sage-middleware     ← 领域组件
L5: sage-cli            ← 命令行接口
    sage-tools          ← 开发工具
```

**独立仓库** (不在 SAGE 核心架构中):

- sage-benchmark - 基准测试
- sage-examples - 应用示例
- sage-studio - Web UI
- sageLLM - LLM 推理引擎

## 设计原则

1. **通用基础设施**：平台服务不是 SAGE 特定的
1. **后端无关**：支持多种实现（Python、Ray、Redis 等）
1. **最小依赖**：仅依赖 `sage-common`
1. **可扩展性**：易于添加新后端

## 为什么需要 L2 层？

原本这些抽象被分散在：

- Queue Descriptor 在 `sage-kernel` (L3) ✖️
- KV Backend 在 `sage-middleware` (L4) ✖️
- BaseService 在 `sage-kernel` (L3) ✖️

这造成了：

- 架构混乱（基础设施与业务逻辑混合）
- 依赖违规（L1 → L3）
- 有限的可重用性

通过创建 L2：

- ✅ 清晰的关注点分离
- ✅ 正确的依赖方向
- ✅ 更好的组件间可重用性

## 🧪 测试

```bash
# 运行单元测试
pytest tests/unit

# 运行集成测试
pytest tests/integration

# 运行覆盖率测试
pytest --cov=sage.platform --cov-report=html
```

## 📚 文档

- **用户指南**：查看 [docs-public](https://intellistream.github.io/SAGE-Pub/guides/packages/sage-platform/)
- **API 参考**：查看包的文档字符串和类型提示
- **架构**：查看
  [平台层设计](https://intellistream.github.io/SAGE-Pub/concepts/architecture/design-decisions/l2-platform-layer/)

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](../../CONTRIBUTING.md) 了解指南。

## 📄 许可证

该项目采用 MIT 许可证 - 详情请查看 [LICENSE](../../LICENSE) 文件。

## 🔗 相关包

- **sage-common**：基础层 (L1) - 提供基本工具
- **sage-kernel**：执行引擎 (L3) - 使用平台抽象
- **sage-middleware**：服务层 (L4) - 使用存储和队列
- **sage-libs**：库层 (L5) - 使用所有平台服务

## 📮 支持

- **文档**：https://intellistream.github.io/SAGE-Pub/
- **问题反馈**：https://github.com/intellistream/SAGE/issues
- **讨论**：https://github.com/intellistream/SAGE/discussions

______________________________________________________________________

**SAGE 框架的一部分** | [主仓库](https://github.com/intellistream/SAGE)
