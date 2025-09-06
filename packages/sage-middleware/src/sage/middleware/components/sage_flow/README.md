# SAGE Flow

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![C++](https://img.shields.io/badge/C%2B%2B-20-blue.svg)](https://isocpp.org)
[![CMake](https://img.shields.io/badge/CMake-3.16%2B-blue.svg)](https://cmake.org)

SAGE Flow 是一个高性能的流处理框架，专为多模态数据处理和向量化而设计。它结合了现代 C++20 的性能优势和 Python 的易用性，为整个 SAGE 生态系统提供核心的数据流处理能力。

## 🚀 核心特性

### 高性能 C++ 运行时
- **现代 C++20 实现**：充分利用最新的 C++ 特性，确保最佳性能
- **Google C++ Style Guide 严格遵循**：所有代码符合 Google 编码规范
- **零警告目标**：通过 clang-tidy 静态分析，确保代码质量
- **内存安全**：使用智能指针和 RAII 原则，避免内存泄漏

### 完整的算子系统
基于 candyFlow 架构，实现所有核心算子：

**基础算子**：
- ✅ `SourceOperator` - 数据源算子
- ✅ `MapOperator` - 一对一映射变换
- ✅ `FilterOperator` - 条件过滤算子
- ✅ `SinkOperator` - 数据输出算子
- ✅ `TopKOperator` - TopK 维护算子
- ✅ `WindowOperator` - 窗口算子
- ✅ `AggregateOperator` - 聚合算子
- ✅ `JoinOperator` - 连接算子

**索引算子**：
- ✅ `BruteForceIndex` - 暴力搜索索引
- ✅ `HNSWIndex` - HNSW 近似最近邻索引
- ✅ `IVFIndex` - IVF 倒排文件索引
- ✅ `KnnOperator` - K 最近邻搜索算子

**函数系统**：
- ✅ `TextCleanerFunction` - 文本清理函数
- ✅ `DocumentParserFunction` - 文档解析函数
- ✅ `QualityAssessorFunction` - 质量评估函数
- ✅ `TextEmbeddingFunction` - 文本嵌入函数

### 多模态数据支持
- **MultiModalMessage**：统一的多模态消息容器
- **VectorData**：高效的向量数据处理
- **RetrievalContext**：RAG 检索上下文支持
- **ContentType**：支持文本、图像、音频、视频等多种数据类型

### SAGE 生态集成
- **sage_core 兼容**：通过 DataStream API 提供统一接口
- **sage_runtime 集成**：支持本地和分布式执行
- **sage_memory 协同**：提供向量检索能力
- **sage_frontend 监控**：实时处理指标支持

## ⚡ 快速构建

### 最简构建 (推荐)

```bash
# 克隆项目
git clone https://github.com/intellistream/SAGE.git
cd SAGE/packages/sage-middleware/src/sage/middleware/components/sage_flow

# 一键构建和安装
pip install -e .
```

### 开发环境构建

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 构建项目
pip install -e .
```

## 📦 安装

### 系统要求
- **操作系统**：Linux (Ubuntu 18.04+), macOS (10.15+)
- **编译器**：GCC 9+ 或 Clang 10+ (支持 C++20)
- **Python**：3.9 或更高版本
- **CMake**：3.16 或更高版本

### 从源码安装

#### 使用 scikit-build-core (推荐)

scikit-build-core 自动管理 CMake 构建过程，提供现代化的 Python 包构建体验。

```bash
# 克隆项目
git clone https://github.com/intellistream/SAGE.git
cd SAGE/packages/sage-middleware/src/sage/middleware/components/sage_flow

# 安装构建依赖
pip install -e ".[dev]"

# 构建和安装 (自动处理 CMake 构建)
pip install -e .
```

### scikit-build-core 高级用法

#### 自定义构建配置

```bash
# 调试构建
SAGE_BUILD_TYPE=Debug pip install -e .

# 启用详细构建日志
SAGE_BUILD_VERBOSE=1 pip install -e .

# 自定义构建目录
SAGE_BUILD_DIR=build_custom pip install -e .

# 交叉编译支持
pip install -e . --config-settings="wheel.expand-macos-universal=true"
```

#### 构建配置说明

基于 `pyproject.toml` 配置，scikit-build-core 提供以下特性：

- **自动 CMake 检测**：自动查找和配置 CMake
- **Python 版本兼容性**：支持 Python 3.9-3.12
- **跨平台构建**：支持 Linux、macOS、Windows
- **可编辑安装**：支持开发时的快速重新构建
- **轮子构建**：自动生成兼容的 Python 轮子包

#### 构建依赖管理

```toml
# pyproject.toml 中的构建系统配置
[build-system]
requires = [
    "wheel",
    "pybind11>=2.10.0",
    "cmake>=3.16",
    "ninja",
    "scikit-build-core>=0.10.0"
]
build-backend = "scikit_build_core.build"
```

#### 手动 CMake 构建

```bash
# 克隆项目
git clone https://github.com/intellistream/SAGE.git
cd SAGE/packages/sage-middleware/src/sage/middleware/components/sage_flow

# 创建构建目录
mkdir build && cd build

# 配置和构建
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

# 安装 Python 包
pip install -e ..
```

### 使用 pip 安装

```bash
pip install sage-flow
```

## 🔧 快速开始

### Python API

```python
import sage_flow as sf

# 创建环境
env = sf.Environment("example_job")

# 创建数据流
stream = env.create_datastream()

# 定义数据处理管道
result = (stream
    .from_source(lambda: sf.create_text_message(1, "Hello, SAGE Flow!"))
    .map(lambda msg: sf.create_text_message(msg.get_uid(), msg.get_content_as_string().upper()))
    .filter(lambda msg: len(msg.get_content_as_string()) > 5)
    .sink(lambda msg: print(f"Processed: {msg.get_content_as_string()}"))
)

# 执行流处理
env.submit()
```

### DataStream 和 Environment 详细使用示例

#### Environment 配置和生命周期管理

```python
import sage_flow as sf

# 创建具有自定义配置的环境
env = sf.Environment(
    job_name="advanced_processing_job",
    config={
        "parallelism": 4,
        "checkpoint_interval": 1000,
        "state_backend": "rocksdb"
    }
)

# 环境配置方法
env.set_parallelism(8)
env.enable_checkpointing(interval=500)
env.set_restart_strategy(sf.RestartStrategies.fixed_delay(3, 10000))

print(f"Environment: {env.get_job_name()}")
print(f"Parallelism: {env.get_parallelism()}")
```

#### DataStream 高级操作

```python
# 创建数据流
stream = env.create_datastream("input_stream")

# 数据源操作
stream = (stream
    .from_collection([1, 2, 3, 4, 5])
    .map(lambda x: x * 2)
    .filter(lambda x: x > 5)
)

# 分支和合并
branch1 = stream.map(lambda x: f"branch1: {x}")
branch2 = stream.filter(lambda x: x % 2 == 0).map(lambda x: f"branch2: {x}")

# 连接流
connected = branch1.connect(branch2)
result = connected.map(lambda x: x.upper())

# 输出
result.sink(lambda x: print(f"Result: {x}"))

# 执行
env.submit()
```

#### 窗口操作示例

```python
from sage_flow import TumblingWindows, SlidingWindows

# 滚动窗口
tumbling_result = (stream
    .window(TumblingWindows.of(sf.Time.seconds(10)))
    .reduce(lambda acc, x: acc + x)
)

# 滑动窗口
sliding_result = (stream
    .window(SlidingWindows.of(sf.Time.seconds(10), sf.Time.seconds(5)))
    .aggregate(lambda acc, x: acc + [x], initial=[])
)

# 会话窗口
session_result = (stream
    .window(SessionWindows.with_gap(sf.Time.minutes(5)))
    .process(lambda key, context, elements: sum(elements))
)
```

#### 状态管理和检查点

```python
# 有状态操作
stateful_stream = (stream
    .key_by(lambda x: x % 10)  # 按键分区
    .map_with_state(
        lambda value, state: (value + (state or 0), value + (state or 0)),
        state_descriptor=sf.ValueStateDescriptor("sum_state")
    )
)

# 启用检查点
env.enable_checkpointing(
    interval=1000,
    mode=sf.CheckpointingMode.EXACTLY_ONCE,
    timeout=60000
)

# 检查点监听器
env.add_checkpoint_listener(
    on_success=lambda checkpoint_id: print(f"Checkpoint {checkpoint_id} completed"),
    on_failure=lambda checkpoint_id, error: print(f"Checkpoint {checkpoint_id} failed: {error}")
)
```

### C++ API

```cpp
#include <sage_flow/api/datastream.h>
#include <sage_flow/message/multimodal_message.h>

using namespace sage_flow;

int main() {
    // 创建环境
    auto env = std::make_shared<SageFlowEnvironment>("example_job");
    
    // 创建数据流
    auto stream = env->create_datastream();
    
    // 定义数据处理管道
    stream.from_source([]() {
        return CreateTextMessage(1, "Hello, SAGE Flow!");
    })
    .map([](auto msg) {
        auto content = msg->getContentAsString();
        std::transform(content.begin(), content.end(), content.begin(), ::toupper);
        return CreateTextMessage(msg->getUid(), content);
    })
    .filter([](const auto& msg) {
        return msg.getContentAsString().length() > 5;
    })
    .sink([](const auto& msg) {
        std::cout << "Processed: " << msg.getContentAsString() << std::endl;
    });
    
    // 执行流处理
    env->submit();
    
    return 0;
}
```

## 📂 项目结构

```
sage-flow/
├── include/                 # C++ 头文件
│   ├── message/            # 消息类型定义
│   ├── operator/           # 算子定义
│   ├── function/           # 函数实现
│   ├── index/              # 索引算子
│   ├── engine/             # 执行引擎
│   └── api/                # 公共 API
├── src/                    # C++ 源文件
│   ├── message/
│   ├── operator/
│   ├── function/
│   ├── index/
│   ├── engine/
│   └── python/             # Python 绑定
├── python/                 # Python 包源码
├── tests/                  # 测试用例
│   ├── unit/               # 单元测试
│   ├── integration/        # 集成测试
│   └── performance/        # 性能测试
├── docs/                   # 文档
├── CMakeLists.txt          # 构建配置
├── pyproject.toml          # Python 包配置
└── README.md              # 项目说明
```

## 🧪 测试

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行性能测试
pytest tests/performance/ -m performance

# 生成覆盖率报告
pytest --cov=sage_flow --cov-report=html
```

## 🛠️ 开发

### 代码规范

本项目严格遵循 Google C++ Style Guide：

```bash
# 代码格式化
clang-format -i src/**/*.cpp include/**/*.h

# 静态分析
clang-tidy src/**/*.cpp -- -I./include

# Python 代码格式化
black python/ tests/
isort python/ tests/
```

### 构建选项

#### scikit-build-core 构建选项

```bash
# 标准发布构建
pip install -e .

# 调试构建
SAGE_BUILD_TYPE=Debug pip install -e .

# 启用详细构建日志
SAGE_BUILD_VERBOSE=1 pip install -e .

# 自定义构建目录
SAGE_BUILD_DIR=build_custom pip install -e .
```

#### CMake 手动构建选项

```bash
# 启用测试
cmake .. -DSAGE_FLOW_BUILD_TESTS=ON

# 启用示例
cmake .. -DSAGE_FLOW_BUILD_EXAMPLES=ON

# 调试构建
cmake .. -DCMAKE_BUILD_TYPE=Debug

# 启用 sanitizers
cmake .. -DCMAKE_BUILD_TYPE=Debug -DENABLE_SANITIZERS=ON

# 自定义安装路径
cmake .. -DCMAKE_INSTALL_PREFIX=/custom/path
```

#### 交叉编译支持

```bash
# macOS Universal 构建
pip install -e . --config-settings="wheel.expand-macos-universal=true"

# Linux manylinux 构建
pip install -e . --config-settings="wheel.manylinux=auto"
```

## 📊 性能

SAGE Flow 设计目标：

- **10x 性能提升**：相比纯 Python 实现至少 10 倍性能提升
- **TB 级数据处理**：支持大规模数据处理，内存占用线性增长
- **7x24 稳定运行**：支持容错恢复和长期稳定运行
- **水平扩展**：支持分布式处理和动态扩展

### 基准测试结果

| 操作 | SAGE Flow | 纯 Python | 性能提升 |
|-----|-----------|-----------|----------|
| 文本处理 | 1.2ms | 15.6ms | 13x |
| 向量计算 | 0.8ms | 12.3ms | 15x |
| 索引搜索 | 2.1ms | 28.7ms | 14x |

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 贡献指南

- 遵循 Google C++ Style Guide
- 确保所有测试通过
- 添加必要的文档
- 更新 CHANGELOG.md

## 📄 许可证

本项目采用 Apache License 2.0 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 🙏 致谢

感谢以下项目的灵感和支持：

- [candyFlow](https://github.com/candyflow/candyflow) - 流处理架构设计参考
- [pybind11](https://github.com/pybind/pybind11) - Python/C++ 绑定
- [HNSW](https://github.com/nmslib/hnswlib) - 高效向量索引算法

## 📞 联系方式

- **项目主页**：https://github.com/intellistream/SAGE
- **问题反馈**：https://github.com/intellistream/SAGE/issues
- **邮件联系**：intellistream@outlook.com

---

**SAGE Flow** - 高性能、现代化的数据流处理框架 🚀