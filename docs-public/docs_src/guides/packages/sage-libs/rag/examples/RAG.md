# RAG系统完整实现示例 (Complete RAG System Implementation)

本文档提供使用SAGE基于Chroma的RAG问答系统的完整实现示例。该示例展示了从数据准备到答案生成的端到端流程，是学习和理解RAG技术的最佳起点。

## 技术概述

### RAG系统简介
检索增强生成（Retrieval Augmented Generation, RAG）是一种结合检索和生成的AI技术架构，广泛应用于智能问答、知识管理和内容生成场景。

### 核心优势
- **知识实时性**：通过检索获取最新信息，避免训练数据时效性限制
- **答案可溯源**：每个答案都基于具体的知识来源，提供可验证性
- **资源效率**：无需重新训练大模型，通过检索机制扩展知识范围
- **领域适应性**：快速适配特定领域知识，支持垂直应用

## 系统架构

### 整体流程设计
RAG系统采用两阶段架构设计：1）知识库构建阶段；2）查询处理阶段。
1）知识库构建阶段：考虑到知识库构建阶段中创建与存储索引需要消耗大量资源与时间，SAGE提供了离线和在线两种知识库构建方式，以供用户依据自身知识库大小，选择合适的知识库构建方式。

2）查询处理阶段：用户提供流式数据，输入到基于SAGE搭建的pipline中，通过检索器和生成器等组件，得到最终输出。

```
[离线阶段/在线阶段] 知识库构建
 文档加载  → 文本分块 →  向量编码 →  索引存储
    ↓           ↓          ↓          ↓
TextLoader → Chunker → Embedding → VectorDB

[在线阶段] 查询处理  
  用户查询   →  向量检索 → 上下文组合 → 答案生成
     ↓            ↓          ↓           ↓
QueryVector → Retriever → Promptor → Generator
```


## 数据准备与索引构建

### 知识库数据格式

知识库输入文件格式 [knowledge_corpus.txt](https://github.com/intellistream/SAGE/blob/main/examples/data/qa_knowledge_base.txt)

SAGE可以通过.txt文件构建知识库，简要示例如下。
```python
"""
ChromaDB是一个开源的向量数据库，专门为AI应用设计。

SAGE是一个现代化的RAG框架，提供了完整的检索增强生成解决方案。

向量检索技术通过计算查询向量与文档向量的相似度来找到最相关的内容。

自然语言处理是人工智能的重要分支，专注于让计算机理解和生成人类语言。
"""
```
知识库查询数据格式 [qa_dataset.jsonl](https://github.com/intellistream/SAGE/blob/main/examples/data/queries.jsonl)

SAGE通过输入.jsonl文件格式模拟流式输入，简要示例如下。
```python
{"query": "什么是ChromaDB？", "expected_answer": "开源向量数据库"}
{"query": "SAGE框架有什么特点？", "expected_answer": "现代化RAG解决方案"}
{"query": "向量检索的工作原理是什么？", "expected_answer": "计算向量相似度"}
```

## RAG系统两阶段执行流程

RAG系统的运行分为两个独立且必需的阶段：**索引构建阶段**和**查询处理阶段**。必须先完成索引构建，才能执行查询处理。

### ⚠️ 重要提醒
在运行任何RAG查询之前，**必须先构建向量索引**。索引构建是一次性的离线或在线过程，完成后可以支持多次查询。

```
第一步：索引构建   →   第二步：查询处理
     ↓                    ↓
构建向量数据库     →   执行RAG流水线
```

## 阶段一：索引构建

### 索引构建的必要性

向量索引是RAG系统的基础设施，类似于传统数据库的索引。没有预先构建的索引，检索器将无法找到相关文档。

**索引构建过程**：
1. 加载原始知识文档；
2. 将文档分割成适合检索的小块；
3. 使用嵌入模型将文本块转换为向量；
4. 将向量存储到向量数据库中；
5. 建立高效的相似度搜索索引。


### 离线索引构建实现

离线索引构建不依赖流水线，需要独立执行索引构建流程。此方法尤其适用于数据量较大的情况下构建知识库。具体示例如下：

[代码实例如下](https://github.com/intellistream/SAGE/blob/main/examples/rag/build_chroma_index.py)

```python
def build_knowledge_index(config: dict) -> None:
    """
    阶段一：构建知识库向量索引（离线过程）
    
    该函数必须在RAG查询之前运行，用于构建可检索的向量索引
    
    Args:
        config: 包含knowledge_file和retriever配置的字典
    """
    print("=== 开始索引构建阶段 ===")
    
    # 1. 加载原始文档
    print("步骤1: 加载原始文档...")
    loader = TextLoader(config["retriever"]["chroma"]["knowledge_file"])
    document = loader.load()
    print(f"✓ 文档加载完成，内容长度: {len(document['content']):,} 字符")
    
    # 2. 文档分块处理
    print("步骤2: 文档分块处理...")
    splitter = CharacterSplitter({
        "separator": "\n\n",        # 按段落分割
        "chunk_size": 800,          # 块大小
        "overlap": 100              # 重叠大小
    })
    chunks = splitter.execute(document)
    print(f"✓ 文档分块完成，共生成 {len(chunks)} 个文档块")
    
    # 3. 构建向量索引
    print("步骤3: 构建向量索引...")
    print("  - 初始化嵌入模型...")
    print("  - 生成文档向量...")
    print("  - 建立索引结构...")
    
    # 初始化检索器会自动触发索引构建过程
    retriever = ChromaRetriever(config["retriever"])
    print("✓ 向量索引构建完成")
    
    # 4. 验证索引质量
    print("步骤4: 验证索引质量...")
    test_queries = [
        "什么是向量数据库？",
        "SAGE框架的特点",
        "如何使用ChromaDB"
    ]
    
    for i, test_query in enumerate(test_queries, 1):
        test_results = retriever.execute(test_query)
        if test_results['results']:
            print(f"✓ 测试查询{i}: '{test_query}' - 找到 {len(test_results['results'])} 个相关文档")
            print(f"  最佳匹配: {test_results['results'][0][:80]}...")
        else:
            print(f"⚠️ 测试查询{i}: '{test_query}' - 未找到相关文档")
    
    print("=== 索引构建阶段完成 ===")
    print(f"索引存储位置: {config['retriever']['chroma']['persist_path']}")
    print("现在可以执行RAG查询流水线了！\n")

# 执行索引构建（必须首先运行）
print("开始RAG系统部署...")
print("注意：首次运行时需要构建索引，这可能需要几分钟时间")
build_knowledge_index(rag_config)
```

### 在线索引构建实现

在线索引构建方法需要依赖RAG流水线，在配置文件中加入“knowledge_file: "./examples/data/qa_knowledge_base.txt"”字段，声明需要在RAG流水线中自动加载文件并创建数据库。如果未加上述字段，则说明流水线需要从数据库中加载离线知识库，如果未找到离线数据库，则返回空值。

## 阶段二：查询处理（在线过程）

### 查询处理流程说明

在向量索引构建完成后，就可以启动RAG查询处理流水线。该阶段处理用户的实际查询请求，生成最终答案。

**查询处理过程**：
1. 接收用户查询或批量查询数据
2. 在向量数据库中检索相关文档
3. 将查询和检索结果组装成提示词
4. 调用生成模型产生最终答案
5. 输出结构化的回答结果

### RAG流水线实现

[代码实例如下](https://github.com/intellistream/SAGE/blob/main/examples/rag/qa_dense_retrieval_chroma.py)

```python
def execute_rag_pipeline(config: dict) -> None:
    """
    阶段二：执行RAG查询处理流水线（在线过程）
    
    前提条件：必须已完成向量索引构建
    
    Args:
        config: 完整的RAG系统配置
    """
    print("=== 开始RAG查询处理阶段 ===")
    
    # 验证索引是否存在
    if not check_index_status(config):
        print("❌ 错误：未发现向量索引！")
        print("请先运行 build_knowledge_index() 构建索引")
        return
    
    print("✓ 索引验证通过，启动RAG流水线...")
    
    # 创建本地执行环境
    env = LocalEnvironment()
    
    # 构建处理流水线
    pipeline = (
        env
        .from_batch(JSONLBatch, config["source"])           # 数据源：用户查询
        .map(ChromaRetriever, config["retriever"])           # 检索：向量相似度搜索
        .map(QAPromptor, config["promptor"])                 # 提示：上下文组装
        .map(OpenAIGenerator, config["generator"]["vllm"])   # 生成：LLM答案生成
        .sink(TerminalSink, config["sink"])                  # 输出：结果展示
    )
    
    print("RAG流水线配置完成，开始处理查询...")
    
    # 提交执行
    env.submit()
    
    # 等待处理完成
    print("正在处理查询，请等待...")
    time.sleep(10)
    
    # 清理资源
    env.close()
    
    print("=== RAG查询处理完成 ===")
```

## 系统配置与运行

### 完整系统配置示例

推荐使用yaml文件配置pipeline各个算子，[配置实例如下](https://github.com/intellistream/SAGE/blob/main/examples/config/config_qa_chroma.yaml)

```python
# 完整的RAG系统配置
rag_config = {
    # 数据源配置
    "source": {
        "file_path": "data/qa_dataset.jsonl",     # 查询数据集路径
        "batch_size": 32,                        # 批处理大小
        "shuffle": False                         # 是否随机打乱
    },
    
    # 检索器配置
    "retriever": {
        "dimension": 384,                        # 向量维度
        "top_k": 5,                             # 检索文档数量
        "embedding": {
            "method": "default",
            "model": "sentence-transformers/all-MiniLM-L6-v2"
        },
        "chroma": {
            "persist_path": "./vector_database",     # 向量数据库路径
            "collection_name": "knowledge_base",     # 集合名称
            "knowledge_file": "data/knowledge_corpus.txt"  # 知识库文件
        }
    },
    
    # 提示词配置
    "promptor": {
        "template_type": "qa",                   # 问答模板类型
        "include_context": True,                 # 包含检索上下文
        "max_context_length": 2000              # 最大上下文长度
    },
    
    # 生成器配置
    "generator": {
        "vllm": {
            "method": "openai",                  # 生成方法
            "model_name": "gpt-4o-mini",        # 模型名称
            "base_url": "http://localhost:8000/v1",  # API服务地址
            "api_key": "your-api-key",          # API密钥
            "temperature": 0.7,                  # 生成温度
            "max_tokens": 512,                   # 最大生成token数
            "seed": 42                          # 随机种子
        }
    },
    
    # 输出配置
    "sink": {
        "format": "json",                       # 输出格式
        "show_metadata": True,                  # 显示元数据
        "save_to_file": "results/rag_output.jsonl"  # 保存文件路径
    }
}
```


## 高级功能扩展
### 使用HuggingFace本地模型

对于需要完全本地部署的场景，可以使用HuggingFace模型：

```python
def execute_rag_with_hf_model(config: dict) -> None:
    """
    使用HuggingFace本地模型的RAG流水线
    """
    print("=== 启动本地模型RAG流水线 ===")
    
    env = LocalEnvironment()
    pipeline = (
        env
        .from_batch(JSONLBatch, config["source"])
        .map(ChromaRetriever, config["retriever"])
        .map(BGEReranker, config["reranker"])
        .map(QAPromptor, config["promptor"])
        .map(HFGenerator, config["generator"]["hf"])    # 使用HF生成器
        .sink(TerminalSink, config["sink"])
    )
    
    env.submit()
    time.sleep(10)
    env.close()

# HuggingFace生成器配置
hf_config = {
    "model_name": "microsoft/DialoGPT-medium",
    "device": "cuda",
    "temperature": 0.8,
    "max_new_tokens": 256
}

# 添加HF配置
rag_config["generator"]["hf"] = hf_config
```

### 使用Rerank重排器

可以进一步使用Rerank进检索结果进行重排序，提高检索精度，这里以BGEReranker为例子进行说明。

核心流程如下，增加了BGEReranker算子：

```python
def pipeline_run(config: dict) -> None:
    env = LocalEnvironment()
    (
        env
        .from_batch(JSONLBatch, config["source"])
        .map(ChromaRetriever, config["retriever"])
        .map(BGEReranker, config["reranker"])  
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"]["vllm"])
        .sink(TerminalSink, config["sink"])
    )
    env.submit()
    time.sleep(10)
    env.close()
```

### 使用Refiner文档优化器

Refiner是基于LongRefiner技术的文档优化组件，能够智能压缩检索文档，在保持语义完整性的同时显著减少上下文长度。

核心流程如下，增加了LongRefinerAdapter算子：

```python
from sage.libs.rag.refiner import LongRefinerAdapter

def pipeline_with_refiner(config: dict) -> None:
    env = LocalEnvironment()
    (
        env
        .from_batch(JSONLBatch, config["source"])
        .map(ChromaRetriever, config["retriever"])
        .map(LongRefinerAdapter, config["refiner"])  # 添加文档优化
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"]["vllm"])
        .sink(TerminalSink, config["sink"])
    )
    env.submit()
    time.sleep(10)
    env.close()
```

配置示例：

```python
refiner_config = {
    "refiner": {
        "model_name": "long-refiner-base",
        "compression_ratio": 0.2,          # 压缩比例
        "enable_cache": True,              # 启用缓存
        "max_input_length": 8192
    }
}
```
### 配置参考

更多配置示例和详细文档：

- [检索器配置](../components/retriever.md)
- <!-- [重排序器配置](../components/BGE_RERANKER_GUIDE.md) -->
BGE重排器指南  
- [文档优化器配置](../components/refiner.md)
- <!-- [基础配置文件](../../config/config_qa_chroma.yaml) -->
Chroma配置文件

---

**注意**：本示例展示了SAGE框架下RAG系统的完整实现。