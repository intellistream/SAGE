#!/usr/bin/env python3
"""
知识库预加载脚本（SAGE多格式+工厂版）
支持 txt / pdf / md / docx 文件，
通过 LoaderFactory 动态选择 Loader，
使用 CharacterSplitter 分块，写入 ChromaDB。
"""
import os
import sys

import chromadb
from sage.libs.rag.chunk import CharacterSplitter
from sage.libs.rag.document_loaders import LoaderFactory


# 在测试模式下避免下载大型模型，提供轻量级嵌入器
def _get_embedder():
    """Return an object with encode(texts)->List[List[float]].

    优先使用环境变量控制的测试模式，避免在CI/本地测试中下载大型模型。
    - 当 SAGE_EXAMPLES_MODE=test 时，返回一个简单的内置嵌入器（固定维度、小开销）。
    - 否则，使用 SentenceTransformer 加载真实模型。
    """
    import os

    if os.environ.get("SAGE_EXAMPLES_MODE") == "test":

        class _MiniEmbedder:
            def __init__(self, dim: int = 8):
                self.dim = dim

            def encode(self, texts):
                # 生成确定性、低维的伪嵌入以便测试通过
                vecs = []
                for i, _ in enumerate(texts):
                    base = float((i % 5) + 1)
                    vecs.append([base / (j + 1) for j in range(self.dim)])
                return vecs

        return _MiniEmbedder(dim=8)

    # 正常模式：使用真实模型（如可选通过环境变量覆盖模型名）
    model_name = os.environ.get(
        "SAGE_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def _to_2dlist(arr):
    """Normalize embeddings to a 2D Python list.

    Accepts list, numpy array, torch tensor, etc., and returns List[List[float]].
    """
    # Fast path for objects that implement .tolist()
    try:
        lst = arr.tolist()
        # Ensure 2D
        if lst and isinstance(lst[0], (int, float)):
            return [list(lst)]
        return lst
    except AttributeError:
        pass

    # Handle plain Python lists
    if isinstance(arr, list):
        if not arr:
            return []
        # 1D -> wrap to 2D
        if not isinstance(arr[0], (list, tuple)):
            return [list(arr)]
        # 2D: ensure inner are lists
        return [list(x) for x in arr]

    # Best-effort: numpy arrays
    try:
        import numpy as np

        if isinstance(arr, np.ndarray):
            lst = arr.tolist()
            if lst and isinstance(lst[0], (int, float)):
                return [list(lst)]
            return lst
    except Exception:
        pass

    # Fallback: return as-is (may still work if already 2D-like)
    return arr


def load_knowledge_to_chromadb():
    # 配置参数
    data_dir = "./data"  # 现在数据在 rag/data 目录下
    persistence_path = "./chroma_multi_store"

    # 文件与集合对应关系
    files_and_collections = [
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
        document = LoaderFactory.load(file_path)
        print(f"已加载文档，长度: {len(document['content'])}")

        # 分块
        splitter = CharacterSplitter({"separator": "\n\n"})
        chunks = splitter.execute(document)
        print(f"分块数: {len(chunks)}")
        chunk_docs = [
            {"content": chunk, "metadata": {"chunk": idx + 1, "source": file_path}}
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
        texts = [c["content"] for c in chunk_docs]
        embeddings = _to_2dlist(model.encode(texts))
        ids = [f"{collection_name}_chunk_{i}" for i in range(len(chunk_docs))]
        metadatas = [c["metadata"] for c in chunk_docs]
        collection.add(
            embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids
        )
        print(f"✓ 已添加 {len(chunk_docs)} 个文本块")
        print(f"✓ 数据库文档数: {collection.count()}")

        # 测试检索
        test_query = "什么是ChromaDB"
        query_embedding = _to_2dlist(model.encode([test_query]))
        results = collection.query(query_embeddings=query_embedding, n_results=3)
        print(f"检索: {test_query}")
        for i, doc in enumerate(results["documents"][0]):
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
