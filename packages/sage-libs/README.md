# SAGE Libraries Package

## 📋 Overview

SAGE Libraries 是基于 SAGE Framework 构建的可复用组件库，提供了丰富的预构建功能模块来帮助开发者快速构建 AI 应用。

## 📚 Package Contents

### Core Libraries

SAGE Libraries 提供了以下核心库组件：

- **LLM Integrations**: 大语言模型集成和适配器
- **Vector Stores**: 向量数据库集成 (FAISS, Milvus, Pinecone 等)
- **Embeddings**: 嵌入模型封装和工具
- **Tools & Utilities**: 通用工具和辅助函数
- **Data Connectors**: 数据源连接器和加载器

## 🚀 Installation

```bash
# 基础安装
pip install -e packages/sage-libs

# 或使用 sage-dev 命令
sage-dev install sage-libs
```

### Optional: LibAMM (Approximate Matrix Multiplication)

LibAMM 是一个高性能的近似矩阵乘法库，作为独立的 C++ 扩展提供。如需使用：

```bash
# 安装 LibAMM（需要 C++ 编译环境）
cd packages/sage-libs/src/sage/libs/libamm
pip install .

# 这会自动安装 PyTorch 依赖
```

**注意**：

- LibAMM 需要 CMake 和 C++ 编译器
- 会自动安装 PyTorch（但用户只需使用 NumPy 接口）
- 详见 `libamm/DEPENDENCY_ISOLATION.md`

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
