# RAG组件文档导航 (RAG Components Documentation Guide)

欢迎使用SAGE框架的RAG（检索增强生成）组件文档。本导航将帮助您快速找到所需的技术文档和实现示例。

## 📖 文档结构

### 组件文档 (`components/`)
包含SAGE框架中所有RAG核心组件的详细技术文档：

| 文档 | 组件功能 | 适用场景 | 难度级别 |
|------|----------|----------|----------|
| [文档加载器](components/document_loaders.md) | 文档读取与预处理 | 数据接入 | ⭐ 入门 |
| [文本分块器](components/chunk.md) | 长文档智能分割 | 数据预处理 | ⭐⭐ 基础 |
| [索引构建](components/index_build.md) | 向量索引构建 | 离线建库 | ⭐⭐⭐ 中级 |
| [检索器](components/retriever.md) | 向量相似度检索 | 在线查询 | ⭐⭐ 基础 |
| [重排序器](components/reranker.md) | 检索结果精排 | 质量优化 | ⭐⭐⭐ 中级 |
| [提示词生成器](components/promptor.md) | 上下文组装 | 提示工程 | ⭐⭐ 基础 |
| [生成器](components/generator.md) | 答案生成 | LLM调用 | ⭐⭐ 基础 |
| [外部搜索器](components/search.md) | 实时信息获取 | 信息扩展 | ⭐⭐⭐ 中级 |
| [评估器](components/evaluate.md) | 系统性能评估 | 质量监控 | ⭐⭐⭐⭐ 高级 |

### 实现示例 (`examples/`)
提供完整的端到端实现示例：

| 示例 | 说明 | 复杂度 |
|------|------|--------|
| [RAG系统完整实现](examples/RAG.md) | 基于ChromaDB的完整RAG问答系统 | ⭐⭐⭐ 中级 |

## 🚀 快速开始

### 新手学习路径
如果您是RAG技术的新手，建议按以下顺序学习：

1. **理解基础概念** 📚
   - 阅读 [RAG系统完整实现](examples/RAG.md) 了解整体架构
   - 理解RAG的两阶段工作流程

2. **掌握核心组件** 🔧
   - [文档加载器](components/document_loaders.md) - 学习数据输入
   - [文本分块器](components/chunk.md) - 理解文档预处理
   - [索引构建](components/index_build.md) - 掌握向量化流程

3. **实现检索生成** 🎯
   - [检索器](components/retriever.md) - 实现相似度检索
   - [提示词生成器](components/promptor.md) - 学习上下文组装
   - [生成器](components/generator.md) - 接入大语言模型

4. **系统优化提升** ⚡
   - [重排序器](components/reranker.md) - 提升检索精度
   - [外部搜索器](components/search.md) - 扩展信息来源
   - [评估器](components/evaluate.md) - 监控系统性能

### 开发者快速参考

#### 基础RAG流水线
```python
# 最小化RAG实现
from sage.libs.rag import ChromaRetriever, QAPromptor, OpenAIGenerator

# 1. 检索相关文档
retriever = ChromaRetriever(config)
docs = retriever.execute("用户查询")

# 2. 组装提示词
promptor = QAPromptor()
prompt = promptor.execute(("用户查询", docs))

# 3. 生成答案
generator = OpenAIGenerator(config)
answer = generator.execute(prompt)
```

#### 完整系统部署
```python
# 生产级RAG系统
from sage.libs.environment import LocalEnvironment

def deploy_rag_system(config):
    env = LocalEnvironment()
    (env
     .from_batch(JSONLBatch, config["source"])
     .map(ChromaRetriever, config["retriever"])
     .map(BGEReranker, config["reranker"])      # 可选：重排序
     .map(QAPromptor, config["promptor"])
     .map(OpenAIGenerator, config["generator"])
     .sink(TerminalSink, config["sink"])
    )
    env.submit()
```

## 📋 组件选择指南

### 根据应用场景选择组件

#### 🏢 企业知识管理
- **核心组件**：TextLoader + CharacterSplitter + ChromaRetriever + QAPromptor + OpenAIGenerator
- **推荐增强**：BGEReranker（提升准确性）
- **特点**：高精度、可追溯、安全可控

#### 🔬 学术研究助手
- **核心组件**：TextLoader + SentenceTransformersTokenTextSplitter + ChromaRetriever + QAPromptor + HFGenerator
- **推荐增强**：LLMbased_Reranker（复杂推理）+ F1Evaluate（质量评估）
- **特点**：深度理解、多文档推理、学术严谨

#### 📰 实时信息问答
- **核心组件**：ChromaRetriever + BochaWebSearch + QAPromptor + OpenAIGenerator
- **推荐增强**：混合检索策略
- **特点**：时效性强、信息全面、来源多样

#### 🤖 智能客服系统
- **核心组件**：TextLoader + CharacterSplitter + ChromaRetriever + BGEReranker + QAPromptor + OpenAIGenerator
- **推荐增强**：RecallEvaluate（召回监控）+ 缓存机制
- **特点**：响应快速、准确率高、用户体验佳

## 🛠 技术规格要求

### 系统环境
- **Python版本**：3.8+
- **内存要求**：建议8GB+（向量模型加载）
- **存储空间**：根据知识库大小，建议预留充足空间
- **GPU支持**：可选，用于加速向量计算和模型推理

### 依赖组件
- **向量数据库**：ChromaDB（默认）
- **嵌入模型**：SentenceTransformers
- **语言模型**：OpenAI API兼容服务或HuggingFace模型
- **外部API**：BochaAI（可选，用于网络搜索）

## 📊 性能基准

### 典型性能指标
| 组件 | 处理速度 | 内存占用 | 准确率 |
|------|----------|----------|--------|
| CharacterSplitter | ~1000文档/秒 | 低 | N/A |
| ChromaRetriever | ~100查询/秒 | 中等 | 85-92% |
| BGEReranker | ~50查询/秒 | 中等 | 90-95% |
| OpenAIGenerator | ~10查询/秒 | 低 | 依赖模型 |

### 优化建议
- **批处理**：对于大量查询，使用批处理提升吞吐量
- **缓存策略**：缓存常见查询结果，减少重复计算
- **分布式部署**：大规模应用考虑分布式架构
- **模型量化**：使用量化模型减少内存占用

## 🔍 故障排查

### 常见问题及解决方案

#### 检索无结果
- **原因**：向量索引未正确构建或查询向量化失败
- **解决**：检查索引状态，验证嵌入模型一致性
- **参考**：[索引构建文档](components/index_build.md)

#### 生成质量差
- **原因**：检索上下文不相关或提示词设计不当
- **解决**：优化检索策略，改进提示词模板
- **参考**：[重排序器](components/reranker.md) + [提示词生成器](components/promptor.md)

#### 响应速度慢
- **原因**：模型推理慢或检索数据量大
- **解决**：使用更快的模型，优化索引结构
- **参考**：[性能优化最佳实践](components/retriever.md)

## 🔗 相关资源

### 学习资料
- <!-- [SAGE框架官方文档](../../README.md) -->
项目README
- <!-- [向量数据库最佳实践](../../../core/vector_database.md) -->
向量数据库
- <!-- [大语言模型集成指南](../../../core/llm_integration.md) -->
LLM集成

### 社区支持
- **GitHub Issues**：技术问题和Bug报告
- **讨论论坛**：经验分享和最佳实践
- **示例代码库**：完整的项目示例

### 版本更新
- 查看 <!-- [CHANGELOG.md](../../../../CHANGELOG.md) -->
更新日志 了解最新更新
- 订阅发布通知获取新功能信息

---

**贡献指南**：欢迎提交文档改进建议和新的使用示例。请参考 <!-- [贡献指南](../../../../CONTRIBUTING.md) -->
贡献指南 了解详细信息。

**许可证**：本文档遵循 Apache 2.0 许可证。详见 [LICENSE](../../LICENSE) 文件。
