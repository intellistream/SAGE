# SAGE Chat 架构详解

**Date**: 2024-10-15\
**Author**: SAGE Team\
**Summary**: SAGE Chat 架构设计文档，包括对话管理、上下文处理和多轮对话支持

## 🎯 核心问题解答

### Q1: 为什么 Mock LLM 也能支持 sage chat？

**答案**：因为 SAGE Chat 采用 **RAG（检索增强生成）架构**，检索和生成是**解耦**的两个阶段。

______________________________________________________________________

## 📊 SAGE Chat 完整架构

```
用户问题
   ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段 1: 文档检索（Retrieval）                                │
│                                                              │
│  问题 → Embedding → 向量检索 → Top-K 文档片段                │
│         (Hash/HF)    (SageDB)                                │
└─────────────────────────────────────────────────────────────┘
   ↓
   文档片段 (contexts) + 引用信息 (references)
   ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段 2: 答案生成（Generation）                               │
│                                                              │
│  [Mock 模式]                                                 │
│  └→ 简单拼接检索结果（无需真实 LLM）                          │
│                                                              │
│  [OpenAI 模式]                                               │
│  └→ 调用真实 LLM 理解并生成答案                              │
└─────────────────────────────────────────────────────────────┘
   ↓
   最终答案
```

______________________________________________________________________

## 🔍 阶段 1: 文档检索的工作原理

### 代码实现（第 1170-1200 行）

```python
def retrieve_context(
    db: Any,
    embedder: EmbeddingModel,
    question: str,
    top_k: int,
) -> Dict[str, object]:
    # 1. 将问题转换为向量
    query_vector = embedder.embed(question)  # ← Embedding 在这里使用

    # 2. 在向量数据库中检索最相似的文档
    results = db.search(query_vector, top_k, True)  # ← 向量相似度搜索

    # 3. 提取文档内容和元数据
    contexts: List[str] = []
    references: List[Dict[str, str]] = []
    for item in results:
        metadata = dict(item.metadata)
        contexts.append(metadata.get("text", ""))  # 检索到的文档片段
        references.append({...})  # 引用信息

    return {"contexts": contexts, "references": references}
```

### 关键点：

- **Embedding 模型**（Hash/HF/OpenAI）只在**检索阶段**使用
- 用于将**问题**和**文档**都转换为向量
- 通过**向量相似度**找到相关文档

______________________________________________________________________

## 🤖 阶段 2: 答案生成的两种模式

### Mock 模式（第 590-603 行）

```python
@staticmethod
def _mock_answer(
    question: str,
    contexts: Sequence[str],  # ← 检索阶段已经拿到的文档
    references: Sequence[Dict[str, str]],
) -> str:
    if not contexts:
        return "暂时没有从知识库检索到答案..."

    # 简单提取第一个文档的前 280 字符
    snippet = contexts[0].strip().replace("\n", " ")
    citation = top_ref.get("label", "Docs")

    # 直接拼接返回，无需 LLM！
    return (
        f"根据 {citation} 的说明：{snippet[:280]}...\n\n"
        "如需更多细节，可以输入 `more` 再次检索，或使用 `--backend openai` 启用真实模型。"
    )
```

**特点**：

- ✅ **不需要真实 LLM**
- ✅ **不需要高质量 Embedding**（只要能检索到文档即可）
- ❌ **无语义理解**：只是简单截取文档片段
- ❌ **无法总结、推理、组合多个来源**

______________________________________________________________________

### OpenAI 模式（第 564-589 行）

```python
def answer(
    self,
    question: str,
    contexts: Sequence[str],  # ← 检索阶段已经拿到的文档
    references: Sequence[Dict[str, str]],
    stream: bool = False,
) -> str:
    # 构建包含上下文的提示词
    messages = build_prompt(question, contexts)

    # 调用真实 LLM 进行理解和生成
    response = self.client.generate(
        messages,
        max_tokens=768,
        temperature=self.temperature,
        stream=stream,
    )
    return response
```

**特点**：

- ✅ **深度语义理解**：LLM 能理解文档内容
- ✅ **智能总结**：可以综合多个来源
- ✅ **推理能力**：可以回答隐含信息
- ❌ **需要 API Key 和费用**

______________________________________________________________________

## 💡 Q2: 为什么真实 LLM 就不需要更好的 Embedding？

### 误解澄清

**这是一个误解！** 实际上：

```
更好的 Embedding → 更准确的检索 → 更好的上下文 → 更好的答案
```

无论使用 Mock 还是 OpenAI 后端，**更好的 Embedding 总是有帮助的**。

______________________________________________________________________

## 🔬 三种配置的对比

| 配置           | Embedding   | LLM Backend | 检索质量              | 答案质量              | 适用场景             |
| -------------- | ----------- | ----------- | --------------------- | --------------------- | -------------------- |
| **当前配置**   | Hash (Mock) | Mock        | ⭐⭐ (只能精确匹配)   | ⭐ (截取片段)         | 快速测试、演示       |
| **建议配置 1** | Hash (Mock) | OpenAI      | ⭐⭐ (只能精确匹配)   | ⭐⭐⭐⭐ (LLM 理解)   | 节省成本、关键词明确 |
| **建议配置 2** | HF (BGE)    | Mock        | ⭐⭐⭐⭐⭐ (语义理解) | ⭐ (截取片段)         | 测试检索效果         |
| **最佳配置**   | HF (BGE)    | OpenAI      | ⭐⭐⭐⭐⭐ (语义理解) | ⭐⭐⭐⭐⭐ (LLM 理解) | 生产环境             |

______________________________________________________________________

## 🎯 实际测试对比

### 测试问题："请列出所有可用的检索器算子"

#### 配置 1: Hash Embedding + Mock LLM（当前）

```
检索结果：
1. SAGE 子模块管理策略 (得分: 1.2308) ← 不相关！
2. SAGE Applications 应用组件 - Tools (得分: 1.2355) ← 不相关！
3. SAGE Kernel 总览 (得分: 1.2424) ← 不相关！

回答：
根据 [ci_cd/submodule_management.md] 的说明：...
```

**问题**：Hash Embedding 无法理解"检索器算子"的语义，只能做简单的字符串匹配。

______________________________________________________________________

#### 配置 2: Hash Embedding + OpenAI LLM（假设）

```
检索结果：
1. SAGE 子模块管理策略 (得分: 1.2308) ← 不相关！
2. SAGE Applications 应用组件 - Tools (得分: 1.2355) ← 不相关！
...

回答（LLM 生成）：
根据检索到的文档，虽然没有直接找到"检索器算子"的完整列表，
但从 SAGE Applications 文档中可以看到工具集相关内容。
建议您查看 librarys/operators_reference.md 文档...
```

**改进**：LLM 能理解检索结果不相关，给出更合理的回复。但仍然受限于差的检索结果。

______________________________________________________________________

#### 配置 3: BGE Embedding + Mock LLM（假设）

```
检索结果：
1. SAGE-Libs 算子参考手册 - RAG 检索器 (得分: 0.85) ← 高度相关！
2. SAGE-Libs 算子参考手册 - ChromaRetriever (得分: 0.87)
3. SAGE-Libs 算子参考手册 - MilvusDenseRetriever (得分: 0.88)

回答：
根据 [librarys/operators_reference.md] 的说明：
### ChromaRetriever
**路径**: sage.libs.rag.retriever.ChromaRetriever
**功能**: 基于 ChromaDB 的向量检索器...
```

**改进**：检索准确！但回答只是简单截取，不够智能。

______________________________________________________________________

#### 配置 4: BGE Embedding + OpenAI LLM（最佳）

```
检索结果：
1. SAGE-Libs 算子参考手册 - RAG 检索器 (得分: 0.85) ← 高度相关！
2. SAGE-Libs 算子参考手册 - ChromaRetriever (得分: 0.87)
3. SAGE-Libs 算子参考手册 - MilvusDenseRetriever (得分: 0.88)

回答（LLM 智能总结）：
SAGE-Libs 目前提供 4 种检索器算子：

1. **ChromaRetriever** - 轻量级向量检索，适合中小规模知识库
2. **MilvusDenseRetriever** - 生产级密集向量检索，支持大规模数据
3. **MilvusSparseRetriever** - 稀疏向量检索（BM25-like），适合关键词匹配
4. **Wiki18FAISSRetriever** - 基于 FAISS 的演示用检索器

选择建议：
- 本地开发 → ChromaRetriever
- 生产环境 → MilvusDenseRetriever
- 混合检索 → Dense + Sparse 结合
```

**完美**：准确检索 + 智能总结！

______________________________________________________________________

## 🚀 为什么当前测试能"工作"？

### 测试问题："MilvusDenseRetriever"

```python
query = "MilvusDenseRetriever"  # ← 精确的算子名称

# Hash Embedding 的工作原理
hash("MilvusDenseRetriever") → [固定向量]

# 在索引时，文档中也包含 "MilvusDenseRetriever" 这个词
hash("...MilvusDenseRetriever...") → [相似向量]

# 结果：能匹配上！
```

检索结果显示成功找到了 `operators_reference.md`：

```
知识引用:
1. SAGE-Libs 算子参考手册 - 高精度 RAG (得分: 1.0649)  ← 包含 "MilvusDenseRetriever"
2. SAGE-Libs 算子参考手册 - 混合检索 (得分: 1.1371)
...
```

**但是**，如果问"语义问题"：

- ❌ "如何选择合适的检索器？" → Hash 无法理解
- ❌ "我需要高性能的向量搜索" → Hash 无法匹配到 MilvusDenseRetriever
- ✅ "MilvusDenseRetriever" → Hash 能精确匹配

______________________________________________________________________

## 📝 总结

### 核心要点

1. **检索和生成是解耦的**：

   - Embedding 只影响检索质量
   - LLM Backend 只影响生成质量

1. **Mock LLM 能工作是因为**：

   - 它只是简单地返回检索到的文档片段
   - 不需要理解语义，只需要"有内容可返回"

1. **真实 LLM 的价值**：

   - 能从**差的检索结果**中提取有用信息
   - 能**综合多个来源**生成答案
   - 能**推理和总结**，而不只是复制粘贴

1. **但真实 LLM ≠ 不需要好 Embedding**：

   - Garbage in, garbage out
   - 更好的检索 → 更好的上下文 → 更好的答案
   - 即使 LLM 再强大，也无法从不相关的文档中生成正确答案

______________________________________________________________________

## 🎓 类比理解

想象你要写一篇报告：

### Mock 模式

```
老师：请根据资料写一篇关于检索器的报告
你：（随机翻开图书馆的书）复制前 280 字 ← Mock LLM
问题：如果拿错书了，复制的内容也是错的
```

### OpenAI 模式（差 Embedding）

```
老师：请根据资料写一篇关于检索器的报告
你：（随机翻开图书馆的书）发现内容不对，但尽力理解并补充 ← 真实 LLM
改进：虽然资料不对，但能给出合理的回复
```

### OpenAI 模式（好 Embedding）

```
老师：请根据资料写一篇关于检索器的报告
你：（精准找到相关书籍）深度理解并总结 ← 真实 LLM + 好检索
完美：找对资料 + 深度理解 = 高质量答案
```

______________________________________________________________________

## 🔧 实践建议

### 当前测试阶段

```bash
# 使用 Mock 模式快速验证功能
sage chat
# 输入具体的类名/函数名（精确匹配）
> ChromaRetriever
```

### 开发阶段

```bash
# 使用真实 LLM，但保持 Hash Embedding（节省资源）
sage chat --backend openai
# 可以问更自然的问题
> 如何选择合适的检索器？
```

### 生产环境

```bash
# 重建索引使用语义 Embedding
sage chat ingest --embedding-method hf --embedding-model BAAI/bge-base-zh-v1.5

# 使用真实 LLM
sage chat --backend openai
# 最佳体验
> 我想构建一个大规模知识库问答系统，应该用什么检索器？
```

______________________________________________________________________

希望这个解释清楚了！简单说：

- **Mock LLM** = 复读机（复制检索结果）
- **真实 LLM** = 智能助手（理解并生成答案）
- **好 Embedding** = 精准的图书管理员（找对资料）
- **差 Embedding** = 随机找书（可能找错）

最佳效果 = 精准找书（好 Embedding）+ 智能理解（真实 LLM）！
