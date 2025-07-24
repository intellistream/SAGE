# 阶段 2: 流处理核心引擎

## 2.1 Python DataStream API集成
参考 `sage_examples` 中的实现模式，sage_flow必须提供与sage_core DataStream完全兼容的Python接口：

### Python API实现要求：
- [ ] **SageFlowEnvironment类**: 继承或兼容`sage_core.environment.BaseEnvironment`
  ```python
  from sage_flow.environment import SageFlowEnvironment
  
  env = SageFlowEnvironment("data_processing")
  env.set_memory(config=config.get("memory"))
  ```

- [ ] **数据源函数**: 实现sage_core兼容的数据源
  ```python
  from sage_flow.sources import FileDataSource, StreamDataSource, KafkaDataSource
  
  # 文件数据源 - 支持多格式(PDF, DOCX, TXT, CSV等)
  source_stream = env.from_source(FileDataSource, {
      "path": "/data/documents/",
      "format": "auto",  # 自动检测格式
      "recursive": True
  })
  ```

- [ ] **链式变换操作**: 支持标准DataStream API
  ```python
  from sage_flow.functions import (
      DocumentParserFunction, TextCleanerFunction, 
      EmbeddingGeneratorFunction, QualityAssessorFunction
  )
  
  processed_stream = (source_stream
      .map(DocumentParserFunction, config["parser"])     # 文档解析
      .map(TextCleanerFunction, config["cleaner"])       # 文本清理  
      .filter(lambda msg: msg.quality_score > 0.5)       # 质量过滤
      .map(EmbeddingGeneratorFunction, config["embedder"]) # 向量化
  )
  ```

- [ ] **输出和存储**: 集成sage_memory和外部系统
  ```python
  from sage_flow.sinks import VectorStoreSink, TerminalSink, FileSink
  
  # 向量存储输出
  processed_stream.sink(VectorStoreSink, {
      "collection_name": "processed_documents",
      "batch_size": 100,
      "update_index": True
  })
  ```

- [ ] **高级流操作**: 支持流连接、分组、窗口等
  ```python
  # 流连接 - 多数据源融合
  text_stream = env.from_source(FileDataSource, text_config)
  meta_stream = env.from_source(FileDataSource, meta_config)
  
  connected = text_stream.connect(meta_stream).map(
      JoinFunction, {"join_key": "document_id"}
  )
  
  # 窗口聚合 - 批处理优化
  windowed = connected.keyby(lambda x: x.category).window(
      size="10min", slide="5min"
  ).aggregate(AggregateFunction, {"operation": "quality_avg"})
  ```

### 与sage_examples模式兼容要求：
- [ ] 配置文件驱动: 支持YAML配置文件，与`sage_utils.config_loader`兼容
- [ ] 环境管理: 支持`env.submit()`, `env.close()`, `env.run_streaming()`
- [ ] 错误处理: 提供详细的错误信息和调试支持
- [ ] 日志集成: 与`sage_utils.logging_utils`和`CustomLogger`集成
- [ ] 内存管理: 支持`env.set_memory()`与sage_memory的集成

### C++后端集成：
- [ ] pybind11绑定: 所有Python API调用最终通过C++实现
- [ ] 零拷贝传输: Python和C++之间高效的数据传递
- [ ] 异步执行: 支持非阻塞的流处理执行
- [ ] 资源管理: 自动的内存和线程资源管理

## 2.2 Stream 抽象层
参考 `flow_old/include/stream/stream.h` 和 `flow_old/python/candyflow.py` 的设计模式，实现新的流处理能力：

### 目标：
- [ ] 设计新的 `AIStream` 类，原生支持多模态数据
- [ ] 集成向量流处理能力，支持 `MultiModalMessage` 数据类型
- [ ] 支持实时 Embedding 计算和索引更新
- [ ] 实现流状态管理和检查点机制
- [ ] 与 `sage_core` 中的 `BaseOperator` 接口兼容
- [ ] 支持背压机制和流控制，确保与 `sage_runtime` 调度器协调

### SAGE框架集成要求：
- [ ] 实现 `MapFunction` 和 `StatefulFunction` 基类
- [ ] 支持 LocalEnvironment 和 RemoteEnvironment 的统一调度
- [ ] 提供 `sage_frontend` 监控所需的实时指标接口
- [ ] 与 `sage_jobmanager` 的任务管理系统集成

## 2.3 完整算子系统实现
参考 `flow_old/include/function/function.h` 和 `flow_old/include/operator/` 的设计思路，结合 `sage_core/operator/` 结构：

### 基础算子实现要求（确保兼容性迁移）：
- [x] `SourceOperator` - 数据源算子，支持多种输入格式
- [x] `MapOperator` - 映射变换算子，一对一数据处理
- [x] `FilterOperator` - 过滤算子，基于条件筛选数据
- [x] `JoinOperator` - 连接算子，支持滑动窗口时间连接
- [x] `AggregateOperator` - 聚合算子，支持窗口聚合操作
- [x] `SinkOperator` - 输出算子，数据输出和持久化
- [x] `TopKOperator` - TopK算子，维护最优K个结果
- [x] `WindowOperator` - 窗口算子，时间和计数窗口支持
- [ ] `OutputOperator` - 输出控制算子
- [x] `ITopKOperator` - Inverted TopK算子（倒排TopK），维护基于倒排索引的TopK结果

### 高级算子实现（基于flow_old功能扩展）：
- [x] `DocumentParserFunction` - 多格式文档解析（PDF、Word、HTML等）
- [x] `TextCleanerFunction` - 文本清理和标准化
- [ ] `ImagePreprocessorFunction` - 图像预处理和特征提取
- [ ] `AudioProcessorFunction` - 音频处理和特征提取
- [ ] `EmbeddingGeneratorFunction` - 多模态embedding生成
- [x] `QualityAssessorFunction` - 数据质量评估和过滤
- [ ] `DeduplicatorFunction` - 数据去重和相似性检测

### 索引算子系统（参考flow_old/index设计）：
- [x] `IndexOperator` - 基础索引算子抽象
- [x] `HNSWIndexOperator` - HNSW近似最近邻索引
- [x] `IVFIndexOperator` - IVF倒排文件索引
- [x] `BruteForceIndexOperator` - 暴力搜索索引
- [x] `KNNOperator` - K最近邻搜索算子
- [x] `VectraFlowIndexOperator` - 自定义向量流索引

### 函数系统实现（参考flow_old/function设计）：
- [ ] `JoinFunction` - 连接函数，支持自定义连接逻辑和滑动窗口
- [ ] `AggregateFunction` - 聚合函数，支持平均值等聚合操作
- [ ] `SinkFunction` - 输出函数
- [ ] `SourceFunction` - 数据源函数，支持文件、内存等多种源
- [ ] `Function` - 基础函数抽象类

### 算子特性要求：
- [ ] **严格遵循Google C++ Style Guide**: 所有类名、方法名、变量名符合规范
- [ ] **类型安全**: 使用强类型设计，避免隐式类型转换
- [ ] **RAII原则**: 正确的资源管理和异常安全
- [ ] **constexpr支持**: 编译时计算优化
- [ ] **move语义**: 高效的数据传递
- [ ] 与 `sage_core` 的 `BaseOperator` 体系兼容
- [ ] 支持算子链式组合和优化（设计新的 Response 机制）

### 与SAGE生态集成：
- [ ] 确保所有算子可通过 `env.from_source().map(Function, config)` 调用
- [ ] 支持 `sage_examples` 中的配置模式（YAML驱动）
- [ ] 集成 `sage_utils.logging_utils` 和 `CustomLogger`
- [ ] 提供 `sage_frontend` 实时监控所需的性能指标

## 2.4 执行引擎与代码质量标准
参考 `flow_old/CMakeLists.txt` 的构建模式，设计新的构建系统：

### C++核心实现要求：
- [ ] 设计新的 C++ 核心执行引擎，使用 Modern C++17/20（**核心运行时**）
- [ ] 所有数据处理算子和流处理逻辑均用C++实现
- [ ] 创建新的 CMake 构建系统，集成 Setuptools
- [ ] 实现新的 Pybind11 绑定层，**仅用于SAGE框架接口交互**
- [ ] C++多线程任务调度和内存管理
- [ ] 与 `sage_runtime` 的任务调度系统集成（通过Python接口层）

### Google C++ Style Guide 严格执行：
- [ ] **命名规范**: 类名CamelCase，函数名camelBack，成员变量lower_case_，常量UPPER_CASE
- [ ] **头文件保护**: 使用 `#pragma once` 而非传统的include guards
- [ ] **智能指针优先**: 使用 `std::unique_ptr`, `std::shared_ptr` 替代裸指针
- [ ] **const正确性**: 所有可能的地方使用const修饰符
- [ ] **初始化列表**: 构造函数使用初始化列表而非赋值
- [ ] **RAII原则**: 资源获取即初始化，自动资源管理

### clang-tidy 检查要求（零警告目标）：
- [ ] **modernize-* 规则**: 使用auto推导、范围for循环、nullptr等现代特性
- [ ] **performance-* 规则**: 避免不必要的拷贝，使用move语义，优化容器操作
- [ ] **google-* 规则**: 严格遵循Google编码标准
- [ ] **readability-* 规则**: 代码可读性优化，合理的函数和变量命名
- [ ] **bugprone-* 规则**: 常见错误模式检测和修复

### 静态分析集成：
- [ ] 集成现有 `.clang-tidy` 配置文件
- [ ] CI/CD 管道中强制执行静态分析
- [ ] 所有代码提交前必须通过 clang-tidy 检查
- [ ] 配置 clang-format 自动代码格式化
