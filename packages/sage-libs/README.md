# SAGE Libraries Package (sage-libs)

## 📋 Overview

**sage-libs** 是 SAGE 框架的算法库层，定位为 **接口/注册表层 (Interface Layer)**。

## 🧭 Governance / 团队协作制度

- `docs/governance/TEAM.md`
- `docs/governance/MAINTAINERS.md`
- `docs/governance/DEVELOPER_GUIDE.md`
- `docs/governance/PR_CHECKLIST.md`
- `docs/governance/SELF_HOSTED_RUNNER.md`
- `docs/governance/TODO.md`

核心设计原则：

- 📦 **轻量级接口**：定义抽象基类和工厂函数
- 🔌 **可插拔实现**：重型实现迁出为独立 PyPI 包 (`isage-*`)
- 🏗️ **注册表模式**：通过 `register_*` / `create_*` 动态加载实现

## 🏗️ Architecture

```
sage-libs (Interface Layer)
    ├── agentic/interface/     → isage-agentic (Agent framework)
    ├── rag/interface/         → isage-rag (RAG toolkit)
    ├── finetune/interface/    → isage-finetune (Fine-tuning)
    ├── eval/interface/        → isage-eval (Evaluation)
    ├── privacy/interface/     → isage-privacy (Privacy/Unlearning)
    ├── safety/interface/      → isage-safety (Guardrails)
    ├── ann/interface/         → isage-anns (ANNS algorithms)
    ├── amms/interface/        → isage-amms (AMM algorithms)
    └── foundation/            → Built-in utilities (no external deps)
```

## 📚 Five Core Domains

### 1. 🤖 Agentic (Agent Framework)

**接口**：`sage.libs.agentic.interface`

| Base Class              | Description                                 |
| ----------------------- | ------------------------------------------- |
| `BaseAgent`             | Agent execution interface                   |
| `BasePlanner`           | Task planning (ToT, ReAct, Hierarchical)    |
| `BaseToolSelector`      | Tool selection (Keyword, Embedding, Hybrid) |
| `BaseOrchestrator`      | Multi-agent orchestration                   |
| `IntentRecognizer`      | Intent recognition                          |
| `IntentClassifier`      | Intent classification                       |
| `BaseReasoningStrategy` | Reasoning strategies (CoT, ToT, ReAct)      |

```python
from sage.libs.agentic.interface import (
    BaseAgent, BasePlanner, BaseToolSelector,
    create_agent, create_planner, register_agent
)

# Register implementation (from isage-agentic)
register_agent("react", ReactAgent)

# Create via factory
agent = create_agent("react", tools=[...])
```

### 2. 📖 RAG (Retrieval-Augmented Generation)

**接口**：`sage.libs.rag.interface`

| Base Class       | Description                            |
| ---------------- | -------------------------------------- |
| `DocumentLoader` | Document loading (PDF, DOCX, MD, etc.) |
| `TextChunker`    | Text segmentation                      |
| `Retriever`      | Vector/BM25 retrieval                  |
| `Reranker`       | Reranking (Cross-Encoder, LLM)         |
| `QueryRewriter`  | Query rewriting (HyDE, Multi-Query)    |
| `RAGPipeline`    | End-to-end RAG pipeline                |

```python
from sage.libs.rag.interface import (
    DocumentLoader, Retriever, RAGPipeline,
    create_loader, create_retriever, create_pipeline
)

loader = create_loader("pdf")
retriever = create_retriever("faiss", dimension=768)
```

### 3. 🔧 Fine-tuning

**接口**：`sage.libs.finetune.interface`

| Base Class         | Description                             |
| ------------------ | --------------------------------------- |
| `FineTuner`        | Fine-tuning trainer                     |
| `DatasetLoader`    | Training data loading                   |
| `TrainingCallback` | Training callbacks (WandB, TensorBoard) |
| `TrainingStrategy` | PEFT strategies (LoRA, QLoRA, Prefix)   |

```python
from sage.libs.finetune.interface import (
    FineTuner, TrainingStrategy, TrainingConfig, LoRAConfig,
    create_trainer, create_strategy
)

strategy = create_strategy("lora")
trainer = create_trainer("lora", model_name="gpt2")
```

### 4. 📊 Evaluation

**接口**：`sage.libs.eval.interface`

| Base Class      | Description                                |
| --------------- | ------------------------------------------ |
| `BaseMetric`    | Evaluation metrics (Accuracy, BLEU, ROUGE) |
| `BaseLLMJudge`  | LLM-as-a-Judge (Faithfulness, Relevance)   |
| `BaseProfiler`  | Performance profiling                      |
| `BaseBenchmark` | Benchmark suites                           |

```python
from sage.libs.eval.interface import (
    BaseMetric, BaseLLMJudge, MetricResult,
    create_metric, create_judge
)

metric = create_metric("accuracy")
judge = create_judge("faithfulness", model="gpt-4")
```

### 5. 🔒 Privacy & Safety

**Privacy 接口**：`sage.libs.privacy.interface`

| Base Class                   | Description                                |
| ---------------------------- | ------------------------------------------ |
| `BaseUnlearner`              | Machine unlearning (SISA, Gradient Ascent) |
| `BasePrivacyMechanism`       | DP mechanisms (Laplace, Gaussian)          |
| `BaseDPOptimizer`            | DP optimizers (DP-SGD, DP-Adam)            |
| `BaseFederatedClient/Server` | Federated learning                         |

**Safety 接口**：`sage.libs.safety.interface`

| Base Class               | Description                          |
| ------------------------ | ------------------------------------ |
| `BaseGuardrail`          | Content safety guardrails            |
| `BaseJailbreakDetector`  | Jailbreak/prompt injection detection |
| `BaseToxicityDetector`   | Toxicity detection                   |
| `BaseAdversarialDefense` | Adversarial input defense            |

```python
from sage.libs.privacy import create_unlearner, create_mechanism
from sage.libs.safety import create_guardrail, create_jailbreak_detector

unlearner = create_unlearner("sisa", num_shards=5)
guardrail = create_guardrail("llm", model="gpt-4")
```

## 📦 External Packages (isage-\*)

| Domain      | Interface (sage-libs) | Implementation (PyPI) | Status       |
| ----------- | --------------------- | --------------------- | ------------ |
| Agentic     | `agentic/interface/`  | `isage-agentic`       | 🚧 Planned   |
| RAG         | `rag/interface/`      | `isage-rag`           | 🚧 Planned   |
| Fine-tuning | `finetune/interface/` | `isage-finetune`      | 🚧 Planned   |
| Evaluation  | `eval/interface/`     | `isage-eval`          | 🚧 Planned   |
| Privacy     | `privacy/interface/`  | `isage-privacy`       | 🚧 Planned   |
| Safety      | `safety/interface/`   | `isage-safety`        | 🚧 Planned   |
| ANNS        | `ann/interface/`      | `isage-anns`          | ✅ Available |
| AMM         | `amms/interface/`     | `isage-amms`          | 🚧 Migration |

## 🚀 Installation

### Basic Installation

```bash
# From PyPI
pip install isage-libs

# Development install (in SAGE repo)
pip install -e packages/sage-libs
```

### With Optional Extras

```bash
# All interfaces
pip install isage-libs[all]

# Specific domains
pip install isage-libs[agentic]    # Agent framework
pip install isage-libs[rag]         # RAG toolkit
pip install isage-libs[finetune]    # Fine-tuning
pip install isage-libs[eval]        # Evaluation
pip install isage-libs[privacy]     # Privacy/Unlearning
pip install isage-libs[safety]      # Safety/Guardrails
```

## 🏛️ Built-in Utilities

These modules are included directly (no external deps):

### Foundation (`foundation/`)

```python
from sage.libs.foundation import (
    text_utils,    # Text processing
    io_utils,      # File I/O helpers
    async_utils,   # Async utilities
)
```

### DataOps (`dataops/`)

```python
from sage.libs.dataops import (
    text_ops,      # Normalization, truncation
    table_ops,     # DataFrame operations
    json_ops,      # JSON processing
    sampling,      # Sampling strategies
)
```

### Lightweight Safety (`safety/`)

```python
from sage.libs.safety import (
    content_filter,  # Pattern-based filtering
    pii_scrubber,    # PII detection
    policy_check,    # Policy validation
)
```

## 📖 Usage Example

```python
# 1. Define custom implementation
from sage.libs.agentic.interface import BaseAgent, AgentResult, register_agent

class MyAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "my_agent"

    def run(self, task, context=None):
        # Implementation
        return AgentResult(success=True, output="Done")

# 2. Register implementation
register_agent("my_agent", MyAgent)

# 3. Use via factory
from sage.libs.agentic.interface import create_agent
agent = create_agent("my_agent")
result = agent.run("Hello")
```

## 📚 Documentation

- **Architecture**: `docs-public/docs_src/dev-notes/l3-libs/`
- **API Reference**: `docs-public/docs_src/api-reference/sage-libs/`
- **Tutorials**: `examples/tutorials/L3-libs/`

## 🔗 Related Packages

- [SAGE](https://github.com/intellistream/SAGE) - Main framework
- [sage-benchmark](https://github.com/intellistream/sage-benchmark) - Evaluation benchmarks
- [SageVDB](https://github.com/intellistream/sageVDB) - Vector database
- [NeuroMem](https://github.com/intellistream/NeuroMem) - Memory system

## 📄 License

Apache 2.0 License
