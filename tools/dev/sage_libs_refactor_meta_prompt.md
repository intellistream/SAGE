# SAGE-Libs 重构 Meta 提示词

## 🎯 重构目标

将 sage-libs 从单体库重构为**轻量级接口层 + 独立算子库生态**，以支持复合型 AI 系统的构建。

## 📋 重构原则

### 1. **接口层优先**（Interface-First Design）

- sage-libs 保留：抽象基类、工厂模式、注册表
- 独立库提供：具体实现、重型依赖、算法细节

### 2. **领域驱动分离**（Domain-Driven Separation）

- 按功能领域拆分（Agentic、RAG、ANN、Privacy 等）
- 每个领域独立仓库、独立版本、独立发布

### 3. **最小依赖原则**（Minimal Dependencies）

- sage-libs 依赖：sage-common, sage-kernel (可选)
- 独立库依赖：sage-libs (接口) + 各自特定依赖

### 4. **文档精简原则**（Documentation Minimalism）

- sage-libs 文档：架构概览、接口说明、集成指南
- 独立库文档：详细 API、使用示例、benchmark 结果

## 🏗️ 目标架构

基于复合型 AI 系统的核心需求，重新设计为 **5 大核心接口领域 + 3 个保留模块**：

```
sage-libs (接口层, L3)
│
├── [保留模块 - 轻量级实现]
│   ├── foundation/        # 保留：纯 Python 工具库（工具注册、IO 抽象、上下文压缩）
│   ├── dataops/           # 保留：轻量级数据操作（文本/表格/JSON 操作、采样）
│   └── integrations/      # 保留：瘦适配器层（HF、VectorDB、Observability）
│
├── [核心接口领域 1: 智能体与编排]
│   └── agentic/interface/
│       ├── base.py        # BaseAgent, BasePlanner, BaseToolSelector, BaseOrchestrator
│       ├── factory.py     # 注册表：agents, planners, selectors, orchestrators
│       └── protocols.py   # AgentAction, AgentResult, PlanStep, ToolSpec
│       → isage-agentic (独立库)
│          包含：ReAct/ReWOO/ToT agents, 工具选择算法, 多智能体协作, SIAS 组件
│
├── [核心接口领域 2: 检索与知识处理]
│   └── rag/interface/
│       ├── base.py        # BaseLoader, BaseChunker, BaseRetriever, BaseReranker
│       ├── factory.py     # 注册表：loaders, chunkers, retrievers, rerankers
│       └── protocols.py   # Document, Chunk, RetrievalResult, RerankScore
│       → isage-rag (独立库)
│          包含：多格式加载器, 智能分块, 混合检索, 上下文压缩, Query 改写
│
├── [核心接口领域 3: 向量与近似算法]
│   ├── anns/interface/    # 近似最近邻搜索
│   │   ├── base.py        # AnnIndex, AnnIndexMeta
│   │   ├── factory.py     # 注册表：索引类型 (HNSW, IVF, DiskANN, etc.)
│   │   └── protocols.py   # SearchParams, SearchResult, IndexConfig
│   │   → isage-anns (独立库) ✅
│   │
│   └── amms/interface/    # 近似矩阵乘法
│       ├── base.py        # BaseAMM, BaseSketch
│       ├── factory.py     # 注册表：AMM 算法
│       └── protocols.py   # SketchConfig, CompressionResult
│       → isage-amms (独立库) 🚧
│
├── [核心接口领域 4: 模型优化与评估]
│   ├── finetune/interface/
│   │   ├── base.py        # BaseTrainer, BaseStrategy, BaseCallback
│   │   ├── factory.py     # 注册表：训练策略 (LoRA, QLoRA, Full FT, PEFT)
│   │   └── protocols.py   # TrainingConfig, TrainingResult, CheckpointInfo
│   │   → isage-finetune (独立库)
│   │      包含：LoRA/QLoRA, 分布式训练, 参数高效微调, 持续学习
│   │
│   └── eval/interface/
│       ├── base.py        # BaseMetric, BaseProfiler, BaseBenchmark
│       ├── factory.py     # 注册表：metrics, profilers, benchmarks
│       └── protocols.py   # EvalResult, ProfileResult, BenchmarkConfig
│       → isage-eval (独立库)
│          包含：准确率/F1/BLEU/ROUGE, 性能分析, A/B 测试, LLM-as-Judge
│
└── [核心接口领域 5: 安全与隐私]
    ├── safety/            # 保留基础实现 + 接口扩展
    │   ├── content_filter.py      # 保留：轻量级内容过滤
    │   ├── pii_scrubber.py        # 保留：简单 PII 检测
    │   ├── policy_check.py        # 保留：策略验证
    │   └── interface/             # 新增：高级安全接口
    │       ├── base.py            # BaseGuardrail, BaseJailbreakDetector
    │       ├── factory.py         # 注册表：guardrails, detectors
    │       → isage-safety (独立库, 可选)
    │          包含：高级 Jailbreak 检测, 对抗样本防御, Prompt 注入检测
    │
    └── privacy/interface/
        ├── base.py        # BaseUnlearner, BasePrivacyMechanism, BaseDPOptimizer
        ├── factory.py     # 注册表：unlearning 算法, 差分隐私机制
        └── protocols.py   # UnlearningConfig, PrivacyBudget, DPResult
        → isage-privacy (独立库)
           包含：机器遗忘 (SISA, Amnesiac), 差分隐私, 联邦学习, 同态加密
```

### 🎯 设计原则

1. **SIAS 不单独成库**：SIAS 是 agentic 的高级特性，作为 `isage-agentic[sias]` 的可选安装
1. **Intent 合并到 Agentic**：意图识别是智能体的输入理解模块，不独立
1. **Reasoning 合并到 Agentic**：搜索/规划算法是智能体的核心能力
1. **Safety 保留基础实现**：轻量级过滤保留在 sage-libs，高级检测独立为 isage-safety（可选）
1. **Foundation/DataOps/Integrations 完全保留**：无重型依赖，是其他模块的基础

## 📦 独立库清单（精简版）

| 库名               | PyPI 包名      | 仓库名        | 功能范围                                                       | 状态        | 优先级 | 负责 Agent |
| ------------------ | -------------- | ------------- | -------------------------------------------------------------- | ----------- | ------ | ---------- |
| **向量与近似算法** |                |               |                                                                |             |        |            |
| ANN Algorithms     | isage-anns     | sage-anns     | HNSW/IVF/DiskANN/CANDY/GTI 等                                  | ✅ 已完成   | P0     | -          |
| AMM Algorithms     | isage-amms     | sage-amms     | 矩阵乘法近似、Sketch 算法                                      | 🚧 进行中   | P0     | -          |
| **智能体与编排**   |                |               |                                                                |             |        |            |
| Agentic Framework  | isage-agentic  | sage-agentic  | Agents + Planning + Tool Selection + SIAS + Intent + Reasoning | 🚧 部分完成 | P1     | Agent-1    |
| **检索与知识**     |                |               |                                                                |             |        |            |
| RAG Toolkit        | isage-rag      | sage-rag      | Loaders + Chunkers + Retrievers + Rerankers + Query Rewrite    | � 部分完成  | P1     | Agent-2    |
| **模型优化**       |                |               |                                                                |             |        |            |
| Fine-tuning        | isage-finetune | sage-finetune | LoRA/QLoRA/PEFT + 分布式训练                                   | 📝 规划中   | P2     | Agent-3    |
| Evaluation         | isage-eval     | sage-eval     | Metrics + Profiling + Benchmarking                             | 📝 规划中   | P2     | Agent-4    |
| **安全与隐私**     |                |               |                                                                |             |        |            |
| Privacy Protection | isage-privacy  | sage-privacy  | Unlearning + DP + FL + 同态加密                                | 📝 规划中   | P2     | Agent-5    |
| Safety (可选)      | isage-safety   | sage-safety   | 高级 Guardrails + Jailbreak 检测                               | 📝 规划中   | P3     | Agent-6    |

**注意**：

- **SIAS**：作为 `isage-agentic` 的子模块 (`isage-agentic[sias]`)
- **Intent**：合并到 `isage-agentic` (`isage-agentic.intent`)
- **Reasoning**：合并到 `isage-agentic` (`isage-agentic.reasoning`)
- **Safety 基础功能**：保留在 `sage-libs.safety`，高级功能可选独立为 `isage-safety`

### 🎯 仓库创建策略

**需要创建的新仓库**（6个 → 4个）：

1. ✅ sage-privacy
1. ✅ sage-finetune
1. ✅ sage-eval
1. ⚠️ sage-safety（可选，P3 优先级）

**不需要创建的仓库**（已合并）：

- ❌ sage-intent → 合并到 sage-agentic
- ❌ sage-reasoning → 合并到 sage-agentic
- ❌ sage-sias → 合并到 sage-agentic

## 🔄 工作流程

### Phase 1: 准备阶段（Agent-0: Orchestrator）

1. ✅ 检查已有独立仓库状态
1. ✅ 创建缺失的独立仓库（仅 4 个：privacy, finetune, eval, safety）
1. ✅ 设置分支策略（main, main-dev）
1. ✅ 配置 CI/CD 模板

### Phase 2: 代码迁移（Agent-1 到 Agent-6 并行）

**Agent-1: Agentic（最复杂）**

- 创建 `sage-libs/agentic/interface/` 接口层
- 迁移到 `sage-agentic`：agents, planners, tool_selection
- 合并 intent → `sage-agentic/intent/`
- 合并 reasoning → `sage-agentic/reasoning/`
- 合并 SIAS → `sage-agentic/sias/` (可选安装)

**Agent-2: RAG**

- 创建 `sage-libs/rag/interface/` 接口层
- 迁移到 `sage-rag`：loaders, chunkers, retrievers, rerankers

**Agent-3: Fine-tuning**

- 创建 `sage-libs/finetune/interface/` 接口层
- 实现基础训练策略到 `sage-finetune`

**Agent-4: Evaluation**

- 创建 `sage-libs/eval/interface/` 接口层（新建）
- 实现评估指标到 `sage-eval`

**Agent-5: Privacy**

- 创建 `sage-libs/privacy/interface/` 接口层
- 迁移 unlearning 实现到 `sage-privacy`

**Agent-6: Safety（可选）**

- 保持 `sage-libs/safety/` 基础实现
- (可选) 创建 `sage-libs/safety/interface/` 高级接口
- (可选) 实现到 `sage-safety`

### Phase 3: 文档重构（Agent-7: Documentation）

1. sage-libs 主文档：5 大接口领域架构图
1. 每个独立库：详细 API 文档 + 示例
1. 清理 sage-libs 过时文档（保留架构、快速开始、集成指南）
1. 生成跨库集成教程

### Phase 4: 验证和发布（Agent-8: Validator）

1. 集成测试（sage-libs + 所有独立库）
1. 版本号对齐
1. PyPI 发布（TestPyPI → PyPI）
1. 更新主仓库依赖

## 📝 接口设计模板

每个接口层必须包含：

```python
# interface/__init__.py
"""Interface for {MODULE_NAME}.

External implementations: isage-{MODULE_NAME}
"""
from .base import *
from .factory import *

# interface/base.py
"""Base classes and protocols."""
from abc import ABC, abstractmethod

class {Module}Base(ABC):
    @abstractmethod
    def execute(self, **kwargs):
        pass

# interface/factory.py
"""Registry and factory."""
_REGISTRY: dict[str, type] = {}

def register(name: str, cls: type) -> None:
    ...

def create(name: str, **kwargs):
    ...
```

## 🎯 成功标准

- [ ] 4 个新仓库已创建（privacy, finetune, eval, safety-可选）
- [ ] sage-libs 代码量减少 60%+（保留接口 + foundation/dataops/safety 基础）
- [ ] 5 大核心接口领域清晰定义（agentic, rag, anns/amms, finetune/eval, privacy/safety）
- [ ] 所有独立库可独立安装（pip install isage-xxx）
- [ ] sage-libs 通过 extras 可选依赖：`pip install isage-libs[agentic,rag,all]`
- [ ] 集成测试覆盖率 > 80%
- [ ] 文档清晰：架构图 + 5 大领域接口说明 + 快速集成指南
- [ ] 所有库发布到 PyPI（TestPyPI 验证后）

## 🚀 Agent 任务分配

总计 **8 个 Agent**（相比之前减少 2 个）：

- Agent-0: 仓库编排器（准备 4 个新仓库）
- Agent-1: Agentic 重构（含 Intent, Reasoning, SIAS 合并）
- Agent-2: RAG 重构
- Agent-3: Fine-tuning 重构
- Agent-4: Evaluation 重构（新建）
- Agent-5: Privacy 重构
- Agent-6: Safety 重构（可选）
- Agent-7: 文档重构
- Agent-8: 集成验证与发布

见下方各 Agent 的专属提示词文件。
