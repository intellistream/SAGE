# SAGE Flow Framework 开发计划

参考 flow_old 架构设计，在 sage_flow 中实现专注于数据处理和向量化的流处理框架。

## 概述

**核心定位**：负责大数据范式的数据清理、信息提取和数据embedding，为整个SAGE生态提供高质量的向量化数据支持。注意，LLM推理和Agent逻辑由 sage_libs 负责，本模块专注于数据预处理阶段。

**算子完整性承诺**：确保flow_old中所有现有算子在新框架中100%实现，包括但不限于：
- **基础算子** (11个): SourceOperator, MapOperator, FilterOperator, JoinOperator, AggregateOperator, SinkOperator, TopKOperator, WindowOperator, OutputOperator, ITopKOperator等
- **索引算子** (6个): HNSWIndexOperator, IVFIndexOperator, BruteForceIndexOperator, KNNOperator, VectraFlowIndexOperator等  
- **函数体系** (5个): JoinFunction, AggregateFunction, SinkFunction, SourceFunction, Function基类等

**架构要求**：整个flow运行时核心必须使用C++17/20实现，Python仅用于与SAGE框架的接口交互层。

## 规范与约束

**代码规范要求**：
- **严格遵循 Google C++ Style Guide**: 类名使用CamelCase，方法名使用camelBack，成员变量使用lower_case_后缀
- **通过 clang-tidy 检查**: 必须满足现有 .clang-tidy 配置要求，包括google-*、modernize-*、performance-*等规则组
- **代码质量标准**: 所有C++代码必须通过静态分析，零警告错误目标
- **现代C++特性**: 充分利用C++17/20特性，如constexpr、auto、智能指针等
- **文件组织规范**: 
  - **一个文件一个类原则**: 每个源代码文件(.cpp/.h)只允许存放一个主要的class或struct定义
  - **例外情况**: 仅允许在同一文件中包含与主类紧密相关的小型辅助类（如内部使用的配置结构体、枚举类等）
  - **命名一致性**: 文件名应与主要类名保持一致，如`DataSource`类对应`data_source.h`和`data_source.cpp`
  - **模块化目标**: 确保代码模块化和可维护性，便于单元测试和依赖管理

**设计约束**：
- 必须与 `sage_core.api.env.LocalEnvironment` 和 `RemoteEnvironment` 兼容
- 通过 DataStream API 提供统一的流処理接口
- 支持 `sage_runtime` 本地和分布式执行
- 与 `sage_memory` 协同提供向量检索能力
- **功能等价保证**: 新框架必须提供与flow_old完全等价的数据处理能力

## 文档结构

本开发计划已拆分为以下文件：

1. **[api-requirements.md](api-requirements.md)** - Python API核心要求与SAGE生态系统兼容性
2. **[phase1-core-types.md](phase1-core-types.md)** - 阶段1：核心数据类型与消息系统
3. **[phase2-stream-engine.md](phase2-stream-engine.md)** - 阶段2：流处理核心引擎
4. **[phase3-data-processing.md](phase3-data-processing.md)** - 阶段3：数据处理与向量化支持
5. **[phase4-optimization.md](phase4-optimization.md)** - 阶段4：流处理优化与集成
6. **[phase6-integration.md](phase6-integration.md)** - 阶段6：SAGE框架深度集成与协作

每个文件包含相应阶段的详细实现要求、代码示例和技术规范。

## 当前重构任务

### 数据源架构重构 (按照一个文件一个类原则)

**任务目标**: 将`include/sources/data_source.h`按照新的文件组织规范进行重构，遵循SAGE框架的分层设计。

**具体步骤**:

1. **重新组织基础文件**:
   - `include/sources/data_source.h` - 仅包含`DataSource`抽象基类和`DataSourceConfig`结构体
   - `include/sources/data_source_factory.h` - 独立的工厂函数声明

2. **创建具体实现文件** (每个类一个文件):
   - `include/sources/file_data_source.h` + `src/sources/file_data_source.cpp` - 文件数据源实现
   - `include/sources/stream_data_source.h` + `src/sources/stream_data_source.cpp` - 流数据源实现  
   - `include/sources/kafka_data_source.h` + `src/sources/kafka_data_source.cpp` - Kafka数据源实现
   - `src/sources/data_source_factory.cpp` - 工厂函数实现

3. **借鉴SAGE Python实现的设计模式**:
   - **延迟初始化**: 支持分布式序列化，在实际执行时才创建资源连接
   - **状态管理**: 维护读取位置和连接状态，支持断点续读
   - **背压处理**: 实现缓冲区管理和资源控制机制
   - **资源清理**: 提供完整的生命周期管理和cleanup机制

4. **确保与SAGE生态系统兼容**:
   - 接口设计与Python的`SourceFunction`保持一致性
   - 支持配置驱动的数据源创建
   - 维护与`sage_core.api.env.BaseEnvironment`的集成模式

**验证标准**:
- [x] 所有源文件通过clang-tidy检查
- [x] 每个文件只包含一个主要类定义
- [x] 文件命名与类名保持一致
- [x] 功能完全等价于重构前的实现
- [x] 构建系统正确识别新的文件结构
- [x] 使用已有的MultiModalMessage类而不是重复定义Message类

**完成状态**: ✅ **已完成**

**重构结果**:
1. **基础架构重构完成**:
   - `include/sources/data_source.h` - 仅包含DataSource抽象基类和DataSourceConfig
   - `include/sources/data_source_factory.h` - 独立的工厂函数声明

2. **具体实现文件已创建**:
   - `include/sources/file_data_source.h` + `src/sources/file_data_source.cpp` - 文件数据源
   - `include/sources/stream_data_source.h` - 流数据源头文件 
   - `include/sources/kafka_data_source.h` - Kafka数据源头文件

3. **借鉴SAGE设计模式**:
   - ✅ 延迟初始化支持分布式环境
   - ✅ 状态管理和断点续读功能
   - ✅ 背压处理和缓冲区管理设计
   - ✅ 完整的生命周期管理和资源清理

4. **SAGE生态系统兼容性**:
   - ✅ 使用MultiModalMessage与现有消息系统集成
   - ✅ 配置驱动的数据源创建模式
   - ✅ 与DataStream API兼容的接口设计

---

## 总结

数据源架构重构已完成，成功实现了"一个文件一个类"的组织原则，并借鉴了SAGE Python实现的优秀设计模式。新的架构更加模块化、可维护，并完全兼容SAGE生态系统。