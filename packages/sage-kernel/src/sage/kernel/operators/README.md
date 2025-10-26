# SAGE Kernel Operators

基础算子层 - 为数据流处理提供基础算子类型。

## 算子类型

### BaseOperator (BaseFunction)

所有算子的基类，定义了算子的核心接口：

- 运行时上下文管理
- 日志记录
- 服务调用
- 状态序列化

### MapOperator (MapFunction)

一对一映射算子 - 接收一个输入，产生一个输出。

```python
from sage.kernel.operators import MapOperator


class MyTransform(MapOperator):
    def execute(self, data):
        return data * 2
```

### FilterOperator (FilterFunction)

过滤算子 - 根据条件决定是否保留数据。

```python
from sage.kernel.operators import FilterOperator


class MyFilter(FilterOperator):
    def execute(self, data):
        return data > 0
```

### FlatMapOperator (FlatMapFunction)

一对多映射算子 - 接收一个输入，产生零个或多个输出。

```python
from sage.kernel.operators import FlatMapOperator


class MySplitter(FlatMapOperator):
    def execute(self, data, collector):
        for item in data.split(","):
            collector.collect(item)
```

## 设计原则

1. **不依赖业务逻辑**: 基础算子只提供通用的数据流转换能力
1. **可组合**: 算子可以链式组合构建复杂流水线
1. **可扩展**: 上层可以继承这些基础算子实现业务逻辑

## 层次关系

```
sage-kernel/operators/        ← 基础算子（本层）
         ↓ 被继承
sage-middleware/operators/    ← 领域算子（业务实现）
```

领域算子（如 VLLMGenerator、DenseRetriever）应该在 middleware 层实现。
