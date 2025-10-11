# SAGE 可用算子清单

本文档列出了 `sage-libs` 中所有可用的算子，供创建 Pipeline 模板时参考。

## 📊 数据源 (Source / Batch)

### Batch 批处理源

| 类名 | 路径 | 功能说明 |
|------|------|----------|
| `HFDatasetBatch` | `sage.libs.io_utils.batch.HFDatasetBatch` | HuggingFace 数据集批处理源 |
| `JSONLBatch` | `sage.libs.io_utils.batch.JSONLBatch` | JSONL 文件批处理源 |

### Source 流式源

| 类名 | 路径 | 功能说明 |
|------|------|----------|
| `FileSource` | `sage.libs.io_utils.source.FileSource` | 文件流式数据源 |
| `SocketSource` | `sage.libs.io_utils.source.SocketSource` | Socket 网络数据源 |
| `ContextFileSource` | `sage.libs.utils.context_source.ContextFileSource` | 上下文文件源 |

---

## 🔄 数据处理 (Map Functions)

### RAG 检索器 (Retrievers)

| 类名 | 路径 | 功能说明 |
|------|------|----------|
| `ChromaRetriever` | `sage.libs.rag.retriever.ChromaRetriever` | ChromaDB 向量检索器 |
| `MilvusDenseRetriever` | `sage.libs.rag.retriever.MilvusDenseRetriever` | Milvus 密集向量检索器 |
| `MilvusSparseRetriever` | `sage.libs.rag.retriever.MilvusSparseRetriever` | Milvus 稀疏向量检索器 |
| `Wiki18FAISSRetriever` | `sage.libs.rag.retriever.Wiki18FAISSRetriever` | Wiki18 FAISS 检索器 |

### RAG 重排序器 (Rerankers)

| 类名 | 路径 | 功能说明 |
|------|------|----------|
| `BGEReranker` | `sage.libs.rag.reranker.BGEReranker` | BGE 重排序器（Cross-Encoder） |
| `LLMbased_Reranker` | `sage.libs.rag.reranker.LLMbased_Reranker` | 基于 LLM 的重排序器 |

### RAG 提示词构建 (Promptors)

| 类名 | 路径 | 功能说明 |
|------|------|----------|
| `QAPromptor` | `sage.libs.rag.promptor.QAPromptor` | 问答提示词构建器 |
| `SummarizationPromptor` | `sage.libs.rag.promptor.SummarizationPromptor` | 摘要提示词构建器 |
| `QueryProfilerPromptor` | `sage.libs.rag.promptor.QueryProfilerPromptor` | 查询分析提示词构建器 |

### RAG 生成器 (Generators)

| 类名 | 路径 | 功能说明 |
|------|------|----------|
| `OpenAIGenerator` | `sage.libs.rag.generator.OpenAIGenerator` | OpenAI 兼容 API 生成器 |
| `HFGenerator` | `sage.libs.rag.generator.HFGenerator` | HuggingFace 模型生成器 |

### RAG 辅助工具

| 类名 | 路径 | 功能说明 |
|------|------|----------|
| `CharacterSplitter` | `sage.libs.rag.chunk.CharacterSplitter` | 字符级文本分割器 |
| `SentenceTransformersTokenTextSplitter` | `sage.libs.rag.chunk.SentenceTransformersTokenTextSplitter` | 基于 Sentence Transformers 的分词分割器 |
| `LongRefinerAdapter` | `sage.libs.rag.longrefiner.longrefiner_adapter.LongRefinerAdapter` | 长文本优化适配器 |
| `MemoryWriter` | `sage.libs.rag.writer.MemoryWriter` | 记忆写入器 |
| `BochaWebSearch` | `sage.libs.rag.searcher.BochaWebSearch` | Bocha 网络搜索 |
| `ArxivPDFDownloader` | `sage.libs.rag.arxiv.ArxivPDFDownloader` | Arxiv PDF 下载器 |
| `ArxivPDFParser` | `sage.libs.rag.arxiv.ArxivPDFParser` | Arxiv PDF 解析器 |

### Agent 智能体

| 类名 | 路径 | 功能说明 |
|------|------|----------|
| `BaseAgent` | `sage.libs.agents.agent.BaseAgent` | 基础智能体 |
| `AgentRuntime` | `sage.libs.agents.runtime.agent.AgentRuntime` | 智能体运行时 |
| `LLMPlanner` | `sage.libs.agents.planning.llm_planner.LLMPlanner` | LLM 规划器 |
| `MCPRegistry` | `sage.libs.agents.action.mcp_registry.MCPRegistry` | MCP 工具注册表 |
| `BaseProfile` | `sage.libs.agents.profile.profile.BaseProfile` | 智能体配置文件 |

### 工具

| 类名 | 路径 | 功能说明 |
|------|------|----------|
| `BochaSearchTool` | `sage.libs.tools.searcher_tool.BochaSearchTool` | Bocha 搜索工具 |

### 评估器 (Evaluators)

| 类名 | 路径 | 功能说明 |
|------|------|----------|
| `F1Evaluate` | `sage.libs.rag.evaluate.F1Evaluate` | F1 分数评估 |
| `RecallEvaluate` | `sage.libs.rag.evaluate.RecallEvaluate` | 召回率评估 |
| `BertRecallEvaluate` | `sage.libs.rag.evaluate.BertRecallEvaluate` | BERT 召回率评估 |
| `RougeLEvaluate` | `sage.libs.rag.evaluate.RougeLEvaluate` | Rouge-L 评估 |
| `BRSEvaluate` | `sage.libs.rag.evaluate.BRSEvaluate` | BRS 评估 |
| `AccuracyEvaluate` | `sage.libs.rag.evaluate.AccuracyEvaluate` | 准确率评估 |
| `TokenCountEvaluate` | `sage.libs.rag.evaluate.TokenCountEvaluate` | Token 计数评估 |
| `LatencyEvaluate` | `sage.libs.rag.evaluate.LatencyEvaluate` | 延迟评估 |
| `ContextRecallEvaluate` | `sage.libs.rag.evaluate.ContextRecallEvaluate` | 上下文召回评估 |
| `CompressionRateEvaluate` | `sage.libs.rag.evaluate.CompressionRateEvaluate` | 压缩率评估 |

---

## 📤 输出端 (Sinks)

| 类名 | 路径 | 功能说明 |
|------|------|----------|
| `TerminalSink` | `sage.libs.io_utils.sink.TerminalSink` | 终端输出 |
| `PrintSink` | `sage.libs.io_utils.sink.PrintSink` | 通用打印输出 |
| `FileSink` | `sage.libs.io_utils.sink.FileSink` | 文件输出 |
| `RetriveSink` | `sage.libs.io_utils.sink.RetriveSink` | 检索结果输出 |
| `MemWriteSink` | `sage.libs.io_utils.sink.MemWriteSink` | 内存写入输出 |
| `ContextFileSink` | `sage.libs.utils.context_sink.ContextFileSink` | 上下文文件输出 |

---

## 📝 模板使用建议

### RAG 问答场景

**基础 RAG 流程**:
```
Source → Retriever → Promptor → Generator → Sink
```

**推荐组合**:
- 向量检索: `ChromaRetriever` 或 `MilvusDenseRetriever`
- 提示词: `QAPromptor`
- 生成: `OpenAIGenerator`

**高精度 RAG（带重排序）**:
```
Source → Retriever → Reranker → Promptor → Generator → Sink
```

**推荐组合**:
- 召回: `ChromaRetriever` (top_k=20)
- 精排: `BGEReranker` (top_k=5)
- 提示词: `QAPromptor`
- 生成: `OpenAIGenerator`

### Agent 场景

**智能体工作流**:
```
Source → LLMPlanner → MCPRegistry → AgentRuntime → Sink
```

### 文档处理场景

**Arxiv 论文处理**:
```
Source → ArxivPDFDownloader → ArxivPDFParser → CharacterSplitter → Sink
```

### 评估场景

**RAG 评估**:
```
Source → Retriever → Generator → F1Evaluate/RecallEvaluate → Sink
```

---

## ⚠️ 重要注意事项

### 1. 检索器选择

- **ChromaRetriever**: 适合中小规模（< 百万文档），易于部署
- **MilvusDenseRetriever**: 适合大规模（百万级+），需要 Milvus 服务
- **MilvusSparseRetriever**: 稀疏向量检索，适合关键词匹配
- **Wiki18FAISSRetriever**: 演示用途，基于 Wiki18 数据集

### 2. 生成器选择

- **OpenAIGenerator**: 
  - 需要 API Key
  - 支持 OpenAI 和兼容的 API（如阿里云 DashScope）
  - 推荐用于生产环境
  
- **HFGenerator**:
  - 需要本地模型
  - 适合离线部署或自定义模型

### 3. 重排序器选择

- **BGEReranker**: 
  - 基于 BGE Cross-Encoder
  - 精确度高，但计算成本较高
  - 推荐用于高精度场景
  
- **LLMbased_Reranker**:
  - 基于 LLM 进行重排序
  - 成本更高但更灵活

### 4. 数据源选择

- **JSONLBatch**: 批处理，适合离线处理大量数据
- **FileSource**: 流式处理，适合实时场景
- **HFDatasetBatch**: 直接使用 HuggingFace 数据集

---

## 🔍 验证模板中的算子使用

在创建新模板时，请确保：

1. ✅ 使用的算子类名与上表完全一致
2. ✅ 算子的路径正确（`sage.libs.xxx.yyy.ClassName`）
3. ✅ 算子类型匹配（Source → Map → Sink）
4. ✅ 参数配置合理（参考 `examples/` 中的示例）

---

## 📚 参考示例

所有算子的使用示例可以在以下位置找到：

- RAG 示例: `examples/rag/`
- Agent 示例: `examples/agents/`
- 多模态示例: `examples/multimodal/`
- 记忆服务示例: `examples/memory/`
- 教程示例: `examples/tutorials/`

---

## 🔄 更新日志

- 2025-10-05: 初始版本，列出所有 sage-libs 可用算子
