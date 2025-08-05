# Function 模块

该模块定义了 Sage Core 中的所有数据处理函数，是数据流操作的核心实现层。

## 核心组件

### 基础框架
- **`base_function.py`**: 所有函数的抽象基类
  - 定义函数执行接口
  - 提供运行时上下文管理
  - 支持服务调用和状态持久化

### 数据源函数
- **`source_function.py`**: 数据源基类，定义数据输入接口
- **`kafka_source.py`**: Kafka 数据源实现
  - 支持多分区消费
  - 提供偏移管理
  - 处理消息序列化

### 数据转换函数
- **`map_function.py`**: 一对一数据映射转换
- **`filter_function.py`**: 数据过滤操作
- **`flatmap_function.py`**: 一对多扁平化映射
- **`keyby_function.py`**: 键分组操作
- **`join_function.py`**: 流连接操作
- **`comap_function.py`**: 协同映射操作

### 数据输出函数
- **`sink_function.py`**: 数据输出基类
- **`flatmap_collector.py`**: 扁平化输出收集器

### 特殊功能函数
- **`batch_function.py`**: 批处理函数基类
- **`simple_batch_function.py`**: 简化批处理实现
- **`future_function.py`**: 异步操作支持
- **`lambda_function.py`**: Lambda 表达式包装器

## 子模块

### [tests/](./tests/)
包含各种函数的单元测试，验证功能正确性和性能。

## 函数类型体系

```
BaseFunction (抽象基类)
├── SourceFunction (数据源)
│   └── KafkaSourceFunction
├── MapFunction (转换操作)
├── FilterFunction (过滤操作)  
├── FlatMapFunction (扁平化映射)
├── KeyByFunction (键分组)
├── BaseJoinFunction (连接操作)
├── BaseCoMapFunction (协同映射)
├── SinkFunction (数据输出)
└── BatchFunction (批处理)
    └── SimpleBatchIteratorFunction
```

## 使用模式

### 自定义函数实现
```python
from sage.api.function.base_function import BaseFunction

class MyMapFunction(BaseFunction):
    def apply(self, data):
        # 实现数据转换逻辑
        return transformed_data
```

### Lambda 函数支持
```python
# 使用 lambda 表达式
stream.map(lambda x: x * 2)

# 自动包装为 LambdaFunction
```

## 设计原则

- **类型安全**: 强类型接口设计
- **可扩展性**: 易于添加新的函数类型
- **性能优化**: 支持批处理和异步操作
- **状态管理**: 内置状态持久化支持
