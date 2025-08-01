# API 模块

该模块是 Sage Core 的 API 层，提供用户友好的接口来构建和配置数据流管道。

## 核心组件

### 环境管理
- **`base_environment.py`**: 执行环境基类，定义管道执行的基础框架
- **`local_environment.py`**: 本地执行环境，用于单机模式的管道执行
- **`remote_environment.py`**: 远程执行环境，支持分布式集群执行

### 数据流抽象
- **`datastream.py`**: 数据流核心类，提供链式操作API
  - 支持 `map()`, `filter()`, `flatmap()` 等转换操作
  - 提供 `keyBy()`, `connect()`, `sink()` 等路由和输出操作
  - 基于泛型的类型安全设计

### 连接流管理
- **`connected_streams.py`**: 管理多个数据流的连接和协同处理
  - 支持多流连接操作
  - 提供协同映射（CoMap）功能
  - 处理流间的同步和协调

## 子模块

### [test/](./test/)
包含 API 层的测试文件，主要测试远程环境和序列化功能。

## 使用示例

```python
from sage.core.api.local_environment import LocalEnvironment

# 创建本地环境
env = LocalEnvironment()

# 创建数据流管道（使用正确的API）
stream = env.from_batch_collection([1, 2, 3, 4, 5])
result = stream.map(lambda x: x * 2).sink(lambda x: print(f"Result: {x}"))

# 提交管道执行
env.submit()
```

## 设计特点

- **声明式API**: 用户通过链式调用描述数据处理逻辑
- **类型安全**: 基于 Python 泛型提供编译时类型检查
- **环境抽象**: 统一的本地和远程环境接口
- **延迟执行**: 构建阶段只定义计算图，调用 `submit()` 时才开始执行
