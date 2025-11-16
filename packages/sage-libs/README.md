# SAGE Libraries Package

## 📋 Overview

SAGE Libraries 是基于 SAGE Framework 构建的可复用组件库，提供了丰富的预构建功能模块来帮助开发者快速构建 AI 应用。

## 📚 Package Contents

### Layered Module Map

| Layer          | Description                                                                   | Modules                                                                                      |
| -------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `foundation`   | 低依赖度工具箱：工具基类、IO Source/Sink、上下文压缩、filters                 | `foundation.tools`, `foundation.io`, `foundation.context`, `foundation.filters` *(即将迁入)* |
| `agentic`      | LangChain 风格的 Agent 框架 + Workflow Optimizer                              | `agentic.agents`, `agentic.workflow`                                                         |
| `rag`          | RAG 组件（loaders/chunkers/retrievers/pipelines）。目前正在从 middleware 回迁 | `rag.loaders`, `rag.chunkers`, ... *(占位包，近期填充)*                                      |
| `integrations` | 第三方服务适配器（LLM、向量库、Observability 等）                             | `integrations.llm.openai`, `integrations.vector.milvus`, ...                                 |
| `privacy`      | 隐私/遗忘算法（原 `unlearning` 包）                                           | `privacy.unlearning`                                                                         |

> ⚠️ 兼容性：旧路径（例如 `sage.libs.tools`, `sage.libs.io`, `sage.libs.agents`）仍可导入，但会触发
> `DeprecationWarning`。请在 0.2.0 前迁移到新的命名空间。

### RAG Building Blocks

`sage.libs.rag` 现已提供可直接复用的核心组件：

- `chunk`：`CharacterSplitter`, `SentenceTransformersTokenTextSplitter`
- `document_loaders`：`TextLoader`, `PDFLoader`, `DocxLoader`, `DocLoader`, `MarkdownLoader`,
  `LoaderFactory`
- `pipeline`：轻量版 `RAGPipeline`
- `types`：`RAGDocument`, `RAGQuery`, `RAGResponse` 及辅助函数

Middleware 仍可通过原 import 路径访问这些类，但新的文档和示例将逐步切换到 `sage.libs.rag.*`。

## 🚀 Installation

### Basic Installation

```bash
# 基础安装（不包含 LibAMM）
pip install -e packages/sage-libs

# 或使用 sage-dev 命令
sage-dev install sage-libs
```

### With LibAMM (Approximate Matrix Multiplication)

LibAMM 是一个高性能的近似矩阵乘法 C++ 库，提供 NumPy 接口。

```bash
# 一键安装（推荐）- 自动编译 LibAMM
pip install -e "packages/sage-libs[amm]"

# 或手动安装
cd packages/sage-libs/src/sage/libs/libamm
pip install .
```

**要求**：

- CMake >= 3.10
- C++ 编译器 (g++ 或 clang++)
- PyTorch >= 2.0（会自动安装）

**特性**：

- ✅ 高性能 C++ 实现
- ✅ NumPy 接口（无需直接使用 PyTorch）
- ✅ 支持 18+ 种近似矩阵乘法算法
- 📖 详见 `src/sage/libs/libamm/DEPENDENCY_ISOLATION.md`

## 📖 Quick Start

```python
from sage_libs.llm import OpenAIAdapter
from sage_libs.vector_stores import FAISSStore
from sage_libs.embeddings import OpenAIEmbeddings

# 使用 LLM 适配器
llm = OpenAIAdapter(model="gpt-4")
response = llm.generate("Hello, world!")

# 使用向量存储
embeddings = OpenAIEmbeddings()
vector_store = FAISSStore(embeddings)
vector_store.add_texts(["document 1", "document 2"])
```

## 📄 License

MIT License - see [LICENSE](../../LICENSE) for details.
