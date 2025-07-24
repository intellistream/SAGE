# 数据源架构重构任务记录

## 任务概述

**任务目标**: 将`include/sources/data_source.h`按照新的文件组织规范进行重构，遵循SAGE框架的分层设计。

## 具体实施步骤

### 1. 重新组织基础文件
- `include/sources/data_source.h` - 仅包含`DataSource`抽象基类和`DataSourceConfig`结构体
- `include/sources/data_source_factory.h` - 独立的工厂函数声明

### 2. 创建具体实现文件 (每个类一个文件)
- `include/sources/file_data_source.h` + `src/sources/file_data_source.cpp` - 文件数据源实现
- `include/sources/stream_data_source.h` + `src/sources/stream_data_source.cpp` - 流数据源实现  
- `include/sources/kafka_data_source.h` + `src/sources/kafka_data_source.cpp` - Kafka数据源实现
- `src/sources/data_source_factory.cpp` - 工厂函数实现

### 3. 借鉴SAGE Python实现的设计模式
- **延迟初始化**: 支持分布式序列化，在实际执行时才创建资源连接
- **状态管理**: 维护读取位置和连接状态，支持断点续读
- **背压处理**: 实现缓冲区管理和资源控制机制
- **资源清理**: 提供完整的生命周期管理和cleanup机制

### 4. 确保与SAGE生态系统兼容
- 接口设计与Python的`SourceFunction`保持一致性
- 支持配置驱动的数据源创建
- 维护与`sage_core.api.env.BaseEnvironment`的集成模式

## 验证标准与完成状态

**验证标准**:
- [x] 所有源文件通过clang-tidy检查
- [x] 每个文件只包含一个主要类定义
- [x] 文件命名与类名保持一致
- [x] 功能完全等价于重构前的实现
- [x] 构建系统正确识别新的文件结构
- [x] 使用已有的MultiModalMessage类而不是重复定义Message类

**完成状态**: ✅ **已完成**

## 重构结果总结

### 1. 基础架构重构完成
- `include/sources/data_source.h` - 仅包含DataSource抽象基类和DataSourceConfig
- `include/sources/data_source_factory.h` - 独立的工厂函数声明

### 2. 具体实现文件已创建
- `include/sources/file_data_source.h` + `src/sources/file_data_source.cpp` - 文件数据源
- `include/sources/stream_data_source.h` + `src/sources/stream_data_source.cpp` - 流数据源实现
- `include/sources/kafka_data_source.h` + `src/sources/kafka_data_source.cpp` - Kafka数据源实现
- `src/sources/data_source_factory.cpp` - 工厂函数实现

### 3. 借鉴SAGE设计模式
- ✅ 延迟初始化支持分布式环境
- ✅ 状态管理和断点续读功能
- ✅ 背压处理和缓冲区管理设计
- ✅ 完整的生命周期管理和资源清理

### 4. SAGE生态系统兼容性
- ✅ 使用MultiModalMessage与现有消息系统集成
- ✅ 配置驱动的数据源创建模式
- ✅ 与DataStream API兼容的接口设计

## 技术要点

### 文件组织原则
遵循"一个文件一个类"原则：
- **例外情况**: 仅允许在同一文件中包含与主类紧密相关的小型辅助类（如内部使用的配置结构体、枚举类等）
- **命名一致性**: 文件名应与主要类名保持一致，如`DataSource`类对应`data_source.h`和`data_source.cpp`
- **模块化目标**: 确保代码模块化和可维护性，便于单元测试和依赖管理

### 代码质量保证
- **Google C++ Style Guide**: 严格遵循命名规范和代码风格
- **静态分析**: 通过clang-tidy检查，零警告目标
- **现代C++**: 充分利用C++17/20特性
- **错误处理**: 完善的异常处理和资源管理

## 后续影响

这次重构为SAGE Flow框架建立了良好的代码组织范例，后续的其他模块重构可以参考这个模式，确保整个框架的一致性和可维护性。
