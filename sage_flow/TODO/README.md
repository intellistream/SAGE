# SAGE Flow Framework 开发计划

参考 flow_old 架构设计，在 sage_flow 中实现专注于数据处理和向量化的流处理框架。

## 概述

**核心定位**：负责大数据范式的数据清理、信息提取和数据embedding，为整个SAGE生态提供高质量的向量化数据支持。注意，LLM推理和Agent逻辑由 sage_libs 负责，本模块专注于数据预处理阶段。

**算子完整性承诺**：确保flow_old中所有现有算子在新框架中100%实现，包括但不限于：
- **基础算子** (11个): SourceOperator, MapOperator, FilterOperator, JoinOperator, AggregateOperator, SinkOperator, TopKOperator, WindowOperator, OutputOperator, ITopKOperator等
- **索引算子** (6个): HNSWIndexOperator, IVFIndexOperator, BruteForceIndexOperator, KNNOperator, VectraFlowIndexOperator等  
- **函数体系** (5个): JoinFunction, AggregateFunction, SinkFunction, SourceFunction, Function基类等

**架构要求**：整个flow运行时核心必须使用C++17/20实现，Python仅用于与SAGE框架的接口交互层。

## 开发规范

### 核心原则
- **一个文件一个类**: 每个源代码文件只包含一个主要类定义
- **Google C++ Style Guide**: 严格遵循命名规范和代码风格  
- **现代C++**: 充分利用C++17/20特性，如constexpr、auto、智能指针等
- **静态分析**: 通过clang-tidy检查，零警告目标

### 设计约束
- 与 `sage_core.api.env.LocalEnvironment` 和 `RemoteEnvironment` 兼容
- 通过 DataStream API 提供统一的流処理接口
- 支持 `sage_runtime` 本地和分布式执行
- 与 `sage_memory` 协同提供向量检索能力
- **功能等价保证**: 新框架必须提供与flow_old完全等价的数据处理能力

详细规范请参考：[coding-standards.md](coding-standards.md)

## 文档结构

### 开发阶段文档
1. **[api-requirements.md](api-requirements.md)** - Python API核心要求与SAGE生态系统兼容性
2. **[phase1-core-types.md](phase1-core-types.md)** - 阶段1：核心数据类型与消息系统
3. **[phase2-stream-engine.md](phase2-stream-engine.md)** - 阶段2：流处理核心引擎
4. **[phase3-data-processing.md](phase3-data-processing.md)** - 阶段3：数据处理与向量化支持
5. **[phase4-optimization.md](phase4-optimization.md)** - 阶段4：流处理优化与集成
6. **[phase6-integration.md](phase6-integration.md)** - 阶段6：SAGE框架深度集成与协作

### 实施记录文档
- **[coding-standards.md](coding-standards.md)** - 详细的代码组织规范与约束
- **[refactoring-data-sources.md](refactoring-data-sources.md)** - 数据源架构重构任务完整记录

## 当前状态

### ✅ 已完成项目
- **数据源架构重构**: 成功实现"一个文件一个类"组织原则，借鉴SAGE设计模式
- **MultiModalMessage系统**: 多模态消息处理框架
- **基础索引系统**: BruteForceIndex, HNSW, IVF索引实现
- **内存管理**: MemoryPool接口和SimpleMemoryPool实现
- **环境系统**: SageFlowEnvironment生命周期管理

### 🔄 进行中项目
根据具体开发进度更新...

### 📋 待办事项
根据phase文档中的具体任务规划...
