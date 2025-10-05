# 新增应用模板总结

## 📋 概述

基于 `examples/` 目录下的应用示例，新增了 **6 个高质量应用模板**，丰富了 SAGE Pipeline Builder 的模板库，使 LLM 能够更准确地为复杂应用场景生成配置。

## ✨ 新增模板列表

### 1. **Milvus 密集向量检索问答** (`rag-dense-milvus`)

**场景**: 生产级大规模语义检索系统

**特点**:
- 使用 Milvus 向量数据库进行密集向量检索
- 支持百万级文档的高效检索
- 支持 BGE 等多种嵌入模型
- 适合生产环境部署

**标签**: `rag`, `qa`, `milvus`, `dense`, `vector`, `embedding`, `向量检索`, `向量数据库`, `生产环境`, `语义搜索`

**示例路径**: `examples/rag/qa_dense_retrieval_milvus.py`

**核心组件**:
- Source: `JSONLBatch` - JSONL 批处理数据源
- Stage 1: `MilvusDenseRetriever` - Milvus 密集向量检索器
- Stage 2: `QAPromptor` - 问答提示词构建器
- Stage 3: `OpenAIGenerator` - LLM 答案生成器
- Sink: `TerminalSink` - 终端输出

---

### 2. **重排序增强检索问答** (`rag-rerank`)

**场景**: 高精度要求的问答系统

**特点**:
- 两阶段检索架构：粗排召回 + 精细重排
- 第一阶段召回更多候选（如 top-20）
- 第二阶段使用 BGE cross-encoder 重排序（如 top-5）
- 显著提升检索精确度

**标签**: `rag`, `qa`, `rerank`, `reranker`, `precision`, `重排序`, `精确度`, `两阶段`, `召回`, `精排`

**示例路径**: `examples/rag/qa_rerank.py`

**核心组件**:
- Source: `JSONLBatch`
- Stage 1: `ChromaRetriever` - Chroma 向量检索（召回阶段）
- Stage 2: `BGEReranker` - BGE 重排序器（精排阶段）
- Stage 3: `QAPromptor` - 提示词构建
- Stage 4: `OpenAIGenerator` - LLM 生成
- Sink: `TerminalSink`

**适用场景**: 法律、医疗、金融等高精度问答

---

### 3. **BM25 关键词检索问答** (`rag-bm25-sparse`)

**场景**: 传统关键词检索，无需向量化

**特点**:
- 基于 BM25 算法的词法匹配
- 无需 GPU 和向量化
- 计算成本低
- 适合精确关键词匹配
- 可与密集检索结合形成混合检索

**标签**: `rag`, `qa`, `bm25`, `sparse`, `keyword`, `关键词`, `稀疏检索`, `词法`, `传统检索`

**示例路径**: `examples/rag/qa_bm25_retrieval.py`

**核心组件**:
- Source: `FileSource` - 文件数据源
- Stage 1: `BM25sRetriever` - BM25 检索器
- Stage 2: `QAPromptor`
- Stage 3: `OpenAIGenerator`
- Sink: `TerminalSink`

**优势**: 
- 专有名词和精确匹配表现优异
- 资源受限环境友好

---

### 4. **LLM 智能体工作流** (`agent-workflow`)

**场景**: 自主规划和执行复杂任务的智能体系统

**特点**:
- LLM 自主任务规划
- Model Context Protocol (MCP) 工具调用
- 支持多步骤推理
- 适合复杂任务执行

**标签**: `agent`, `llm`, `planning`, `tool`, `mcp`, `智能体`, `工具调用`, `规划`, `自主`, `任务执行`

**示例路径**: `examples/agents/agent.py`

**核心组件**:
- Source: `iter_queries` - 任务查询迭代器
- Stage 1: `LLMPlanner` - LLM 规划器（Agent 类型）
- Stage 2: `MCPRegistry` - MCP 工具注册表（Tool 类型）
- Stage 3: `AgentRuntime` - 智能体运行时（Agent 类型）
- Sink: `TerminalSink`
- Service: MCP 工具服务

**适用场景**: 
- 数据分析
- 代码生成
- 信息收集
- 自动化操作

---

### 5. **记忆增强对话问答** (`rag-memory-enhanced`)

**场景**: 支持多轮对话的上下文感知问答系统

**特点**:
- 自动存储历史对话到记忆服务
- 检索时考虑历史上下文
- 保持对话连贯性
- 使用服务架构管理会话状态

**标签**: `rag`, `memory`, `conversation`, `multi-turn`, `dialogue`, `记忆`, `对话`, `上下文`, `多轮`, `会话`

**示例路径**: `examples/memory/rag_memory_pipeline.py`

**核心组件**:
- Source: `QuestionSource` - 问题批处理源
- Stage 1: `Retriever` - 记忆感知检索器
- Stage 2: `QAPromptor`
- Stage 3: `OpenAIGenerator`
- Stage 4: `Writer` - 记忆写入器
- Sink: `PrintSink`
- Service: `RAGMemoryService` - 记忆服务（ChromaDB 后端）

**适用场景**:
- 客服机器人
- 个人助手
- 长对话系统

---

### 6. **跨模态搜索引擎** (`multimodal-cross-search`)

**场景**: 支持文本、图像及融合检索的多模态搜索

**特点**:
- 支持三种检索模式：文本、图像、融合
- 可配置融合策略（加权平均、RRF 等）
- 基于 SageDB 或多模态向量库
- 灵活的模态权重配置

**标签**: `multimodal`, `cross-modal`, `search`, `fusion`, `image`, `text`, `跨模态`, `搜索`, `图文`, `检索`

**示例路径**: `examples/multimodal/cross_modal_search.py`

**核心组件**:
- Source: `JSONLBatch` - 多模态查询数据源
- Stage 1: `create_text_image_db` - 跨模态检索器
- Stage 2: `MultimodalReranker` - 多模态重排序
- Sink: `TerminalSink` (JSON 格式)

**适用场景**:
- 电商搜索
- 新闻检索
- 社交媒体

---

## 📊 模板匹配测试结果

所有 6 个新模板均通过了匹配测试：

| 测试场景 | 预期模板 | 实际匹配 | 匹配度 | 结果 |
|---------|---------|---------|--------|------|
| Milvus 向量检索 | `rag-dense-milvus` | `rag-dense-milvus` | 0.305 | ✅ |
| 重排序检索 | `rag-rerank` | `rag-rerank` | 0.200 | ✅ |
| BM25 关键词检索 | `rag-bm25-sparse` | `rag-bm25-sparse` | 0.222 | ✅ |
| 智能体系统 | `agent-workflow` | `agent-workflow` | 0.300 | ✅ |
| 记忆对话 | `rag-memory-enhanced` | `rag-memory-enhanced` | 0.300 | ✅ |
| 跨模态搜索 | `multimodal-cross-search` | `multimodal-cross-search` | 0.340 | ✅ |

**测试通过率**: 6/6 (100%)

---

## 🏗️ 技术实现

### 文件修改

1. **`packages/sage-tools/src/sage/tools/cli/pipeline_blueprints.py`**
   - 新增 6 个 `PipelineBlueprint` 定义
   - 每个蓝图包含完整的 Source、Stages、Sink 规格
   - 定义了相关的 graph_channels 和 graph_agents

2. **`packages/sage-tools/src/sage/tools/templates/catalog.py`**
   - 新增 6 个 `ApplicationTemplate` 定义
   - 为每个模板提供详细的描述、标签、指导和注意事项
   - 关联对应的蓝图 ID

### 蓝图与模板对应关系

| 蓝图 ID | 模板 ID | 示例路径 |
|---------|---------|----------|
| `rag-dense-milvus` | `rag-dense-milvus` | `examples/rag/qa_dense_retrieval_milvus.py` |
| `rag-rerank` | `rag-rerank` | `examples/rag/qa_rerank.py` |
| `rag-bm25-sparse` | `rag-bm25-sparse` | `examples/rag/qa_bm25_retrieval.py` |
| `agent-workflow` | `agent-workflow` | `examples/agents/agent.py` |
| `rag-memory-enhanced` | `rag-memory-enhanced` | `examples/memory/rag_memory_pipeline.py` |
| `multimodal-cross-search` | `multimodal-cross-search` | `examples/multimodal/cross_modal_search.py` |

---

## 🎯 使用场景覆盖

新增的模板覆盖了以下应用场景：

### RAG 增强场景
- ✅ **密集向量检索** - 大规模语义搜索（Milvus）
- ✅ **重排序优化** - 高精度两阶段检索
- ✅ **稀疏检索** - BM25 关键词匹配
- ✅ **记忆增强** - 多轮对话上下文

### 高级应用场景
- ✅ **智能体系统** - LLM 规划 + 工具调用
- ✅ **多模态检索** - 跨文本和图像的融合搜索

### 生产环境支持
- ✅ **向量数据库** - Milvus 生产级部署
- ✅ **精确度优化** - Reranker 二次排序
- ✅ **资源优化** - BM25 低成本检索
- ✅ **状态管理** - 记忆服务架构

---

## 📈 改进效果

### 模板库扩充
- **原有模板**: 4 个
- **新增模板**: 6 个
- **总计**: 10 个
- **增长**: 150%

### 场景覆盖增强
- **RAG 场景**: 从 1 个简单示例扩展到覆盖密集、稀疏、重排、记忆等多种检索方式
- **Agent 场景**: 新增完整的智能体工作流支持
- **多模态场景**: 扩展到跨模态检索和融合

### LLM 生成能力提升
通过更丰富的模板和标签，LLM 现在可以：
- 更准确地理解用户意图
- 为复杂场景生成合适的 Pipeline 配置
- 提供更具体的实现指导和注意事项

---

## 🧪 测试验证

创建了两个测试脚本：

1. **`examples/tutorials/test_template_matching.py`**
   - 验证模板匹配的准确性
   - 测试 6 种典型场景
   - 显示所有可用模板

2. **`examples/tutorials/test_new_templates.py`**
   - 使用真实 LLM API 测试配置生成
   - 验证端到端功能

**运行测试**:
```bash
python examples/tutorials/test_template_matching.py
```

---

## 💡 最佳实践

### 1. 为新应用选择合适的模板

**向量检索场景**:
- 大规模生产环境 → `rag-dense-milvus`
- 高精度要求 → `rag-rerank`
- 关键词匹配 → `rag-bm25-sparse`

**对话场景**:
- 简单问答 → `rag-simple-demo`
- 多轮对话 → `rag-memory-enhanced`

**高级应用**:
- 自主任务执行 → `agent-workflow`
- 图文混合检索 → `multimodal-cross-search`

### 2. 标签使用指南

为获得更好的匹配效果，用户需求中应包含：
- **明确的关键词**: "Milvus"、"重排序"、"智能体" 等
- **场景描述**: "多轮对话"、"跨模态" 等
- **技术需求**: "向量数据库"、"工具调用" 等

### 3. 扩展建议

未来可以继续添加模板：
- 流式处理场景
- 实时推理场景
- 分布式部署场景
- 更多垂直领域场景（医疗、金融、法律等）

---

## 📚 相关文档

- [Pipeline Builder V2 改进文档](./PIPELINE_BUILDER_V2_IMPROVEMENTS.md)
- [LLM 交互详细说明](./LLM_INTERACTION_IN_PIPELINE_BUILDER.md)
- [模板在 LLM 中的使用](./TEMPLATES_IN_LLM_DETAILED.md)

---

## ✅ 总结

通过新增 6 个高质量应用模板，SAGE Pipeline Builder 现在能够：

1. ✅ 支持更多复杂的生产环境场景
2. ✅ 为 LLM 提供更丰富的参考样本
3. ✅ 提高配置生成的准确性和实用性
4. ✅ 覆盖从简单到复杂、从单模态到多模态的广泛应用场景

所有新模板都经过测试验证，可以直接投入使用！🎉
