# 代码组织规范与约束

## 代码规范要求

### Google C++ Style Guide 遵循
- **类名**: 使用CamelCase (例: `DataSource`, `FileDataSource`)
- **方法名**: 使用camelBack (例: `initialize()`, `nextMessage()`)
- **成员变量**: 使用lower_case_后缀 (例: `config_`, `initialized_`)
- **常量**: 使用kCamelCase (例: `kDefaultBufferSize`)

### 文件组织规范 ⭐ 核心原则

#### 一个文件一个类原则
每个源代码文件(.cpp/.h)只允许存放一个主要的class或struct定义

#### 例外情况
仅允许在同一文件中包含与主类紧密相关的小型辅助类：
- 内部使用的配置结构体
- 枚举类定义
- 小型工具类（如果仅被主类使用）

#### 命名一致性
文件名应与主要类名保持一致：
- `DataSource`类 → `data_source.h` + `data_source.cpp`
- `FileDataSource`类 → `file_data_source.h` + `file_data_source.cpp`
- `StreamDataSource`类 → `stream_data_source.h` + `stream_data_source.cpp`

#### 模块化目标
- 确保代码模块化和可维护性
- 便于单元测试和依赖管理
- 提高编译效率和并行构建能力
- 降低代码耦合度

### 静态分析要求

#### clang-tidy 检查
必须满足现有 .clang-tidy 配置要求：
- `google-*`: Google风格检查
- `modernize-*`: 现代C++特性使用
- `performance-*`: 性能优化建议
- `bugprone-*`: 潜在bug检测
- `readability-*`: 代码可读性

#### 代码质量标准
- 所有C++代码必须通过静态分析
- 零警告错误目标
- 编译时警告必须修复

### 现代C++特性使用

#### C++17/20 特性
- `constexpr`: 编译时常量和函数
- `auto`: 类型推导
- 智能指针: `std::unique_ptr`, `std::shared_ptr`
- 移动语义: `std::move`, 右值引用
- 范围for循环: `for (const auto& item : container)`
- 结构化绑定: `auto [key, value] = map.find(...)`

#### 内存管理
- 优先使用RAII和智能指针
- 避免原始指针和手动内存管理
- 使用容器类而非C风格数组

## 设计约束

### SAGE框架兼容性
- 必须与 `sage_core.api.env.LocalEnvironment` 和 `RemoteEnvironment` 兼容
- 通过 DataStream API 提供统一的流処理接口
- 支持 `sage_runtime` 本地和分布式执行
- 与 `sage_memory` 协同提供向量检索能力

### 功能等价保证
新框架必须提供与flow_old完全等价的数据处理能力

### 架构要求
- 整个flow运行时核心必须使用C++17/20实现
- Python仅用于与SAGE框架的接口交互层
- 支持分布式序列化和远程执行

## 实施指南

### 新模块开发流程
1. **设计阶段**: 确定类的职责和接口
2. **文件创建**: 按照命名规范创建头文件和实现文件
3. **接口定义**: 在头文件中定义清晰的公共接口
4. **实现编写**: 在cpp文件中实现具体逻辑
5. **测试验证**: 编写单元测试验证功能
6. **静态分析**: 通过clang-tidy检查
7. **集成测试**: 确保与SAGE框架兼容

### 重构现有代码
1. **分析依赖**: 识别类之间的依赖关系
2. **拆分规划**: 制定文件拆分方案
3. **逐步重构**: 一次重构一个类，保持功能完整
4. **测试验证**: 每次重构后进行回归测试
5. **文档更新**: 更新相关文档和注释

### 代码审查要点
- 文件组织是否符合一个文件一个类原则
- 命名是否遵循Google C++ Style Guide
- 是否充分使用现代C++特性
- 静态分析是否通过
- 与SAGE框架集成是否正确
