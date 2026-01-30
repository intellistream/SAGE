# Adaptive-RAG 重构任务：从 Service 模式改为简单 VDB 模式

## 任务概述

将 Adaptive-RAG 实验中的向量检索方式从 **服务化模式（call_service）** 改为 **简单内嵌 VDB 模式**。数据路径已硬编码在代码中。

## 背景

当前实现使用 `self.call_service("embedding")` 和 `self.call_service("vector_db")`
进行向量检索，这种服务化方式在分布式环境下会带来额外复杂性。现在需要改为直接在算子内部使用简单的 FAISS VDB，类似于 `FiQAFAISSRetriever` 的实现方式。

## 涉及文件

所有文件位于：`packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments/common/`

### 需要修改的文件

1. **operators.py** - 主要修改

   - `SingleRetrievalStrategy` (line ~1690-1760)
   - `IterativeRetriever` (line ~1770-1830)

1. **pipeline.py** - 可能需要移除服务注册（如果 Adaptive-RAG 不再依赖服务）

## 数据路径（已硬编码）

```python
# operators.py line 640-641
FIQA_DATA_DIR = "/home/sage/data/FiQA-PL"
FIQA_INDEX_DIR = "/home/sage/data"

# 索引文件路径
INDEX_PATH = "/home/sage/data/fiqa_faiss.index"
DOCS_PATH = "/home/sage/data/fiqa_documents.jsonl"

# 语料库路径
CORPUS_PATH = "/home/sage/data/FiQA-PL/corpus/test-00000-of-00001.parquet"
```

## 具体修改任务

### 1. 修改 `SingleRetrievalStrategy` 类

**当前实现** (使用 call_service):

```python
class SingleRetrievalStrategy(MapFunction):
    def _retrieve_via_service(self, query: str) -> list[dict]:
        # RPC 调用
        query_embeddings = self.call_service("embedding", texts=[query])
        query_vec = np.array(query_embeddings[0], dtype=np.float32)
        results = self.call_service("vector_db", query_vec=query_vec, k=self.top_k)
        # ...
```

**目标实现** (直接使用 FAISS):

参考 `FiQAFAISSRetriever` 的实现模式：

```python
class SingleRetrievalStrategy(MapFunction):
    def __init__(self,
                 embedding_base_url: str = "http://11.11.11.7:8090/v1",
                 embedding_model: str = "BAAI/bge-large-en-v1.5",
                 index_dir: str = FIQA_INDEX_DIR,
                 llm_base_url: str = ...,
                 llm_model: str = ...,
                 max_tokens: int = 512,
                 top_k: int = 3,
                 **kwargs):
        super().__init__(**kwargs)
        self.embedding_base_url = embedding_base_url
        self.embedding_model = embedding_model
        self.index_dir = index_dir
        # ... 其他参数

        # 延迟初始化
        self._initialized = False
        self._faiss_index = None
        self._documents: list[dict] = []

    def _get_embeddings(self, texts: list[str]) -> list[list[float]] | None:
        """使用远程 embedding 服务获取向量"""
        return get_remote_embeddings(texts, self.embedding_base_url, self.embedding_model)

    def _initialize(self):
        """初始化 FAISS 索引 - 从持久化文件加载"""
        if self._initialized:
            return

        import json
        import faiss
        from pathlib import Path

        index_path = Path(self.index_dir) / "fiqa_faiss.index"
        docs_path = Path(self.index_dir) / "fiqa_documents.jsonl"

        if not index_path.exists() or not docs_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_path}")

        self._faiss_index = faiss.read_index(str(index_path))
        self._documents = []
        with open(docs_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self._documents.append(json.loads(line))

        print(f"[SingleRetrieval] Loaded FAISS index: {self._faiss_index.ntotal} vectors")
        self._initialized = True

    def _retrieve(self, query: str) -> list[dict]:
        """使用 FAISS 进行向量检索"""
        self._initialize()

        import numpy as np

        query_embeddings = self._get_embeddings([query])
        if not query_embeddings:
            return []

        query_vec = np.array(query_embeddings[0], dtype=np.float32)
        query_vec = query_vec / (np.linalg.norm(query_vec) + 1e-8)
        query_vec = query_vec.reshape(1, -1)

        scores, indices = self._faiss_index.search(query_vec, self.top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(self._documents):
                doc = self._documents[idx]
                results.append({
                    "id": doc.get("id", str(idx)),
                    "content": doc.get("text", doc.get("content", "")),
                    "score": float(score),
                })
        return results
```

### 2. 修改 `IterativeRetriever` 类

**当前实现**:

```python
class IterativeRetriever(MapFunction):
    def _retrieve_via_service(self, query: str) -> list[dict]:
        query_embeddings = self.call_service("embedding", texts=[query])
        results = self.call_service("vector_db", query_vec=query_vec, k=self.top_k)
```

**目标实现**: 与 `SingleRetrievalStrategy` 类似，添加：

- `embedding_base_url`, `embedding_model`, `index_dir` 参数
- `_faiss_index`, `_documents`, `_initialized` 状态
- `_initialize()` 方法加载 FAISS 索引
- `_retrieve()` 方法使用 FAISS 检索

### 3. 辅助函数

已存在的辅助函数可以复用：

```python
# operators.py line ~590-630
def get_remote_embeddings(texts: list[str], base_url: str, model: str) -> list[list[float]] | None:
    """从远程 embedding 服务获取向量"""

def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """计算余弦相似度"""
```

## 测试验证

修改完成后，运行以下命令验证：

```bash
cd /home/sage/SAGE

# 运行 Adaptive-RAG 测试
sage-dev project test --quick -k "adaptive"

# 或直接运行脚本
python packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments/pipelines/adaptive_rag/sage_dataflow_pipeline.py
```

## 注意事项

1. **FAISS 索引文件必须存在** - 如果索引不存在，需要先运行 FiQA pipeline 创建索引
1. **远程 embedding 服务仍然需要** - 只是 VDB 改为本地 FAISS，embedding 仍用远程服务
1. **保持 LLM 调用方式不变** - `_generate_via_service` 和 `_llm_call_via_service` 保持原样
1. **考虑 Ray 分布式序列化** - FAISS 索引在每个 worker 上延迟加载，避免序列化问题
1. **保留 `__module__` 设置** - 确保 Ray 序列化一致性（operators.py 末尾的 `_ADAPTIVE_RAG_CLASSES` 列表）

## 可选优化

1. 添加常量定义：

```python
# 在 FIQA_DATA_DIR, FIQA_INDEX_DIR 附近添加
ADAPTIVE_RAG_INDEX_DIR = FIQA_INDEX_DIR  # 与 FiQA 共用索引
```

2. 如果 Adaptive-RAG 完全不再使用服务，可以移除 `pipeline.py` 中相关的 `register_all_services` 调用

## 参考实现

查看 `FiQAFAISSRetriever` 类 (operators.py line ~745-920) 作为完整参考，该类已实现：

- 延迟初始化 FAISS 索引
- 索引持久化加载
- 远程 embedding + 本地 FAISS 检索
