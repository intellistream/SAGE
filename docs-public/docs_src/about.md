# SAGE - Streaming-Augmented Generative Execution

> 用于构建透明 LLM 系统的声明式、可组合框架

[![CI](https://github.com/intellistream/SAGE/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/SAGE/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/intellistream/SAGE/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![PyPI version](https://badge.fury.io/py/isage.svg)](https://badge.fury.io/py/isage)

[![WeChat Group](https://img.shields.io/badge/WeChat-%E5%8A%A0%E5%85%A5%E5%BE%AE%E4%BF%A1%E7%BE%A4-brightgreen?style=flat&logo=wechat)](join_sage/community.md)
[![QQ Group](https://img.shields.io/badge/%E3%80%90IntelliStream%E8%AF%BE%E9%A2%98%E7%BB%84%E8%AE%A8%E8%AE%BAQQ%E7%BE%A4%E3%80%91-blue?style=flat&logo=tencentqq)](https://qm.qq.com/q/bcnuyQVcvm)
[![Slack](https://img.shields.io/badge/Slack-Join%20Slack-purple?style=flat&logo=slack)](https://join.slack.com/t/intellistream/shared_invite/zt-2qayp8bs7-v4F71ge0RkO_rn34hBDWQg)

**SAGE** 是一个用于构建 AI 驱动数据处理流水线的高性能流处理框架。通过声明式数据流抽象，将复杂的 LLM 推理工作流转换为透明、可扩展且易于维护的系统。

## 为什么选择 SAGE？

**生产就绪**: 为企业级应用构建，提供开箱即用的分布式处理、容错机制和全面的监控功能。

**开发体验**: 使用直观的声明式 API，只需几行代码即可编写复杂的 AI 流水线，消除样板代码。

**性能优化**: 针对高吞吐量流式工作负载优化，具备智能内存管理和并行执行能力。

**透明可观测**: 内置可观测性和调试工具，提供执行路径和性能特征的完整可见性。

## 快速开始

将传统的命令式 LLM 应用转换为灵活、可观测的工作流。传统方法创建的系统脆弱且难以修改：

```python
# 传统方法 - 僵化且难以修改
def traditional_rag(query):
    docs = retriever.retrieve(query)
    if len(docs) < 3:
        docs = fallback_retriever.retrieve(query)
    prompt = build_prompt(query, docs)
    response = llm.generate(prompt)
    return response
```

SAGE 将其转换为**声明式、可组合的工作流**：

```python
from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io.source import FileSource
from sage.libs.rag.retriever import DenseRetriever
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.io.sink import TerminalSink

# 创建执行环境
env = LocalEnvironment("rag_pipeline")

# 构建声明式流水线
(
    env.from_source(FileSource, {"file_path": "questions.txt"})
    .map(DenseRetriever, {"model": "sentence-transformers/all-MiniLM-L6-v2"})
    .map(QAPromptor, {"template": "基于上下文回答: {context}\n问: {query}\n答:"})
    .map(OpenAIGenerator, {"model": "gpt-3.5-turbo"})
    .sink(TerminalSink)
)

# 执行流水线
env.submit()
```

### 为什么这很重要

**灵活性**: 无需修改执行逻辑即可修改流水线结构。轻松替换组件、添加监控或更改部署目标。

**透明性**: 通过内置的可观测性和调试工具，清楚地了解每一步发生的事情。

**性能**: 基于数据流分析的自动优化、并行化和资源管理。

**可靠性**: 内置容错、检查点和错误恢复机制。

## 架构设计

### 系统架构

SAGE 基于分层架构构建，提供灵活性、可扩展性和可维护性。架构由五个主要层次组成：

1. **用户层**: 使用 SAGE 构建的应用（RAG、Agent、Memory、QA 系统）
1. **API 层**: LocalEnvironment 和 RemoteEnvironment 用于不同的执行上下文
1. **核心层**: Dispatcher、Job Manager、Service Manager 和运行时执行引擎
1. **库层**: RAG 流水线、Agent 框架、Memory 存储、中间件组件
1. **基础设施层**: 计算后端（Ray、本地）、数据存储、模型服务、监控

### 模块化设计

SAGE 遵循清晰的关注点分离，具有无缝协作的可插拔组件：

- **Core (sage-kernel)**: 流处理引擎和执行环境
- **Libraries (sage-libs)**: 丰富的 AI、I/O、转换和工具算子
- **Kernel (sage-kernel)**: 分布式计算原语和通信
- **Middleware (sage-middleware)**: 服务发现、监控和管理
- **Common (sage-common)**: 共享工具、配置和日志

### 生产级特性

为满足企业需求的实际部署而构建：

- **分布式执行**: 通过自动负载均衡跨多个节点扩展
- **容错机制**: 全面的错误处理和恢复机制
- **可观测性**: 详细的指标、日志和性能监控
- **安全性**: 身份验证、授权和数据加密支持
- **集成**: 为流行的数据库、消息队列和 AI 服务提供原生连接器

## 🧩 核心原生扩展

SAGE 提供两个 C++ 原生扩展，覆盖向量存储与流式计算：

### SAGE DB - 向量数据库

基于 FAISS 的高性能向量数据库，支持：

- **多模态数据**: 文本、图像、音频等多种数据类型
- **元数据过滤**: 基于元数据的精确过滤和检索
- **Hybrid 检索**: 结合向量检索和关键词检索
- **持久化存储**: 数据持久化到磁盘并支持增量更新
- **多索引管理**: 支持创建和管理多个索引

**安装方式**:

```bash
sage extensions install sage_db
```

### SAGE Flow - 流式处理引擎

向量级流式处理引擎，提供：

- **窗口化算子**: 时间窗口、计数窗口、会话窗口
- **低延迟状态更新**: 毫秒级状态更新和查询
- **RAG 联动**: 与向量数据库无缝集成
- **实时处理**: 适合实时 Agent 和交互场景

**安装方式**:

```bash
sage extensions install sage_flow
```

### 扩展管理

```bash
# 安装所有扩展
sage extensions install all

# 检查扩展状态
sage extensions status

# 重新编译扩展
sage extensions install all --force
```

更多扩展正在规划中。您可以在 `packages/sage-middleware/src/sage/middleware/components/` 下查看示例并提交提案。

## 安装

我们提供交互式安装器和明确的命令标志。推荐开发者使用开发模式。

### 克隆仓库并交互式安装

```bash
git clone https://github.com/intellistream/SAGE.git
cd SAGE
git checkout main-dev
./quickstart.sh  # 打开交互式菜单
```

### 常用非交互式安装模式

```bash
# 开发者安装
./quickstart.sh --dev --yes

# 最小核心安装
./quickstart.sh --minimal --yes

# 标准安装 + vLLM 支持
./quickstart.sh --standard --vllm --yes

# 使用系统 Python 而非 conda
./quickstart.sh --minimal --pip --yes

# 查看所有标志
./quickstart.sh --help
```

### 快速 PyPI 安装

```bash
# 选择您的安装模式:
pip install isage[minimal]   # 核心功能  
pip install isage[standard]  # 完整特性
pip install isage[dev]       # 所有功能 + 开发工具
```

> 注意: PyPI 安装可能不包含所有系统依赖；使用 quickstart.sh 进行完整的环境设置。

### 关键安装特性

- 🎯 为首次用户提供交互式菜单
- 🤖 通过 `--vllm` 集成 vLLM
- 🐍 通过 `--pip` 支持 conda 或系统 Python
- ⚡ 三种模式: minimal / standard / dev

## 环境配置

安装后，配置您的 API 密钥和环境设置：

### 快速设置

```bash
# 运行交互式环境设置
sage config env setup
```

### 手动设置

```bash
# 复制环境模板
cp .env.template .env

# 编辑 .env 并添加您的 API 密钥
# 大多数示例需要:
OPENAI_API_KEY=your_openai_api_key_here
HF_TOKEN=your_huggingface_token_here
```

## 核心概念

### Environment（执行环境）

Environment 是 SAGE 的执行入口点，提供两种模式：

- **LocalEnvironment**: 本地多线程执行，适合开发和小规模任务
- **RemoteEnvironment**: 基于 Ray 的分布式执行，适合生产和大规模任务

```python
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.remote_environment import RemoteEnvironment

# 本地环境
env = LocalEnvironment("my_pipeline")

# 分布式环境
env = RemoteEnvironment("distributed_pipeline")
```

### DataStream（数据流）

DataStream 是 SAGE 的核心抽象，表示数据流。通过链式 API 构建流水线：

```python
# 构建流水线
stream = (
    env.from_source(FileSource, {"file_path": "input.txt"})
    .map(ProcessFunction, {"param": "value"})
    .filter(FilterFunction)
    .sink(OutputSink)
)
```

### Function（函数算子）

Function 是流水线中的处理单元。SAGE 提供多种函数类型：

- **SourceFunction**: 数据源（文件、API、数据库等）
- **MapFunction**: 一对一转换
- **FlatMapFunction**: 一对多转换
- **FilterFunction**: 过滤数据
- **BatchFunction**: 批处理数据源
- **SinkFunction**: 数据输出（终端、文件、数据库等）

### Operator（算子）

Operator 封装 Function，提供执行逻辑。支持的算子：

| 算子方法        | 描述                   |
| --------------- | ---------------------- |
| `from_source()` | 从外部系统读取输入数据 |
| `from_batch()`  | 批处理数据源           |
| `map()`         | 一对一转换             |
| `flatmap()`     | 一对多转换             |
| `filter()`      | 过滤数据               |
| `sink()`        | 定义流的终端输出       |

## 功能库

SAGE 提供丰富的内置功能库，覆盖常见的 AI 应用场景：

### RAG (检索增强生成)

位于 `sage.libs.rag`:

- **Retriever**: 密集检索器（DenseRetriever）、稀疏检索器、混合检索器
- **Reranker**: 基于交叉编码器的重排序
- **Promptor**: 提示词构建器（QAPromptor、ChatPromptor）
- **Generator**: LLM 生成器（OpenAI、vLLM、本地模型）
- **Evaluator**: 评估指标（BLEU、ROUGE、F1）

### Agent (智能体)

位于 `sage.libs.agent`:

- **Tool Calling**: 工具调用和参数解析
- **ReAct**: 推理-行动循环
- **Planning**: 任务规划和分解
- **Memory**: 对话历史和上下文管理

### Memory (内存管理)

位于 `sage.middleware.components.sage_db`:

- **VectorDB**: 基于 FAISS 的向量数据库
- **Metadata Filtering**: 元数据过滤
- **Multi-Index**: 多索引管理
- **Persistence**: 持久化存储

### I/O (输入输出)

位于 `sage.libs.io`:

- **Source**: FileSource、APISource、StreamSource
- **Sink**: TerminalSink、FileSink、DatabaseSink
- **Serialization**: JSON、Pickle、自定义序列化

## 示例应用

完整的示例代码位于 [examples 目录](https://github.com/intellistream/SAGE/tree/main-dev/examples)：

### 基础教程

- **Hello World**: 简单的批处理示例
- **Stream Processing**: 无限流处理
- **Service Integration**: 微服务集成

### RAG 应用

- **Basic RAG**: 基础检索增强生成
- **Multi-Document RAG**: 多文档检索
- **Conversational RAG**: 对话式 RAG

### Agent 应用

- **Tool Agent**: 工具调用 Agent
- **ReAct Agent**: 推理-行动 Agent
- **Planning Agent**: 任务规划 Agent

## CLI 工具

SAGE 提供强大的命令行工具：

```bash
# 系统诊断
sage doctor

# 扩展管理
sage extensions install all
sage extensions status

# 环境配置
sage config env setup
sage config env show

# 开发工具
sage-dev status      # 显示开发状态
sage-dev clean       # 清理构建产物

# 聊天界面（实验性）
sage chat
```

## 下一步

- 📖 阅读 [安装指南](get_start/install.md)
- 🚀 尝试 [快速开始](get_start/quickstart.md)
- 💻 查看 [示例代码](https://github.com/intellistream/SAGE/tree/main-dev/examples)
- 🤝 加入 [社区](join_sage/community.md)

## 许可证

SAGE 采用 [MIT 许可证](https://github.com/intellistream/SAGE/blob/main/LICENSE)。

```
```
