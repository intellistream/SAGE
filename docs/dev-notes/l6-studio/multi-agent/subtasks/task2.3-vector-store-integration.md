# Task 2.3: 向量存储集成

## 目标
集成向量数据库，实现文档的向量化存储和检索。

## 依赖
- Task 2.2 (DocumentLoader, DocumentChunk)

## 文件位置
`packages/sage-studio/src/sage/studio/services/vector_store.py`

## 提示词

```
请实现向量存储服务，封装 Embedding 生成和向量数据库操作。

## 背景
SAGE 已有以下组件可复用:
- sage.common.components.sage_embedding: Embedding 服务
- sage.middleware.components.sage_db: 向量数据库服务 (可选)
- 或使用 ChromaDB 作为轻量级方案

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/services/vector_store.py

2. 实现 VectorStore 类:
   ```python
   class VectorStore:
       def __init__(
           self,
           collection_name: str,
           embedding_model: str = "BAAI/bge-small-zh-v1.5",
           persist_dir: str | Path | None = None,
       ):
           pass

       async def add_documents(self, chunks: list[DocumentChunk]) -> int:
           """添加文档到向量库，返回添加数量"""
           pass

       async def search(
           self,
           query: str,
           top_k: int = 5,
           score_threshold: float = 0.5,
       ) -> list[SearchResult]:
           """语义检索"""
           pass

       async def delete_by_source(self, source_file: str) -> int:
           """删除指定来源的文档"""
           pass

       def get_stats(self) -> dict:
           """获取统计信息"""
           pass
   ```

3. Embedding 服务选择:
   - 优先使用 sage.common.components.sage_embedding
   - 备选: 直接使用 sentence-transformers
   - 支持本地模型和远程 API

4. 向量数据库选择:
   - 默认使用 ChromaDB (轻量、易部署)
   - 可选: Milvus (生产级、高性能)

## 代码模板
```python
from pathlib import Path
from typing import Any

# 尝试导入 SAGE 组件
try:
    from sage.common.components.sage_embedding import EmbeddingFactory
    SAGE_EMBEDDING_AVAILABLE = True
except ImportError:
    SAGE_EMBEDDING_AVAILABLE = False

# ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


class VectorStore:
    """向量存储服务"""

    def __init__(
        self,
        collection_name: str,
        embedding_model: str = "BAAI/bge-small-zh-v1.5",
        persist_dir: str | Path | None = None,
    ):
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.persist_dir = Path(persist_dir).expanduser() if persist_dir else None

        # 初始化 Embedding
        self._init_embedding()

        # 初始化向量数据库
        self._init_vector_db()

    def _init_embedding(self):
        if SAGE_EMBEDDING_AVAILABLE:
            self._embedder = EmbeddingFactory.create("hf", model=self.embedding_model)
        else:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.embedding_model)
            self._embedder = None

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if self._embedder:
            return [self._embedder.embed(t) for t in texts]
        return self._model.encode(texts).tolist()

    def _init_vector_db(self):
        if not CHROMA_AVAILABLE:
            raise ImportError("ChromaDB not installed. Run: pip install chromadb")

        settings = Settings(
            persist_directory=str(self.persist_dir) if self.persist_dir else None,
            anonymized_telemetry=False,
        )
        self._client = chromadb.Client(settings)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    async def add_documents(self, chunks: list[DocumentChunk]) -> int:
        if not chunks:
            return 0

        texts = [c.content for c in chunks]
        embeddings = self._embed(texts)

        ids = [f"{c.source_file}_{c.chunk_index}" for c in chunks]
        metadatas = [{"source": c.source_file, **c.metadata} for c in chunks]

        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        return len(chunks)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.5,
    ) -> list[SearchResult]:
        query_embedding = self._embed([query])[0]

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        search_results = []
        for i, doc in enumerate(results["documents"][0]):
            score = 1 - results["distances"][0][i]  # cosine distance -> similarity
            if score >= score_threshold:
                search_results.append(SearchResult(
                    content=doc,
                    score=score,
                    source=results["metadatas"][0][i].get("source", "unknown"),
                    metadata=results["metadatas"][0][i],
                ))
        return search_results
```

## 注意
- 使用 async/await 保持异步接口一致性
- 持久化目录使用 XDG 标准路径
- 批量操作时控制 batch size
```

## 验收标准
- [ ] Embedding 生成正常工作
- [ ] 文档可正确添加到向量库
- [ ] 语义检索返回相关结果
- [ ] 支持持久化和重新加载
