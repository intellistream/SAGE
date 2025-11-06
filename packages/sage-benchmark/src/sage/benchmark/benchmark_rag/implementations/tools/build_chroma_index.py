#!/usr/bin/env python3
"""
知识库预加载脚本（SAGE多格式+工厂版）
支持 txt / pdf / md / docx 文件，
通过 LoaderFactory 动态选择 Loader，
使用 CharacterSplitter 分块，写入 ChromaDB。
"""

import os
import sys
from typing import TYPE_CHECKING, Any, Protocol, TypedDict, cast, overload

import chromadb
import numpy as np
from numpy.typing import NDArray

from sage.middleware.operators.rag import CharacterSplitter
from sage.middleware.operators.rag.document_loaders import LoaderFactory

if TYPE_CHECKING:
    from chromadb.api.types import Embeddings, Metadatas


class Document(TypedDict):
    """Document structure from LoaderFactory."""

    content: str
    metadata: dict[str, Any]


class ChunkDocument(TypedDict):
    """Structure for chunked document."""

    content: str
    metadata: dict[str, Any]


class Embedder(Protocol):
    """Protocol for embedder objects."""

    def encode(
        self, texts: list[str], convert_to_numpy: bool = True, **kwargs: Any
    ) -> NDArray[np.float32] | list[list[float]]:
        """Encode texts to embeddings."""
        ...


# 在测试模式下避免下载大型模型，提供轻量级嵌入器
def _get_embedder() -> Embedder:
    """Return an object with encode(texts)->embeddings.

    优先使用环境变量控制的测试模式，避免在CI/本地测试中下载大型模型。
    - 当 SAGE_EXAMPLES_MODE=test 时，返回一个简单的内置嵌入器（固定维度、小开销）。
    - 否则，使用 SentenceTransformer 加载真实模型。
    """
    import os

    if os.environ.get("SAGE_EXAMPLES_MODE") == "test":

        class _MiniEmbedder:
            """Mini embedder for testing."""

            def __init__(self, dim: int = 8) -> None:
                self.dim = dim

            def encode(
                self, texts: list[str], convert_to_numpy: bool = True, **kwargs: Any
            ) -> list[list[float]]:
                """生成确定性、低维的伪嵌入以便测试通过."""
                vecs: list[list[float]] = []
                for i, _text in enumerate(texts):
                    base = float((i % 5) + 1)
                    vecs.append([base / (j + 1) for j in range(self.dim)])
                return vecs

        embedder: Embedder = _MiniEmbedder(dim=8)
        return embedder

    # 正常模式：使用真实模型（如可选通过环境变量覆盖模型名）
    model_name = os.environ.get("SAGE_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    from sentence_transformers import SentenceTransformer

    model: Embedder = SentenceTransformer(model_name)  # type: ignore[assignment]
    return model


@overload
def _to_2dlist(arr: NDArray[np.float32]) -> list[list[float]]: ...


@overload
def _to_2dlist(arr: list[float]) -> list[list[float]]: ...


@overload
def _to_2dlist(arr: list[list[float]]) -> list[list[float]]: ...


def _to_2dlist(
    arr: NDArray[np.float32] | list[list[float]] | list[float],
) -> list[list[float]]:
    """Normalize embeddings to a 2D Python list.

    Accepts list, numpy array, torch tensor, etc., and returns List[List[float]].

    Args:
        arr: Input array (can be numpy array, list of floats, or list of lists)

    Returns:
        2D list of floats suitable for ChromaDB
    """
    # Handle numpy arrays first
    if isinstance(arr, np.ndarray):
        # Convert to Python list
        if arr.ndim == 1:
            # 1D array -> wrap to 2D
            return [arr.tolist()]
        elif arr.ndim == 2:
            # 2D array -> convert directly
            return arr.tolist()
        else:
            raise ValueError(f"Expected 1D or 2D array, got {arr.ndim}D")

    # At this point arr must be a list (either list[float] or list[list[float]])
    # Check if it's empty
    if not arr:
        return []

    # Check the type of the first element to determine structure
    first_elem = arr[0]

    # If first element is a number, this is a 1D list[float] -> wrap to 2D
    if isinstance(first_elem, (int, float, np.floating)):
        # We know arr is list[float] because first element is a number
        float_list: list[float] = arr  # type: ignore[assignment]
        return [float_list]

    # Otherwise, first element is a list/sequence
    # We know arr is list[list[float]]
    nested_list: list[list[float]] = arr  # type: ignore[assignment]
    # Ensure all inner elements are properly converted to float
    return [[float(x) for x in row] for row in nested_list]


def load_knowledge_to_chromadb() -> bool:
    """Load knowledge base to ChromaDB from multiple file formats.

    Returns:
        True if successful, False otherwise
    """
    # 配置参数
    data_dir = "./data/qa"  # 数据在共享的 data/qa 目录下
    persistence_path = "./chroma_multi_store"

    # 文件与集合对应关系
    files_and_collections: list[tuple[str, str]] = [
        (os.path.join(data_dir, "qa_knowledge_base.txt"), "txt_collection"),
        (os.path.join(data_dir, "qa_knowledge_base.pdf"), "pdf_collection"),
        (os.path.join(data_dir, "qa_knowledge_base.md"), "md_collection"),
        (os.path.join(data_dir, "qa_knowledge_base.docx"), "docx_collection"),
    ]

    print("=== 预加载多格式知识库到 ChromaDB ===")
    print(f"存储路径: {persistence_path}")

    # 初始化嵌入模型（在测试模式下不下载大模型）
    print("\n加载嵌入模型...")
    model = _get_embedder()

    # 初始化 ChromaDB
    print("初始化ChromaDB...")
    client = chromadb.PersistentClient(path=persistence_path)

    for file_path, collection_name in files_and_collections:
        if not os.path.exists(file_path):
            print(f"⚠ 文件不存在，跳过: {file_path}")
            continue

        print(f"\n=== 处理文件: {file_path} | 集合: {collection_name} ===")

        # 使用工厂类获取 loader
        # LoaderFactory.load returns dict with 'content' and 'metadata' keys
        raw_document = LoaderFactory.load(file_path)
        document: Document = {
            "content": str(raw_document.get("content", "")),
            "metadata": dict(raw_document.get("metadata", {})),
        }
        print(f"已加载文档，长度: {len(document['content'])}")

        # 分块
        splitter = CharacterSplitter({"separator": "\n\n"})
        raw_chunks = splitter.execute(raw_document)
        # Convert chunks to list of strings
        chunks: list[str] = [str(chunk) for chunk in raw_chunks]
        print(f"分块数: {len(chunks)}")

        chunk_docs: list[ChunkDocument] = [
            {
                "content": chunk,
                "metadata": {"chunk": idx + 1, "source": file_path},
            }
            for idx, chunk in enumerate(chunks)
        ]

        # 删除旧集合并创建新集合
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            pass

        index_type = "flat"  # 可选: "flat", "hnsw"
        collection = client.create_collection(
            name=collection_name, metadata={"index_type": index_type}
        )
        print(f"集合已创建，索引类型: {index_type}")

        # 嵌入与写入
        texts: list[str] = [doc["content"] for doc in chunk_docs]
        raw_embeddings = model.encode(texts, convert_to_numpy=True)
        embeddings = _to_2dlist(raw_embeddings)

        ids: list[str] = [f"{collection_name}_chunk_{i}" for i in range(len(chunk_docs))]
        metadatas: list[dict[str, str | int | float | bool]] = [
            {
                "chunk": doc["metadata"]["chunk"],
                "source": doc["metadata"]["source"],
            }
            for doc in chunk_docs
        ]

        # ChromaDB accepts List[List[float]] for embeddings
        # Cast to satisfy type checker - the types are compatible at runtime
        collection.add(
            embeddings=cast("Embeddings", embeddings),
            documents=texts,
            metadatas=cast("Metadatas", metadatas),
            ids=ids,
        )
        print(f"✓ 已添加 {len(chunk_docs)} 个文本块")
        print(f"✓ 数据库文档数: {collection.count()}")

        # 测试检索
        test_query = "什么是ChromaDB"
        raw_query_embedding = model.encode([test_query], convert_to_numpy=True)
        query_embedding = _to_2dlist(raw_query_embedding)

        results = collection.query(
            query_embeddings=cast("Embeddings", query_embedding), n_results=3
        )
        print(f"检索: {test_query}")

        if results and "documents" in results and results["documents"]:
            docs = results["documents"]
            # docs is List[List[Document]] where Document is str
            if len(docs) > 0:
                first_results = docs[0]
                for i, doc in enumerate(first_results):
                    print(f"  {i + 1}. {doc[:100]}...")

        print("=== 完成 ===")

    print("\n=== 所有文件已处理完成 ===")
    return True


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if load_knowledge_to_chromadb():
        print("知识库已成功加载，可运行检索/问答脚本")
    else:
        print("知识库加载失败")
        sys.exit(1)
