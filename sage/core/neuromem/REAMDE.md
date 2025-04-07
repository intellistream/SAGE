# Neuromem Module / Neuromem 模块

A flexible memory management system with STM, LTM and DCM capabilities.  
一个具有短期记忆(STM)、长期记忆(LTM)和动态上下文记忆(DCM)功能的灵活内存管理系统。

- test/测试(SAGE目录下)：

```
python -m sage.core.neuromem.mem_test.mem_test
```

## Core Features / 核心功能

- **Unified Memory API** for different memory types  
  **统一内存接口** 支持不同类型的内存

- **Multiple Storage Backends** (FAISS, Candy, etc.)  
  **多种存储后端** (FAISS, Candy 等)

- **Embedding Integration** with built-in model support  
  **嵌入集成** 内置模型支持

## Quick Start / 快速开始

```python
# Initialize memory manager / 初始化内存管理器
manager = NeuronMemManager()

# Create memory collection / 创建内存集合
collection = MemoryCollection("facts", embedding_model)

# Store information / 存储信息
collection.store("New data")

# Retrieve information / 检索信息
results = collection.retrieve("query")
```

## Directory Structure / 目录结构

```
neuromem/
├── memory_manager.py       # Main manager class / 主管理类
├── memory_collection.py    # Memory operations / 内存操作
└── storage_engine/         # Backend implementations / 后端实现
```

For detailed usage see examples in mem_test/  
详细用法请参考 mem_test/ 中的示例