# L3: Kernel - 核心引擎层示例

> 对应 SAGE 包：`sage-kernel`

## 📖 层级说明

**Kernel** 层是 SAGE 的核心引擎，提供：

- 流处理 API (DataStream)
- 批处理 API (Batch)
- 操作符系统 (Operators)
- 函数系统 (Functions)
- 运行时环境 (Runtime)

## 📚 目录结构

```
L3-kernel/
├── batch/              # 批处理示例
├── stream/             # 流处理示例
├── operators/          # 操作符示例
├── functions/          # 函数示例
└── advanced/           # 高级特性
    └── fault_tolerance/  # 容错机制
```

## 🎯 学习路径

### 1️⃣ 批处理基础 (`batch/`)

从批处理开始，理解数据处理的基本概念：

- `hello_local_batch.py` - 本地批处理
- `hello_remote_batch.py` - 远程批处理
- `hello_batch_operator_examples.py` - 批处理操作符

### 2️⃣ 流处理基础 (`stream/`)

进入流处理的世界：

- `hello_streaming_world.py` - 基础流处理
- `hello_onebyone_world.py` - 单条数据流
- `hello_connected_stream_example.py` - 连接流

### 3️⃣ 操作符系统 (`operators/`)

掌握核心操作符：

- `hello_comap_world.py` - CoMap 操作符
- `hello_filter_world.py` - Filter 过滤
- `hello_flatmap_world.py` - FlatMap 展开
- `hello_join_world.py` - Join 连接
- `hello_three_input_comap.py` - 多输入 CoMap

### 4️⃣ 函数系统 (`functions/`)

理解函数抽象：

- `hello_comap_function_example.py` - 函数版 CoMap
- `hello_comap_lambda_example.py` - Lambda 版本
- `hello_wordcount_*.py` - WordCount 系列示例

### 5️⃣ 高级特性 (`advanced/`)

探索高级功能：

- `hello_future_world.py` - Future 异步处理
- `hello_realistic_service_example.py` - 实际服务示例
- `fault_tolerance/` - 容错和检查点

## 🎯 学习目标

完成本层示例后，你将掌握：

1. SAGE 的核心 API 和编程模型
1. 批处理和流处理的差异
1. 各种操作符的使用场景
1. 如何构建数据处理管道

## ⏭️ 下一步

学完内核层后，继续学习：

- **L3-libs/** - 算法库和工具（同层级）
- **L4-middleware/** - 中间件和领域算子
