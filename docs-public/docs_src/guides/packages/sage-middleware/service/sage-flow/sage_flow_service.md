# SageFlowService - 流式处理微服务

## 概述

`SageFlowService` 是 SAGE-Flow 流式处理引擎的轻量级微服务封装。它提供了一个简单的 API，用于将向量数据推送到流处理管道，并实时获取处理结果。

______________________________________________________________________

## 架构设计

### 层级定位

```
L4: sage-middleware
    └── components/sage_flow/python/micro_service/
        └── sage_flow_service.py   # SageFlowService
```

### 核心组件

```
┌─────────────────────────────────────────────────────┐
│                 SageFlowService                      │
├─────────────────────────────────────────────────────┤
│  push(uid, vec)  ──► Queue ──► StreamSource         │
│                              ──► StreamEnvironment  │
│                              ──► Sink (callback)    │
│  run()           ──► execute()                      │
└─────────────────────────────────────────────────────┘
```

______________________________________________________________________

## 快速开始

### 基本用法

```python
import numpy as np
from sage.middleware.components.sage_flow.python.micro_service import SageFlowService

# 创建服务实例（4维向量）
service = SageFlowService(dim=4, dtype="Float32")

# 设置结果回调
def on_result(uid: int, ts: int):
    print(f"处理完成: uid={uid}, timestamp={ts}")

service.set_sink(on_result, name="my_sink")

# 推送向量数据
for i in range(10):
    vec = np.random.rand(4).astype(np.float32)
    service.push(uid=i, vec=vec)

# 执行处理
service.run()
```

______________________________________________________________________

## API 参考

### SageFlowService

```python
class SageFlowService:
    def __init__(self, dim: int = 4, dtype: str = "Float32") -> None:
        """初始化流处理服务。

        Args:
            dim: 向量维度
            dtype: 数据类型 ("Float32", "Float64" 等)
        """

    def push(self, uid: int, vec: np.ndarray) -> None:
        """推送向量到处理队列。

        Args:
            uid: 唯一标识符
            vec: numpy 向量（必须匹配 dim 维度）

        Raises:
            ValueError: 向量维度不匹配时抛出
        """

    def run(self) -> None:
        """执行流处理。

        从队列中取出所有待处理数据，送入流处理管道执行一次。
        """

    def set_sink(self, callback: Callable[[int, int], None], name: str = "py_sink") -> None:
        """设置结果回调。

        Args:
            callback: 回调函数，接收 (uid, timestamp) 参数
            name: Sink 名称
        """

    @property
    def env(self) -> StreamEnvironment:
        """获取底层 StreamEnvironment（高级用法）。"""
```

______________________________________________________________________

## 使用场景

### 1. 实时向量处理

```python
# 场景：实时处理 embedding 向量
service = SageFlowService(dim=768)

def process_embedding(uid, ts):
    # 处理完成后的逻辑
    save_to_database(uid, ts)

service.set_sink(process_embedding)

# 持续推送数据
while True:
    embedding = model.encode(get_next_text())
    service.push(uid=generate_uid(), vec=embedding)
    service.run()
```

### 2. 批量数据处理

```python
# 场景：批量处理文档向量
service = SageFlowService(dim=384)

results = []

def collect_result(uid, ts):
    results.append({"uid": uid, "processed_at": ts})

service.set_sink(collect_result)

# 批量推送
for doc_id, vector in documents:
    service.push(uid=doc_id, vec=vector)

# 一次性执行
service.run()

print(f"处理完成: {len(results)} 条记录")
```

### 3. 与 Pipeline 集成

```python
# 高级用法：直接访问 StreamEnvironment
service = SageFlowService(dim=4)
env = service.env

# 添加自定义算子
from sage.middleware.components.sage_flow.python import FilterOperator

# 构建复杂流处理图
# ... (使用 env 的 API)
```

______________________________________________________________________

## 内部机制

### 数据流

```
1. push(uid, vec)
   │
   ▼
2. Queue (线程安全)
   │
   ▼
3. run() 调用
   │
   ▼
4. SimpleStreamSource.addRecord(uid, ts, vec)
   │
   ▼
5. StreamEnvironment.execute()
   │
   ▼
6. Sink callback(uid, ts)
```

### 线程安全

- `push()` 方法是线程安全的，可从多个线程调用
- `run()` 方法会获取锁，确保同一时间只有一个执行
- Queue 使用 Python 标准库的线程安全队列

______________________________________________________________________

## 最佳实践

1. **维度一致性**：确保所有推送的向量维度与初始化时的 `dim` 匹配
1. **类型转换**：向量会自动转换为 `float32`，但建议预先转换以提高效率
1. **批量处理**：对于大量数据，先批量 `push()` 再调用一次 `run()` 更高效
1. **错误处理**：在 sink 回调中处理可能的异常
1. **资源管理**：长期运行的服务应定期检查队列大小

______________________________________________________________________

## 与 SAGE-Flow 的关系

`SageFlowService` 是 SAGE-Flow C++ 流处理引擎的 Python 封装：

| 组件                | 层级 | 功能              |
| ------------------- | ---- | ----------------- |
| SAGE-Flow C++       | L4   | 高性能流处理引擎  |
| SimpleStreamSource  | L4   | Python 数据源包装 |
| StreamEnvironment   | L4   | 执行环境          |
| **SageFlowService** | L4   | 微服务封装        |

______________________________________________________________________

## 相关文档

- [SAGE-Flow 概览](./README.md)
- [StreamEnvironment API](./stream_environment.md)
- [流处理算子](../../operators/stream_operators.md)
