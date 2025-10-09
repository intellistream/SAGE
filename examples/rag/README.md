
# SAGE RAG 示例项目说明

本目录包含一系列与 RAG（Retrieval-Augmented Generation，检索增强生成）相关的 Python 示例脚本，涵盖了密集检索、稀疏检索、混合检索、知识预加载、重排序、Refiner、无检索等典型场景，便于开发者快速理解和测试 SAGE 框架下的 RAG 能力。

## 🌟 新功能：多模态数据融合

### 🎯 多模态融合QA示例
`qa_multimodal_fusion.py` - 展示如何使用多模态数据融合功能进行问答系统

**核心特性：**
- **多模态检索**：同时处理文本和图像数据，支持联合搜索
- **动态融合策略**：可运行时切换不同的数据融合算法（加权平均、连接、注意力机制等）
- **智能权重配置**：可配置文本和图像的融合权重
- **完整QA流程**：从多模态查询到答案生成的完整流程

**快速开始：**
```bash
python qa_multimodal_fusion.py
```

**支持的融合策略：**
- `weighted_average`: 加权平均融合（推荐用于文本+图像）
- `concatenation`: 向量连接融合
- `attention_based`: 注意力机制融合
- `tensor_fusion`: 张量融合

详见：[多模态融合详细说明](README_multimodal_fusion.md)

## 目录结构

- `rag.py` / `rag_simple.py`：最基础的 RAG 流程示例，适合快速入门。
- `qa_multimodal_fusion.py`：**🆕 多模态数据融合QA示例**，支持文本+图像联合检索。
- `preload_knowledge.py`：知识库预加载脚本，演示如何将知识数据导入 ChromaDB。
- `qa_dense_retrieval.py`：密集向量检索示例，使用 embedding+ChromaDB 实现。
- `qa_dense_retrieval_chroma.py`：专门演示 ChromaDB 密集检索。
- `qa_dense_retrieval_mixed.py`：混合检索示例，结合密集和稀疏检索。
- `qa_dense_retrieval_ray.py`：分布式密集检索示例，基于 Ray。
- `qa_bm25_retrieval.py`：BM25 稀疏检索示例。
- `qa_hf_model.py`：调用 HuggingFace 模型进行问答。
- `qa_multiplex.py`：多路检索与融合示例。
- `qa_refiner.py`：Refiner（答案精炼）流程示例。
- `qa_rerank.py`：检索结果重排序示例。
- `qa_without_retrieval.py`：无检索直接问答示例。
- `README_multimodal_fusion.md`：多模态融合功能详细说明。
- `README.md`：本说明文件。
- `config/`：各脚本的配置文件目录。
- `chroma_qa_database/`：ChromaDB 数据库文件及相关数据。

## 快速开始

1. 安装依赖（建议使用 Python 3.11+，并提前安装好 chromadb、sentence-transformers 等依赖）：
	 ```bash
	 pip install -r requirements.txt
	 ```

2. 运行基础 RAG 示例：
	 ```bash
	 python rag_simple.py
	 # 或
	 python rag.py
	 ```

3. 运行其他脚本：
	 ```bash
	 python qa_dense_retrieval.py
	 python qa_bm25_retrieval.py
	 # ...
	 ```

## 典型脚本说明

- **rag_simple.py / rag.py**：
	- 演示最基础的检索增强生成流程，包括问题输入、知识检索、答案生成。

- **preload_knowledge.py**：
	- 用于将本地知识文本或 jsonl 文件批量导入 ChromaDB，便于后续检索。

- **qa_dense_retrieval.py / qa_dense_retrieval_chroma.py**：
	- 演示如何使用 embedding 模型和 ChromaDB 进行密集向量检索。

- **qa_bm25_retrieval.py**：
	- 演示 BM25 稀疏检索流程，适合文本检索场景。

- **qa_dense_retrieval_mixed.py**：
	- 演示密集与稀疏检索的混合使用。

- **qa_dense_retrieval_ray.py**：
	- 演示分布式密集检索，适合大规模知识库。

- **qa_hf_model.py**：
	- 演示如何调用 HuggingFace 的问答模型。

- **qa_multiplex.py**：
	- 演示多路检索与融合。

- **qa_refiner.py**：
	- 演示答案精炼流程。

- **qa_rerank.py**：
	- 演示检索结果重排序。

- **qa_without_retrieval.py**：
	- 演示无检索直接问答。

## 数据与配置

- `chroma_qa_database/` 目录下为 ChromaDB 的数据库文件和相关二进制数据。
- `config/` 目录下为各脚本的配置文件（如模型、数据库路径、参数等）。


## 如何创建和查询向量数据库（ChromaDB）

向量数据库用于存储文本的 embedding 向量，并支持高效的相似度检索。SAGE 示例主要采用 ChromaDB，本地运行，无需额外服务。

### 1. 数据加载与分块

可参考 `preload_knowledge.py` 或 `qa_dense_retrieval.py`：

```python
from sage.libs.utils.chroma import ChromaBackend
from sage.common.components.sage_embedding.embedding_model import EmbeddingModel

# 加载文本数据
with open('data/qa_knowledge_base.txt', 'r', encoding='utf-8') as f:
	documents = [line.strip() for line in f if line.strip()]

# 初始化 embedding 模型
embedding_model = EmbeddingModel(method="default", model="sentence-transformers/all-MiniLM-L6-v2")

# 生成 embedding 向量
embeddings = [embedding_model.embed(doc) for doc in documents]

# 初始化 ChromaDB 后端
chroma_backend = ChromaBackend(chroma_config, logger=None)

# 添加文档到向量库
doc_ids = [f"doc_{i}" for i in range(len(documents))]
chroma_backend.add_documents(documents, embeddings, doc_ids)
```

### 2. 相似度检索

可参考 `qa_dense_retrieval.py` 或 `qa_dense_retrieval_chroma.py`：

```python
query = "总统如何评价某某人物？"
query_embedding = embedding_model.embed(query)
query_vector = np.array(query_embedding, dtype=np.float32)

# 检索最相似的文档
top_k = 5
retrieved_docs = chroma_backend.search(query_vector, query, top_k)
for doc in retrieved_docs:
	print(doc)
```

### 3. 进阶用法

- 支持通过 embedding 向量直接检索（如 search_by_vector）。
- 支持异步检索（可用多线程/分布式 Ray 示例）。
- 支持多路检索、重排序、答案精炼等高级流程。

### 4. 相关脚本

- `preload_knowledge.py`：批量导入知识到 ChromaDB。
- `qa_dense_retrieval.py`：密集检索主流程。
- `qa_dense_retrieval_chroma.py`：专用 ChromaDB 检索。
- `qa_dense_retrieval_ray.py`：分布式检索。

### 5. 参考

- SAGE 官方文档：https://intellistream.github.io/SAGE-Pub/
- ChromaDB：https://www.trychroma.com/
- HuggingFace：https://huggingface.co/

如需进一步定制或有疑问，请查阅各脚本源码或联系项目维护者。
