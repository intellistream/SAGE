# 阶段 1: 核心数据类型与消息系统

## 1.1 多模态消息体设计 (Message)
参考 `flow_old/include/common/data_types.h` 中的 `VectorRecord` 和 `VectorData` 设计理念，在 sage_flow 中实现全新的AI原生消息类型：

### 目标：
- [x] 设计新的 `MultiModalMessage` 类，支持文本、图像、音频等数据类型
- [x] 实现新的 `VectorData` 结构，原生支持 `numpy.ndarray` 类型的 Embedding
- [x] 添加元数据管理（ID、时间戳、来源、相似度得分、检索上下文等）
- [ ] ~~实现高效的序列化/反序列化机制，支持 Protocol Buffers~~ (跳过)
- [x] 与 `sage_core` 中的 Packet 数据结构兼容，确保可通过 DataStream API 传递
- [x] 支持数据血缘追踪和处理链路记录

### 核心类型设计：
```python
from typing import Dict, Any, Optional, Union, List
import numpy as np

class MultiModalMessage:
    """参考 flow_old VectorRecord 设计的多模态消息，兼容 sage_core Packet 协议"""
    uid: int                              # 参考原有 uid_ 字段设计
    timestamp: int                        # 参考原有 timestamp_ 字段设计
    content: Union[str, np.ndarray, bytes]  # 原始内容
    embedding: Optional[np.ndarray]       # 向量嵌入，与 sage_vector 兼容
    metadata: Dict[str, Any]              # 扩展元数据，支持 sage_memory 索引
    context: Optional[List['RetrievalContext']]  # RAG检索上下文
    processing_trace: List[str]           # 数据处理血缘，用于调试和监控
    quality_score: Optional[float]       # 数据质量评分
```

### 与SAGE框架集成要求：
- [ ] 实现与 `sage_core.api.datastream.DataStream` 的兼容接口
- [ ] 支持通过 `env.from_source()` 和 `.map()` 链式调用
- [ ] 确保消息可被 `sage_runtime` 正确调度和传输
- [ ] 提供 `sage_memory` 所需的向量存储格式

## 1.2 向量数据类型设计
参考 `flow_old/include/common/data_types.h` 中的 `VectorData` 设计思路，实现AI优化的新向量类型：

### 目标：
- [ ] 设计新的 `VectorData` 支持更多数据类型（Float16, BFloat16, Int8 量化）
- [ ] 实现向量相似度计算接口（余弦、欧几里得、点积）
- [ ] 支持稀疏向量类型和混合精度
- [ ] C++ 后端通过 pybind11 优化向量运算，参考 py_candy_pybind11.cpp 的设计模式
- [ ] 与 numpy.ndarray 的零拷贝转换机制
