# Memory API Documentation

## Overview
This API provides interfaces for memory management and operations in the Sage system.

## API Reference

### `init_default_manager() -> NeuronMemManager`
Initializes the global default manager  
初始化全局默认管理器

### `get_default_manager() -> NeuronMemManager`
Gets the global default manager (must be initialized first)  
获取全局默认管理器（需要先初始化）

**Raises**:  
`RuntimeError` if default manager is not initialized  
如果默认管理器未初始化则抛出运行时错误

### `create_table(memory_table_name: str, manager: NeuronMemManager, embedding_model=default_model, memory_table_backend: str | None = None) -> MemoryCollection`
Creates a new memory table  
创建新的记忆表

Parameters:  
- `memory_table_name`: Name of the memory table  
  记忆表名称
- `manager`: Memory manager instance  
  内存管理器实例
- `embedding_model`: Embedding model to use (default: default_model)  
  使用的嵌入模型（默认：default_model）
- `memory_table_backend`: Backend storage type  
  后端存储类型

### `connect(manager: NeuronMemManager, *memory_names: str) -> CompositeMemory`
Connects to one or more registered memory collections  
连接到一个或多个已注册的记忆集合

**CompositeMemory Operations**:  
- `retrieve(raw_data: str, retrieve_func=None)`: Retrieves data from all connected memories  
  从所有连接的记忆中检索数据
- `store(raw_data: str, write_func=None)`: Stores data to all connected memories  
  存储数据到所有连接的记忆
- `flush_kv_to_vdb(kv, vdb)`: Transfers data from KV to VDB storage  
  将数据从KV存储转移到VDB存储

## Example Usage
```python
# Initialize manager
manager = init_default_manager()

# Create memory table
memory = create_table("my_memory", manager)

# Connect to multiple memories
composite = connect(manager, "memory1", "memory2")

# Store and retrieve data
composite.store("sample data")
results = composite.retrieve("query")
```

## 示例用法
```python
# 初始化管理器
manager = init_default_manager()

# 创建记忆表
memory = create_table("my_memory", manager)

# 连接到多个记忆
composite = connect(manager, "memory1", "memory2")

# 存储和检索数据
composite.store("示例数据")
results = composite.retrieve("查询")