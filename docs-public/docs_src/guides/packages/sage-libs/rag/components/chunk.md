# 文本分块组件 (Text Chunking Components)

本文档详细介绍SAGE框架中`sage.libs.rag.chunk`模块的文本分块组件。文本分块是RAG（检索增强生成）系统的基础预处理步骤，负责将长文档分割为适合检索和生成的语义单元。

## 组件概述

### 核心功能

文本分块组件在RAG系统中承担以下关键职责：

- **语义保持**：在分割过程中保持文本的语义完整性
- **检索优化**：生成适合向量检索的文本块大小
- **重叠控制**：通过重叠策略提高检索召回率
- **格式标准化**：输出统一的文档格式供下游组件使用

### 可用分块器

本模块提供两类分块器，适用于不同的应用场景：

| 分块器                                  | 适用场景     | 特点                           |
| --------------------------------------- | ------------ | ------------------------------ |
| `CharacterSplitter`                     | 通用文本处理 | 基于字符计数，支持自定义分隔符 |
| `SentenceTransformersTokenTextSplitter` | 深度学习应用 | 基于模型分词器，与下游模型兼容 |

## CharacterSplitter

### 组件描述

`CharacterSplitter`是一个轻量级文本分块器，基于字符计数和可配置分隔符进行文本分割。该组件特别适合于需要精确控制文本块大小的场景。

### 技术规格

**输入格式**：

```python
document = {
    "content": str,  # 必需：待分块的文本内容
    "metadata": dict,  # 可选：文档元数据
}
```

**输出格式**：

```python
chunks = [str, str, ...]  # 分块后的文本列表
```

**配置参数**：

| 参数名       | 类型 | 默认值 | 说明                   |
| ------------ | ---- | ------ | ---------------------- |
| `chunk_size` | int  | 512    | 每个文本块的最大字符数 |
| `overlap`    | int  | 128    | 相邻文本块的重叠字符数 |
| `separator`  | str  | None   | 自定义分隔符（可选）   |

### 实现示例

#### 基础分块操作

```python
from sage.libs.rag.chunk import CharacterSplitter

# 配置分块器
config = {"chunk_size": 500, "overlap": 100}
splitter = CharacterSplitter(config)

# 准备文档数据
document = {
    "content": "这是一个很长的文档内容，需要被分割成多个小块以便处理。" * 20,
    "metadata": {"title": "示例文档", "author": "技术团队"},
}

# 执行分块
chunks = splitter.execute(document)
print(f"分块完成，共生成 {len(chunks)} 个文档块")

for i, chunk in enumerate(chunks[:3], 1):  # 显示前3个块
    print(f"文档块 {i}: {chunk[:80]}...")
```

#### 自定义分隔符分块

```python
# 按段落分割策略
paragraph_config = {
    "separator": "\n\n",  # 使用双换行符作为段落分隔符
    "chunk_size": 1000,  # 适中的块大小
    "overlap": 50,  # 较小的重叠避免段落内容截断
}

paragraph_splitter = CharacterSplitter(paragraph_config)

# 示例文档
document = {
    "content": """第一段内容：介绍了文档的背景和目标。

第二段内容：详细描述了技术实现方案。

第三段内容：总结了项目的核心价值和未来发展方向。""",
    "metadata": {"doc_type": "technical_report"},
}

chunks = paragraph_splitter.execute(document)
print(f"段落分割结果：共 {len(chunks)} 个段落块")
# 输出：['第一段内容：介绍了文档的背景和目标。', '第二段内容：详细描述了技术实现方案。', ...]
```

#### 重叠机制详解

```python
# 重叠机制演示
overlap_config = {"chunk_size": 20, "overlap": 8}  # 较小的块用于演示  # 8字符重叠

overlap_splitter = CharacterSplitter(overlap_config)

demo_document = {
    "content": "人工智能技术正在快速发展，深度学习算法在各个领域都有重要应用。"
}

overlap_chunks = overlap_splitter.execute(demo_document)

print("重叠分块演示:")
for i, chunk in enumerate(overlap_chunks, 1):
    print(f"块{i}: '{chunk}'")

# 输出示例:
# 块1: '人工智能技术正在快速发展，深度学习'
# 块2: '深度学习算法在各个领域都有重要应用'
# 注意：'深度学习' 在两个块中都出现，形成重叠
```

## SentenceTransformersTokenTextSplitter

### 组件描述

`SentenceTransformersTokenTextSplitter`是基于SentenceTransformer模型分词器的高级分块器，特别适用于需要与下游NLP模型保持一致的应用场景。

### 技术规格

**核心优势**：

- 与SentenceTransformer模型的分词器完全兼容
- 基于Token计数而非字符计数，更精确
- 保持与后续嵌入过程的一致性
- 支持多语言分词标准

**配置参数**：

| 参数名          | 类型 | 默认值              | 说明                        |
| --------------- | ---- | ------------------- | --------------------------- |
| `model_name`    | str  | "all-mpnet-base-v2" | SentenceTransformer模型名称 |
| `chunk_size`    | int  | 512                 | 每个文本块的最大Token数     |
| `chunk_overlap` | int  | 50                  | 相邻文本块的重叠Token数     |
| `device`        | str  | "auto"              | 模型运行设备                |

### 实现示例

#### 基础Token分块

```python
from sage.libs.rag.chunk import SentenceTransformersTokenTextSplitter

# 配置Token分块器
token_config = {
    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
    "chunk_size": 256,  # 256个Token
    "chunk_overlap": 32,  # 32个Token重叠
}

token_splitter = SentenceTransformersTokenTextSplitter(token_config)

# 处理技术文档
tech_document = {
    "content": """
    自然语言处理（Natural Language Processing, NLP）是人工智能的重要分支。
    它致力于让计算机理解、解释和生成人类语言。NLP技术包括文本分析、语义理解、
    机器翻译、情感分析等多个方向。近年来，基于Transformer架构的预训练模型
    如BERT、GPT等在NLP任务上取得了突破性进展。
    """,
    "metadata": {"topic": "nlp_introduction", "language": "zh"},
}

token_chunks = token_splitter.execute(tech_document)
print(f"Token分块完成，共 {len(token_chunks)} 个Token块")
```

#### 多语言文档处理

```python
# 多语言模型配置
multilingual_config = {
    "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "chunk_size": 384,
    "chunk_overlap": 48,
}

multilingual_splitter = SentenceTransformersTokenTextSplitter(multilingual_config)

# 中英混合文档
mixed_document = {
    "content": """
    SAGE是一个现代化的RAG框架。SAGE is a modern RAG framework that supports
    multiple languages and provides comprehensive documentation. 该框架支持多种
    embedding模型，包括sentence-transformers系列模型。The framework is designed
    for scalability and ease of use.
    """,
    "metadata": {"content_type": "bilingual_doc"},
}

mixed_chunks = multilingual_splitter.execute(mixed_document)
print("多语言分块处理完成")
```

## 高级应用场景

### 自适应分块策略

```python
class AdaptiveChunker:
    """根据文档类型自动选择最优分块策略"""

    def __init__(self):
        # 预定义不同类型的分块配置
        self.strategies = {
            "academic_paper": {
                "type": "character",
                "config": {"separator": "\n\n", "chunk_size": 800, "overlap": 100},
            },
            "technical_doc": {
                "type": "token",
                "config": {
                    "model_name": "sentence-transformers/all-mpnet-base-v2",
                    "chunk_size": 384,
                    "chunk_overlap": 50,
                },
            },
            "news_article": {
                "type": "character",
                "config": {"separator": "。", "chunk_size": 600, "overlap": 80},
            },
            "code_documentation": {
                "type": "character",
                "config": {
                    "separator": "\n\nclass |def |async def ",
                    "chunk_size": 1200,
                    "overlap": 0,  # 代码块通常不需要重叠
                },
            },
        }

    def chunk_document(self, document, doc_type="technical_doc"):
        """根据文档类型执行相应的分块策略"""

        if doc_type not in self.strategies:
            doc_type = "technical_doc"  # 默认策略

        strategy = self.strategies[doc_type]

        if strategy["type"] == "character":
            splitter = CharacterSplitter(strategy["config"])
        else:  # token
            splitter = SentenceTransformersTokenTextSplitter(strategy["config"])

        chunks = splitter.execute(document)

        print(f"使用 {doc_type} 策略，生成 {len(chunks)} 个文档块")
        return chunks


# 使用自适应分块器
adaptive_chunker = AdaptiveChunker()

# 学术论文分块
paper_doc = {
    "content": "摘要\n\n本文介绍了...\n\n1. 引言\n\n近年来...",
    "metadata": {"type": "academic"},
}
paper_chunks = adaptive_chunker.chunk_document(paper_doc, "academic_paper")

# 技术文档分块
tech_doc = {
    "content": "API documentation for SAGE framework...",
    "metadata": {"type": "technical"},
}
tech_chunks = adaptive_chunker.chunk_document(tech_doc, "technical_doc")
```

### 质量评估与优化

```python
class ChunkQualityEvaluator:
    """文档分块质量评估器"""

    def __init__(self):
        self.metrics = {}

    def evaluate_chunks(self, chunks, original_document):
        """评估分块质量"""

        # 1. 覆盖率评估
        total_chars = len(original_document["content"])
        chunk_chars = sum(len(chunk) for chunk in chunks)
        coverage = chunk_chars / total_chars

        # 2. 块大小分布
        chunk_lengths = [len(chunk) for chunk in chunks]
        avg_length = sum(chunk_lengths) / len(chunk_lengths)
        length_variance = sum((l - avg_length) ** 2 for l in chunk_lengths) / len(
            chunk_lengths
        )

        # 3. 语义完整性（简化评估）
        incomplete_chunks = sum(
            1 for chunk in chunks if chunk.endswith(("，", "和", "的", "是"))
        )
        semantic_completeness = 1 - (incomplete_chunks / len(chunks))

        self.metrics = {
            "coverage": coverage,
            "average_chunk_length": avg_length,
            "length_variance": length_variance,
            "semantic_completeness": semantic_completeness,
            "total_chunks": len(chunks),
        }

        return self.metrics

    def print_evaluation(self):
        """打印评估结果"""
        print("=== 分块质量评估报告 ===")
        print(f"内容覆盖率: {self.metrics['coverage']:.2%}")
        print(f"平均块长度: {self.metrics['average_chunk_length']:.0f} 字符")
        print(f"长度方差: {self.metrics['length_variance']:.0f}")
        print(f"语义完整性: {self.metrics['semantic_completeness']:.2%}")
        print(f"总块数: {self.metrics['total_chunks']}")

        # 质量建议
        if self.metrics["coverage"] < 0.95:
            print("⚠️ 建议：内容覆盖率较低，检查分块逻辑")
        if self.metrics["length_variance"] > 10000:
            print("⚠️ 建议：块长度差异较大，考虑调整分块参数")
        if self.metrics["semantic_completeness"] < 0.8:
            print("⚠️ 建议：语义完整性较低，优化分隔符选择")


# 使用质量评估器
evaluator = ChunkQualityEvaluator()

# 评估不同分块策略的效果
test_document = {
    "content": """人工智能是计算机科学的一个分支，旨在创建能够模拟人类智能的系统。
    机器学习是人工智能的核心技术之一，通过算法让计算机从数据中学习模式。
    深度学习作为机器学习的子集，使用神经网络来处理复杂的数据结构。
    自然语言处理则专注于让计算机理解和生成人类语言。""",
    "metadata": {"test_doc": True},
}

# 测试字符分块
char_chunks = CharacterSplitter({"chunk_size": 80, "overlap": 20}).execute(
    test_document
)
char_metrics = evaluator.evaluate_chunks(char_chunks, test_document)
print("字符分块评估：")
evaluator.print_evaluation()

print("\n" + "=" * 50 + "\n")

# 测试Token分块
token_chunks = SentenceTransformersTokenTextSplitter(
    {"chunk_size": 64, "chunk_overlap": 16}
).execute(test_document)
token_metrics = evaluator.evaluate_chunks(token_chunks, test_document)
print("Token分块评估：")
evaluator.print_evaluation()
```

## 配置优化指南

### 根据应用场景优化配置

#### 问答系统优化

```python
# 问答系统最优配置
qa_config = {
    "chunk_size": 400,  # 适中块大小，平衡上下文和精度
    "overlap": 80,  # 充足重叠确保信息完整性
    "separator": "。",  # 按句子分割保持语义完整
}

print("问答系统配置特点：")
print("- 中等块大小：平衡检索精度和上下文完整性")
print("- 适度重叠：确保跨句信息不丢失")
print("- 句子分割：保持回答的语义逻辑性")
```

#### 摘要系统优化

```python
# 摘要系统最优配置
summary_config = {
    "chunk_size": 800,  # 较大块包含更多上下文
    "overlap": 120,  # 更多重叠保持连贯性
    "separator": "\n\n",  # 按段落分割保持结构
}

print("摘要系统配置特点：")
print("- 较大块：包含足够信息支持摘要生成")
print("- 高重叠率：保持文档结构和逻辑连贯性")
print("- 段落分割：维护原文的层次结构")
```

#### 代码文档优化

```python
# 代码文档最优配置
code_config = {
    "separator": "\n\nclass |def |async def ",  # 按函数/类分割
    "chunk_size": 1500,  # 较大块容纳完整函数
    "overlap": 0,  # 代码块通常不需要重叠
}

print("代码文档配置特点：")
print("- 函数级分割：保持代码逻辑完整性")
print("- 大块容量：容纳完整的函数或类定义")
print("- 无重叠：避免代码重复和逻辑混乱")
```

### 性能优化策略

#### 批量处理优化

```python
def batch_chunk_documents(documents, splitter_config, batch_size=10):
    """批量处理多个文档的分块操作"""

    splitter = CharacterSplitter(splitter_config)
    all_chunks = []

    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]

        print(f"处理批次 {i//batch_size + 1}: {len(batch)} 个文档")

        batch_chunks = []
        for doc in batch:
            chunks = splitter.execute(doc)
            batch_chunks.extend(chunks)

        all_chunks.extend(batch_chunks)
        print(f"批次完成，生成 {len(batch_chunks)} 个文档块")

    return all_chunks


# 批量处理示例
documents = [
    {"content": f"文档{i}内容..." * 50, "metadata": {"id": i}} for i in range(100)
]

optimized_config = {"chunk_size": 500, "overlap": 100, "separator": "\n\n"}

chunks = batch_chunk_documents(documents, optimized_config, batch_size=20)
print(f"批量处理完成，总共生成 {len(chunks)} 个文档块")
```

## 最佳实践总结

### 分块策略选择原则

1. **语义完整性优先**：

   - 优先使用自然分界符（段落、句子）
   - 避免在词汇中间切分
   - 保持概念和逻辑的完整性

1. **下游任务适配**：

   - 问答任务：中等块大小（300-600字符）
   - 摘要任务：较大块大小（600-1000字符）
   - 检索任务：根据检索模型优化

1. **性能与精度平衡**：

   - 块大小与检索精度成反比
   - 重叠率与信息完整性成正比
   - 根据应用需求找到最优平衡点

### 常见错误与避免方法

1. **过度分块**：

   - 问题：块太小导致上下文信息不足
   - 解决：增加块大小或重叠率

1. **分界点选择不当**：

   - 问题：在关键信息中间切分
   - 解决：使用语义分界符

1. **忽略重叠设计**：

   - 问题：重要信息在块边界丢失
   - 解决：合理设置重叠区域

### 监控与调试

```python
def debug_chunking_process(document, config):
    """分块过程调试工具"""

    print("=== 分块调试信息 ===")
    print(f"原文档长度: {len(document['content'])} 字符")
    print(f"分块配置: {config}")

    splitter = CharacterSplitter(config)
    chunks = splitter.execute(document)

    print(f"生成块数: {len(chunks)}")
    print(f"平均块长: {sum(len(c) for c in chunks) / len(chunks):.1f} 字符")
    print(f"最小块长: {min(len(c) for c in chunks)} 字符")
    print(f"最大块长: {max(len(c) for c in chunks)} 字符")

    # 显示前几个块的内容
    print("\n前3个块的内容预览:")
    for i, chunk in enumerate(chunks[:3], 1):
        print(f"块{i}: {chunk[:100]}{'...' if len(chunk) > 100 else ''}")

    return chunks


# 调试示例
debug_config = {"chunk_size": 200, "overlap": 50}
debug_doc = {"content": "这是一个用于调试的示例文档..." * 20}
debug_chunks = debug_chunking_process(debug_doc, debug_config)
```

______________________________________________________________________

**总结**：文本分块是RAG系统的基础步骤，直接影响后续检索和生成的质量。选择合适的分块策略需要综合考虑文档特性、应用场景和性能要求。建议在实际应用中通过实验和评估来优化分块参数，以达到最佳效果。
"content": "这是第一句。这是第二句。这是第三句。" } chunks = sentence_splitter.execute(document)

# 结果：\['这是第一句', '这是第二句', '这是第三句'\]

````

#### 重叠机制说明

```python
# 演示重叠机制
config = {
    "chunk_size": 10,  # 每块10个字符
    "overlap": 3       # 重叠3个字符
}
splitter = CharacterSplitter(config)

document = {"content": "0123456789ABCDEFGHIJ"}
chunks = splitter.execute(document)

# 输出结果：
# 块1: 0123456789 (0-9)
# 块2: 789ABCDEFG (7-16)  # 与块1重叠3个字符(789)
# 块3: EFGHIJ     (16-21) # 与块2重叠3个字符(EFG)
````

### 2. SentenceTransformersTokenTextSplitter - Token分块器

这是一个基于Transformer模型的高级分块器，使用模型的tokenizer进行精确的token级分割。

#### 特性

- 基于预训练模型的tokenizer
- 精确的token计数
- 保持模型兼容性
- 支持多种Transformer模型

#### 依赖要求

```bash
pip install sentence-transformers transformers torch
```

#### 配置参数

```python
config = {
    "chunk": {
        "model_name": "sentence-transformers/all-mpnet-base-v2",  # 模型名称
        "chunk_size": 512,  # 每块的token数（默认512）
        "chunk_overlap": 50,  # 重叠token数（默认50）
    }
}
```

#### 基本使用

```python
from sage.libs.rag.chunk import SentenceTransformersTokenTextSplitter

# 配置
config = {
    "chunk": {
        "chunk_size": 128,
        "chunk_overlap": 20,
        "model_name": "sentence-transformers/all-mpnet-base-v2",
    }
}

# 初始化分块器（会自动下载模型）
splitter = SentenceTransformersTokenTextSplitter(config)

# 执行分块
text = (
    "This is a long document that needs to be split into smaller chunks for processing. "
    * 10
)
chunks = splitter.execute(text)

print(f"原文长度: {len(text)} 字符")
print(f"分块数量: {len(chunks)}")
for i, chunk in enumerate(chunks):
    print(f"块 {i+1}: {chunk[:60]}...")
```

#### 支持的模型

```python
# 常用模型配置
models = {
    # 英文模型
    "all-mpnet-base-v2": "sentence-transformers/all-mpnet-base-v2",
    "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
    # 中文模型
    "paraphrase-multilingual": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    # BERT系列
    "bert-base": "bert-base-uncased",
    "bert-chinese": "bert-base-chinese",
}

# 使用中文模型
config = {
    "chunk": {"model_name": "bert-base-chinese", "chunk_size": 256, "chunk_overlap": 32}
}
```

#### Token级分块详解

```python
# 演示token级分块的精确性
config = {
    "chunk": {
        "chunk_size": 8,  # 每块8个token
        "chunk_overlap": 2,  # 重叠2个token
        "model_name": "sentence-transformers/all-mpnet-base-v2",
    }
}

splitter = SentenceTransformersTokenTextSplitter(config)
text = "This is a test sentence to be split into smaller chunks."

chunks = splitter.execute(text)

# 可以看到详细的分块过程：
# Input IDs: [101, 2023, 2003, 1037, 3231, 6251, 2000, 2022, 3975, 2046, 3760, 9060, 1012, 102]
# Start Index: 0
# 块1: [CLS] This is a test sentence to [SEP]
# Start Index: 6  # 8-2=6 (chunk_size - overlap)
# 块2: sentence to be split into smaller
# ...
```

## 完整使用示例

### RAG文档处理流水线

```python
from sage.libs.rag.chunk import CharacterSplitter, SentenceTransformersTokenTextSplitter


class DocumentProcessor:
    def __init__(self, chunk_strategy="character"):
        if chunk_strategy == "character":
            self.splitter = CharacterSplitter(
                {"chunk_size": 1000, "overlap": 200, "separator": None}
            )
        elif chunk_strategy == "token":
            self.splitter = SentenceTransformersTokenTextSplitter(
                {
                    "chunk": {
                        "chunk_size": 512,
                        "chunk_overlap": 64,
                        "model_name": "sentence-transformers/all-mpnet-base-v2",
                    }
                }
            )

    def process_document(self, document):
        """处理单个文档"""
        if isinstance(document, dict):
            # CharacterSplitter格式
            chunks = self.splitter.execute(document)
            return [
                {
                    "content": chunk,
                    "metadata": document.get("metadata", {}),
                    "chunk_id": i,
                }
                for i, chunk in enumerate(chunks)
            ]
        else:
            # SentenceTransformersTokenTextSplitter格式
            chunks = self.splitter.execute(document)
            return [{"content": chunk, "chunk_id": i} for i, chunk in enumerate(chunks)]

    def process_multiple_documents(self, documents):
        """处理多个文档"""
        all_chunks = []
        for doc_id, document in enumerate(documents):
            chunks = self.process_document(document)
            for chunk in chunks:
                chunk["document_id"] = doc_id
                all_chunks.append(chunk)
        return all_chunks


# 使用示例
processor = DocumentProcessor("character")

documents = [
    {
        "content": "第一篇文档的内容..." * 100,
        "metadata": {"title": "文档1", "category": "技术"},
    },
    {
        "content": "第二篇文档的内容..." * 150,
        "metadata": {"title": "文档2", "category": "科学"},
    },
]

all_chunks = processor.process_multiple_documents(documents)
print(f"总共生成了 {len(all_chunks)} 个文档块")
```

### 自适应分块策略

```python
class AdaptiveChunker:
    def __init__(self):
        self.char_splitter = CharacterSplitter({"chunk_size": 1000, "overlap": 100})

        self.token_splitter = SentenceTransformersTokenTextSplitter(
            {
                "chunk": {
                    "chunk_size": 256,
                    "chunk_overlap": 32,
                    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                }
            }
        )

    def choose_strategy(self, text):
        """根据文本特征选择分块策略"""
        if len(text) < 1000:
            return "character"  # 短文本用字符分块
        elif any(lang in text for lang in ["中文", "日文", "한국어"]):
            return "character"  # 非英文用字符分块
        else:
            return "token"  # 长英文用token分块

    def adaptive_chunk(self, document):
        content = (
            document.get("content", "") if isinstance(document, dict) else document
        )
        strategy = self.choose_strategy(content)

        if strategy == "character":
            if isinstance(document, dict):
                return self.char_splitter.execute(document)
            else:
                doc_dict = {"content": document}
                return self.char_splitter.execute(doc_dict)
        else:
            if isinstance(document, dict):
                content = document["content"]
            else:
                content = document
            return self.token_splitter.execute(content)


# 使用自适应分块
chunker = AdaptiveChunker()

# 中文文档 - 使用字符分块
chinese_doc = {"content": "这是一篇中文文档" * 200}
chunks1 = chunker.adaptive_chunk(chinese_doc)

# 英文文档 - 使用token分块
english_text = "This is an English document " * 200
chunks2 = chunker.adaptive_chunk(english_text)
```

### 分块质量评估

```python
def evaluate_chunks(chunks, original_text):
    """评估分块质量"""
    stats = {
        "total_chunks": len(chunks),
        "avg_length": sum(len(chunk) for chunk in chunks) / len(chunks),
        "min_length": min(len(chunk) for chunk in chunks),
        "max_length": max(len(chunk) for chunk in chunks),
        "coverage": sum(len(chunk) for chunk in chunks) / len(original_text),
    }

    print("分块质量评估:")
    print(f"- 总块数: {stats['total_chunks']}")
    print(f"- 平均长度: {stats['avg_length']:.1f}")
    print(f"- 最短块: {stats['min_length']}")
    print(f"- 最长块: {stats['max_length']}")
    print(f"- 覆盖率: {stats['coverage']:.2%}")

    return stats


# 评估示例
text = "示例文本内容" * 1000
splitter = CharacterSplitter({"chunk_size": 200, "overlap": 50})
chunks = splitter.execute({"content": text})
evaluate_chunks(chunks, text)
```

## 配置建议

### 根据用途选择配置

#### 1. 问答系统

```python
# 短问答 - 精确匹配
qa_config = {"chunk_size": 256, "overlap": 32}

# 长问答 - 更多上下文
long_qa_config = {"chunk_size": 512, "overlap": 64}
```

#### 2. 摘要系统

```python
# 摘要 - 较大块保持完整性
summary_config = {"chunk_size": 1024, "overlap": 128}
```

#### 3. 代码文档

```python
# 代码 - 按函数/类分割
code_config = {
    "separator": "\n\nclass ",  # 按类分割
    "chunk_size": 2000,
    "overlap": 0,  # 代码通常不需要重叠
}
```

#### 4. 学术论文

```python
# 论文 - 按段落分割
paper_config = {"separator": "\n\n", "chunk_size": 800, "overlap": 100}  # 按段落分割
```
