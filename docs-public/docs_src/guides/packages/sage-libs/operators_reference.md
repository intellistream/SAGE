# SAGE-Libs 算子参考手册

本文档提供 SAGE-Libs 中所有可用算子的完整清单，供开发者在构建 Pipeline 时参考。

!!! info "关于本文档" - **最后更新**: 2025-10-05 - **算子总数**: 44 个 - **覆盖范围**: 数据源、处理、输出全流程 - **状态**:
所有算子已验证可用

______________________________________________________________________

## 📊 算子分类概览

| 类别                             | 数量 | 主要用途             |
| -------------------------------- | ---- | -------------------- |
| [数据源](#data-sources)          | 5    | 批处理和流式数据输入 |
| [RAG 检索器](#rag-retrievers)    | 4    | 向量检索和语义搜索   |
| [RAG 重排序器](#rag-rerankers)   | 2    | 检索结果精排         |
| [RAG 提示词构建](#rag-promptors) | 3    | LLM 提示词生成       |
| [RAG 生成器](#rag-generators)    | 2    | 文本生成和问答       |
| [RAG 辅助工具](#rag-utilities)   | 7    | 分块、解析、搜索等   |
| [Agent 智能体](#agents)          | 5    | 智能体规划和执行     |
| [工具](#tools)                   | 1    | 外部工具集成         |
| [评估器](#evaluators)            | 10   | 性能评估和指标计算   |
| [输出端](#sinks)                 | 6    | 数据输出和持久化     |

______________________________________________________________________

## 📥 数据源 (Sources & Batches) {#data-sources}

### 批处理数据源 (Batch Sources)

#### `HFDatasetBatch`

**路径**: `sage.libs.io.batch.HFDatasetBatch`

**功能**: 从 HuggingFace Datasets 加载批处理数据

**使用场景**:

- 使用公开数据集进行训练或评估
- 快速原型开发
- 标准化数据集测试

**示例配置**:

```yaml
source:
  class: sage.libs.io.batch.HFDatasetBatch
  params:
    dataset_name: "squad"
    split: "train"
    streaming: false
```

______________________________________________________________________

#### `JSONLBatch`

**路径**: `sage.libs.io.batch.JSONLBatch`

**功能**: 从 JSONL 文件批量读取数据

**使用场景**:

- 本地数据处理
- 自定义数据集
- 批量问答任务

**示例配置**:

```yaml
source:
  class: sage.libs.io.batch.JSONLBatch
  params:
    data_path: "./data/questions.jsonl"
    field_query: "query"
```

______________________________________________________________________

### 流式数据源 (Stream Sources)

#### `FileSource`

**路径**: `sage.libs.io.source.FileSource`

**功能**: 从文件流式读取数据

**使用场景**:

- 实时数据处理
- 逐行处理大文件
- 流式 Pipeline

**示例配置**:

```yaml
source:
  class: sage.libs.io.source.FileSource
  params:
    data_path: "./data/stream.txt"
```

______________________________________________________________________

#### `SocketSource`

**路径**: `sage.libs.io.source.SocketSource`

**功能**: 通过 Socket 接收流式数据

**使用场景**:

- 网络数据流
- 实时服务
- 分布式系统

______________________________________________________________________

#### `ContextFileSource`

**路径**: `sage.libs.utils.context_source.ContextFileSource`

**功能**: 带上下文的文件数据源

**使用场景**:

- 需要保留上下文信息
- 多文件关联处理

______________________________________________________________________

## 🔍 RAG 检索器 (Retrievers) {#rag-retrievers}

### `ChromaRetriever`

**路径**: `sage.libs.rag.retriever.ChromaRetriever`

**功能**: 基于 ChromaDB 的向量检索器

**特点**:

- 轻量级向量数据库
- 易于部署
- 适合中小规模（< 百万文档）

**使用场景**:

- 本地开发和测试
- 中小型知识库
- 快速原型验证

**示例配置**:

```yaml
stages:
  - id: retriever
    class: sage.libs.rag.retriever.ChromaRetriever
    params:
      collection_name: "knowledge_base"
      top_k: 5
      embedding_model: "bge-base-zh-v1.5"
```

______________________________________________________________________

### `MilvusDenseRetriever`

**路径**: `sage.libs.rag.retriever.MilvusDenseRetriever`

**功能**: 基于 Milvus 的密集向量检索器

**特点**:

- 生产级向量数据库
- 支持大规模（百万级+）
- 高性能分布式检索

**使用场景**:

- 生产环境部署
- 大规模知识库
- 高并发查询

**示例配置**:

```yaml
stages:
  - id: retriever
    class: sage.libs.rag.retriever.MilvusDenseRetriever
    params:
      dimension: 768
      top_k: 5
      milvus_dense:
        collection_name: "knowledge_base"
        uri: "http://localhost:19530"
      embedding:
        method: "bge-base-zh-v1.5"
```

**依赖**: 需要运行中的 Milvus 服务

______________________________________________________________________

### `MilvusSparseRetriever`

**路径**: `sage.libs.rag.retriever.MilvusSparseRetriever`

**功能**: 基于 Milvus 的稀疏向量检索器（BM25-like）

**特点**:

- 关键词匹配
- 无需 GPU
- 适合精确匹配场景

**使用场景**:

- 关键词检索
- 混合检索（与密集向量结合）
- 专有名词匹配

**示例配置**:

```yaml
stages:
  - id: sparse-retriever
    class: sage.libs.rag.retriever.MilvusSparseRetriever
    params:
      collection_name: "sparse_index"
      top_k: 5
      milvus_sparse:
        uri: "http://localhost:19530"
```

______________________________________________________________________

### `Wiki18FAISSRetriever`

**路径**: `sage.libs.rag.retriever.Wiki18FAISSRetriever`

**功能**: 基于 Wiki18 数据集的 FAISS 检索器

**使用场景**:

- 教学演示
- 快速测试
- 无需外部依赖

______________________________________________________________________

## 🔄 RAG 重排序器 (Rerankers) {#rag-rerankers}

### `BGEReranker`

**路径**: `sage.libs.rag.reranker.BGEReranker`

**功能**: 基于 BGE Cross-Encoder 的重排序器

**特点**:

- 高精确度
- Cross-Encoder 架构
- 显著提升检索质量

**使用场景**:

- 高精度要求的问答
- 两阶段检索架构
- 法律、医疗、金融等专业领域

**示例配置**:

```yaml
stages:
  - id: reranker
    class: sage.libs.rag.reranker.BGEReranker
    params:
      model_name: "bge-reranker-base"
      top_k: 5
```

**最佳实践**:

- 第一阶段召回 top-20
- 第二阶段重排选 top-5

______________________________________________________________________

### `LLMbased_Reranker`

**路径**: `sage.libs.rag.reranker.LLMbased_Reranker`

**功能**: 基于 LLM 的重排序器

**特点**:

- 使用 LLM 进行语义理解
- 更灵活的排序策略
- 成本较高

**使用场景**:

- 需要深度语义理解
- 复杂查询场景

______________________________________________________________________

## 📝 RAG 提示词构建 (Promptors) {#rag-promptors}

### `QAPromptor`

**路径**: `sage.libs.rag.promptor.QAPromptor`

**功能**: 问答提示词构建器

**特点**:

- 可自定义模板
- 支持上下文注入
- 长度控制

**使用场景**:

- 标准问答任务
- RAG Pipeline

**示例配置**:

```yaml
stages:
  - id: promptor
    class: sage.libs.rag.promptor.QAPromptor
    params:
      template: "Context: {context}\nQuestion: {question}\nAnswer:"
      max_context_length: 2000
```

______________________________________________________________________

### `SummarizationPromptor`

**路径**: `sage.libs.rag.promptor.SummarizationPromptor`

**功能**: 摘要生成提示词构建器

**使用场景**:

- 文档摘要
- 内容总结

______________________________________________________________________

### `QueryProfilerPromptor`

**路径**: `sage.libs.rag.promptor.QueryProfilerPromptor`

**功能**: 查询分析提示词构建器

**使用场景**:

- 查询意图分析
- 查询改写

______________________________________________________________________

## 🤖 RAG 生成器 (Generators) {#rag-generators}

### `OpenAIGenerator`

**路径**: `sage.libs.rag.generator.OpenAIGenerator`

**功能**: OpenAI 兼容 API 生成器

**特点**:

- 支持 OpenAI 官方 API
- 支持兼容的 API（阿里云、DeepSeek 等）
- 流式输出支持

**使用场景**:

- 生产环境推荐
- 高质量文本生成
- 问答系统

**示例配置**:

```yaml
stages:
  - id: generator
    class: sage.libs.rag.generator.OpenAIGenerator
    params:
      model_name: "gpt-3.5-turbo"
      temperature: 0.7
      max_tokens: 256
```

**环境变量**:

- `OPENAI_API_KEY`: API 密钥
- `OPENAI_BASE_URL`: API 端点（可选）

______________________________________________________________________

### `HFGenerator`

**路径**: `sage.libs.rag.generator.HFGenerator`

**功能**: HuggingFace 模型生成器

**特点**:

- 本地模型部署
- 离线运行
- 自定义模型

**使用场景**:

- 数据隐私要求
- 离线部署
- 自定义模型微调

______________________________________________________________________

## 🛠️ RAG 辅助工具 {#rag-utilities}

### 文本分块 (Text Splitters)

#### `CharacterSplitter`

**路径**: `sage.libs.rag.chunk.CharacterSplitter`

**功能**: 字符级文本分割器

**使用场景**: 简单文本分块

______________________________________________________________________

#### `SentenceTransformersTokenTextSplitter`

**路径**: `sage.libs.rag.chunk.SentenceTransformersTokenTextSplitter`

**功能**: 基于 Token 的智能分割器

**使用场景**:

- 考虑 Token 限制
- 保持语义完整性

______________________________________________________________________

### 文档处理

#### `ArxivPDFDownloader`

**路径**: `sage.libs.rag.arxiv.ArxivPDFDownloader`

**功能**: Arxiv 论文 PDF 下载器

**使用场景**: 学术论文处理

______________________________________________________________________

#### `ArxivPDFParser`

**路径**: `sage.libs.rag.arxiv.ArxivPDFParser`

**功能**: Arxiv PDF 解析器

**使用场景**: 提取论文文本内容

______________________________________________________________________

### 其他工具

#### `LongRefinerAdapter`

**路径**: `sage.libs.rag.longrefiner.longrefiner_adapter.LongRefinerAdapter`

**功能**: 长文本优化适配器

______________________________________________________________________

#### `MemoryWriter`

**路径**: `sage.libs.rag.writer.MemoryWriter`

**功能**: 记忆写入器

**使用场景**: 对话历史存储

______________________________________________________________________

#### `BochaWebSearch`

**路径**: `sage.libs.rag.searcher.BochaWebSearch`

**功能**: Bocha 网络搜索

**使用场景**: 实时网络信息检索

______________________________________________________________________

## 🤖 智能体 (Agents) {#agents}

### `BaseAgent`

**路径**: `sage.libs.agentic.agents.agent.BaseAgent`

**功能**: 基础智能体类

______________________________________________________________________

### `AgentRuntime`

**路径**: `sage.libs.agentic.agents.runtime.agent.AgentRuntime`

**功能**: 智能体运行时环境

**特点**:

- 管理智能体生命周期
- 工具调用协调
- 状态管理

**使用场景**:

- Agent 工作流
- 复杂任务执行

**示例配置**:

```yaml
stages:
  - id: agent-runtime
    kind: agent
    class: sage.libs.agentic.agents.runtime.agent.AgentRuntime
    params:
      max_iterations: 10
```

______________________________________________________________________

### `LLMPlanner`

**路径**: `sage.libs.agentic.agents.planning.llm_planner.LLMPlanner`

**功能**: 基于 LLM 的任务规划器

**特点**:

- 自主任务分解
- 多步骤规划
- 动态调整

**使用场景**:

- 复杂任务自动化
- 多步骤推理

**示例配置**:

```yaml
stages:
  - id: planner
    kind: agent
    class: sage.libs.agentic.agents.planning.llm_planner.LLMPlanner
    params:
      model: "gpt-3.5-turbo"
      temperature: 0.7
```

______________________________________________________________________

### `MCPRegistry`

**路径**: `sage.libs.agentic.agents.action.mcp_registry.MCPRegistry`

**功能**: Model Context Protocol 工具注册表

**特点**:

- 工具管理
- MCP 标准支持
- 动态工具加载

**使用场景**:

- Agent 工具调用
- 外部能力集成

______________________________________________________________________

### `BaseProfile`

**路径**: `sage.libs.agentic.agents.profile.profile.BaseProfile`

**功能**: 智能体配置文件

**使用场景**:

- Agent 参数配置
- 角色定义

______________________________________________________________________

## 🔧 工具 (Tools) {#tools}

### `BochaSearchTool`

**路径**: `sage.libs.tools.searcher_tool.BochaSearchTool`

**功能**: Bocha 搜索工具

**使用场景**:

- Agent 搜索能力
- 信息检索

______________________________________________________________________

## 📊 评估器 (Evaluators) {#evaluators}

### 准确性评估

#### `F1Evaluate`

**路径**: `sage.libs.rag.evaluate.F1Evaluate`

**功能**: F1 分数计算

**使用场景**: 分类任务评估

______________________________________________________________________

#### `AccuracyEvaluate`

**路径**: `sage.libs.rag.evaluate.AccuracyEvaluate`

**功能**: 准确率计算

______________________________________________________________________

### 召回评估

#### `RecallEvaluate`

**路径**: `sage.libs.rag.evaluate.RecallEvaluate`

**功能**: 召回率计算

______________________________________________________________________

#### `BertRecallEvaluate`

**路径**: `sage.libs.rag.evaluate.BertRecallEvaluate`

**功能**: 基于 BERT 的语义召回率

______________________________________________________________________

#### `ContextRecallEvaluate`

**路径**: `sage.libs.rag.evaluate.ContextRecallEvaluate`

**功能**: 上下文召回评估

**使用场景**: RAG 系统评估

______________________________________________________________________

### 生成质量评估

#### `RougeLEvaluate`

**路径**: `sage.libs.rag.evaluate.RougeLEvaluate`

**功能**: Rouge-L 指标计算

**使用场景**: 摘要生成评估

______________________________________________________________________

#### `BRSEvaluate`

**路径**: `sage.libs.rag.evaluate.BRSEvaluate`

**功能**: BRS 评估

______________________________________________________________________

### 性能评估

#### `TokenCountEvaluate`

**路径**: `sage.libs.rag.evaluate.TokenCountEvaluate`

**功能**: Token 数量统计

**使用场景**: 成本估算

______________________________________________________________________

#### `LatencyEvaluate`

**路径**: `sage.libs.rag.evaluate.LatencyEvaluate`

**功能**: 延迟测量

**使用场景**: 性能优化

______________________________________________________________________

#### `CompressionRateEvaluate`

**路径**: `sage.libs.rag.evaluate.CompressionRateEvaluate`

**功能**: 压缩率计算

______________________________________________________________________

## 📤 输出端 (Sinks) {#sinks}

### `TerminalSink`

**路径**: `sage.libs.io.sink.TerminalSink`

**功能**: 终端输出

**特点**:

- 支持 JSON 格式
- 彩色输出
- 调试友好

**示例配置**:

```yaml
sink:
  class: sage.libs.io.sink.TerminalSink
  params:
    output_format: "json"
    pretty_print: true
```

______________________________________________________________________

### `PrintSink`

**路径**: `sage.libs.io.sink.PrintSink`

**功能**: 通用打印输出

**使用场景**: 简单调试输出

______________________________________________________________________

### `FileSink`

**路径**: `sage.libs.io.sink.FileSink`

**功能**: 文件输出

**特点**:

- 结果持久化
- 支持多种格式

**示例配置**:

```yaml
sink:
  class: sage.libs.io.sink.FileSink
  params:
    output_path: "./results/output.jsonl"
    format: "jsonl"
```

______________________________________________________________________

### `RetriveSink`

**路径**: `sage.libs.io.sink.RetriveSink`

**功能**: 检索结果输出

______________________________________________________________________

### `MemWriteSink`

**路径**: `sage.libs.io.sink.MemWriteSink`

**功能**: 内存写入输出

**使用场景**:

- 中间结果缓存
- 多阶段 Pipeline

______________________________________________________________________

### `ContextFileSink`

**路径**: `sage.libs.utils.context_sink.ContextFileSink`

**功能**: 带上下文的文件输出

______________________________________________________________________

## 💡 使用建议

### RAG Pipeline 推荐组合

#### 基础 RAG

```
JSONLBatch → ChromaRetriever → QAPromptor → OpenAIGenerator → TerminalSink
```

#### 高精度 RAG

```
JSONLBatch → MilvusDenseRetriever → BGEReranker → QAPromptor → OpenAIGenerator → FileSink
```

#### 混合检索

```
JSONLBatch → [MilvusDenseRetriever + MilvusSparseRetriever] → BGEReranker → QAPromptor → OpenAIGenerator → TerminalSink
```

### Agent Pipeline 推荐组合

```
Source → LLMPlanner → MCPRegistry → AgentRuntime → TerminalSink
```

### 评估 Pipeline 推荐组合

```
JSONLBatch → Retriever → Generator → [F1Evaluate + RecallEvaluate + LatencyEvaluate] → FileSink
```

______________________________________________________________________

## ⚠️ 重要注意事项

### 检索器选择

- **ChromaRetriever**: 中小规模（< 百万），易部署
- **MilvusDenseRetriever**: 大规模（百万+），需 Milvus 服务
- **MilvusSparseRetriever**: 关键词匹配，无需 GPU

### 生成器选择

- **OpenAIGenerator**: 生产推荐，需 API Key
- **HFGenerator**: 离线部署，需本地模型

### 性能优化

1. **两阶段检索**: 召回（top-20）+ 重排（top-5）
1. **批处理优化**: 使用 JSONLBatch 而非 FileSource
1. **并行处理**: 合理设置 parallelism 参数

______________________________________________________________________

## 📚 相关文档

- [RAG 组件详解](./rag.md)
- [Agent 组件详解](./agents.md)
- [IO 组件详解](./io.md)
- [工具组件详解](./tools_intro.md)

______________________________________________________________________

## 🔄 更新日志

- **2025-10-05**: 初始版本，包含 44 个算子
- 所有算子已验证可用
- 提供完整的使用示例和最佳实践

______________________________________________________________________

!!! tip "获取帮助" - 查看具体算子的详细文档: [RAG 文档](rag/README.md), [Agent 文档](agents.md) - 查看示例代码: `examples/`
目录 - 提交问题: GitHub Issues
