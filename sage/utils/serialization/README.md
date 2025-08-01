# SAGE 序列化模块

本模块提供统一的序列化接口，支持多种序列化方式，确保SAGE框架中对象的正确序列化和反序列化。

## 概述

序列化模块为SAGE框架提供通用的对象序列化能力，特别针对分布式环境下的对象传输和持久化需求。

## 核心组件

### `universal_serializer.py`
通用序列化器，提供自动选择最佳序列化方式的智能接口：
- 自动检测对象类型
- 根据对象特性选择合适的序列化方法
- 提供统一的序列化/反序列化API
- 支持序列化失败时的降级策略

### `dill_serializer.py`
基于Dill库的高级序列化器：
- 支持复杂Python对象序列化（函数、类、lambda等）
- 适用于需要序列化代码逻辑的场景
- 提供更强的序列化兼容性

## 主要特性

- **智能选择**: 根据对象类型自动选择最优序列化方法
- **兼容性**: 支持标准库pickle无法序列化的复杂对象
- **降级处理**: 序列化失败时提供备选方案
- **性能优化**: 在保证兼容性的前提下优化序列化性能

## 使用场景

- **分布式计算**: Ray等框架中的对象传输
- **任务序列化**: 用户函数和算子的序列化传输
- **状态持久化**: 运行时状态的保存和恢复
- **缓存机制**: 复杂对象的序列化缓存

## 快速开始

```python
from sage.utils.serialization.universal_serializer import UniversalSerializer

# 创建序列化器
serializer = UniversalSerializer()

# 序列化对象
data = {"key": "value", "function": lambda x: x + 1}
serialized = serializer.serialize(data)

# 反序列化对象
restored = serializer.deserialize(serialized)

# 使用Dill序列化器
from sage.utils.serialization.dill_serializer import DillSerializer

dill_serializer = DillSerializer()
serialized = dill_serializer.serialize(data)
restored = dill_serializer.deserialize(serialized)
```

## 设计原则

1. **通用性**: 支持尽可能多的Python对象类型
2. **可靠性**: 提供错误处理和降级机制
3. **性能**: 在兼容性和性能之间找到平衡
4. **易用性**: 提供简单统一的API接口
