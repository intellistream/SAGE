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
# 从 PyPI 安装（推荐）- 自动包含 LibAMM
pip install isage-libs

# 或在 SAGE 仓库中开发安装
pip install -e packages/sage-libs
```

**包含内容**：

- ✅ **LibAMM**：高性能近似矩阵乘法库（预编译，自动安装）

- ✅ **RAG 组件**：loaders, chunkers, retrievers, pipelines

- ✅ **Agent 框架**：LangChain 风格的 Agent + Workflow Optimizer

- ✅ **隐私算法**：unlearning, privacy preservation

- ✅ **集成组件**：LLM, Vector DB 适配器

### 架构说明

**sage-libs 的设计理念**：

```
isage-libs (PyPI)
  └── 依赖 isage-libamm (自动安装预编译版本)
  └── 可选 isage-anns (独立安装 ANNS 算法)
```

- 📦 **isage-libs**：课题组算法集合的统一入口
- 📦 **isage-libamm**：独立维护和发布的 C++ 扩展包（自动安装）
- 📦 **isage-anns**：独立维护的 ANNS 算法包（可选安装）
- 🎯 **一键安装**：用户只需 `pip install isage-libs`，libamm 自动包含
- 🔧 **按需安装 ANNS**：如需 ANNS 算法，额外执行 `pip install isage-anns`

### Optional: ANNS Algorithms

ANNS (Approximate Nearest Neighbor Search) algorithms have been moved to an independent repository:

```bash
# 安装 ANNS 算法包（可选）
pip install isage-anns
```

- 📦 **Repository**: https://github.com/intellistream/sage-anns
- 📦 **PyPI**: https://pypi.org/project/isage-anns/
- 🔍 **Algorithms**: FAISS, DiskANN, CANDY, PUCK, SPTAG, etc.
- 📖 **Documentation**: See `docs/anns/MIGRATION.md` for migration details

### LibAMM 开发者模式

如果需要修改 LibAMM 源码：

```bash
# 克隆 LibAMM 独立仓库
git clone https://github.com/intellistream/LibAMM.git
cd LibAMM

# 编译并安装
./buildCPUOnly.sh  # CPU 版本
# 或
./buildWithCuda.sh  # GPU 版本（需要 CUDA）

pip install -e .
```

或者在 SAGE 主仓库中（作为子模块）：

```bash
cd packages/sage-libs/src/sage/libs/libamm
./buildCPUOnly.sh
```

# 或手动安装

cd packages/sage-libs/src/sage/libs/libamm pip install .

````

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
````

## 📄 License

MIT License - see [LICENSE](../../LICENSE) for details.

______________________________________________________________________

## 🤖 Agent Fine-tuning Module

The `sage.libs.finetune.agent` module provides specialized tools for fine-tuning language models on
agent tasks, including tool calling, planning, and timing judgment.

### Quick Start

```python
from sage.libs.finetune.agent import AgentSFTConfig, AgentSFTTrainer

# Basic configuration
config = AgentSFTConfig(
    base_model="Qwen/Qwen2.5-1.5B-Instruct",
    train_data="agent_sft:train",
    num_epochs=1,
)

# Create and run trainer
trainer = AgentSFTTrainer(config)
trainer.train()
```

### Available Training Methods

| Method ID           | Name                | Description              | Key Features                     |
| ------------------- | ------------------- | ------------------------ | -------------------------------- |
| `A_baseline`        | Baseline            | Standard SFT             | No enhancements                  |
| `B3_coreset_hybrid` | Coreset (Hybrid)    | 60% loss + 40% diversity | `coreset_strategy="hybrid"`      |
| `C_continual`       | Continual Learning  | Experience replay buffer | `use_continual=True`             |
| `D_combined`        | Coreset + Continual | Best of both approaches  | Combined                         |
| `E_fireact`         | FireAct             | Trajectory fine-tuning   | `use_trajectory_collection=True` |
| `F_agenttuning`     | AgentTuning         | Multi-task training      | `use_multi_task=True`            |
| `G_dora`            | DoRA                | Weight-decomposed LoRA   | `use_dora=True`                  |
| `H_lora_plus`       | LoRA+               | Differentiated LR        | `use_lora_plus=True`             |

### Key Components

| Component                | Description                   | Import Path                                  |
| ------------------------ | ----------------------------- | -------------------------------------------- |
| `AgentSFTTrainer`        | Main trainer class            | `sage.libs.finetune.agent`                   |
| `CoresetSelector`        | Sample selection (SIAS)       | `sage.libs.sias`                             |
| `OnlineContinualLearner` | Experience replay (SIAS)      | `sage.libs.sias`                             |
| `TrajectoryCollector`    | FireAct trajectory collection | `sage.libs.finetune.agent`                   |
| `MultiTaskMixer`         | AgentTuning data mixing       | `sage.libs.finetune.agent`                   |
| `MethodRegistry`         | Predefined methods            | `sage.benchmark.benchmark_agent.experiments` |

> **Note**: `CoresetSelector` and `OnlineContinualLearner` have been moved to the SIAS module
> (`sage.libs.sias`). They are re-exported from `sage.libs.finetune.agent` for backward
> compatibility.

For detailed API documentation, see
[Agent Fine-tuning API Reference](../../docs/dev-notes/l3-libs/AGENT_FINETUNE_API_REFERENCE.md).
