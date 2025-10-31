# L4: Middleware - 中间件层示例

> 对应 SAGE 包：`sage-middleware`

## 📖 层级说明

**Middleware** 层提供领域算子和中间件组件：

- Memory Service - 内存管理服务
- SAGE-DB - 向量数据库
- SAGE-TSDB - 时序数据库
- NeuroMem - 神经记忆栈

## 📚 目录结构

```
L4-middleware/
├── hello_service_world.py  # 服务入门示例
├── memory_service/          # 内存服务示例
├── sage_db/                 # 向量数据库示例
└── sage_tsdb/               # 时序数据库示例
```

## 🎯 学习路径

### 1️⃣ 服务基础

- `hello_service_world.py` - 理解服务模型

### 2️⃣ Memory Service (`memory_service/`)

内存管理和持久化：

- `rag_memory_service.py` - RAG 内存服务
- `rag_memory_pipeline.py` - 内存管道
- `rag_memory_manager.py` - 内存管理器

### 3️⃣ SAGE-DB (`sage_db/`)

向量数据库操作：

- `workflow_demo.py` - 工作流演示

### 4️⃣ SAGE-TSDB (`sage_tsdb/`)

时序数据处理：

- `basic_dag_example.py` - 基础 DAG
- `advanced_dag_example.py` - 高级 DAG
- `stream_join_dag_example.py` - 流连接 DAG

## 🎯 学习目标

完成本层示例后，你将掌握：

1. 如何使用 SAGE 的数据服务
1. 向量数据库的基本操作
1. 时序数据的处理方法
1. 内存管理的最佳实践

## ⏭️ 下一步

学完中间件层后，继续学习：

- **L5-apps/** - 完整应用和解决方案
