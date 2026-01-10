# sage-libs 接口层完成总结

**日期**: 2026-01-10\
**状态**: ✅ 完成

## 概览

为 sage-libs 中的外迁模块创建了统一的接口层架构，遵循 ANNS/AMMS 的成功模式。

## 完成的接口层

### 1. ✅ agentic/interface/ - Agent 框架接口

**位置**: `packages/sage-libs/src/sage/libs/agentic/interface/`

**核心抽象**:

- `Agent` - Agent 基类（run, reset, stream）
- `Planner` - 规划器（plan, replan）
- `ToolSelector` - 工具选择器（select, rank）
  - **SIAS 应该在这里实现**（isage-agentic 包中）
- `WorkflowEngine` - 工作流引擎（execute, add_step）

**数据类型**:

- `AgentResponse` - Agent 响应结构

**工厂函数**:

- `register_agent()`, `create_agent()`
- `register_planner()`, `create_planner()`
- `register_tool_selector()`, `create_tool_selector()`
- `register_workflow_engine()`, `create_workflow_engine()`

**目标包**: `isage-agentic`

______________________________________________________________________

### 2. ✅ finetune/interface/ - 模型微调接口

**位置**: `packages/sage-libs/src/sage/libs/finetune/interface/`

**核心抽象**:

- `FineTuner` - 微调器（train, evaluate, save_model, load_model）
- `DatasetLoader` - 数据集加载器（load, preprocess, stream）

**数据类型**:

- `TrainingConfig` - 训练配置（20+ 超参数）
- `LoRAConfig` - LoRA 配置（rank, alpha, dropout, etc.）

**工厂函数**:

- `register_trainer()`, `create_trainer()`
- `register_loader()`, `create_loader()`

**目标包**: `isage-finetune`

______________________________________________________________________

### 3. ✅ rag/interface/ - RAG 组件接口

**位置**: `packages/sage-libs/src/sage/libs/rag/interface/`

**核心抽象**:

- `DocumentLoader` - 文档加载器（load, load_batch, supported_formats）
- `TextChunker` - 文本分块器（chunk, chunk_document）
- `Retriever` - 检索器（retrieve, add_documents, delete_documents）
- `Reranker` - 重排序器（rerank）
- `RAGPipeline` - RAG 流程（index_documents, query, configure）

**数据类型**:

- `Document` - 文档（content, metadata）
- `Chunk` - 文本块（text, start_pos, end_pos, metadata）
- `RetrievalResult` - 检索结果（document, score, rank）

**工厂函数**:

- `register_loader()`, `create_loader()`
- `register_chunker()`, `create_chunker()`
- `register_retriever()`, `create_retriever()`
- `register_reranker()`, `create_reranker()`
- `register_pipeline()`, `create_pipeline()`

**目标包**: `isage-rag` (可选)

______________________________________________________________________

### 4. ✅ intent/interface/ - 意图识别接口

**位置**: `packages/sage-libs/src/sage/libs/intent/interface/`

**核心抽象**:

- `IntentRecognizer` - 意图识别器（recognize, recognize_batch, get_top_k）
- `IntentClassifier` - 意图分类器（classify, classify_with_confidence, train）
- `IntentCatalog` - 意图目录（add_intent, get_intent, list_intents, search_intents）
- `IntentSlotExtractor` - 槽位提取器（extract_slots, extract_slot_by_name）

**数据类型**:

- `Intent` - 意图（name, confidence, slots, metadata）
- `IntentDefinition` - 意图定义（name, description, examples, slots, patterns）
- `Slot` - 槽位（name, value, entity_type, confidence）

**工厂函数**:

- `register_recognizer()`, `create_recognizer()`
- `register_classifier()`, `create_classifier()`
- `register_catalog()`, `create_catalog()`
- `register_extractor()`, `create_extractor()`

**目标包**: `isage-intent` (可选)

______________________________________________________________________

## ❌ 删除的模块

### sias/ - **架构错误**

**原因**: SIAS (Sample Importance-Aware Selection) 不是独立模块，而是 `ToolSelector` 接口的一个算法实现。

**正确位置**: `isage-agentic` 包中，作为 `ToolSelector` 的具体实现类。

**已完成操作**:

- ❌ 删除了 `sias/interface/` 目录
- ✅ 更新了重组文档，明确 SIAS 的正确定位

______________________________________________________________________

## 架构模式

所有接口层遵循统一模式（参考 ANNS/AMMS）：

```
<module>/interface/
├── __init__.py      # 导出所有公共 API
├── base.py          # 抽象基类（ABC + @abstractmethod）
└── factory.py       # 注册表 + 工厂函数
```

### 设计原则

1. **接口层在 sage-libs**：定义抽象基类和工厂模式
1. **实现层在 isage-**\*：外部 PyPI 包提供具体实现
1. **自动注册**：实现包导入时自动注册到工厂
1. **类型安全**：使用 ABC + @abstractmethod 强制实现
1. **灵活性**：支持工厂模式和直接实例化两种用法

### 使用示例

```python
# 方式 1: 工厂模式（推荐）
from sage.libs.agentic.interface import create_agent
agent = create_agent("react", llm_client=client)

# 方式 2: 直接实例化
from isage_agentic import ReActAgent
agent = ReActAgent(llm_client=client)
```

______________________________________________________________________

## 与现有模块对比

| 模块          | 接口层状态 | 实现位置                  | PyPI 包               |
| ------------- | ---------- | ------------------------- | --------------------- |
| **anns/**     | ✅ 已有    | isage-anns                | `isage-anns`          |
| **amms/**     | ✅ 已有    | isage-amms                | `isage-amms`          |
| **agentic/**  | ✅ 新建    | isage-agentic             | `isage-agentic`       |
| **finetune/** | ✅ 新建    | isage-finetune            | `isage-finetune`      |
| **rag/**      | ✅ 新建    | sage-libs (或 isage-rag)  | 待定                  |
| **intent/**   | ✅ 新建    | isage-intent              | `isage-intent` (可选) |
| **~~sias/~~** | ❌ 删除    | → agentic/tool_selectors/ | -                     |

______________________________________________________________________

## 下一步行动

### 1. 验证接口层 ✅ 已完成

- [x] 为 agentic 创建接口层
- [x] 为 finetune 创建接口层
- [x] 为 rag 创建接口层
- [x] 为 intent 创建接口层
- [x] 删除错误的 sias 接口层

### 2. 更新父模块 __init__.py

需要更新以下文件，使其从 `interface/` 导入：

- [ ] `packages/sage-libs/src/sage/libs/agentic/__init__.py`
- [ ] `packages/sage-libs/src/sage/libs/finetune/__init__.py`
- [ ] `packages/sage-libs/src/sage/libs/rag/__init__.py`
- [ ] `packages/sage-libs/src/sage/libs/intent/__init__.py`

### 3. 删除 sias 模块

- [ ] 删除 `packages/sage-libs/src/sage/libs/sias/` 整个目录
- [ ] 从 `packages/sage-libs/src/sage/libs/__init__.py` 移除 sias 引用

### 4. 实现层迁移（外部包）

按优先级：

1. **isage-agentic** (高优先级)

   - 迁移 agentic/ 实现代码
   - 实现 SIAS tool selector
   - 发布到 PyPI

1. **isage-finetune** (中优先级)

   - 迁移 finetune/ 实现代码
   - 发布到 PyPI

1. **isage-rag** (待定)

   - 决定是否外迁
   - 如外迁，迁移实现代码

1. **isage-intent** (低优先级)

   - 如决定外迁，迁移实现代码

### 5. 更新文档

- [ ] 更新 `REORGANIZATION_PROPOSAL.md`
- [ ] 创建迁移指南
- [ ] 更新 API 文档

______________________________________________________________________

## 参考文档

- `REORGANIZATION_PROPOSAL.md` - 重组方案
- `packages/sage-libs/src/sage/libs/anns/interface/` - ANNS 接口参考
- `packages/sage-libs/src/sage/libs/amms/interface/` - AMMS 接口参考

______________________________________________________________________

## 总结

✅ **4 个接口层已完成**：agentic, finetune, rag, intent\
❌ **1 个模块需删除**：sias（架构错误）\
📋 **下一步**：更新父模块导入 → 删除 sias → 迁移实现代码

**架构一致性**: 所有接口层现在遵循统一的设计模式，与 ANNS/AMMS 保持一致。
