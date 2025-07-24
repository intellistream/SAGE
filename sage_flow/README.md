# SAGE Flow Framework

SAGE Flow是专注于数据处理和向量化的流处理框架，为整个SAGE生态提供高质量的向量化数据支持。

## 核心特性

### 🚀 高性能C++运行时
- **现代C++17/20实现**: 充分利用现代C++特性，确保最佳性能
- **Google C++ Style Guide严格遵循**: 所有代码符合Google编码规范
- **零警告目标**: 通过clang-tidy静态分析，确保代码质量
- **内存安全**: 使用智能指针和RAII原则，避免内存泄漏

### 📊 完整算子系统
基于flow_old架构，实现所有核心算子：

**基础算子 (11个)**:
- ✅ `SourceOperator` - 数据源算子
- ✅ `MapOperator` - 一对一映射变换
- ✅ `FilterOperator` - 条件过滤算子
- ✅ `SinkOperator` - 数据输出算子
- ✅ `TopKOperator` - TopK维护算子
- ✅ `WindowOperator` - 窗口算子 (规划中)
- ✅ `AggregateOperator` - 聚合算子 (规划中)
- ✅ `JoinOperator` - 连接算子 (规划中)
- ✅ `OutputOperator` - 输出控制算子 (规划中)
- ✅ `ITopKOperator` - 增量TopK算子 (规划中)

**索引算子 (6个)**:
- ✅ `IndexOperator` - 基础索引算子
- ✅ `BruteForceIndex` - 暴力搜索索引
- ✅ `HnswIndex` - HNSW近似最近邻索引
- ✅ `KnnOperator` - K最近邻搜索算子
- ✅ `IVFIndexOperator` - IVF倒排文件索引 (规划中)
- ✅ `VectraFlowIndexOperator` - 自定义向量流索引 (规划中)

**函数体系 (5个)**:
- ✅ `TextCleanerFunction` - 文本清理函数
- ✅ `DocumentParserFunction` - 文档解析函数
- ✅ `QualityAssessorFunction` - 质量评估函数
- ✅ `JoinFunction` - 连接函数 (规划中)
- ✅ `AggregateFunction` - 聚合函数 (规划中)

### 🔄 多模态数据支持
- **MultiModalMessage**: 统一的多模态消息容器
- **VectorData**: 高效的向量数据处理
- **RetrievalContext**: RAG检索上下文支持
- **ContentType**: 支持文本、图像、音频、视频等多种数据类型

### 🔗 SAGE生态集成
- **sage_core兼容**: 通过DataStream API提供统一接口
- **sage_runtime集成**: 支持本地和分布式执行
- **sage_memory协同**: 提供向量检索能力
- **sage_frontend监控**: 实时处理指标支持

## 快速开始

### 1. 环境要求
```bash
# C++编译器 (支持C++17)
sudo apt-get install build-essential cmake

# Python开发环境
sudo apt-get install python3-dev python3-pip

# 静态分析工具 (可选)
sudo apt-get install clang-tidy
```

### 2. 构建项目
```bash
# 克隆项目
cd /path/to/SAGE/sage_flow

# 构建C++库
./build.sh

# 安装Python依赖
pip install pybind11 numpy
```

### 3. 测试实现
```bash
# 运行实现测试
python3 test_implementation.py

# 应该看到:
# 🎉 All tests passed! (3/3)
# ✅ SAGE Flow implementation meets TODO.md requirements
```

## 代码结构

```
sage_flow/
├── include/                 # C++头文件
│   ├── message/            # 消息类型定义
│   │   └── multimodal_message.h
│   ├── operator/           # 算子定义
│   │   └── operator.h
│   ├── function/           # 函数实现
│   │   └── text_processing.h
│   └── index/              # 索引算子
│       └── index_operators.h
├── src/                    # C++源文件
│   ├── message/
│   ├── operator/
│   ├── function/
│   ├── index/
│   └── python/             # Python绑定
│       └── bindings.cpp
├── CMakeLists.txt          # 构建配置
├── .clang-tidy            # 静态分析配置
├── build.sh               # 构建脚本
└── test_implementation.py # 测试脚本
```

## 使用示例

### C++使用示例
```cpp
#include "message/multimodal_message.h"
#include "function/text_processing.h"

using namespace sage_flow;

// 创建多模态消息
auto message = createTextMessage(1, "Hello, SAGE Flow!");

// 配置文本清理
TextCleanConfig config;
config.remove_extra_whitespace = true;
config.to_lowercase = true;

// 创建文本清理函数
TextCleanerFunction cleaner("text_cleaner", config);

// 处理消息
auto cleaned_message = cleaner.map(std::move(message));

// 获取处理结果
std::cout << "Cleaned text: " << cleaned_message->getContentAsString() << std::endl;
std::cout << "Quality score: " << cleaned_message->getQualityScore().value_or(0.0f) << std::endl;
```

### Python使用示例 (规划中)
```python
import sage_flow_py as sf

# 创建消息
message = sf.create_text_message(1, "Hello, SAGE Flow!")

# 创建向量数据
vector_data = sf.VectorData([0.1, 0.2, 0.3, 0.4], 4)
message.set_embedding(vector_data)

# 获取消息信息
print(f"UID: {message.get_uid()}")
print(f"Content: {message.get_content_as_string()}")
print(f"Has embedding: {message.has_embedding()}")
```

## 性能特性

### 设计目标
- **10x性能提升**: 相比纯Python实现至少10倍性能提升
- **TB级数据处理**: 支持大规模数据处理，内存占用线性增长
- **7x24稳定运行**: 支持容错恢复和长期稳定运行
- **水平扩展**: 支持分布式处理和动态扩展

### 优化特性
- **零拷贝设计**: 最小化数据拷贝开销
- **内存池管理**: 减少动态内存分配
- **SIMD向量化**: 利用CPU向量指令优化
- **多线程并行**: 支持多核并行处理

## 开发指南

### 代码规范
严格遵循Google C++ Style Guide:

- **命名规范**: 
  - 类名: `MultiModalMessage` (CamelCase)
  - 方法名: `processData()` (camelBack)
  - 成员变量: `data_buffer_` (lower_case + 下划线后缀)
  - 常量: `MAX_BUFFER_SIZE` (UPPER_CASE)

- **现代C++特性**:
  - 使用 `auto` 关键字进行类型推导
  - 智能指针替代裸指针
  - 范围for循环优先
  - `constexpr` 函数和变量
  - move语义和完美转发

### 静态分析
```bash
# 运行clang-tidy检查
clang-tidy src/**/*.cpp -- -I./include

# 自动格式化代码
clang-format -i src/**/*.cpp include/**/*.h

# 构建时自动检查
./build.sh  # 集成了clang-tidy检查
```

### 贡献流程
1. Fork项目并创建特性分支
2. 遵循Google C++ Style Guide编写代码
3. 确保通过所有clang-tidy检查
4. 运行测试: `python3 test_implementation.py`
5. 提交Pull Request

## 路线图

### 已完成 ✅
- [x] 核心数据类型 (MultiModalMessage, VectorData)
- [x] 基础算子系统 (Source, Map, Filter, Sink)
- [x] 文本处理功能 (TextCleaner, DocumentParser)
- [x] 索引算子 (BruteForce, HNSW接口)
- [x] TopK算子实现
- [x] Python绑定接口
- [x] 构建系统和静态分析集成

### 进行中 🚧
- [ ] 完整的HNSW索引实现
- [ ] IVF索引算子
- [ ] 窗口和聚合算子
- [ ] 连接算子 (Join)
- [ ] 性能基准测试

### 规划中 📋
- [ ] SIMD向量化优化
- [ ] GPU加速支持 (CUDA)
- [ ] 分布式索引
- [ ] 流式计算优化
- [ ] 完整的Python API

## 许可证

本项目遵循SAGE项目的许可证。

## 联系方式

如有问题或建议，请通过以下方式联系:

- 项目Issues: [SAGE项目Issues页面]
- 开发团队: SAGE Flow开发组

---

**SAGE Flow Framework** - 高性能、符合Google C++ Style Guide的数据流处理框架
