# SAGE Libraries Package

## 📋 Overview

SAGE Libraries 是基于 SAGE Framework 构建的可复用组件库，提供了丰富的预构建功能模块来帮助开发者快速构建 AI 应用。

## 📚 Package Contents（接口层定位）

`sage-libs` 现在定位为 **接口/注册表层**，重型实现迁出为独立 PyPI 包。

### 🎯 Top-Level Domains (L3 Algorithm Libraries)

The library is organized into clear functional domains:

#### 1. **Agentic & Orchestration** (`agentic/`)

- **Planning**: ToT, ReAct, hierarchical, dependency graph, timing deciders
- **Tool Selection**: keyword/embedding/hybrid/DFS-DT, Gorilla adapters, registry
- **Multi-bot Roles**: answer/critic/question/searcher
- **Runtime Glue**: orchestrator, adapters, telemetry contracts
- **Intent**: intent classifiers/recognizers and catalogs

#### 2. **Retrieval & RAG Toolkit** (`rag/`)

- **Loaders**: Document loaders for various formats (PDF, DOCX, Markdown, etc.)
- **Chunking**: Text segmentation and chunking strategies
- **Future**: Retriever interfaces, rerankers, context builders, post-processing

#### 3. **ANN / Vector Index Algorithms** (`ann/`)

- **Registry & Factory**: Unified interface for ANN algorithms
- **Base Classes**: `AnnIndex`, `AnnIndexMeta`
- **External Implementations**: `isage-anns` package (HNSW, IVF, DiskANN, etc.)
- **Used By**: SageVDB backend, benchmark_anns, RAG pipelines

#### 4. **Reasoning & Optimization Primitives** (`reasoning/`)

- **Search Algorithms**: Beam search, DFS, BFS, UCT, Monte Carlo
- **Scoring & Aggregation**: Utility functions, voting, self-consistency
- **Future**: SMT/ILP hooks for constraint satisfaction

#### 5. **Dataflow Helpers** (`dataops/`)

- **Text Operations**: Normalization, truncation, keyword extraction
- **Table Operations**: Filtering, aggregation, sorting, pivoting
- **JSON Operations**: Schema validation, field extraction, flattening
- **Sampling**: Random, stratified, reservoir sampling; outlier filtering

#### 6. **Evaluation & Profiling** (`eval/`)

- **Metrics**: Accuracy, precision/recall, F1, BLEU, MRR
- **Telemetry**: Span and trace helpers for profiling
- **Determinism**: Seed control and reproducibility utilities

#### 7. **Safety & Guardrails** (`safety/`)

- **Content Filtering**: Regex/pattern-based content filters
- **PII Scrubbing**: Simple PII detection and scrubbing
- **Policy Checks**: Tool call policy validation

#### 8. **SIAS (Internal Reasoning / Tool Selection)** (`sias/`)

- **CoresetSelector**: Importance-aware sample selection for agent tool/trajectory curation
- **OnlineContinualLearner**: Replay buffer with importance weighting
- **Future**: StreamingImportanceScorer for streaming traces

### 📦 External Packages

| Domain       | In this repo (stable surface)                 | External package (impl)          | Status    |
| ------------ | --------------------------------------------- | -------------------------------- | --------- |
| Agentic      | Protocols, planners/tool-selection registries | `isage-agentic` (planned)        | 🚧        |
| RAG toolkit  | Protocols, light pipelines                    | `isage-rag` (planned)            | 🚧        |
| ANN          | Registry, type hints                          | `isage-anns`                     | ✅ 已独立 |
| AMM          | Registry, type hints                          | `isage-amms`                     | 🚧 迁移中 |
| Integrations | Thin adapters only                            | heavy clients as optional extras | 🚧        |
| Privacy      | Protocols and shared utils                    | `isage-privacy` (planned)        | 🚧        |
| Foundation   | Low-dependency helpers (pure Python)          | n/a                              | ✅        |
| SIAS         | Streaming importance-aware agent system       | `isage-sias` (planned)           | 🚧        |

## 🚀 Installation

### Basic Installation

```bash
# 从 PyPI 安装（推荐）- 自动包含 LibAMM
pip install isage-libs

# 或在 SAGE 仓库中开发安装
pip install -e packages/sage-libs
```

**包含内容**：

- ✅ **RAG 组件**：loaders, chunkers, retrievers, pipelines
- ✅ **Agent 框架**：LangChain 风格的 Agent + Workflow Optimizer
- ✅ **隐私算法**：unlearning, privacy preservation
- ✅ **集成组件**：LLM, Vector DB 适配器

**可选扩展（独立仓库，需单独安装）**：

- 🔧 **AMM 算法**：`pip install isage-amms`
- 🔧 **ANNS 算法**：`pip install isage-anns`

### 架构说明

**sage-libs 的设计理念**：

```
isage-libs (PyPI) - 纯 Python 算法库
  ├── 可选依赖: isage-amms（独立仓库，C++ 扩展）
  └── 可选依赖: isage-anns（独立仓库，C++ 扩展）
```

- 📦 **isage-libs**：SAGE 算法库的统一接口和纯 Python 实现
- 📦 **isage-amms**：AMM 算法独立包（可选）
  - 仓库：`packages/sage-libs/src/sage/libs/amms/`（待迁移独立仓库）
  - 状态：独立可选依赖，不自动安装
  - PyPI: https://pypi.org/project/isage-amms/
- 📦 **isage-anns**：ANNS 算法独立包（可选）
  - 仓库：https://github.com/intellistream/sage-anns
  - 状态：已完全迁移到独立仓库
  - PyPI: https://pypi.org/project/isage-anns/
- 🎯 **安装方式**：
  - 基础安装：`pip install isage-libs`（不含 C++ 扩展）
  - AMM 扩展：`pip install isage-amms`（可选，高性能矩阵运算）
  - ANNS 扩展：`pip install isage-anns`（可选，向量检索算法）

### Optional Extensions（独立包）

> **重要**：所有可选扩展都通过 `pyproject.toml` 的 extras 声明安装；不要手动 `pip install`。

#### ANNS

- 外部包：`isage-anns`（已独立）
- 本仓库仅保留注册表/类型；即将移除本地实现代码

#### AMMS

- 外部包：`isage-amms`（迁移中）
- 本仓库仅保留注册表/类型；实现位于外部包

#### Agentic / RAG / Privacy

- 规划中：拆分为对应独立包（`isage-agentic`, `isage-rag`, `isage-privacy`），本仓库保留接口

**安装示例（使用 extras）**

```bash
pip install -e packages/sage-libs[anns,amms]
```

在 CI/开发脚本中使用 extras，避免裸命令 `pip install <pkg>`。

### Development Mode

#### LibAMM 开发者模式

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
| `CoresetSelector`        | Sample selection (SIAS)       | `sage.libs.agentic.sias`                     |
| `OnlineContinualLearner` | Experience replay (SIAS)      | `sage.libs.agentic.sias`                     |
| `TrajectoryCollector`    | FireAct trajectory collection | `sage.libs.finetune.agent`                   |
| `MultiTaskMixer`         | AgentTuning data mixing       | `sage.libs.finetune.agent`                   |
| `MethodRegistry`         | Predefined methods            | `sage.benchmark.benchmark_agent.experiments` |

> **Note**: `CoresetSelector` and `OnlineContinualLearner` are part of the SIAS module
> (`sage.libs.agentic.sias`). They are re-exported from `sage.libs.finetune.agent` for backward
> compatibility.

For detailed API documentation, see
[Agent Fine-tuning API Reference](../../docs/dev-notes/l3-libs/AGENT_FINETUNE_API_REFERENCE.md).
