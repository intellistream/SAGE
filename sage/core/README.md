# Sage Core 模块

Sage Core 是 Sage 框架的核心模块，负责数据流管道的定义、编译和执行管理。本模块提供了完整的数据流处理框架，从用户友好的API接口到底层的运行时执行引擎。

## 模块架构概览

Sage Core 采用分层架构设计，每一层都有明确的职责和接口：

```
用户API层 (api/) → 转换层 (transformation/) → 函数层 (function/) → 算子层 (operator/)
```

## 子模块详细说明

### [API 模块 (api/)](./api/)
提供用户友好的 API 接口，用于构建数据流管道：
- **环境管理**: 本地和远程执行环境的统一抽象
- **数据流抽象**: 链式操作API，支持 `map()`, `filter()`, `sink()` 等操作  
- **连接流管理**: 多流连接和协同处理功能
- **类型安全**: 基于泛型的编译时类型检查

### [Function 模块 (function/)](./function/)
定义所有数据处理函数的逻辑实现：
- **基础框架**: 函数抽象基类和运行时上下文管理
- **数据源函数**: Kafka源等各种数据输入实现
- **转换函数**: map、filter、join等数据转换操作
- **输出函数**: 各种数据输出和收集器实现
- **Lambda支持**: 支持Lambda表达式的自动包装

### [Operator 模块 (operator/)](./operator/)
算子系统，负责运行时的具体执行：
- **运行时执行**: 函数在运行时的执行载体
- **生命周期管理**: 算子的初始化、启动、执行、停止
- **状态管理**: 支持有状态算子的状态维护和恢复
- **资源管理**: 自动管理内存和网络资源
- **容错处理**: 内置错误处理和恢复机制

### [Transformation 模块 (transformation/)](./transformation/)
转换系统，负责将用户逻辑转换为可执行的算子图：
- **编译时优化**: 图优化、并行度推导、资源分配
- **任务调度**: 将转换编译为可调度的任务
- **平台适配**: 支持本地、远程和混合执行环境
- **类型推导**: 编译时类型检查和自动推导

### [Service 模块 (service/)](./service/)
服务集成功能（预留模块）：
- 预留用于服务发现、调用和管理功能
- 目前相关功能在其他模块中实现

### [Tests 模块 (tests/)](./tests/)
核心模块的集成测试：
- 协同映射服务集成测试
- 端到端数据流处理测试
- 服务集成和协调测试

## 数据流处理流程

### 1. 用户编程阶段
```python
# 用户使用 API 模块定义数据流管道
env = LocalEnvironment()
stream = env.from_batch([1, 2, 3, 4, 5])
result = stream.map(lambda x: x * 2).filter(lambda x: x > 4).sink(lambda x: print(x))
```

### 2. 编译阶段
- **Transformation**: API调用被转换为Transformation对象
- **优化**: 图优化、算子融合、并行度推导
- **任务生成**: 生成可执行的任务图

### 3. 执行阶段
- **算子实例化**: 基于Function创建Operator实例
- **数据处理**: 算子执行具体的数据处理逻辑
- **结果输出**: 处理结果输出到指定目标

## 核心设计原则

### 分层抽象
- **用户层**: 提供简洁易用的API接口
- **逻辑层**: 定义数据处理的抽象逻辑
- **运行层**: 实现具体的执行机制

### 类型安全
- 基于Python泛型系统提供编译时类型检查
- 自动类型推导和验证
- 防止运行时类型错误

### 平台无关
- 统一的本地和远程执行环境接口
- 支持多种执行后端（本地进程、Ray集群等）
- 可扩展的平台适配机制

### 高性能
- 算子融合和图优化
- 并行执行和流水线处理
- 内存和网络资源的高效利用

## 使用示例

```python
from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.source_function import SourceFunction

# 创建执行环境
env = LocalEnvironment("example_pipeline")

# 构建数据流管道
source_stream = env.from_source(SourceFunction)
processed_stream = source_stream.map(lambda x: x * 2)
result_stream = processed_stream.filter(lambda x: x > 4)
result_stream.sink(lambda x: print(f"Result: {x}"))

# 提交管道执行
env.submit()
```

## 扩展开发

### 添加新的数据处理函数
1. 在 `function/` 模块中实现新的Function类
2. 在 `operator/` 模块中实现对应的Operator类  
3. 在 `transformation/` 模块中实现相应的Transformation类
4. 在 `api/datastream.py` 中添加对应的API方法

### 添加新的数据源
1. 继承 `SourceFunction` 实现数据源逻辑
2. 继承 `SourceOperator` 实现运行时执行
3. 在环境类中添加相应的创建方法

## 相关文档

- [Installation Guide](../../docs/installation_architecture.md) - 安装和配置指南
- [API Documentation](../../docs/sage_core_api_documentation.md) - API详细文档
- [System Design](../../docs/service_system_design.md) - 系统设计文档