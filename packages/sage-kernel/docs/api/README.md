# SAGE Kernel API 模块

SAGE Kernel API 模块为流数据处理提供了简洁而强大的编程接口。采用声明式编程范式，让开发者能够专注于业务逻辑而不是底层实现细节。

## 📋 API 模块概览

```
sage.kernel.api/
├── __init__.py              # API 主入口，导出所有公共接口
├── base_environment.py      # 环境基类，定义通用接口
├── local_environment.py     # 本地环境实现
├── remote_environment.py    # 远程/分布式环境实现
├── datastream.py           # 数据流核心类
├── connected_streams.py     # 连接流管理
└── function/               # 函数接口目录
    ├── __init__.py
    ├── base_function.py     # 函数基类
    ├── map_function.py      # Map函数
    ├── filter_function.py   # Filter函数
    ├── sink_function.py     # Sink函数
    ├── source_function.py   # Source函数
    ├── keyby_function.py    # KeyBy函数
    ├── flatmap_function.py  # FlatMap函数
    ├── comap_function.py    # CoMap函数
    └── join_function.py     # Join函数
```

## 🎯 核心组件

### 1. 环境管理 (Environments)
- **BaseEnvironment**: 环境抽象基类
- **LocalEnvironment**: 本地单机环境
- **RemoteEnvironment**: 分布式集群环境

### 2. 数据流处理 (DataStreams)
- **DataStream**: 核心数据流类，支持链式操作
- **ConnectedStreams**: 多流连接和协同处理

### 3. 函数接口 (Functions)
- **转换函数**: Map, FlatMap, Filter等
- **路由函数**: KeyBy, Partition等
- **输出函数**: Sink, Print等
- **连接函数**: Join, CoMap等

## 🔄 典型工作流程

```python
# 1. 创建环境
env = LocalEnvironment("my_app")

# 2. 创建数据源
stream = env.from_batch([1, 2, 3, 4, 5])

# 3. 数据转换 (构建计算图)
result = (stream
    .map(lambda x: x * 2)
    .filter(lambda x: x > 5)
    .sink(print))

# 4. 提交执行
env.submit()
```

## 📚 详细文档

- [**环境管理**](environments.md) - 创建和管理执行环境
- [**数据流处理**](datastreams.md) - 数据流操作和转换  
- [**函数接口**](functions.md) - 用户自定义函数规范
- [**连接流**](connected-streams.md) - 多流连接和协同处理

## 🌟 设计特性

### 类型安全
```python
from typing import TypeVar

T = TypeVar('T')
U = TypeVar('U')

class DataStream(Generic[T]):
    def map(self, func: Callable[[T], U]) -> DataStream[U]:
        # 编译时类型检查
        pass
```

### 延迟执行
```python
# 构建阶段 - 只创建计算图，不执行
stream = env.from_kafka("topic").map(process).sink(output)

# 执行阶段 - 调用submit()时才开始处理数据
env.submit()
```

### 链式调用
```python
# 支持流畅的链式API
result = (data_stream
    .map(transform1)
    .filter(condition)
    .map(transform2)
    .sink(output))
```

## 🔌 扩展机制

### 自定义函数
```python
class MyMapFunction(MapFunction[int, str]):
    def map(self, value: int) -> str:
        return f"Value: {value}"

stream.map(MyMapFunction())
```

### 自定义数据源
```python
class MySourceFunction(SourceFunction[dict]):
    def run(self, ctx: SourceContext[dict]):
        # 自定义数据源逻辑
        pass

stream = env.add_source(MySourceFunction())
```

## 📖 最佳实践

1. **环境隔离**: 不同应用使用独立环境
2. **资源管理**: 及时关闭环境释放资源
3. **错误处理**: 实现适当的错误处理逻辑
4. **性能优化**: 合理设置并行度和缓冲区大小
5. **类型注解**: 使用类型注解提高代码可读性

## 🚀 快速开始

查看 [快速开始指南](../guides/quickstart.md) 了解如何快速上手 SAGE Kernel API。
